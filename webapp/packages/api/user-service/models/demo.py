# webapp/packages/api/user-service/models/demo.py
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import Dict, Any, List, Optional
from .chat import ProviderConfig
from .agent import DeployedApi
import uuid
from datetime import datetime

class GenerateDemoCodeRequest(BaseModel):
    user_prompt: str = Field(..., alias="userPrompt")
    selected_apis: List[DeployedApi] = Field(..., alias="selectedApis")
    composer_model_config: ProviderConfig = Field(..., alias="modelConfig")
    model_config = ConfigDict(populate_by_name=True)

class GenerateDemoCodeResponse(BaseModel):
    html: str = ""
    css: str = ""
    js: str = ""

class CreateDemoAppRequest(BaseModel):
    name: str
    description: Optional[str] = None
    selected_apis: List[DeployedApi] = Field(..., alias="selectedApis")
    composer_model_config: ProviderConfig = Field(..., alias="modelConfig")
    user_prompt: str = Field(..., alias="userPrompt")
    generated_code: GenerateDemoCodeResponse = Field(..., alias="generatedCode")
    model_config = ConfigDict(populate_by_name=True)


class DemoApp(CreateDemoAppRequest):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    rev: Optional[str] = Field(None, alias="_rev")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(populate_by_name=True)