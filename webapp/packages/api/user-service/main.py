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

# Import the shared provider configuration
from config.provider_config import PROVIDER_CONFIG as APP_PROVIDER_CONFIG

app = FastAPI()

origins = ["http://localhost:3000", "http://localhost:3001"] # TODO: Set this with config

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local storage paths
STORAGE_PATH = Path("./local_storage")
TICKETS_PATH = STORAGE_PATH / "tickets"
SESSIONS_PATH = STORAGE_PATH / "sessions"

# Ensure directories exist
TICKETS_PATH.mkdir(parents=True, exist_ok=True)
SESSIONS_PATH.mkdir(parents=True, exist_ok=True)

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

class ChatResponse(BaseModel):
    ticket_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ProviderConfig(BaseModel):
    provider: str
    model: str
    parameters: Dict[str, Any]

class SessionData(BaseModel):
    session_id: str
    provider_config: Optional[ProviderConfig] = None
    created_at: datetime
    updated_at: datetime

# Removed the hardcoded PROVIDER_CONFIGS dictionary.
# Now using APP_PROVIDER_CONFIG imported from config.provider_config

# Helper functions
# NOTE: The user requested stubbing out database backends for now.
# For simplicity, these helper functions currently operate on local JSON files.
# When a NoSQL database is introduced, these will be replaced with custom getter/setter functions.

_tickets_in_memory: Dict[str, Dict[str, Any]] = {}
_sessions_in_memory: Dict[str, SessionData] = {}


def _save_ticket_stub(ticket_id: str, data: dict):
    _tickets_in_memory[ticket_id] = data
    # In a real scenario, this would persist to a DB
    # For POC, local file system simulation is enough, but with in-memory dict as requested.
    # ticket_file = TICKETS_PATH / f"{ticket_id}.json"
    # with open(ticket_file, 'w') as f:
    #     json.dump(data, f, default=str)

def _load_ticket_stub(ticket_id: str) -> dict:
    data = _tickets_in_memory.get(ticket_id)
    if not data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return data
    # ticket_file = TICKETS_PATH / f"{ticket_id}.json"
    # if not ticket_file.exists():
    #     raise HTTPException(status_code=404, detail="Ticket not found")
    # with open(ticket_file, 'r') as f:
    #     return json.load(f)

def _save_session_stub(session_id: str, data: SessionData):
    _sessions_in_memory[session_id] = data
    # session_file = SESSIONS_PATH / f"{session_id}.json"
    # with open(session_file, 'w') as f:
    #     json.dump(data.dict(), f, default=str)

def _load_session_stub(session_id: str) -> SessionData:
    session_data = _sessions_in_memory.get(session_id)
    if not session_data:
        # Create new session if not found, as per original logic
        session_data = SessionData(
            session_id=session_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        _save_session_stub(session_id, session_data)
    return session_data
    # session_file = SESSIONS_PATH / f"{session_id}.json"
    # if not session_file.exists():
    #     # Create new session
    #     session_data = SessionData(
    #         session_id=session_id,
    #         created_at=datetime.utcnow(),
    #         updated_at=datetime.utcnow()
    #     )
    #     _save_session_stub(session_id, session_data)
    #     return session_data
    
    # with open(session_file, 'r') as f:
    #     data = json.load(f)
    #     return SessionData(**data)


# Background task for LLM processing
async def process_chat(ticket_id: str, request: ChatRequest):
    try:
        # Update ticket status
        ticket_data = {
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(), # Use isoformat for JSON serialization
            "request": request.dict()
        }
        _save_ticket_stub(ticket_id, ticket_data)
        
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
        _save_ticket_stub(ticket_id, ticket_data)
        
    except Exception as e:
        # Update ticket with error
        ticket_data.update({
            "status": "failed",
            "completed_at": datetime.utcnow().isoformat(),
            "error": str(e)
        })
        _save_ticket_stub(ticket_id, ticket_data)

# Routes
@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}

@app.get("/providers")
def get_providers():
    """Get all available providers and their configurations"""
    return APP_PROVIDER_CONFIG

@app.get("/providers/{provider}")
def get_provider_config_route(provider: str): # Renamed to avoid name collision with APP_PROVIDER_CONFIG
    """Get configuration for a specific provider"""
    if provider not in APP_PROVIDER_CONFIG:
        raise HTTPException(status_code=404, detail="Provider not found")
    return APP_PROVIDER_CONFIG[provider]

@app.get("/providers/{provider}/models")
def get_provider_models(provider: str):
    """Get available models for a provider"""
    if provider not in APP_PROVIDER_CONFIG:
        raise HTTPException(status_code=404, detail="Provider not found")
    return list(APP_PROVIDER_CONFIG[provider]["models"].keys())

@app.get("/providers/{provider}/models/{model}")
def get_model_config(provider: str, model: str):
    """Get configuration for a specific model"""
    if provider not in APP_PROVIDER_CONFIG:
        raise HTTPException(status_code=404, detail="Provider not found")
    if model not in APP_PROVIDER_CONFIG[provider]["models"]:
        raise HTTPException(status_code=404, detail="Model not found")
    return APP_PROVIDER_CONFIG[provider]["models"][model]

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
async def get_chat_status(ticket_id: str):
    """Get the status and result of a chat request"""
    try:
        ticket_data = _load_ticket_stub(ticket_id) # Use the stubbed function
        return ChatResponse(
            ticket_id=ticket_id,
            status=ticket_data["status"],
            result=ticket_data.get("result"),
            error=ticket_data.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/config")
async def update_session_config(session_id: str, config: ProviderConfig):
    """Update session configuration"""
    session = _load_session_stub(session_id) # Use the stubbed function
    session.provider_config = config
    session.updated_at = datetime.utcnow()
    _save_session_stub(session_id, session) # Use the stubbed function
    return {"message": "Configuration updated", "session_id": session_id}

@app.get("/sessions/{session_id}/config")
async def get_session_config(session_id: str):
    """Get session configuration"""
    session = _load_session_stub(session_id) # Use the stubbed function
    return session.provider_config

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in _sessions_in_memory:
        del _sessions_in_memory[session_id]
        return {"message": "Session deleted"}
    # session_file = SESSIONS_PATH / f"{session_id}.json"
    # if session_file.exists():
    #     session_file.unlink()
    #     return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-service"}
