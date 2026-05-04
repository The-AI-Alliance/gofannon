# webapp/packages/api/user-service/models/agent.py
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from pydantic.alias_generators import to_camel
from typing import Dict, Any, List, Literal, Optional, Union
from .chat import ProviderConfig
from datetime import datetime

import uuid


class SwaggerSpec(BaseModel):
    name: str
    content: str


class DataStoreNamespaceConfig(BaseModel):
    """Per-agent declaration of a data-store namespace the agent uses.

    Advisory: the runtime doesn't enforce access mode — an agent with
    ``access="read"`` can still technically call ``data_store.set(...)``.
    This metadata exists so the editor UI can surface what data each agent
    touches and so the data-store viewer can show which agents have
    declared reliance on which namespace.
    """
    namespace: str
    access: Literal["read", "write", "both"] = "both"
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class GenerateCodeRequest(BaseModel):
    tools: Dict[str, List[str]]
    description: str
    input_schema: Dict[str, Any] = Field(..., alias="inputSchema")
    output_schema: Dict[str, Any] = Field(..., alias="outputSchema")
    composer_model_config: ProviderConfig = Field(..., alias="modelConfig")
    invokable_models: Optional[List[ProviderConfig]] = Field(None, alias="invokableModels")
    swagger_specs: Optional[List[SwaggerSpec]] = Field(None, alias="swaggerSpecs")
    gofannon_agents: Optional[List[str]] = Field(None, alias="gofannonAgents")
    built_in_tools: Optional[List[str]] = Field(default_factory=list, alias="builtInTools")
    model_config = ConfigDict(populate_by_name=True)

class GenerateCodeResponse(BaseModel):
    code: str
    friendly_name: str = Field(..., alias="friendlyName")
    docstring: str
    thoughts: Optional[Any] = None


    model_config = ConfigDict(populate_by_name=True)

class CreateAgentRequest(BaseModel):
    name: str
    description: str
    code: str
    docstring: Optional[str] = None
    friendly_name: Optional[str] = Field(None, alias="friendlyName")
    tools: Dict[str, List[str]] = Field(default_factory=dict)
    swagger_specs: Optional[List[SwaggerSpec]] = Field(default_factory=list, alias="swaggerSpecs")
    input_schema: Optional[Dict[str, Any]] = Field(None, alias="inputSchema")
    output_schema: Optional[Dict[str, Any]] = Field(None, alias="outputSchema")
    invokable_models: Optional[List[ProviderConfig]] = Field(None, alias="invokableModels")
    gofannon_agents: Optional[List[str]] = Field(default_factory=list, alias="gofannonAgents")
    composer_thoughts: Optional[Any] = Field(None, alias="composerThoughts")
    composer_model_config: Optional[ProviderConfig] = Field(None, alias="composerModelConfig")
    data_store_config: Optional[List[DataStoreNamespaceConfig]] = Field(
        default_factory=list, alias="dataStoreConfig"
    )

    model_config = ConfigDict(
        populate_by_name=True,   
        alias_generator=to_camel,
        extra="ignore",
        serialize_by_alias=True
    )

class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    docstring: Optional[str] = None
    friendly_name: Optional[str] = Field(None, alias="friendlyName")
    tools: Optional[Dict[str, List[str]]] = Field(default=None)
    swagger_specs: Optional[List[SwaggerSpec]] = Field(default=None, alias="swaggerSpecs")
    input_schema: Optional[Dict[str, Any]] = Field(None, alias="inputSchema")
    output_schema: Optional[Dict[str, Any]] = Field(None, alias="outputSchema")
    invokable_models: Optional[List[ProviderConfig]] = Field(None, alias="invokableModels")
    gofannon_agents: Optional[List[str]] = Field(default=None, alias="gofannonAgents")
    composer_thoughts: Optional[Any] = Field(None, alias="composerThoughts")
    composer_model_config: Optional[ProviderConfig] = Field(None, alias="composerModelConfig")
    data_store_config: Optional[List[DataStoreNamespaceConfig]] = Field(
        default=None, alias="dataStoreConfig"
    )
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore",
        serialize_by_alias=True
    )

class Agent(CreateAgentRequest):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    rev: Optional[str] = Field(None, alias="_rev")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # model_config = ConfigDict(populate_by_name=True) # model_config is inherited from CreateAgentRequest
        
class LlmSettings(BaseModel):
    """LLM settings passed from the UI to control model behavior in agent sandbox."""
    max_tokens: Optional[int] = Field(None, alias="maxTokens")
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = Field(None, alias="reasoningEffort")
    model_config = ConfigDict(populate_by_name=True)

class RunCodeRequest(BaseModel):
    code: str
    input_dict: Dict[str, Any] = Field(..., alias="inputDict")
    tools: Dict[str, List[str]]
    gofannon_agents: Optional[List[str]] = Field(default=[], alias="gofannonAgents")
    llm_settings: Optional[LlmSettings] = Field(default=None, alias="llmSettings")
    # Optional: when provided, the sandbox validates the agent's return value
    # against this schema and surfaces any mismatches as schema_warnings in
    # the response. Advisory only — never fails the run.
    output_schema: Optional[Dict[str, Any]] = Field(default=None, alias="outputSchema")
    # Optional: human-friendly agent name for the trace's per-event
    # agent_name field. Used by the Progress Log UI to label runs and
    # group nested-agent activity. Falls back to "sandbox_agent" if not
    # provided (legacy clients).
    friendly_name: Optional[str] = Field(default=None, alias="friendlyName")
    model_config = ConfigDict(populate_by_name=True)

class RunCodeResponse(BaseModel):
    result: Optional[Any] = None
    error: Optional[str] = None
    # Populated when output_schema was provided on the request and the
    # agent's return value doesn't match it. Empty or missing means OK.
    schema_warnings: Optional[List[str]] = Field(default=None, alias="schemaWarnings")
    # Accumulated data-store operations performed during the sandbox run,
    # in chronological order. Each entry is a dict: {op, namespace, agent,
    # ts, key?, valuePreview?, found?, count?}. Used by the sandbox UI's
    # live Data Store panel. None when the agent didn't touch the data store.
    ops_log: Optional[List[Dict[str, Any]]] = Field(default=None, alias="opsLog")
    # Per-run trace populated by services/agent_trace.py. Each entry is
    # one of: agent_start, agent_end, llm_call, data_store, error,
    # stdout, log, trace_truncated. The sandbox UI's Progress Log
    # accordion groups these by run and per-agent. None for non-sandbox
    # invocations (e.g., deployed agent runs).
    trace: Optional[List[Dict[str, Any]]] = Field(default=None)
    model_config = ConfigDict(populate_by_name=True)

class Deployment(BaseModel):
    id: str = Field(..., alias="_id") # This will be the friendly_name
    agent_id: str = Field(..., alias="agentId")
    rev: Optional[str] = Field(None, alias="_rev")
    model_config = ConfigDict(populate_by_name=True)
 
 
class DeployedApi(BaseModel):
    friendly_name: str = Field(..., alias="friendlyName")
    agent_id: str = Field(..., alias="agentId")
    description: str
    input_schema: Dict[str, Any] = Field(..., alias="inputSchema")
    output_schema: Dict[str, Any] = Field(..., alias="outputSchema")
    model_config = ConfigDict(populate_by_name=True)