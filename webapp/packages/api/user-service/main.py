# webapp/packages/api/user-service/main.py
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
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
from firebase_admin import credentials, auth
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from services.database_service import get_database_service, DatabaseService
from config import settings
from services.mcp_client_service import McpClientService, get_mcp_client_service

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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Import the shared provider configuration
from config.provider_config import PROVIDER_CONFIG as APP_PROVIDER_CONFIG
from models.agent import GenerateCodeRequest, GenerateCodeResponse, RunCodeRequest, RunCodeResponse, Agent, CreateAgentRequest
from agent_factory.remote_mcp_client import RemoteMCPClient

app = FastAPI()

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
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to verify Firebase ID token and get user info."""
    if settings.APP_ENV != "firebase":
        # In non-firebase environments (like 'local'), skip authentication.
        return {"uid": "local-dev-user"}

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {e}")
 

# Models
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    parameters: Dict[str, Any] = {}
    stream: bool = False


class ListMcpToolsRequest(BaseModel):
    mcp_url: str
    auth_token: Optional[str] = None


# Import models after defining local ones to avoid circular dependencies
from models.chat import ChatResponse, ProviderConfig, SessionData


# Database service dependency
def get_db() -> DatabaseService:
    yield get_database_service(settings)


# Background task for LLM processing
async def process_chat(ticket_id: str, request: ChatRequest):
    # Background tasks don't have access to dependency injection, so we get a service instance directly
    db_service = get_database_service(settings)
    try:
        # Update ticket status
        ticket_data = {
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(), # Use isoformat for JSON serialization
            "request": request.dict()
        }
        db_service.save("tickets", ticket_id, ticket_data)
        
        # Convert messages to format expected by litellm
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Prepare litellm parameters
        # Adjust model name for non-OpenAI providers if needed by litellm,
        # otherwise litellm typically handles "provider/model" format automatically.
        # The frontend sends "openai" as provider, "gpt-3.5-turbo" as model, which litellm handles directly.
        # For others, it will be "anthropic/claude-3-opus", "ollama/llama2".
        model_name = f"{request.provider}/{request.model}" if request.provider not in ["openai", "azure"] else request.model
        
        response = await litellm.acompletion(
            model=model_name,
            messages=messages,
            **request.parameters
        )
        
        # Update ticket with success
        ticket_data.update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "result": {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }
        })
        db_service.save("tickets", ticket_id, ticket_data)
        
    except Exception as e:
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

# Routes
@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}

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
async def chat(request: ChatRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Submit a chat request and get a ticket ID"""
    ticket_id = str(uuid.uuid4())
    
    # Start processing in background
    background_tasks.add_task(process_chat, ticket_id, request)
    
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
async def create_agent(request: CreateAgentRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Saves a new agent configuration to the database."""
    # Instantiate Agent model from CreateAgentRequest data.
    # Convert request data to a dictionary using internal field names (snake_case)
    # for robust instantiation of the Agent model.
    agent_data_internal_names = request.model_dump(by_alias=True)
    agent = Agent(**agent_data_internal_names)

    # Save the agent to the database.
    # Use by_alias=True to serialize the Agent model into a dictionary
    # with camelCase keys (e.g., inputSchema, swaggerSpecs, _id, _rev)
    # matching the common external representation and CouchDB's _id/_rev.
    saved_doc_data = agent.model_dump(by_alias=True)
    saved_doc = db.save("agents", agent.id, saved_doc_data)
    
    agent.rev = saved_doc.get("rev") # Add revision from DB response
    return agent

@app.get("/agents", response_model=List[Agent])
async def list_agents(db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Lists all saved agents."""
    # This simple query returns all documents. A more advanced implementation
    # might use views for sorting or filtering.
    all_docs = db.list_all("agents")
    return [Agent(**doc) for doc in all_docs]
    # return all_docs

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific agent by its ID."""
    agent_doc = db.get("agents", agent_id)
    return Agent(**agent_doc)

@app.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Deletes an agent by its ID."""
    try:
        db.delete("agents", agent_id)
        return
    except HTTPException as e:
        raise e

@app.post("/mcp/tools")
async def list_mcp_tools(
    request: ListMcpToolsRequest,
    mcp_service: McpClientService = Depends(get_mcp_client_service),
    user: dict = Depends(get_current_user)
):
    """
    Connects to a remote MCP server and lists its available tools.
    """
    print(f"Received request to list tools for MCP server: {request.mcp_url}")
    tools = await mcp_service.list_tools_for_server(request.mcp_url, request.auth_token)
    return {"mcp_url": request.mcp_url, "tools": tools}

@app.post("/agents/generate-code", response_model=GenerateCodeResponse)
async def generate_agent_code(request: GenerateCodeRequest, user: dict = Depends(get_current_user)):
    """
    Generates agent code based on the provided configuration.
    """
    from agent_factory import generate_agent_code as generate_code_function
    code = await generate_code_function(request)
    return code


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
async def run_agent_code(request: RunCodeRequest, user: dict = Depends(get_current_user), db: DatabaseService = Depends(get_db)):
    """Executes agent code in a sandboxed environment."""
    try:
        result = await _execute_agent_code(
            code=request.code,
            input_dict=request.input_dict,
            tools=request.tools,
            gofannon_agents=request.gofannon_agents,
            db=db
        )
        
        return RunCodeResponse(result=result)
        
    except Exception as e:
        error_str = f"{type(e).__name__}: {e}"
        tb_str = traceback.format_exc()
        print(f"Error running agent code: {tb_str}")
        return JSONResponse(status_code=400, content={"result": None, "error": f"{error_str}\n\n{tb_str}"})


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

@https_fn.on_request(memory=1024)
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


