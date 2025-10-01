from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Annotated, Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import json
import os
from pathlib import Path
import asyncio
import litellm

app = FastAPI()

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

# Provider configurations
PROVIDER_CONFIGS = {
    "openai": {
        "models": {
            "gpt-3.5-turbo": {
                "parameters": {
                    "temperature": {"type": "float", "default": 0.7, "min": 0, "max": 2},
                    "max_tokens": {"type": "int", "default": 1000, "min": 1, "max": 4096},
                    "top_p": {"type": "float", "default": 1.0, "min": 0, "max": 1},
                    "frequency_penalty": {"type": "float", "default": 0, "min": -2, "max": 2},
                    "presence_penalty": {"type": "float", "default": 0, "min": -2, "max": 2}
                }
            },
            "gpt-4": {
                "parameters": {
                    "temperature": {"type": "float", "default": 0.7, "min": 0, "max": 2},
                    "max_tokens": {"type": "int", "default": 1000, "min": 1, "max": 8192},
                    "top_p": {"type": "float", "default": 1.0, "min": 0, "max": 1},
                    "frequency_penalty": {"type": "float", "default": 0, "min": -2, "max": 2},
                    "presence_penalty": {"type": "float", "default": 0, "min": -2, "max": 2}
                }
            }
        }
    },
    "anthropic": {
        "models": {
            "claude-2": {
                "parameters": {
                    "temperature": {"type": "float", "default": 0.7, "min": 0, "max": 1},
                    "max_tokens": {"type": "int", "default": 1000, "min": 1, "max": 100000},
                    "top_p": {"type": "float", "default": 1.0, "min": 0, "max": 1}
                }
            },
            "claude-instant-1": {
                "parameters": {
                    "temperature": {"type": "float", "default": 0.7, "min": 0, "max": 1},
                    "max_tokens": {"type": "int", "default": 1000, "min": 1, "max": 100000},
                    "top_p": {"type": "float", "default": 1.0, "min": 0, "max": 1}
                }
            }
        }
    },
    "cohere": {
        "models": {
            "command": {
                "parameters": {
                    "temperature": {"type": "float", "default": 0.7, "min": 0, "max": 5},
                    "max_tokens": {"type": "int", "default": 1000, "min": 1, "max": 4096},
                    "p": {"type": "float", "default": 0.75, "min": 0, "max": 1},
                    "k": {"type": "int", "default": 0, "min": 0, "max": 500},
                    "frequency_penalty": {"type": "float", "default": 0, "min": 0, "max": 1},
                    "presence_penalty": {"type": "float", "default": 0, "min": 0, "max": 1}
                }
            }
        }
    }
}

# Helper functions
def save_ticket(ticket_id: str, data: dict):
    ticket_file = TICKETS_PATH / f"{ticket_id}.json"
    with open(ticket_file, 'w') as f:
        json.dump(data, f, default=str)

def load_ticket(ticket_id: str) -> dict:
    ticket_file = TICKETS_PATH / f"{ticket_id}.json"
    if not ticket_file.exists():
        raise HTTPException(status_code=404, detail="Ticket not found")
    with open(ticket_file, 'r') as f:
        return json.load(f)

def save_session(session_id: str, data: SessionData):
    session_file = SESSIONS_PATH / f"{session_id}.json"
    with open(session_file, 'w') as f:
        json.dump(data.dict(), f, default=str)

def load_session(session_id: str) -> SessionData:
    session_file = SESSIONS_PATH / f"{session_id}.json"
    if not session_file.exists():
        # Create new session
        session_data = SessionData(
            session_id=session_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        save_session(session_id, session_data)
        return session_data
    
    with open(session_file, 'r') as f:
        data = json.load(f)
        return SessionData(**data)

# Background task for LLM processing
async def process_chat(ticket_id: str, request: ChatRequest):
    try:
        # Update ticket status
        ticket_data = {
            "status": "processing",
            "created_at": datetime.utcnow(),
            "request": request.dict()
        }
        save_ticket(ticket_id, ticket_data)
        
        # Convert messages to format expected by litellm
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Prepare litellm parameters
        model_name = f"{request.provider}/{request.model}" if request.provider != "openai" else request.model
        
        # Call LiteLLM
        response = await litellm.acompletion(
            model=model_name,
            messages=messages,
            **request.parameters
        )
        
        # Update ticket with success
        ticket_data.update({
            "status": "completed",
            "completed_at": datetime.utcnow(),
            "result": {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else None
            }
        })
        save_ticket(ticket_id, ticket_data)
        
    except Exception as e:
        # Update ticket with error
        ticket_data.update({
            "status": "failed",
            "completed_at": datetime.utcnow(),
            "error": str(e)
        })
        save_ticket(ticket_id, ticket_data)

# Routes
@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}

@app.get("/providers")
def get_providers():
    """Get all available providers and their configurations"""
    return PROVIDER_CONFIGS

@app.get("/providers/{provider}")
def get_provider_config(provider: str):
    """Get configuration for a specific provider"""
    if provider not in PROVIDER_CONFIGS:
        raise HTTPException(status_code=404, detail="Provider not found")
    return PROVIDER_CONFIGS[provider]

@app.get("/providers/{provider}/models")
def get_provider_models(provider: str):
    """Get available models for a provider"""
    if provider not in PROVIDER_CONFIGS:
        raise HTTPException(status_code=404, detail="Provider not found")
    return list(PROVIDER_CONFIGS[provider]["models"].keys())

@app.get("/providers/{provider}/models/{model}")
def get_model_config(provider: str, model: str):
    """Get configuration for a specific model"""
    if provider not in PROVIDER_CONFIGS:
        raise HTTPException(status_code=404, detail="Provider not found")
    if model not in PROVIDER_CONFIGS[provider]["models"]:
        raise HTTPException(status_code=404, detail="Model not found")
    return PROVIDER_CONFIGS[provider]["models"][model]

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
        ticket_data = load_ticket(ticket_id)
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
    session = load_session(session_id)
    session.provider_config = config
    session.updated_at = datetime.utcnow()
    save_session(session_id, session)
    return {"message": "Configuration updated", "session_id": session_id}

@app.get("/sessions/{session_id}/config")
async def get_session_config(session_id: str):
    """Get session configuration"""
    session = load_session(session_id)
    return session.provider_config

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    session_file = SESSIONS_PATH / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-service"}