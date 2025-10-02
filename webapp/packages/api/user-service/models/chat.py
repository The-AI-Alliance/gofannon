from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

class ChatStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    parameters: Dict[str, Any] = {} # Renamed from 'config' to 'parameters'
    stream: bool = False

class ChatResponse(BaseModel):
    ticket_id: str
    status: ChatStatus
    result: Optional[Dict[str, Any]] = None # This will hold the LLM response content, model, usage, etc.
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ProviderConfig(BaseModel):
    provider: str
    model: str
    parameters: Dict[str, Any]

class SessionData(BaseModel):
    session_id: str
    provider_config: Optional[ProviderConfig] = None
    created_at: str
    updated_at: str