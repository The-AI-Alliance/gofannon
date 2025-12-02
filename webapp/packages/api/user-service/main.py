# webapp/packages/api/user-service/main.py
from fastapi import APIRouter, FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from datetime import datetime
import uuid
import json
import os
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

from config import settings
from config.routes_config import RouterConfig, resolve_router_configs
from dependencies import (
    deploy_agent,
    fetch_spec_content,
    get_agent_deployment,
    get_available_providers,
    get_db,
    get_logger,
    get_user_service_dep,
    list_deployments as list_deployments_logic,
    oauth2_scheme,
    process_chat,
    require_admin_access,
    run_deployed_agent as run_deployed_agent_logic,
    undeploy_agent,
    _execute_agent_code,
)
from models.agent import (
    GenerateCodeRequest,
    GenerateCodeResponse,
    RunCodeRequest,
    RunCodeResponse,
    Agent,
    CreateAgentRequest,
    Deployment,
    DeployedApi,
)
from models.demo import (
    GenerateDemoCodeRequest,
    GenerateDemoCodeResponse,
    CreateDemoAppRequest,
    DemoApp,
)
from models.user import User
from services.database_service import DatabaseService
from services.mcp_client_service import McpClientService, get_mcp_client_service
from services.observability_service import (
    get_observability_service,
    get_sanitized_request_data,
    ObservabilityMiddleware,
    ObservabilityService,
)
from services.user_service import UserService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger = get_observability_service()
    logger.log(
        level="INFO",
        event_type="lifecycle",
        message="Application startup complete."
    )
    yield


app = FastAPI(lifespan=lifespan)
router = APIRouter()

# Add observability middleware
app.add_middleware(ObservabilityMiddleware)



frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

allowed_origins = [frontend_url,]

print(f"Configured allowed CORS origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], # For local/docker, "*" is fine for dev
)

# --- Security Dependency ---
async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    """
    Dependency to verify Firebase ID token and get user info.
    Attaches the user object to request.state for observability.
    """
    if settings.APP_ENV != "firebase":
        # In non-firebase environments (like 'local'), skip authentication.
        user = {"uid": "local-dev-user"}
        request.state.user = user # Attach user to state
        return user

    if not token:
        # Set a default anonymous user for observability before raising
        request.state.user = {"uid": "anonymous"}
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        decoded_token = auth.verify_id_token(token)
        request.state.user = decoded_token # Attach user to state
        return decoded_token
    except auth.InvalidIdTokenError:
        request.state.user = {"uid": "invalid-token"}
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        request.state.user = {"uid": "auth-error"}
        raise HTTPException(status_code=500, detail=f"Authentication error: {e}")
 

class ListMcpToolsRequest(BaseModel):
    mcp_url: str
    auth_token: Optional[str] = None

class ClientLogPayload(BaseModel):
    eventType: str
    message: str
    level: str = "INFO"
    metadata: Optional[Dict[str, Any]] = None

class FetchSpecRequest(BaseModel):
    url: str


class UpdateMonthlyAllowanceRequest(BaseModel):
    monthly_allowance: float = Field(..., alias="monthlyAllowance")

    model_config = ConfigDict(populate_by_name=True)


class UpdateResetDateRequest(BaseModel):
    allowance_reset_date: float = Field(..., alias="allowanceResetDate")

    model_config = ConfigDict(populate_by_name=True)


class UpdateSpendRemainingRequest(BaseModel):
    spend_remaining: float = Field(..., alias="spendRemaining")

    model_config = ConfigDict(populate_by_name=True)


class AddUsageRequest(BaseModel):
    response_cost: float = Field(..., alias="responseCost")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class AdminUpdateUserRequest(BaseModel):
    monthly_allowance: Optional[float] = Field(default=None, alias="monthlyAllowance")
    allowance_reset_date: Optional[float] = Field(default=None, alias="allowanceResetDate")
    spend_remaining: Optional[float] = Field(default=None, alias="spendRemaining")

    model_config = ConfigDict(populate_by_name=True)

# Import models after defining local ones to avoid circular dependencies
from models.chat import ChatRequest, ChatMessage, ChatResponse, ProviderConfig, SessionData


# --- Routes ---
@router.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}

