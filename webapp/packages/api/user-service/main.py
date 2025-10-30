# webapp/packages/api/user-service/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import json
import os
from pathlib import Path
import asyncio
import litellm
import traceback
import httpx
import firebase_admin
import yaml
from firebase_admin import credentials, auth
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from services.database_service import get_database_service, DatabaseService
from config import settings
from services.mcp_client_service import McpClientService, get_mcp_client_service

from services.observability_service import (
    get_observability_service,
    ObservabilityMiddleware,
    ObservabilityService,
    get_sanitized_request_data
)

from services.llm_service import call_llm

# Import the shared provider configuration
from config.provider_config import PROVIDER_CONFIG as APP_PROVIDER_CONFIG
from models.agent import (
    GenerateCodeRequest, GenerateCodeResponse, RunCodeRequest, 
    RunCodeResponse, Agent, CreateAgentRequest, Deployment, DeployedApi
)
from models.demo import (
    GenerateDemoCodeRequest, GenerateDemoCodeResponse,
    CreateDemoAppRequest, DemoApp
)

from agent_factory.remote_mcp_client import RemoteMCPClient


# --- Firebase Admin SDK Initialization ---
if settings.APP_ENV == "firebase":
    try:
        # In a Cloud Function environment, GOOGLE_APPLICATION_CREDENTIALS is set automatically.
        # For local emulation, you'd need to set this env var to your service account key file.
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")

app = FastAPI()

# Add observability middleware
app.add_middleware(ObservabilityMiddleware)

@app.on_event("startup")
async def startup_event():
    """Log application startup event."""
    logger = get_observability_service()
    logger.log(
        level="INFO",
        event_type="lifecycle",
        message="Application startup complete."
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)



frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

allowed_origins = [frontend_url,]

print(f"Configured allowed CORS origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

# Import models after defining local ones to avoid circular dependencies
from models.chat import ChatRequest, ChatMessage, ChatResponse, ProviderConfig, SessionData


# --- Dependencies ---
def get_db() -> DatabaseService:
    yield get_database_service(settings)

def get_logger() -> ObservabilityService:
    """Dependency to get the observability service instance."""
    return get_observability_service()

# Background task for LLM processing
async def process_chat(ticket_id: str, request: ChatRequest, user: dict, req: Request):
    # Background tasks don't have access to dependency injection, so we get service instances directly
    db_service = get_database_service(settings)
    logger = get_observability_service()
    try:
        # Update ticket status
        ticket_data = {
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(), # Use isoformat for JSON serialization
            "request": request.dict(by_alias=True)
        }
        db_service.save("tickets", ticket_id, ticket_data)
        
        # Convert messages to format expected by litellm
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Build tools list from config
        built_in_tools = []
        model_tool_config = APP_PROVIDER_CONFIG.get(request.provider, {}).get("models", {}).get(request.model, {}).get("built_in_tools", [])
        if request.built_in_tools:
            for tool_id in request.built_in_tools:
                tool_conf = next((t for t in model_tool_config if t["id"] == tool_id), None)
                if tool_conf:
                    built_in_tools.append(tool_conf["tool_config"])


        logger.log("INFO", "llm_request", f"Initiating LLM call to {request.provider}/{request.model}", metadata={"request": get_sanitized_request_data(req)})

        content, thoughts = await call_llm(
            provider=request.provider,
            model=request.model,
            messages=messages,
            parameters=request.parameters,
            tools=built_in_tools if built_in_tools else None
        )
        
        # Update ticket with success
        ticket_data.update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "result": {
                "content": content,
                "thoughts": thoughts,
                "model": f"{request.provider}/{request.model}",
                # Usage data is not consistently available across both litellm APIs, so omitting for now
            }
        })
        db_service.save("tickets", ticket_id, ticket_data)
        
    except Exception as e:
        logger.log("ERROR", "background_task_failure", f"Chat processing failed for ticket {ticket_id}: {e}", metadata={"traceback": traceback.format_exc(), "request": get_sanitized_request_data(req)})
        # Update ticket with error
        ticket_data.update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e)
        })
        db_service.save("tickets", ticket_id, ticket_data)

# Helper function to filter providers based on environment variables
def get_available_providers():
    available_providers = {}
    for provider, config in APP_PROVIDER_CONFIG.items():
        api_key_env_var = config.get("api_key_env_var")
        # Include provider if api_key_env_var is not specified, or if it is specified and the env var is set.
        if not api_key_env_var or os.getenv(api_key_env_var):
            available_providers[provider] = config
    return available_providers

# --- Routes ---
@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}

