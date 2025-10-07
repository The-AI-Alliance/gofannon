from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from .chat import ProviderConfig

class GenerateCodeRequest(BaseModel):
    tools: Dict[str, List[str]]
    description: str
    input_schema: Dict[str, Any] = Field(..., alias="inputSchema")
    output_schema: Dict[str, Any] = Field(..., alias="outputSchema")
    composer_model_config: ProviderConfig = Field(..., alias="modelConfig")
    invokable_models: Optional[List[ProviderConfig]] = Field(None, alias="invokableModels")

    class ConfigDict:
        validate_by_name = True
        
class GenerateCodeResponse(BaseModel):
    code: str