@router.post("/log/client", status_code=202)
async def log_client_event(
    payload: ClientLogPayload,
    request: Request,
    logger: ObservabilityService = Depends(get_logger)
):
    """Receives and logs an event from the frontend client."""
    user_id = getattr(request.state, 'user', {}).get('uid', 'anonymous')
    
    # Add client-specific info to metadata
    metadata = payload.metadata or {}
    metadata['client_host'] = request.client.host if request.client else "unknown"
    metadata['user_agent'] = request.headers.get("user-agent")

    logger.log(
        event_type=payload.eventType,
        message=payload.message,
        level=payload.level,
        service="webui",  # Explicitly set service to webui
        user_id=user_id,
        metadata=metadata
    )
    return {"status": "logged"}

@router.get("/providers")
def get_providers():
    """Get all available providers and their configurations"""
    return get_available_providers()

@router.get("/providers/{provider}")
def get_provider_config_route(provider: str):
    """Get configuration for a specific provider"""
    available_providers = get_available_providers()
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    return available_providers[provider]

@router.get("/providers/{provider}/models")
def get_provider_models(provider: str):
    """Get available models for a provider"""
    available_providers = get_available_providers()
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    return list(available_providers[provider]["models"].keys())

@router.get("/providers/{provider}/models/{model}")
def get_model_config(provider: str, model: str):
    """Get configuration for a specific model"""
    available_providers = get_available_providers()
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    if model not in available_providers[provider]["models"]:
        raise HTTPException(status_code=404, detail="Model not found")
    return available_providers[provider]["models"][model]


@router.get("/users/me", response_model=User)
def get_current_user_profile(user: dict = Depends(get_current_user), user_service: UserService = Depends(get_user_service_dep)):
    return user_service.get_user(user.get("uid", "anonymous"), user)


@router.get("/admin/users", response_model=List[User])
def list_all_users(
    user_service: UserService = Depends(get_user_service_dep),
    _: None = Depends(require_admin_access),
):
    return user_service.list_users()


@router.put("/admin/users/{user_id}", response_model=User)
def update_user_allowances(
    user_id: str,
    request: AdminUpdateUserRequest,
    user_service: UserService = Depends(get_user_service_dep),
    _: None = Depends(require_admin_access),
):
    return user_service.update_user_usage_info(
        user_id,
        monthly_allowance=request.monthly_allowance,
        allowance_reset_date=request.allowance_reset_date,
        spend_remaining=request.spend_remaining,
    )