@app.post("/log/client", status_code=202)
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

@app.get("/providers")
def get_providers():
    """Get all available providers and their configurations"""
    return get_available_providers()

@app.get("/providers/{provider}")
def get_provider_config_route(provider: str):
    """Get configuration for a specific provider"""
    available_providers = get_available_providers()
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    return available_providers[provider]

@app.get("/providers/{provider}/models")
def get_provider_models(provider: str):
    """Get available models for a provider"""
    available_providers = get_available_providers()
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    return list(available_providers[provider]["models"].keys())

@app.get("/providers/{provider}/models/{model}")
def get_model_config(provider: str, model: str):
    """Get configuration for a specific model"""
    available_providers = get_available_providers()
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    if model not in available_providers[provider]["models"]:
        raise HTTPException(status_code=404, detail="Model not found")
    return available_providers[provider]["models"][model]

@app.post("/chat")
async def chat(request: ChatRequest, req: Request, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Submit a chat request and get a ticket ID"""
    ticket_id = str(uuid.uuid4())
    
    # Start processing in background, passing user context
    background_tasks.add_task(process_chat, ticket_id, request, user, req)
    
    return ChatResponse(
        ticket_id=ticket_id,
        status="pending"
    )

@app.get("/chat/{ticket_id}")
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

@app.post("/sessions/{session_id}/config")
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

@app.get("/sessions/{session_id}/config")
async def get_session_config(session_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get session configuration"""
    session_doc = db.get("sessions", session_id)
    return session_doc.get("provider_config")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Delete a session"""
    db.delete("sessions", session_id)
    return {"message": "Session deleted"}

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-service"}


@app.post("/agents", response_model=Agent, status_code=201)
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

@app.get("/agents", response_model=List[Agent])
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

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific agent by its ID."""
    agent_doc = db.get("agents", agent_id)
    return Agent(**agent_doc)

@app.delete("/agents/{agent_id}", status_code=204)
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


@app.post("/mcp/tools")
async def list_mcp_tools(
    request: ListMcpToolsRequest,
    mcp_service: McpClientService = Depends(get_mcp_client_service),
    user: dict = Depends(get_current_user)
):
    """Connects to a remote MCP server and lists its available tools."""
    tools = await mcp_service.list_tools_for_server(request.mcp_url, request.auth_token)
    return {"mcp_url": request.mcp_url, "tools": tools}

@app.post("/agents/generate-code", response_model=GenerateCodeResponse)
async def generate_agent_code(request: GenerateCodeRequest, user: dict = Depends(get_current_user)):
    """Generates agent code based on the provided configuration."""
    from agent_factory import generate_agent_code as generate_code_function
    code = await generate_code_function(request)
    return code

@app.post("/specs/fetch")
async def fetch_spec_from_url(request: FetchSpecRequest, user: dict = Depends(get_current_user)):
    """Fetches OpenAPI/Swagger spec content from a public URL."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(request.url)
            response.raise_for_status() # Raises an exception for 4xx/5xx responses
            
            # Basic validation: Try to parse as JSON or YAML
            content = response.text
            try:
                json.loads(content)
            except json.JSONDecodeError:
                try:
                    yaml.safe_load(content)
                except yaml.YAMLError:
                    raise HTTPException(status_code=400, detail="Content from URL is not valid JSON or YAML.")

            # Create a name from the URL path
            from urllib.parse import urlparse
            path = urlparse(str(request.url)).path
            name = path.split('/')[-1] if path else "spec_from_url.json"
            if not name:
                name = "spec_from_url.json"

            return {"name": name, "content": content}
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=f"Error fetching from URL: {e}")


@app.post("/agents/{agent_id}/deploy", status_code=201)
async def deploy_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Registers an agent for internal REST deployment."""
    agent_doc = db.get("agents", agent_id)
    agent = Agent(**agent_doc)
    friendly_name = agent.friendly_name

    if not friendly_name:
        raise HTTPException(status_code=400, detail="Agent must have a friendly_name to be deployed.")

    try:
        # Check if a deployment with this name already exists
        existing_deployment = db.get("deployments", friendly_name)
        # If it exists and belongs to this agent, it's already deployed
        if existing_deployment.get("agentId") == agent_id:
            return {"message": "Agent is already deployed", "endpoint": f"/rest/{friendly_name}"}
        else:
            # Another agent is using this friendly_name
            raise HTTPException(status_code=409, detail=f"A deployment with the name '{friendly_name}' already exists for a different agent.")
    except HTTPException as e:
        if e.status_code == 404:
            # No existing deployment, proceed to create one
            deployment_doc = {"agentId": agent_id}
            db.save("deployments", friendly_name, deployment_doc)
            return {"message": "Agent deployed successfully", "endpoint": f"/rest/{friendly_name}"}
        else:
            raise e

@app.delete("/agents/{agent_id}/undeploy", status_code=204)
async def undeploy_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Removes an agent from the internal REST deployment registry."""
    agent_doc = db.get("agents", agent_id)
    agent = Agent(**agent_doc)
    friendly_name = agent.friendly_name
    if not friendly_name:
        # Agent doesn't have a friendly name, so it can't be deployed. Nothing to do.
        return

    try:
        # This will raise 404 if not found, which we can ignore.
        db.delete("deployments", friendly_name)
    except HTTPException as e:
        if e.status_code == 404:
            pass # It wasn't deployed, so the goal is achieved.
        else:
            raise e # Re-raise other errors
    return

@app.get("/agents/{agent_id}/deployment")
async def get_agent_deployment(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Checks if an agent is deployed and returns its public-facing name."""
    agent_doc = db.get("agents", agent_id)
    agent = Agent(**agent_doc)
    friendly_name = agent.friendly_name

    if not friendly_name:
        return {"is_deployed": False}

    try:
        deployment_doc = db.get("deployments", friendly_name)
        # Ensure the deployment record points back to this agent_id
        if deployment_doc.get("agentId") == agent_id:
            return {"is_deployed": True, "friendly_name": friendly_name}
        else:
            # A different agent is using this friendly_name, so this one is not deployed.
            return {"is_deployed": False}
    except HTTPException as e:
        if e.status_code == 404:
            return {"is_deployed": False}
        raise e

@app.get("/deployments", response_model=List[DeployedApi])
async def list_deployments(db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Lists all deployed agents/APIs with their relevant details."""
    try:
        all_deployments_docs = db.list_all("deployments")
        deployment_infos = []
        for dep_doc in all_deployments_docs:
            try:
                agent_doc = db.get("agents", dep_doc["agentId"])
                agent = Agent(**agent_doc)
                dep_info = DeployedApi(
                    friendlyName=dep_doc["_id"],
                    agentId=dep_doc["agentId"],
                    description=agent.description,
                    inputSchema=agent.input_schema,
                    outputSchema=agent.output_schema
                )
                deployment_infos.append(dep_info)
            except Exception as e:
                print(f"Skipping deployment '{dep_doc['_id']}' due to error fetching agent '{dep_doc['agentId']}': {e}")
                continue
        return deployment_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _execute_agent_code(code: str, input_dict: dict, tools: dict, gofannon_agents: List[str], db: DatabaseService):
    """Helper function for recursive execution of agent code."""
    
    class GofannonClient:
        def __init__(self, agent_ids: List[str], db_service: DatabaseService):
            self.db = db_service
            self.agent_map = {}
            if agent_ids:
                try:
                    all_agents = [Agent(**self.db.get("agents", agent_id)) for agent_id in agent_ids]
                    for agent in all_agents:
                        self.agent_map[agent.name] = agent
                except Exception as e:
                    print(f"Error loading dependent agents: {e}")
                    raise ValueError("Could not load one or more dependent Gofannon agents.")

        async def call(self, agent_name: str, input_dict: dict) -> Any:
            agent_to_run = self.agent_map.get(agent_name)
            if not agent_to_run:
                raise ValueError(f"Gofannon agent '{agent_name}' not found or not imported for this run.")

            # Recursive call to the execution helper
            return await _execute_agent_code(
                code=agent_to_run.code,
                input_dict=input_dict,
                tools=agent_to_run.tools,
                gofannon_agents=agent_to_run.gofannon_agents,
                db=self.db
            )

    exec_globals = {
        "RemoteMCPClient": RemoteMCPClient,
        "litellm": litellm,
        "asyncio": asyncio,
        "http_client": httpx.AsyncClient(),
        "gofannon_client": GofannonClient(gofannon_agents, db),
        "__builtins__": __builtins__
    }
    
    local_scope = {}
    
    code_obj = compile(code, '<string>', 'exec')
    exec(code_obj, exec_globals, local_scope)

    run_function = local_scope.get('run')

    if not run_function or not asyncio.iscoroutinefunction(run_function):
        raise ValueError("Code did not define an 'async def run(input_dict, tools)' function.")

    result = await run_function(input_dict=input_dict, tools=tools)
    return result

@app.post("/agents/run-code", response_model=RunCodeResponse)
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

@app.post("/rest/{friendly_name}")
async def run_deployed_agent(friendly_name: str, request: Request, db: DatabaseService = Depends(get_db)):
    """Public endpoint to run a deployed agent by its friendly_name."""
    try:
        # 1. Find the deployment record by its friendly_name
        deployment_doc = db.get("deployments", friendly_name)
        agent_id = deployment_doc["agentId"]

        # 2. Fetch the full agent configuration
        agent_data = db.get("agents", agent_id)
        agent = Agent(**agent_data)
        
        input_dict = await request.json()

        # 3. Execute the agent's code
        result = await _execute_agent_code(
            code=agent.code,
            input_dict=input_dict,
            tools=agent.tools,
            gofannon_agents=agent.gofannon_agents,
            db=db
        )
        return result
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="No deployed agent found with that name.")
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")

# --- Demo App Endpoints ---

@app.post("/demos/generate-code", response_model=GenerateDemoCodeResponse)
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

@app.post("/demos", response_model=DemoApp, status_code=201)
async def create_demo_app(request: CreateDemoAppRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Saves a new demo app configuration."""
    demo_app_data = request.model_dump(by_alias=True)
    demo_app = DemoApp(**demo_app_data)
    saved_doc_data = demo_app.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("demos", demo_app.id, saved_doc_data)
    demo_app.rev = saved_doc.get("rev")
    return demo_app

@app.get("/demos", response_model=List[DemoApp])
async def list_demo_apps(db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Lists all saved demo apps."""
    all_docs = db.list_all("demos")
    return [DemoApp(**doc) for doc in all_docs]

@app.get("/demos/{demo_id}", response_model=DemoApp)
async def get_demo_app(demo_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific demo app."""
    doc = db.get("demos", demo_id)
    return DemoApp(**doc)

@app.put("/demos/{demo_id}", response_model=DemoApp)
async def update_demo_app(demo_id: str, request: CreateDemoAppRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Updates an existing demo app."""
    demo_app_data = request.model_dump(by_alias=True)
    updated_model = DemoApp(_id=demo_id, **demo_app_data)
    saved_doc_data = updated_model.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("demos", demo_id, saved_doc_data)
    updated_model.rev = saved_doc.get("rev")
    return updated_model

@app.delete("/demos/{demo_id}", status_code=204)
async def delete_demo_app(demo_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Deletes a demo app."""
    db.delete("demos", demo_id)
    return 

# This is an unseemly hack to adapt FastAPI to Google Cloud Functions.
# TODO refactor all of this into microservices.
from firebase_functions import https_fn, options
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

@https_fn.on_request(memory=2048, timeout_sec=540)
def api(req: https_fn.Request):
    """
    An HTTPS Cloud Function that wraps the FastAPI application.
    Handles CORS preflight (OPTIONS) and routes other requests to FastAPI.
    """

    # 1) Handle CORS preflight immediately
    if req.method == "OPTIONS":
        return https_fn.Response("", status=204, headers=build_cors_headers(req))

    # 2) Run the ASGI app for non-OPTIONS requests
    response_headers = []
    response_body = b""
    status_code = 200  # default; will be set from ASGI start message

    async def send(message):
        nonlocal response_headers, response_body, status_code
        if message["type"] == "http.response.start":
            status_code = int(message.get("status", 200))
            response_headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            response_body += message.get("body", b"")

    async def receive():
        return {
            "type": "http.request",
            "body": req.data or b"",
            "more_body": False
        }

    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # ASGI expects bytes for headers and query_string.
    asgi_headers = []
    for k, v in req.headers.items():
        asgi_headers.append((k.lower().encode("latin-1"), str(v).encode("latin-1")))

    query_string = (req.query_string or "").encode("latin-1")

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": req.method,
        "scheme": req.scheme or "https",
        "path": req.path or "/",
        "raw_path": (req.path or "/").encode("latin-1"),
        "query_string": query_string,
        "headers": asgi_headers,
        "client": (req.remote_addr, 0),
        "server": ("gcf", 80),
    }

    try:
        loop.run_until_complete(app(scope, receive, send))
    finally:
        loop.close()

    # 3) Add CORS headers to the final response as well
    cors_headers = build_cors_headers(req)
    response_headers.extend([(k.encode(), v.encode()) for k, v in cors_headers.items()])

    # Convert to str headers for firebase-functions Response
    final_headers = {h.decode("latin-1"): v.decode("latin-1") for h, v in response_headers}

    print(f"Response status: {status_code}, headers: {final_headers}")
    return https_fn.Response(response_body, status=status_code, headers=final_headers)
