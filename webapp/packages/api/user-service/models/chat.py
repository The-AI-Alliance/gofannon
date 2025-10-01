from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class ChatStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ChatRequest(BaseModel):
    provider: str
    model: str
    messages: List[Dict[str, str]]
    config: Optional[Dict[str, Any]] = None
    stream: Optional[bool] = False

class ChatResponse(BaseModel):
    ticket_id: str
    status: ChatStatus
    result: Optional[str] = None
    error: Optional[str] = None

class ChatStatusResponse(BaseModel):
    ticket_id: str
    status: ChatStatus
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str