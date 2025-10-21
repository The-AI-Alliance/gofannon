from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.alias_generators import to_camel
from typing import Dict, Any, List, Optional, Union
from .chat import ProviderConfig
from datetime import datetime

import uuid


class SwaggerSpec(BaseModel):
    name: str
    content: str

class GenerateCodeRequest(BaseModel):
    tools: Dict[str, List[str]]
    description: str
    input_schema: Dict[str, Any] = Field(..., alias="inputSchema")
    output_schema: Dict[str, Any] = Field(..., alias="outputSchema")
    composer_model_config: ProviderConfig = Field(..., alias="modelConfig")
    invokable_models: Optional[List[ProviderConfig]] = Field(None, alias="invokableModels")
    swagger_specs: Optional[List[SwaggerSpec]] = Field(None, alias="swaggerSpecs")
    gofannon_agents: Optional[List[str]] = Field(None, alias="gofannonAgents")
    model_config = ConfigDict(populate_by_name=True)

class GenerateCodeResponse(BaseModel):
    code: str
    friendly_name: str = Field(..., alias="friendlyName")
    docstring: str

    model_config = ConfigDict(populate_by_name=True)

class CreateAgentRequest(BaseModel):
    name: str
    description: str
    code: str
    docstring: Optional[str] = None
    friendly_name: Optional[str] = Field(None, alias="friendlyName")
    tools: Dict[str, List[str]]
    swagger_specs: Optional[List[SwaggerSpec]] = Field(default_factory=list, alias="swaggerSpecs")
    input_schema: Optional[Dict[str, Any]] = Field(..., alias="inputSchema")
    output_schema: Optional[Dict[str, Any]] = Field(..., alias="outputSchema")
    invokable_models: Optional[List[ProviderConfig]] = Field(None, alias="invokableModels")
    gofannon_agents: Optional[List[str]] = Field(default_factory=list, alias="gofannonAgents")

    model_config = ConfigDict(
        populate_by_name=True,   
        alias_generator=to_camel 
    )

class Agent(CreateAgentRequest):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    rev: Optional[str] = Field(None, alias="_rev")
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    # model_config = ConfigDict(populate_by_name=True) # model_config is inherited from CreateAgentRequest
        

class RunCodeRequest(BaseModel):
    code: str
    input_dict: Dict[str, Any] = Field(..., alias="inputDict")
    tools: Dict[str, List[str]]
    gofannon_agents: Optional[List[str]] = Field(default=[], alias="gofannonAgents")
    model_config = ConfigDict(populate_by_name=True)

class RunCodeResponse(BaseModel):
    result: Optional[Any] = None
    error: Optional[str] = None


