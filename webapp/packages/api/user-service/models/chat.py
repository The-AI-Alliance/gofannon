# webapp/packages/api/user-service/models/chat.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from config.provider_config import PROVIDER_CONFIG


def _ensure_mutually_exclusive(provider: str, model: str, parameters: Dict[str, Any]) -> None:
    """
    Validate that no parameters marked as mutually exclusive are set together.
    """
    parameters = parameters or {}
    model_config = (
        PROVIDER_CONFIG.get(provider, {})
        .get("models", {})
        .get(model, {})
    )
    parameter_schemas = model_config.get("parameters", {}) if isinstance(model_config, dict) else {}

    def _has_value(val: Any) -> bool:
        return val is not None

    for param_name, schema in parameter_schemas.items():
        mutually_exclusive_with = schema.get("mutually_exclusive_with", [])
        if not mutually_exclusive_with or not _has_value(parameters.get(param_name)):
            continue

        for other_param in mutually_exclusive_with:
            if _has_value(parameters.get(other_param)):
                raise ValueError(
                    f"Parameters '{param_name}' and '{other_param}' are mutually exclusive for {provider}/{model}."
                )

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
    built_in_tools: Optional[List[str]] = Field(default_factory=list, alias="builtInTools")
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_mutually_exclusive(self):
        _ensure_mutually_exclusive(self.provider, self.model, self.parameters)
        return self


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
    built_in_tool: Optional[str] = Field(None, alias="builtInTool")
    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_mutually_exclusive(self):
        _ensure_mutually_exclusive(self.provider, self.model, self.parameters)
        return self

class SessionData(BaseModel):
    session_id: str
    provider_config: Optional[ProviderConfig] = None
    created_at: str
    updated_at: str