@router.put("/users/me/monthly-allowance", response_model=User)
def set_monthly_allowance(
    request: UpdateMonthlyAllowanceRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.set_monthly_allowance(user.get("uid", "anonymous"), request.monthly_allowance, user)


@router.put("/users/me/allowance-reset-date", response_model=User)
def set_allowance_reset_date(
    request: UpdateResetDateRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.set_reset_date(user.get("uid", "anonymous"), request.allowance_reset_date, user)


@router.post("/users/me/reset-allowance", response_model=User)
def reset_allowance(user: dict = Depends(get_current_user), user_service: UserService = Depends(get_user_service_dep)):
    return user_service.reset_allowance(user.get("uid", "anonymous"), user)


@router.put("/users/me/spend-remaining", response_model=User)
def update_spend_remaining(
    request: UpdateSpendRemainingRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.update_spend_remaining(user.get("uid", "anonymous"), request.spend_remaining, user)


@router.post("/users/me/usage", response_model=User)
def add_usage_entry(
    request: AddUsageRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.add_usage(user.get("uid", "anonymous"), request.response_cost, request.metadata, user)

@router.post("/chat")
async def chat(request: ChatRequest, req: Request, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Submit a chat request and get a ticket ID"""
    ticket_id = str(uuid.uuid4())
    
    # Start processing in background, passing user context
    background_tasks.add_task(process_chat, ticket_id, request, user, req)
    
    return ChatResponse(
        ticket_id=ticket_id,
        status="pending"
    )

@router.get("/chat/{ticket_id}")
async def get_chat_status(ticket_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get the status and result of a chat request"""
    try:
        ticket_data = db.get("tickets", ticket_id)
        return ChatResponse(
            ticket_id=ticket_data.get("_id", ticket_id),
            status=ticket_data["status"],
            result=ticket_data.get("result"),
            error=ticket_data.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/config")
async def update_session_config(session_id: str, config: ProviderConfig, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Update session configuration"""
    try:
        session_doc = db.get("sessions", session_id)
    except HTTPException as e:
        if e.status_code == 404:
            session_doc = {"created_at": datetime.utcnow().isoformat()}
        else:
            raise

    session_doc["provider_config"] = config.dict()
    session_doc["updated_at"] = datetime.utcnow().isoformat()
    
    db.save("sessions", session_id, session_doc)
    return {"message": "Configuration updated", "session_id": session_id}

@router.get("/sessions/{session_id}/config")
async def get_session_config(session_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get session configuration"""
    session_doc = db.get("sessions", session_id)
    return session_doc.get("provider_config")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Delete a session"""
    db.delete("sessions", session_id)
    return {"message": "Session deleted"}

# Health check
@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-service"}


@router.post("/agents", response_model=Agent, status_code=201)
async def create_agent(
    request: CreateAgentRequest,
    req: Request,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Saves a new agent configuration to the database."""
    agent_data_internal_names = request.model_dump(by_alias=True)
    agent = Agent(**agent_data_internal_names)

    # Save the agent to the database.
    # Use by_alias=True to serialize the Agent model into a dictionary
    # with camelCase keys (e.g., inputSchema, swaggerSpecs, _id, _rev)
    # matching the common external representation and CouchDB's _id/_rev.
    saved_doc_data = agent.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("agents", agent.id, saved_doc_data)
    
    agent.rev = saved_doc.get("rev")
    
    logger.log(
        "INFO", "user_action", f"Agent '{agent.name}' created.",
        metadata={"agent_id": agent.id, "agent_name": agent.name, "request": get_sanitized_request_data(req)}
    )
    return agent

@router.get("/agents", response_model=List[Agent])
async def list_agents(
    req: Request,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Lists all saved agents."""
    all_docs = db.list_all("agents")
    logger.log("INFO", "user_action", "Listed all agents.", metadata={"request": get_sanitized_request_data(req)})
    return [Agent(**doc) for doc in all_docs]

@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific agent by its ID."""
    agent_doc = db.get("agents", agent_id)
    return Agent(**agent_doc)

@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str, 
    req: Request,
    db: DatabaseService = Depends(get_db), 
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Deletes an agent by its ID."""
    try:
        db.delete("agents", agent_id)
        logger.log("INFO", "user_action", f"Agent '{agent_id}' deleted.", metadata={"agent_id": agent_id, "request": get_sanitized_request_data(req)})
        return
    except HTTPException as e:
        raise e


@router.post("/mcp/tools")
async def list_mcp_tools(
    request: ListMcpToolsRequest,
    mcp_service: McpClientService = Depends(get_mcp_client_service),
    user: dict = Depends(get_current_user)
):
    """Connects to a remote MCP server and lists its available tools."""
    tools = await mcp_service.list_tools_for_server(request.mcp_url, request.auth_token)
    return {"mcp_url": request.mcp_url, "tools": tools}

@router.post("/agents/generate-code", response_model=GenerateCodeResponse)
async def generate_agent_code(request: GenerateCodeRequest, user: dict = Depends(get_current_user)):
    """Generates agent code based on the provided configuration."""
    from agent_factory import generate_agent_code as generate_code_function
    code = await generate_code_function(request)
    return code

@router.post("/specs/fetch")
async def fetch_spec_from_url(request: FetchSpecRequest, user: dict = Depends(get_current_user)):
    """Fetches OpenAPI/Swagger spec content from a public URL."""
    return await fetch_spec_content(request.url)


@router.post("/agents/{agent_id}/deploy", status_code=201)
async def deploy_agent_route(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Registers an agent for internal REST deployment."""
    return await deploy_agent(agent_id, db)

@router.delete("/agents/{agent_id}/undeploy", status_code=204)
async def undeploy_agent_route(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Removes an agent from the internal REST deployment registry."""
    await undeploy_agent(agent_id, db)
    return

@router.get("/agents/{agent_id}/deployment")
async def get_agent_deployment_route(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Checks if an agent is deployed and returns its public-facing name."""
    return await get_agent_deployment(agent_id, db)

@router.get("/deployments", response_model=List[DeployedApi])
async def list_deployments_route(db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Lists all deployed agents/APIs with their relevant details."""
    deployments = await list_deployments_logic(db)
    return [DeployedApi(**dep) for dep in deployments]

@router.post("/agents/run-code", response_model=RunCodeResponse)
async def run_agent_code(
    request: RunCodeRequest,
    req: Request,
    user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    logger: ObservabilityService = Depends(get_logger)
):
    """Executes agent code in a sandboxed environment."""
    logger.log("INFO", "user_action", "Attempting to run agent code in sandbox.", metadata={"request": get_sanitized_request_data(req)})
    try:
        result = await _execute_agent_code(
            code=request.code,
            input_dict=request.input_dict,
            tools=request.tools,
            gofannon_agents=request.gofannon_agents,
            db=db
        )

        logger.log("INFO", "sandbox_run", "Agent code executed successfully.", metadata={"request": get_sanitized_request_data(req)})
        return RunCodeResponse(result=result)
        
    except Exception as e:
        error_str = f"{type(e).__name__}: {e}"
        tb_str = traceback.format_exc()
        
        logger.log(
            "ERROR", "sandbox_run_failure", f"Error running agent code: {error_str}", 
            metadata={"traceback": tb_str, "request": get_sanitized_request_data(req)}
        )
        
        # The ObservabilityMiddleware will catch this and return a 500 response.
        # We re-raise it here so that middleware can do its job.
        raise e

@router.post("/rest/{friendly_name}")
async def run_deployed_agent_route(friendly_name: str, request: Request, db: DatabaseService = Depends(get_db)):
    """Public endpoint to run a deployed agent by its friendly_name."""
    input_dict = await request.json()
    return await run_deployed_agent_logic(friendly_name, input_dict, db)

# --- Demo App Endpoints ---

@router.post("/demos/generate-code", response_model=GenerateDemoCodeResponse)
async def generate_demo_app_code(request: GenerateDemoCodeRequest, user: dict = Depends(get_current_user)):
    """
    Generates HTML/CSS/JS for a demo app based on a prompt and selected APIs.
    """
    from agent_factory.demo_factory import generate_demo_code
    try:
        code_response = await generate_demo_code(request)
        return code_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating demo code: {e}")

@router.post("/demos", response_model=DemoApp, status_code=201)
async def create_demo_app(request: CreateDemoAppRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Saves a new demo app configuration."""
    demo_app_data = request.model_dump(by_alias=True)
    demo_app = DemoApp(**demo_app_data)
    saved_doc_data = demo_app.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("demos", demo_app.id, saved_doc_data)
    demo_app.rev = saved_doc.get("rev")
    return demo_app

@router.get("/demos", response_model=List[DemoApp])
async def list_demo_apps(db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Lists all saved demo apps."""
    all_docs = db.list_all("demos")
    return [DemoApp(**doc) for doc in all_docs]

@router.get("/demos/{demo_id}", response_model=DemoApp)
async def get_demo_app(demo_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific demo app."""
    doc = db.get("demos", demo_id)
    return DemoApp(**doc)

@router.put("/demos/{demo_id}", response_model=DemoApp)
async def update_demo_app(demo_id: str, request: CreateDemoAppRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Updates an existing demo app."""
    demo_app_data = request.model_dump(by_alias=True)
    updated_model = DemoApp(_id=demo_id, **demo_app_data)
    saved_doc_data = updated_model.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("demos", demo_id, saved_doc_data)
    updated_model.rev = saved_doc.get("rev")
    return updated_model

@router.delete("/demos/{demo_id}", status_code=204)
async def delete_demo_app(demo_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Deletes a demo app."""
    db.delete("demos", demo_id)
    return

# Apply router configuration to the FastAPI app, allowing extensions to provide routers.
for router_config in resolve_router_configs([RouterConfig(router=router)]):
    app.include_router(router_config.router, prefix=router_config.prefix, tags=router_config.tags or [])

# This is an unseemly hack to adapt FastAPI to Google Cloud Functions.
# TODO refactor all of this into microservices.
from a2wsgi import ASGIMiddleware

wsgi_app = ASGIMiddleware(app)

ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
ALLOWED_HEADERS_FALLBACK = "authorization,content-type"
MAX_AGE = "3600"

def build_cors_headers(req, *, origin_override=None):
    origin = origin_override or req.headers.get("origin") or frontend_url or "*"
    req_headers = req.headers.get("access-control-request-headers", "")
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": ALLOWED_METHODS,
        "access-control-allow-headers": req_headers or ALLOWED_HEADERS_FALLBACK,
        "access-control-max-age": MAX_AGE,
        # Vary ensures proper caching when Origin / ACR* differ
        "vary": "Origin, Access-Control-Request-Method, Access-Control-Request-Headers",
        # Uncomment if you use cookies/Authorization with browsers:
        # "access-control-allow-credentials": "true",
    }

