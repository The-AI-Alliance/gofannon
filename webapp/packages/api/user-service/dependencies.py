from __future__ import annotations

import asyncio
import json
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import yaml
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer

from agent_factory.remote_mcp_client import RemoteMCPClient
from config import settings
from config.provider_config import PROVIDER_CONFIG as APP_PROVIDER_CONFIG
from models.agent import Agent
from models.chat import ChatRequest
from services.database_service import DatabaseService, get_database_service
from services.llm_service import call_llm
from services.observability_service import (
    ObservabilityService,
    get_observability_service,
    get_sanitized_request_data,
)
from services.user_service import UserService, get_user_service


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_db() -> DatabaseService:
    yield get_database_service(settings)


def get_logger() -> ObservabilityService:
    """Dependency to get the observability service instance."""
    return get_observability_service()


def get_user_service_dep(db: DatabaseService = Depends(get_db)) -> UserService:
    return get_user_service(db)


def require_admin_access(admin_password: str | None = Header(default=None, alias="X-Admin-Password")):
    if not settings.ADMIN_PANEL_ENABLED:
        raise HTTPException(status_code=403, detail="Admin panel is disabled")

    if admin_password != settings.ADMIN_PANEL_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin password")


async def _execute_agent_code(
    code: str, 
    input_dict: dict, 
    tools: dict, 
    gofannon_agents: List[str], 
    db: DatabaseService,
    user_id: Optional[str] = None,
    user_basic_info: Optional[Dict[str, Any]] = None,
):
    """Helper function for recursive execution of agent code."""
    # Get user service for API key lookup if user_id is provided
    user_service = get_user_service(db) if user_id else None

    class GofannonClient:
        def __init__(self, agent_ids: List[str], db_service: DatabaseService):
            self.db = db_service
            self.agent_map = {}
            if agent_ids:
                try:
                    all_agents = [Agent(**self.db.get("agents", agent_id)) for agent_id in agent_ids]
                    for agent in all_agents:
                        self.agent_map[agent.name] = agent
                except Exception as e:
                    print(f"Error loading dependent agents: {e}")
                    raise ValueError("Could not load one or more dependent Gofannon agents.")

        async def call(self, agent_name: str, input_dict: dict) -> Any:
            agent_to_run = self.agent_map.get(agent_name)
            if not agent_to_run:
                raise ValueError(f"Gofannon agent '{agent_name}' not found or not imported for this run.")

            # Recursive call to the execution helper
            return await _execute_agent_code(
                code=agent_to_run.code,
                input_dict=input_dict,
                tools=agent_to_run.tools,
                gofannon_agents=agent_to_run.gofannon_agents,
                db=self.db,
                user_id=user_id,
                user_basic_info=user_basic_info,
            )

    # Create a wrapped call_llm that includes user context
    async def call_llm_with_context(
        provider: str,
        model: str,
        messages: List[Dict[str, Any]],
        parameters: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        """Wrapped call_llm that includes user context for API key lookup."""
        # Remove user context kwargs if they were passed by generated code
        # (we'll set them explicitly from the outer scope)
        kwargs.pop("user_service", None)
        kwargs.pop("user_id", None)
        kwargs.pop("user_basic_info", None)
        return await call_llm(
            provider=provider,
            model=model,
            messages=messages,
            parameters=parameters,
            tools=tools,
            user_service=user_service,
            user_id=user_id,
            user_basic_info=user_basic_info,
            **kwargs
        )

    exec_globals = {
        "RemoteMCPClient": RemoteMCPClient,
        "call_llm": call_llm_with_context,  # Use wrapped LLM service with user context
        "asyncio": asyncio,
        "httpx": httpx,
        "re": __import__('re'),
        "json": __import__('json'),
        "http_client": httpx.AsyncClient(follow_redirects=True),  # Follow redirects automatically
        "gofannon_client": GofannonClient(gofannon_agents, db),
        "__builtins__": __builtins__,
    }

    local_scope: Dict[str, Any] = {}

    code_obj = compile(code, "<string>", "exec")
    exec(code_obj, exec_globals, local_scope)

    run_function = local_scope.get("run")

    if not run_function or not asyncio.iscoroutinefunction(run_function):
        raise ValueError("Code did not define an 'async def run(input_dict, tools)' function.")

    result = await run_function(input_dict=input_dict, tools=tools)
    return result


async def process_chat(ticket_id: str, request: ChatRequest, user: dict, req: Request):
    # Background tasks don't have access to dependency injection, so we get service instances directly
    db_service = get_database_service(settings)
    user_service = get_user_service(db_service)
    logger = get_observability_service()
    user_basic_info = {
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }
    try:
        # Update ticket status
        ticket_data = {
            "status": "processing",
            "created_at": datetime.utcnow().isoformat(),  # Use isoformat for JSON serialization
            "request": request.dict(by_alias=True),
        }
        db_service.save("tickets", ticket_id, dict(ticket_data))

        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        content = ""
        thoughts = None

        if request.provider == "gofannon":
            logger.log(
                "INFO",
                "agent_chat_request",
                f"Initiating Agent call to {request.model}",
                metadata={"request": get_sanitized_request_data(req)},
            )
            agent_friendly_name = request.model

            try:
                deployment_doc = db_service.get("deployments", agent_friendly_name)
                agent_id = deployment_doc["agentId"]
                agent_data = db_service.get("agents", agent_id)
                agent = Agent(**agent_data)
            except Exception:
                raise ValueError(f"Could not find a deployed agent with name '{agent_friendly_name}'")

            last_user_message = next((msg for msg in reversed(messages) if msg["role"] == "user"), None)
            if not last_user_message:
                raise ValueError("No user message found to run the agent with.")

            input_dict = request.parameters.copy()
            # The user query is always mapped to 'inputText'
            input_dict["inputText"] = last_user_message["content"]

            result = await _execute_agent_code(
                code=agent.code,
                input_dict=input_dict,
                tools=agent.tools,
                gofannon_agents=agent.gofannon_agents,
                db=db_service,
                user_id=user.get("uid"),
                user_basic_info=user_basic_info,
            )

            if isinstance(result, dict):
                # The response is always from 'outputText'
                content = result.get("outputText", json.dumps(result))
                thoughts = result
            else:
                content = str(result)
                thoughts = {"raw_output": content}

        else:
            built_in_tools = []
            model_tool_config = (
                APP_PROVIDER_CONFIG.get(request.provider, {})
                .get("models", {})
                .get(request.model, {})
                .get("built_in_tools", [])
            )
            if request.built_in_tools:
                for tool_id in request.built_in_tools:
                    tool_conf = next((t for t in model_tool_config if t["id"] == tool_id), None)
                    if tool_conf:
                        built_in_tools.append(tool_conf["tool_config"])

            logger.log(
                "INFO",
                "llm_request",
                f"Initiating LLM call to {request.provider}/{request.model}",
                metadata={"request": get_sanitized_request_data(req)},
            )

            content, thoughts = await call_llm(
                provider=request.provider,
                model=request.model,
                messages=messages,
                parameters=request.parameters,
                tools=built_in_tools if built_in_tools else None,
                user_service=user_service,
                user_id=user.get("uid"),
                user_basic_info=user_basic_info,
            )

        completed_ticket_data = {
            **ticket_data,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "result": {
                "content": content,
                "thoughts": thoughts,
                "model": f"{request.provider}/{request.model}",
            },
        }
        db_service.save("tickets", ticket_id, completed_ticket_data)

    except Exception as e:
        logger.log(
            "ERROR",
            "background_task_failure",
            f"Chat processing failed for ticket {ticket_id}: {e}",
            metadata={"traceback": traceback.format_exc(), "request": get_sanitized_request_data(req)},
        )
        if "ticket_data" not in locals():
            ticket_data = db_service.get("tickets", ticket_id)

        ticket_data.update(
            {
                "status": "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e),
            }
        )
        db_service.save("tickets", ticket_id, ticket_data)


def get_available_providers(user_id: Optional[str] = None, user_basic_info: Optional[Dict[str, Any]] = None):
    """
    Get available providers.
    
    If user_id is provided, checks user's stored API keys first,
    then falls back to environment variables.
    """
    db_service = get_database_service(settings)
    available_providers: Dict[str, Any] = {}
    
    # Get user service if user_id is provided
    user_service = None
    if user_id:
        user_service = get_user_service(db_service)
    
    for provider, config in APP_PROVIDER_CONFIG.items():
        api_key_env_var = config.get("api_key_env_var")
        
        # Check if provider is available
        is_available = False
        
        # First, check if user has a stored API key for this provider
        if user_service and user_id:
            user_key = user_service.get_effective_api_key(user_id, provider, basic_info=user_basic_info)
            if user_key:
                is_available = True
        
        # If no user key, check environment variable
        if not is_available and (not api_key_env_var or os.getenv(api_key_env_var)):
            is_available = True
        
        # Ollama doesn't require an API key
        if not api_key_env_var:
            is_available = True
        
        if is_available:
            available_providers[provider] = config

    try:
        all_deployments = db_service.list_all("deployments")
        gofannon_models: Dict[str, Any] = {}
        for deployment_doc in all_deployments:
            try:
                agent_id = deployment_doc["agentId"]
                agent_doc = db_service.get("agents", agent_id)
                agent = Agent(**agent_doc)

                friendly_name = deployment_doc["_id"]

                parameters = agent.input_schema
                formatted_params = {}
                for name, schema in parameters.items():
                    formatted_params[name] = {
                        "type": schema,
                        "description": name,
                        "default": "",
                    }

                gofannon_models[friendly_name] = {
                    "id": agent.id,
                    "description": agent.description,
                    "parameters": formatted_params,
                }
            except Exception as agent_load_e:
                print(f"Skipping deployed agent '{deployment_doc.get('_id')}' due to error: {agent_load_e}")

        if gofannon_models:
            available_providers["gofannon"] = {"models": gofannon_models}

    except Exception as e:
        print(f"Could not load Gofannon agents as a provider: {e}")

    return available_providers


async def fetch_spec_content(url: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()

            content = response.text
            try:
                json.loads(content)
            except json.JSONDecodeError:
                try:
                    yaml.safe_load(content)
                except yaml.YAMLError:
                    raise HTTPException(status_code=400, detail="Content from URL is not valid JSON or YAML.")

            from urllib.parse import urlparse

            path = urlparse(str(url)).path
            name = path.split("/")[-1] if path else "spec_from_url.json"
            if not name:
                name = "spec_from_url.json"

            return {"name": name, "content": content}
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=f"Error fetching from URL: {e}")


async def deploy_agent(agent_id: str, db: DatabaseService):
    agent_doc = db.get("agents", agent_id)
    agent = Agent(**agent_doc)
    friendly_name = agent.friendly_name

    if not friendly_name:
        raise HTTPException(status_code=400, detail="Agent must have a friendly_name to be deployed.")

    try:
        existing_deployment = db.get("deployments", friendly_name)
        if existing_deployment.get("agentId") == agent_id:
            return {"message": "Agent is already deployed", "endpoint": f"/rest/{friendly_name}"}
        raise HTTPException(
            status_code=409,
            detail=f"A deployment with the name '{friendly_name}' already exists for a different agent.",
        )
    except HTTPException as e:
        if e.status_code == 404:
            deployment_doc = {"agentId": agent_id}
            db.save("deployments", friendly_name, deployment_doc)
            return {"message": "Agent deployed successfully", "endpoint": f"/rest/{friendly_name}"}
        raise e


async def undeploy_agent(agent_id: str, db: DatabaseService):
    agent_doc = db.get("agents", agent_id)
    agent = Agent(**agent_doc)
    friendly_name = agent.friendly_name
    if not friendly_name:
        return

    try:
        db.delete("deployments", friendly_name)
    except HTTPException as e:
        if e.status_code == 404:
            return
        raise e


async def get_agent_deployment(agent_id: str, db: DatabaseService):
    agent_doc = db.get("agents", agent_id)
    agent = Agent(**agent_doc)
    friendly_name = agent.friendly_name

    if not friendly_name:
        return {"is_deployed": False}

    try:
        deployment_doc = db.get("deployments", friendly_name)
        if deployment_doc.get("agentId") == agent_id:
            return {"is_deployed": True, "friendly_name": friendly_name}
        return {"is_deployed": False}
    except HTTPException as e:
        if e.status_code == 404:
            return {"is_deployed": False}
        raise e


async def list_deployments(db: DatabaseService):
    try:
        all_deployments_docs = db.list_all("deployments")
        deployment_infos = []
        for dep_doc in all_deployments_docs:
            try:
                agent_doc = db.get("agents", dep_doc["agentId"])
                agent = Agent(**agent_doc)
                dep_info = {
                    "friendlyName": dep_doc["_id"],
                    "agentId": dep_doc["agentId"],
                    "description": agent.description,
                    "inputSchema": agent.input_schema,
                    "outputSchema": agent.output_schema,
                }
                deployment_infos.append(dep_info)
            except Exception as e:
                print(
                    f"Skipping deployment '{dep_doc['_id']}' due to error fetching agent '{dep_doc['agentId']}': {e}"
                )
                continue
        return deployment_infos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_deployed_agent(
    friendly_name: str, 
    input_dict: dict, 
    db: DatabaseService,
    user_id: Optional[str] = None,
    user_basic_info: Optional[Dict[str, Any]] = None,
):
    try:
        deployment_doc = db.get("deployments", friendly_name)
        agent_id = deployment_doc["agentId"]

        agent_data = db.get("agents", agent_id)
        agent = Agent(**agent_data)

        result = await _execute_agent_code(
            code=agent.code,
            input_dict=input_dict,
            tools=agent.tools,
            gofannon_agents=agent.gofannon_agents,
            db=db,
            user_id=user_id,
            user_basic_info=user_basic_info,
        )
        return result
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail="No deployed agent found with that name.")
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing agent: {str(e)}")


__all__ = [
    "get_db",
    "get_logger",
    "get_user_service_dep",
    "require_admin_access",
    "process_chat",
    "get_available_providers",
    "fetch_spec_content",
    "deploy_agent",
    "undeploy_agent",
    "get_agent_deployment",
    "list_deployments",
    "run_deployed_agent",
    "_execute_agent_code",
    "oauth2_scheme",
]
