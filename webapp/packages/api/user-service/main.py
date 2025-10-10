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

from services.database_service import get_database_service, DatabaseService
from config import settings
from services.mcp_client_service import McpClientService, get_mcp_client_service

# Import the shared provider configuration
from config.provider_config import PROVIDER_CONFIG as APP_PROVIDER_CONFIG
from models.agent import GenerateCodeRequest, GenerateCodeResponse, RunCodeRequest, RunCodeResponse, Agent, CreateAgentRequest
from agent_factory.remote_mcp_client import RemoteMCPClient

app = FastAPI()

origins = ["http://localhost:3000", "http://localhost:3001"] # TODO: Set this with config

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """Submit a chat request and get a ticket ID"""
    ticket_id = str(uuid.uuid4())
    
    # Start processing in background
    background_tasks.add_task(process_chat, ticket_id, request)
    
    return ChatResponse(
        ticket_id=ticket_id,
        status="pending"
    )

@app.get("/chat/{ticket_id}")
async def get_chat_status(ticket_id: str, db: DatabaseService = Depends(get_db)):
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
async def update_session_config(session_id: str, config: ProviderConfig, db: DatabaseService = Depends(get_db)):
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
async def get_session_config(session_id: str, db: DatabaseService = Depends(get_db)):
    """Get session configuration"""
    session_doc = db.get("sessions", session_id)
    return session_doc.get("provider_config")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: DatabaseService = Depends(get_db)):
    """Delete a session"""
    db.delete("sessions", session_id)
    return {"message": "Session deleted"}

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-service"}


@app.post("/agents", response_model=Agent, status_code=201)
async def create_agent(request: CreateAgentRequest, db: DatabaseService = Depends(get_db)):
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
    saved_doc_data = agent.model_dump()
    saved_doc = db.save("agents", agent.id, saved_doc_data)
    
    agent.rev = saved_doc.get("rev") # Add revision from DB response
    return agent

@app.get("/agents", response_model=List[Agent])
async def list_agents(db: DatabaseService = Depends(get_db)):
    """Lists all saved agents."""
    # This simple query returns all documents. A more advanced implementation
    # might use views for sorting or filtering.
    all_docs = db.list_all("agents")
    return [Agent(**doc) for doc in all_docs]
    # return all_docs

@app.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: DatabaseService = Depends(get_db)):
    """Retrieves a specific agent by its ID."""
    agent_doc = db.get("agents", agent_id)
    return Agent(**agent_doc)

@app.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: DatabaseService = Depends(get_db)):
    """Deletes an agent by its ID."""
    try:
        db.delete("agents", agent_id)
        return
    except HTTPException as e:
        raise e

@app.post("/mcp/tools")
async def list_mcp_tools(
    request: ListMcpToolsRequest,
    mcp_service: McpClientService = Depends(get_mcp_client_service)
):
    """
    Connects to a remote MCP server and lists its available tools.
    """
    print(f"Received request to list tools for MCP server: {request.mcp_url}")
    tools = await mcp_service.list_tools_for_server(request.mcp_url, request.auth_token)
    return {"mcp_url": request.mcp_url, "tools": tools}

@app.post("/agents/generate-code", response_model=GenerateCodeResponse)
async def generate_agent_code(request: GenerateCodeRequest):
    """
    Generates agent code based on the provided configuration.
    """
    from agent_factory import generate_agent_code as generate_code_function
    code = await generate_code_function(request)
    return code


@app.post("/agents/run-code", response_model=RunCodeResponse)
async def run_agent_code(request: RunCodeRequest):
    """
    Executes agent code in a sandboxed environment.
    """
    try:
        # Prepare the execution scope. The code string will handle its own imports.
        # We pass necessary modules/classes in globals for the `exec` context.
        exec_globals = {
            "RemoteMCPClient": RemoteMCPClient,
            "litellm": litellm,
            "asyncio": asyncio,
            "http_client": httpx.AsyncClient(),
            "__builtins__": __builtins__
        }
        
        local_scope = {}
        
        # The user's code is a string that defines `async def run(...)`
        # We execute it to define the function within our local_scope.
        code_obj = compile(request.code, '<string>', 'exec')
        exec(code_obj, exec_globals, local_scope)

        run_function = local_scope.get('run')

        if not run_function or not asyncio.iscoroutinefunction(run_function):
            raise ValueError("Code did not define an 'async def run(input, tools)' function.")

        # Call the async function with the provided input and tools
        result = await run_function(input_dict=request.input_dict, tools=request.tools)
        
        return RunCodeResponse(result=result)
        
    except Exception as e:
        error_str = f"{type(e).__name__}: {e}"
        tb_str = traceback.format_exc()
        print(f"Error running agent code: {tb_str}")
        return JSONResponse(status_code=400, content={"result": None, "error": f"{error_str}\n\n{tb_str}"})
