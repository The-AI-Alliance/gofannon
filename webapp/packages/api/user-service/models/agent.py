from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from .chat import ProviderConfig


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

    class ConfigDict:
        # validate_by_name = True
        populate_by_name = True
        
class GenerateCodeResponse(BaseModel):
    code: str

class RunCodeRequest(BaseModel):
    code: str
    input_dict: Dict[str, Any] = Field(..., alias="inputDict")
    tools: Dict[str, List[str]]

    class ConfigDict:
        populate_by_name = True

class RunCodeResponse(BaseModel):
    result: Optional[Any] = None
    error: Optional[str] = None


