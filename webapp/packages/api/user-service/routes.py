import asyncio
import copy
import json
import traceback
import uuid
from typing import Optional, Dict, Any, List

from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from config import settings
from services.agent_trace import Trace
from dependencies import (
    _execute_agent_code,
    build_agent_chain,
    deploy_agent,
    fetch_spec_content,
    get_agent_deployment,
    get_available_providers,
    get_async_db,
    get_db,
    get_logger,
    get_user_service_dep,
    list_deployments as list_deployments_logic,
    oauth2_scheme,
    process_chat,
    require_admin_access,
    run_deployed_agent as run_deployed_agent_logic,
    undeploy_agent,
    validate_output_against_schema,
)
from models.agent import (
    Agent,
    CreateAgentRequest,
    DeployedApi,
    GenerateCodeRequest,
    GenerateCodeResponse,
    RunCodeRequest,
    RunCodeResponse,
    UpdateAgentRequest,
)
from models.chat import ChatRequest, ChatResponse, ProviderConfig
from models.demo import (
    CreateDemoAppRequest,
    DemoApp,
    GenerateDemoCodeRequest,
    GenerateDemoCodeResponse,
)
from models.data_store import (
    ClearNamespaceResponse,
    DataStoreRecord,
    NamespaceListResponse,
    NamespaceStats,
    SetRecordRequest,
)
from models.user import User, ApiKeys
from services.database_service import DatabaseService
from services.data_store_service import (
    DataStoreService,
    get_data_store_service,
)
from services.mcp_client_service import McpClientService, get_mcp_client_service
from services.observability_service import (
    ObservabilityService,
    get_observability_service,
    get_request_user_id,
    get_sanitized_request_data,
)
from services.user_service import UserService
from time_utils import naive_utc_now


router = APIRouter()


async def _verify_session_cookie(request: Request, sid: str) -> Optional[dict]:
    """Check for a session cookie. Returns a user dict on success,
    None if no session could be resolved (so the caller falls back to the
    legacy Firebase path).

    The user dict shape matches what the rest of the code expects from
    Firebase's verify_id_token: at minimum ``uid`` and ``email``. We
    augment with session-specific fields (``workspaces``, ``is_site_admin``,
    ``provider_type``) so downstream code gated on auth can read
    them directly.
    """
    try:
        from services.session_service import get_session_service
    except Exception:
        return None
    from services.database_service import get_database_service
    db = get_database_service(settings)
    svc = get_session_service(db)
    session = await svc.get_by_id(sid)
    if not session:
        return None
    user = {
        "uid": session.user_uid,
        "email": session.email,
        "name": session.display_name,
        "displayName": session.display_name,
        "provider_type": session.provider_type,
        "workspaces": [w.model_dump(by_alias=True) for w in session.workspaces],
        "is_site_admin": session.is_site_admin,
        "auth_mode": "session",
    }
    request.state.user = user
    return user


async def _verify_firebase_token(request: Request, token: str):
    if not token:
        request.state.user = {"uid": "anonymous"}
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        from firebase_admin import auth
    except Exception as exc:  # pragma: no cover - optional dependency
        request.state.user = {"uid": "auth-error"}
        raise HTTPException(status_code=500, detail=f"Authentication error: {exc}")

    try:
        decoded_token = auth.verify_id_token(token)
        decoded_token.setdefault("auth_mode", "firebase")
        request.state.user = decoded_token
        return decoded_token
    except auth.InvalidIdTokenError:
        request.state.user = {"uid": "invalid-token"}
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as exc:  # pragma: no cover - passthrough
        request.state.user = {"uid": "auth-error"}
        raise HTTPException(status_code=500, detail=f"Authentication error: {exc}")


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    """
    Dependency to authenticate a request. Supports two modes:

      1. Session cookie (``gofannon_sid``) -- checked first.
      2. Legacy Firebase bearer token -- fallback when ``APP_ENV`` is
         ``firebase``.

    If neither is present, returns 401. There is no unauthenticated
    fallthrough; dev users get a session cookie through the dev_stub
    provider's picker page.

    Attaches the user object to request.state for observability.
    """
    # Short-circuit: ObservabilityMiddleware resolves
    # the session cookie before any route runs so request logs can include
    # the authenticated user_id even on public endpoints. When that happened
    # this request, the session lookup has already been performed and the
    # user dict is exactly what _verify_session_cookie would return. Reuse
    # it instead of redoing the same DB roundtrip.
    existing = getattr(request.state, "user", None)
    if isinstance(existing, dict) and existing.get("auth_mode") == "session":
        return existing

    # 1) Session cookie
    sid = request.cookies.get("gofannon_sid")
    if sid:
        user = await _verify_session_cookie(request, sid)
        if user:
            return user
        # Cookie present but invalid/expired -- don't fall through to
        # Firebase with stale cookie. Return 401 so the client clears it.
        # emit X-Auth-Reason so the SPA distinguishes session
        # expiry from authz-denied for a better re-login UX.
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid",
            headers={"X-Auth-Reason": "session_expired"},
        )

    # 2) Legacy Firebase path
    if settings.APP_ENV == "firebase":
        return await _verify_firebase_token(request, token)

    # emit X-Auth-Reason for the SPA's expiry modal.
    raise HTTPException(
        status_code=401,
        detail="Not authenticated. Session cookie missing or invalid.",
        headers={"X-Auth-Reason": "not_authenticated"},
    )


class ListMcpToolsRequest(BaseModel):
    mcp_url: str
    auth_token: Optional[str] = None


class ClientLogPayload(BaseModel):
    eventType: str
    message: str
    level: str = "INFO"
    metadata: Optional[Dict[str, Any]] = None


class FetchSpecRequest(BaseModel):
    url: str


class UpdateMonthlyAllowanceRequest(BaseModel):
    monthly_allowance: float = Field(..., alias="monthlyAllowance")

    model_config = ConfigDict(populate_by_name=True)


class UpdateResetDateRequest(BaseModel):
    allowance_reset_date: float = Field(..., alias="allowanceResetDate")

    model_config = ConfigDict(populate_by_name=True)


class UpdateSpendRemainingRequest(BaseModel):
    spend_remaining: float = Field(..., alias="spendRemaining")

    model_config = ConfigDict(populate_by_name=True)


class AddUsageRequest(BaseModel):
    response_cost: float = Field(..., alias="responseCost")
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class AdminUpdateUserRequest(BaseModel):
    monthly_allowance: Optional[float] = Field(default=None, alias="monthlyAllowance")
    allowance_reset_date: Optional[float] = Field(default=None, alias="allowanceResetDate")
    spend_remaining: Optional[float] = Field(default=None, alias="spendRemaining")

    model_config = ConfigDict(populate_by_name=True)


# --- Routes ---
@router.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}


@router.post("/log/client", status_code=202)
async def log_client_event(
    payload: ClientLogPayload,
    request: Request,
    logger: ObservabilityService = Depends(get_logger)
):
    """Receives and logs an event from the frontend client."""
    user_id = get_request_user_id(request)

    metadata = payload.metadata or {}
    metadata['client_host'] = request.client.host if request.client else "unknown"
    metadata['user_agent'] = request.headers.get("user-agent")

    logger.log(
        event_type=payload.eventType,
        message=payload.message,
        level=payload.level,
        service="webui",
        user_id=user_id,
        metadata=metadata
    )
    return {"status": "logged"}


@router.get("/providers")
def get_providers(user: dict = Depends(get_current_user)):
    """Get all available providers and their configurations"""
    return get_available_providers(user.get("uid", "anonymous"), user)


@router.get("/providers/{provider}")
def get_provider_config_route(provider: str, user: dict = Depends(get_current_user)):
    """Get configuration for a specific provider"""
    available_providers = get_available_providers(user.get("uid", "anonymous"), user)
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    return available_providers[provider]


@router.get("/providers/{provider}/models")
def get_provider_models(provider: str, user: dict = Depends(get_current_user)):
    """Get available models for a provider"""
    available_providers = get_available_providers(user.get("uid", "anonymous"), user)
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    return list(available_providers[provider]["models"].keys())


@router.get("/providers/{provider}/models/{model}")
def get_model_config(provider: str, model: str, user: dict = Depends(get_current_user)):
    """Get configuration for a specific model"""
    available_providers = get_available_providers(user.get("uid", "anonymous"), user)
    if provider not in available_providers:
        raise HTTPException(status_code=404, detail="Provider not found or not configured")
    if model not in available_providers[provider]["models"]:
        raise HTTPException(status_code=404, detail="Model not found")
    return available_providers[provider]["models"][model]


@router.get("/users/me", response_model=User)
def get_current_user_profile(user: dict = Depends(get_current_user), user_service: UserService = Depends(get_user_service_dep)):
    return user_service.get_user(user.get("uid", "anonymous"), user)


@router.get("/admin/users", response_model=List[User])
def list_all_users(
    user_service: UserService = Depends(get_user_service_dep),
    _: None = Depends(require_admin_access),
):
    return user_service.list_users()


@router.put("/admin/users/{user_id}", response_model=User)
def update_user_allowances(
    user_id: str,
    request: AdminUpdateUserRequest,
    user_service: UserService = Depends(get_user_service_dep),
    _: None = Depends(require_admin_access),
):
    return user_service.update_user_usage_info(
        user_id,
        monthly_allowance=request.monthly_allowance,
        allowance_reset_date=request.allowance_reset_date,
        spend_remaining=request.spend_remaining,
    )


@router.put("/users/me/monthly-allowance", response_model=User)
def set_monthly_allowance(
    request: UpdateMonthlyAllowanceRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.set_monthly_allowance(user.get("uid", "anonymous"), request.monthly_allowance, user)


@router.put("/users/me/allowance-reset-date", response_model=User)
def set_allowance_reset_date(
    request: UpdateResetDateRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.set_reset_date(user.get("uid", "anonymous"), request.allowance_reset_date, user)


@router.post("/users/me/reset-allowance", response_model=User)
def reset_allowance(user: dict = Depends(get_current_user), user_service: UserService = Depends(get_user_service_dep)):
    return user_service.reset_allowance(user.get("uid", "anonymous"), user)


@router.put("/users/me/spend-remaining", response_model=User)
def update_spend_remaining(
    request: UpdateSpendRemainingRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.update_spend_remaining(user.get("uid", "anonymous"), request.spend_remaining, user)


@router.post("/users/me/usage", response_model=User)
def add_usage_entry(
    request: AddUsageRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    return user_service.add_usage(user.get("uid", "anonymous"), request.response_cost, request.metadata, user)


# --- API Key Management Routes ---

@router.get("/users/me/api-keys", response_model=ApiKeys)
def get_user_api_keys(
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    """Get the current user's API keys (keys are masked for security)"""
    return user_service.get_api_keys(user.get("uid", "anonymous"), user)


class UpdateApiKeyRequest(BaseModel):
    provider: str
    api_key: str

    model_config = ConfigDict(populate_by_name=True)


@router.put("/users/me/api-keys", response_model=User)
def update_user_api_key(
    request: UpdateApiKeyRequest,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    """Update an API key for a specific provider"""
    return user_service.update_api_key(
        user.get("uid", "anonymous"), 
        request.provider, 
        request.api_key, 
        user
    )


@router.delete("/users/me/api-keys/{provider}", response_model=User)
def delete_user_api_key(
    provider: str,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    """Delete (clear) an API key for a specific provider"""
    return user_service.delete_api_key(user.get("uid", "anonymous"), provider, user)


@router.get("/users/me/api-keys/{provider}/effective")
def get_effective_api_key(
    provider: str,
    user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep),
):
    """
    Check if an effective API key exists for a provider.
    Returns whether a key is available (does not expose the actual key).
    """
    key = user_service.get_effective_api_key(user.get("uid", "anonymous"), provider, user)
    return {
        "provider": provider,
        "has_key": key is not None and len(key) > 0,
        "source": "user" if user_service.get_api_keys(user.get("uid", "anonymous"), user).dict().get(f"{provider}_api_key") else ("env" if key else None)
    }


@router.post("/chat")
async def chat(request: ChatRequest, req: Request, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """Submit a chat request and get a ticket ID"""
    ticket_id = str(uuid.uuid4())
    background_tasks.add_task(process_chat, ticket_id, request, user, req)
    return ChatResponse(
        ticket_id=ticket_id,
        status="pending"
    )


@router.get("/chat/{ticket_id}")
async def get_chat_status(ticket_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get the status and result of a chat request"""
    try:
        ticket_data = db.get("tickets", ticket_id)
        return ChatResponse(
            ticket_id=ticket_data.get("_id", ticket_id),
            status=ticket_data["status"],
            result=ticket_data.get("result"),
            error=ticket_data.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/config")
async def update_session_config(session_id: str, config: ProviderConfig, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Update session configuration"""
    try:
        session_doc = db.get("sessions", session_id)
    except HTTPException as e:
        if e.status_code == 404:
            session_doc = {"created_at": naive_utc_now().isoformat()}
        else:
            raise

    session_doc["provider_config"] = config.dict()
    session_doc["updated_at"] = naive_utc_now().isoformat()

    db.save("sessions", session_id, session_doc)
    return {"message": "Configuration updated", "session_id": session_id}


@router.get("/sessions/{session_id}/config")
async def get_session_config(session_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get session configuration"""
    session_doc = db.get("sessions", session_id)
    return session_doc.get("provider_config")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Delete a session"""
    db.delete("sessions", session_id)
    return {"message": "Session deleted"}


@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "user-service"}


@router.post("/agents", response_model=Agent, status_code=201)
async def create_agent(
    request: CreateAgentRequest,
    req: Request,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Saves a new agent configuration to the database."""
    agent_data_internal_names = request.model_dump(by_alias=True)
    agent = Agent(**agent_data_internal_names)

    saved_doc_data = agent.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("agents", agent.id, saved_doc_data)

    agent.rev = saved_doc.get("rev")

    logger.log(
        "user_action", f"Agent '{agent.name}' created.",
        user_id=user.get("uid"),
        metadata={"agent_id": agent.id, "agent_name": agent.name, "request": get_sanitized_request_data(req)}
    )
    return agent


@router.get("/agents", response_model=List[Agent])
async def list_agents(
    req: Request,
    db = Depends(get_async_db),  # async shim — don't block event loop
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Lists all saved agents."""
    all_docs = await db.list_all("agents")
    logger.log("user_action", "Listed all agents.", user_id=user.get("uid"), metadata={"request": get_sanitized_request_data(req)})
    return [Agent(**doc) for doc in all_docs]


@router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific agent by its ID."""
    agent_doc = db.get("agents", agent_id)
    return Agent(**agent_doc)


@router.get("/agents/{agent_id}/chain")
async def get_agent_chain(
    agent_id: str,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return the transitive call graph for an agent.

    Walks gofannon_agents dependencies recursively (bounded depth, cycle-safe)
    and emits an MCP-server leaf node per distinct tool URL. Used by the
    Chain View UI to show what other agents and tools this agent reaches.
    """
    return await build_agent_chain(agent_id, db)


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    req: Request,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Deletes an agent by its ID.

    Always runs undeploy_agent first, which scans the deployments collection
    by the `agentId` field and removes every matching deployment doc. That
    covers friendly_name renames and pre-existing orphans.
    """
    try:
        # undeploy_agent is now idempotent and self-healing: safe to call
        # unconditionally, including when there are no deployments or when
        # the agent's friendly_name no longer matches any deployment.
        await undeploy_agent(agent_id, db)
        db.delete("agents", agent_id)
        logger.log("user_action", f"Agent '{agent_id}' deleted.", user_id=user.get("uid"), metadata={"agent_id": agent_id, "request": get_sanitized_request_data(req)})
        return
    except HTTPException as e:
        raise e


@router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: str,
    request: UpdateAgentRequest,
    req: Request,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger)
):
    """Updates an existing agent configuration."""
    existing_doc = db.get("agents", agent_id)

    update_data = request.model_dump(by_alias=True, exclude_unset=True)
    merged_data = {**existing_doc, **update_data}

    merged_data.pop("_rev", None)
    merged_data.pop("_id", None)

    updated_agent = Agent(_id=agent_id, **merged_data)

    if "createdAt" in existing_doc:
        updated_agent.created_at = existing_doc["createdAt"]
    elif "created_at" in existing_doc:
        updated_agent.created_at = existing_doc["created_at"]
    updated_agent.updated_at = naive_utc_now()

    saved_doc_data = updated_agent.model_dump(by_alias=True, mode="json")
    saved_doc_data["_rev"] = existing_doc.get("_rev")

    saved_doc = db.save("agents", agent_id, saved_doc_data)
    updated_agent.rev = saved_doc.get("rev")

    logger.log(
        "user_action", f"Agent '{updated_agent.name}' updated.",
        user_id=user.get("uid"),
        metadata={"agent_id": agent_id, "agent_name": updated_agent.name, "request": get_sanitized_request_data(req)}
    )
    return updated_agent


@router.post("/mcp/tools")
async def list_mcp_tools(
    request: ListMcpToolsRequest,
    mcp_service: McpClientService = Depends(get_mcp_client_service),
    user: dict = Depends(get_current_user)
):
    """Connects to a remote MCP server and lists its available tools."""
    tools = await mcp_service.list_tools_for_server(request.mcp_url, request.auth_token)
    return {"mcp_url": request.mcp_url, "tools": tools}


@router.post("/agents/generate-code", response_model=GenerateCodeResponse)
async def generate_agent_code(request: GenerateCodeRequest, user: dict = Depends(get_current_user)):
    """Generates agent code based on the provided configuration."""
    from agent_factory import generate_agent_code as generate_code_function
    user_basic_info = {
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }
    code = await generate_code_function(request, user_id=user.get("uid"), user_basic_info=user_basic_info)
    return code


@router.post("/specs/fetch")
async def fetch_spec_from_url(request: FetchSpecRequest, user: dict = Depends(get_current_user)):
    """Fetches OpenAPI/Swagger spec content from a public URL."""
    return await fetch_spec_content(request.url)


@router.post("/agents/{agent_id}/deploy", status_code=201)
async def deploy_agent_route(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Registers an agent for internal REST deployment."""
    return await deploy_agent(agent_id, db)


@router.delete("/agents/{agent_id}/undeploy", status_code=204)
async def undeploy_agent_route(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Removes an agent from the internal REST deployment registry."""
    await undeploy_agent(agent_id, db)
    return


@router.get("/agents/{agent_id}/deployment")
async def get_agent_deployment_route(agent_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Checks if an agent is deployed and returns its public-facing name."""
    return await get_agent_deployment(agent_id, db)


@router.get("/deployments", response_model=List[DeployedApi])
async def list_deployments_route(db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Lists all deployed agents/APIs with their relevant details."""
    deployments = await list_deployments_logic(db)
    return [DeployedApi(**dep) for dep in deployments]


@router.post("/agents/run-code/stream")
async def run_agent_code_stream(
    request: RunCodeRequest,
    req: Request,
    user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    logger: ObservabilityService = Depends(get_logger),
):
    """Stream a sandbox run as Server-Sent Events.

    Emits one SSE 'event' frame per Trace event as the agent runs,
    then a final 'done' frame carrying {outcome, result, error,
    schema_warnings, ops_log}. The non-streaming /agents/run-code
    endpoint remains for callers that want a bulk response.

    Frame format:
        event: trace
        data: {{...event dict...}}

        event: done
        data: {{outcome, result, error, schema_warnings, ops_log}}
    """
    logger.log(
        "user_action",
        "Attempting to run agent code in sandbox (streaming).",
        user_id=user.get("uid"),
        metadata={"request": get_sanitized_request_data(req)},
    )

    user_basic_info = {
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }

    # Trace + queue. The queue is unbounded — emitters never block —
    # because the alternative (drop events on slow consumer) is
    # worse than memory pressure. The trace's own 2000-event cap
    # is the real bound.
    trace = Trace()
    queue: asyncio.Queue = asyncio.Queue()
    # Pass the current loop into attach_queue so the agent\'s
    # side-thread (Path A executor) can emit events into this queue
    # via threadsafe routing. Without the loop arg, _publish would
    # call put_nowait directly from the agent thread and corrupt
    # the queue\'s asyncio waiters.
    trace.attach_queue(queue, loop=asyncio.get_running_loop())

    # Register this run with the registry + cancel registry so the client 
    # can address it for stop. Stream's runId is emitted as the first SSE event 
    # ("run_id") so RunsScreen can capture it and enable the Stop button. The 
    # streaming endpoint still pins its worker (we haven't moved to the 
    # start-then-subscribe model here), but the runId binding makes stop 
    # wiring possible.
    from services.run_registry import get_run_registry
    from services.run_cancel_registry import publish as register_cancel_token
    from services.cancel_token import CancelToken, bind_token, AgentStopped
    from services.agent_executor import execute_in_thread

    _registry = get_run_registry()
    _run_record = _registry.new_record(
        user_id=user.get("uid") or "anonymous",
        agent_name=request.friendly_name or "sandbox_agent",
        agent_id=request.agent_id,
        input_dict=request.input_dict,
    )
    _cancel_token = CancelToken()
    register_cancel_token(_run_record.run_id, _cancel_token)
    bind_token(_cancel_token)

    # Sentinel posted to the queue when the agent finishes (success
    # or error) so the streaming generator knows to stop pulling.
    DONE_SENTINEL = object()

    # Holders for the final result. Set by the agent task; read by
    # the streamer when it sees DONE_SENTINEL.
    final = {"result": None, "error": None, "schema_warnings": None, "ops_log": None}

    async def run_agent_task():
        try:
            # Path A: run the agent in a separate OS thread with its
            # own event loop. This keeps THIS worker\'s loop free to
            # serve other requests while the agent does sync CouchDB
            # calls. The factory shape (lambda returning a coro) is
            # what executor.execute_in_thread expects -- the coro
            # has to be instantiated inside the target thread to bind
            # to the right loop.
            def _build_agent_coro():
                return _execute_agent_code(
                    code=request.code,
                    input_dict=request.input_dict,
                    tools=request.tools,
                    gofannon_agents=request.gofannon_agents,
                    db=db,
                    llm_settings=request.llm_settings,
                    user_id=user.get("uid"),
                    user_basic_info=user_basic_info,
                    agent_name=request.friendly_name or "sandbox_agent",
                    trace=trace,
                    env_vars=request.env_vars,
                )
            result, ops_log = await execute_in_thread(
                _build_agent_coro,
                _cancel_token,
                thread_name=f"agent-{_run_record.run_id[:8]}",
            )
            schema_warnings = validate_output_against_schema(result, request.output_schema)
            if schema_warnings:
                logger.log(
                    "WARNING", "output_schema_mismatch",
                    f"Agent output did not match declared schema: {schema_warnings}",
                    metadata={"warnings": schema_warnings},
                )
            final["result"] = result
            final["schema_warnings"] = schema_warnings or None
            final["ops_log"] = ops_log or None
            # Update the run registry so /runs and /runs/<id> reflect
            # completion. Without this, every streaming run sits as
            # 'running' until eviction at EVICTION_TTL_SECONDS (1 hour).
            try:
                _registry.mark_complete(
                    _run_record,
                    status="success",
                    result=result,
                    schema_warnings=schema_warnings or None,
                    ops_log=ops_log or None,
                )
            except Exception:
                logger.log(
                    "ERROR", "run_registry_update_failed",
                    f"mark_complete failed for run {_run_record.run_id}",
                    metadata={"traceback": traceback.format_exc()},
                )
            logger.log(
                "INFO", "sandbox_run",
                "Agent code executed successfully (streaming).",
                metadata={"request": get_sanitized_request_data(req)},
            )
        except asyncio.CancelledError:
            # event_generator's finally cancels agent_task when the
            # SSE stream closes mid-run (client disconnect, or the
            # frontend's handleStop aborting the fetch). Without
            # explicit handling here, CancelledError would skip past
            # mark_complete and leave the registry record stuck at
            # 'running' indefinitely -- this was the 'silent death'
            # case where no traceback was logged and the run never
            # got a final status.
            #
            # Treat the cancel as a stop: flip the token (if not
            # already) so the agent thread terminates at its next
            # structural boundary, then mark the registry stopped.
            # Re-raise so upstream asyncio task accounting still
            # treats this task as cancelled.
            if not _cancel_token.is_stopped():
                _cancel_token.request_stop()
            try:
                _registry.mark_complete(
                    _run_record,
                    status="stopped",
                    error="Run cancelled (SSE stream closed)",
                    ops_log=final.get("ops_log"),
                )
            except Exception:
                logger.log(
                    "ERROR", "run_registry_update_failed",
                    f"mark_complete failed for run {_run_record.run_id}",
                    metadata={"traceback": traceback.format_exc()},
                )
            logger.log(
                "INFO", "sandbox_run_cancelled",
                f"Streaming run cancelled (SSE closed) for run {_run_record.run_id}",
                metadata={"request": get_sanitized_request_data(req)},
            )
            raise
        except (Exception, AgentStopped) as e:
            # AgentStopped now inherits from BaseException so user code
            # can't swallow it via except Exception; we have to name it
            # explicitly here to keep our cleanup-and-mark-complete
            # handler covering it. Same handler logic for error and
            # stop cases below.
            final["error"] = f"{type(e).__name__}: {e}"
            # Distinguish a user-initiated stop from a genuine error.
            # AgentStopped is raised by check_should_stop() when the
            # cancel token flips, propagated by the data store / LLM
            # services. Also check the token directly in case the
            # agent did pure-Python work after the stop, didn't hit
            # a structural check, and exited some other way.
            is_stop = isinstance(e, AgentStopped) or _cancel_token.is_stopped()
            # Wrap registry write in its own try -- if mark_complete
            # itself raises (registry race, etc.), we still want the
            # log line and the DONE_SENTINEL to reach the stream so
            # the client doesn't hang. Leaving the record as 'running'
            # is the symptom we're explicitly trying to avoid.
            try:
                _registry.mark_complete(
                    _run_record,
                    status="stopped" if is_stop else "error",
                    error=f"{type(e).__name__}: {e}",
                    ops_log=final.get("ops_log"),
                )
            except Exception:
                logger.log(
                    "ERROR", "run_registry_update_failed",
                    f"mark_complete failed for run {_run_record.run_id}",
                    metadata={"traceback": traceback.format_exc()},
                )
            logger.log(
                "ERROR", "sandbox_run_failure",
                f"Error running agent code (streaming, trace events: {len(trace.events)})",
                metadata={
                    "traceback": traceback.format_exc(),
                    "request": get_sanitized_request_data(req),
                },
            )
        finally:
            await queue.put(DONE_SENTINEL)

    async def event_generator():
        # emit run_id as the first frame so the
        # client can render the Stop button without waiting for the
        # first trace event.
        yield f"event: run_id\ndata: {json.dumps({'runId': _run_record.run_id, 'status': 'running'})}\n\n"

        # Kick off the agent. The task runs concurrently with this
        # generator; events flow through the queue.
        agent_task = asyncio.create_task(run_agent_task())
        # Give the registry a STRONG reference to the task. This is required
        # now that the finally block below no longer awaits or cancels it:
        # once this generator's frame is gone, the registry is the only thing
        # keeping the task reachable, and asyncio holds only weak references
        # ("Save a reference to the result of create_task, to avoid a task
        # disappearing mid-execution" -- asyncio docs).
        #
        # The non-streaming /agents/run-code/start handler already does this;
        # the streaming path never did, because it always awaited or cancelled
        # before returning. Detaching without binding would leave an
        # hours-long pipeline eligible for GC.
        _registry.bind_task(_run_record, agent_task)

        try:
            while True:
                # Use a heartbeat-style wait so a hung agent eventually
                # frees the connection if the client disconnected.
                # 10s gives margin against Apache's 60s Timeout even
                # if intermediate proxies buffer small writes.
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=10.0)
                except asyncio.TimeoutError:
                    # Heartbeat comment frame keeps proxies from
                    # idling out the connection.
                    yield ": heartbeat\n\n"
                    continue

                if item is DONE_SENTINEL:
                    # Agent task finished. Send the done frame with
                    # final state and exit.
                    payload = json.dumps({
                        "outcome": "error" if final["error"] else "success",
                        "result": final["result"],
                        "error": final["error"],
                        "schemaWarnings": final["schema_warnings"],
                        "opsLog": final["ops_log"],
                    })
                    yield f"event: done\ndata: {payload}\n\n"
                    break
                else:
                    # Trace event. JSON-encode with default=str so any
                    # stray non-serialisable values become strings
                    # rather than crashing the stream.
                    payload = json.dumps(item, default=str)
                    yield f"event: trace\ndata: {payload}\n\n"
        finally:
            # Client disconnect DETACHES from the run; it does not kill it.
            #
            # The previous behavior (await up to 5s, then cancel) meant a tab
            # close, a browser crash, a network glitch, or a render error in
            # the SSE reader all killed an in-flight run. For LLM pipelines
            # that run for minutes to hours, the 5s branch was always the kill
            # path -- it cost 61 of 64 batches on one run and a full scan on
            # another.
            #
            # The task continues; the registry holds a strong reference to it
            # (bound above) and tracks completion via mark_complete in
            # run_agent_task's handlers. A new SSE connection to
            # /runs/{run_id}/stream re-attaches with replay-then-live.
            # POST /runs/{run_id}/stop is now the ONLY way to cancel work --
            # implicit cancellation is gone by design.
            if not agent_task.done():
                logger.log(
                    "INFO",
                    "sse_disconnect_run_continues",
                    f"SSE closed for run {_run_record.run_id}; run continues "
                    f"in background (detached)",
                    metadata={"run_id": _run_record.run_id},
                )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # Prevent intermediate proxies from buffering the response.
            # Without this, nginx/cloudflare can hold onto chunks until
            # the response closes — defeats the point of streaming.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/agents/run-code/start", status_code=202)
async def start_agent_run(
    request: RunCodeRequest,
    req: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    logger: ObservabilityService = Depends(get_logger),
):
    """Fire-and-forget agent run. Returns ``{run_id}`` immediately.

    The agent executes in a background asyncio task registered with
    RunRegistry. Clients subscribe via ``GET /runs/{run_id}/stream``
    to receive trace events with replay-then-live semantics.
    """
    from services.run_registry import get_run_registry

    registry = get_run_registry()
    record = registry.new_record(
        user_id=user.get("uid") or "anonymous",
        agent_name=request.friendly_name or "sandbox_agent",
    )

    user_basic_info = {
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }

    async def runner():
        try:
            result, ops_log = await _execute_agent_code(
                code=request.code,
                input_dict=request.input_dict,
                tools=request.tools,
                gofannon_agents=request.gofannon_agents,
                db=db,
                llm_settings=request.llm_settings,
                user_id=user.get("uid"),
                user_basic_info=user_basic_info,
                agent_name=record.agent_name,
                trace=record.trace,
            )
            warnings = validate_output_against_schema(result, request.output_schema)
            registry.mark_complete(
                record,
                status="success",
                result=result,
                schema_warnings=warnings or None,
                ops_log=ops_log or None,
            )
        except Exception as e:
            logger.log(
                "ERROR",
                "run_failure",
                f"Run {record.run_id} failed: {type(e).__name__}",
                metadata={"traceback": traceback.format_exc()},
            )
            registry.mark_complete(
                record,
                status="error",
                error=f"{type(e).__name__}: {e}",
            )

    task = asyncio.create_task(runner())
    registry.bind_task(record, task)

    return {"runId": record.run_id, "status": record.status}


# A run that has appended no trace event for this long is treated as
# abandoned by force_complete_run. Long enough that a slow LLM call
# (the ASVS pipeline routinely runs 300-600s per call) is never
# mistaken for a dead worker; short enough to be useful.
STALE_RUN_SECONDS = 900


class ForceCompleteRequest(BaseModel):
    """Body for POST /runs/{run_id}/force-complete."""

    force: bool = False


def _run_idle_seconds(record) -> Optional[float]:
    """Seconds since this run last appended a trace event.

    Falls back to time since start when the run has produced no events
    at all. Returns None if neither timestamp is usable, in which case
    the caller treats staleness as unknown and allows the clear.
    """
    from datetime import datetime, timezone

    def _age(ts):
        if not ts:
            return None
        try:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            return None

    events = list(getattr(record.trace, "events", []) or [])
    for ev in reversed(events):
        if isinstance(ev, dict):
            age = _age(ev.get("timestamp") or ev.get("ts"))
            if age is not None:
                return age
        break

    return _age(getattr(record, "started_at", None))


@router.get("/runs")
async def list_runs(
    user: dict = Depends(get_current_user),
    agent_id: Optional[str] = None,
):
    """List the current user's recent runs (in-memory; up to 100).

    Pass ``?agent_id=<id>`` to restrict to one agent — the per-agent
    runs screen uses this so its past-runs list only shows that
    agent's history rather than everything the user has ever run.
    """
    from services.run_registry import get_run_registry
    registry = get_run_registry()
    records = registry.list_for_user(user.get("uid") or "", agent_id=agent_id)
    return {"runs": [r.to_summary() for r in records]}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user: dict = Depends(get_current_user)):
    """Fetch a run's full state. Returns 404 if not found or not owned."""
    from services.run_registry import get_run_registry
    registry = get_run_registry()
    record = registry.get(run_id)
    if record is None or record.user_id != user.get("uid"):
        # 404 not 403 — don't leak existence to non-owners.
        raise HTTPException(status_code=404, detail="Run not found")
    return record.to_full()


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, user: dict = Depends(get_current_user)):
    """Subscribe to a run's trace events via SSE. Replay-then-live.

    Sends every event already in ``record.trace.events`` first, then
    transitions to live events from a per-subscriber queue. Emits a
    final ``done`` frame when the run completes. Disconnecting does
    NOT terminate the underlying run.
    """
    from services.run_registry import get_run_registry, DONE_SENTINEL
    registry = get_run_registry()
    record = registry.get(run_id)
    if record is None or record.user_id != user.get("uid"):
        raise HTTPException(status_code=404, detail="Run not found")

    queue: asyncio.Queue = asyncio.Queue()
    record.trace.add_subscriber(queue, loop=asyncio.get_running_loop())

    async def event_generator():
        # 1. Emit the run_id as the first frame so clients can correlate.
        yield f"event: run_id\ndata: {json.dumps({'runId': run_id})}\n\n"

        # 2. Replay phase — snapshot the events list to avoid races with
        #    appends from the running task. Each replayed event is sent
        #    before we begin consuming the queue.
        replay = list(record.trace.events)
        for ev in replay:
            yield f"event: trace\ndata: {json.dumps(ev, default=str)}\n\n"

        # 3. If the run already finished, drain any "missed" tail from
        #    the queue (the fanout might have placed events while we
        #    were replaying), then emit done and exit.
        if record.status != "running":
            # Send any queued items that arrived during replay.
            while not queue.empty():
                item = queue.get_nowait()
                if item is DONE_SENTINEL:
                    break
                yield f"event: trace\ndata: {json.dumps(item, default=str)}\n\n"
            done_payload = json.dumps({
                "outcome": record.status,
                "result": record.result,
                "error": record.error,
                "schemaWarnings": record.schema_warnings,
                "opsLog": record.ops_log,
            })
            yield f"event: done\ndata: {done_payload}\n\n"
            return

        # 4. Live phase — pull from the queue until DONE_SENTINEL.
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=10.0)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue
                if item is DONE_SENTINEL:
                    done_payload = json.dumps({
                        "outcome": record.status,
                        "result": record.result,
                        "error": record.error,
                        "schemaWarnings": record.schema_warnings,
                        "opsLog": record.ops_log,
                    })
                    yield f"event: done\ndata: {done_payload}\n\n"
                    return
                yield f"event: trace\ndata: {json.dumps(item, default=str)}\n\n"
        finally:
            record.trace.remove_subscriber(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/runs/{run_id}/stop", status_code=202)
async def stop_run(
    run_id: str,
    user: dict = Depends(get_current_user),
):
    """Request cooperative stop of an in-flight run.

    Sets the run's ``CancelToken``. The next structural boundary
    inside the agent (LLM call, data-store op, gofannon-client call,
    tool entry) raises ``AgentStopped`` and the run terminates with
    status ``stopped``. In-flight LLM requests finish naturally;
    cleanup handlers (``finally:`` blocks, ``httpx`` client closes)
    run before exit.

    Authorization: only the run's owner may stop it; widening to
    workspace membership is a later change.
    """
    # cross-worker stop: the registry's request_stop
    # method handles both the local-token-flip fast path (when this
    # worker happens to own the run) and the CouchDB stop_requested
    # write that the owning worker's polling task picks up.
    from services.run_registry import get_run_registry
    outcome = get_run_registry().request_stop(run_id, user.get("uid") or "")
    if outcome == "not_found":
        raise HTTPException(status_code=404, detail="Run not found or already complete")
    if outcome == "forbidden":
        # Match the pre-persistence behavior: don't leak existence of
        # other users' runs via a 403.
        raise HTTPException(status_code=404, detail="Run not found")
    # outcome is one of 'flipped_local' or 'persisted_remote'. Both
    # are success cases. The status text gives clients a hint about
    # whether the stop will be immediate (local) or has a small
    # polling-window latency (remote).
    return {"runId": run_id, "status": "stopping", "via": outcome}


@router.post("/runs/{run_id}/force-complete", status_code=200)
async def force_complete_run(
    run_id: str,
    request: ForceCompleteRequest = None,
    user: dict = Depends(get_current_user),
    logger: ObservabilityService = Depends(get_logger),
):
    """Manually clear a run that is stuck in 'running'.

    This is the escape hatch for orphaned records: a run whose owning
    worker died (api container restart, OOM kill) leaves a row that says
    'running' forever, because the task that would have called
    mark_complete no longer exists. POST /stop cannot help -- it flips a
    cancel token that nothing is left to observe.

    SAFETY: refuses by default unless the run has been silent for at
    least STALE_RUN_SECONDS. A healthy run appends trace events
    continuously, so a recent event is strong evidence the pipeline is
    alive and this is a misclick. Pass {"force": true} to override --
    the UI does that only behind a second confirmation.

    Marks the run 'error' rather than 'success': we do not know what the
    pipeline produced, and recording an unverified success would poison
    any downstream consumer that trusts the status field.
    """
    from services.run_registry import get_run_registry

    registry = get_run_registry()
    record = registry.get(run_id)
    if record is None or record.user_id != (user.get("uid") or ""):
        # Same 404-for-forbidden policy as stop_run: don't leak the
        # existence of other users' runs.
        raise HTTPException(status_code=404, detail="Run not found")

    if record.status != "running":
        # Already terminal. Idempotent success so a double-click from the
        # UI doesn't surface an error.
        return {
            "runId": run_id,
            "status": record.status,
            "changed": False,
            "detail": "Run was already complete.",
        }

    force = bool(request.force) if request is not None else False
    idle_seconds = _run_idle_seconds(record)

    if not force and idle_seconds is not None and idle_seconds < STALE_RUN_SECONDS:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Run produced an event {int(idle_seconds)}s ago and looks "
                f"alive. Use /runs/{run_id}/stop to cancel it, or retry with "
                f'{{"force": true}} to clear it anyway.'
            ),
        )

    # A live local task means this worker still owns a running pipeline.
    # Clearing the record without cancelling would orphan real work that
    # keeps consuming tokens, so cancel it too.
    if record.task is not None and not record.task.done():
        record.task.cancel()
        logger.log(
            "WARNING",
            "force_complete_cancelled_live_task",
            f"force-complete cancelled a still-live task for run {run_id}",
            metadata={"run_id": run_id, "idle_seconds": idle_seconds},
        )

    registry.mark_complete(
        record,
        status="error",
        error=(
            "Manually cleared by user. The run was stuck in 'running' with "
            f"no activity for {int(idle_seconds) if idle_seconds is not None else 'an unknown number of'} seconds; "
            "its owning worker had most likely exited. Any work it completed "
            "before being cleared is not reflected here."
        ),
    )
    logger.log(
        "user_action",
        "run_force_completed",
        f"Run {run_id} force-completed by user",
        user_id=user.get("uid"),
        metadata={"run_id": run_id, "idle_seconds": idle_seconds, "forced": force},
    )
    return {"runId": run_id, "status": "error", "changed": True}


@router.post("/agents/run-code", response_model=RunCodeResponse)
async def run_agent_code(
    request: RunCodeRequest,
    req: Request,
    user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    logger: ObservabilityService = Depends(get_logger)
):
    """Executes agent code in a sandboxed environment."""
    logger.log("user_action", "Attempting to run agent code in sandbox.", user_id=user.get("uid"), metadata={"request": get_sanitized_request_data(req)})
    try:
        user_basic_info = {
            "email": user.get("email"),
            "name": user.get("name") or user.get("displayName"),
        }
        # Per-request trace. Lives only for this invocation; events
        # are collected as the agent runs and shipped back in the
        # response. On failure we return a structured response with
        # error+trace so the Progress Log can show the partial trace
        # (rather than raising and losing the events the agent
        # already emitted).
        trace = Trace()

        try:
            result, ops_log = await _execute_agent_code(
                code=request.code,
                input_dict=request.input_dict,
                tools=request.tools,
                gofannon_agents=request.gofannon_agents,
                db=db,
                llm_settings=request.llm_settings,
                user_id=user.get("uid"),
                user_basic_info=user_basic_info,
                agent_name=request.friendly_name or "sandbox_agent",
                trace=trace,
                env_vars=request.env_vars,
            )
        except Exception as _exc:
            logger.log(
                "ERROR", "sandbox_run_failure",
                f"Error running agent code (trace events: {len(trace.events)})",
                metadata={"traceback": traceback.format_exc(), "request": get_sanitized_request_data(req)}
            )
            return RunCodeResponse(
                result=None,
                error=f"{type(_exc).__name__}: {_exc}",
                trace=trace.events or None,
            )

        # Advisory schema check: surface mismatches as warnings in the response.
        # Never fails the run — LLM compliance is best-effort.
        schema_warnings = validate_output_against_schema(result, request.output_schema)
        if schema_warnings:
            logger.log(
                "WARNING", "output_schema_mismatch",
                f"Agent output did not match declared schema: {schema_warnings}",
                metadata={"warnings": schema_warnings}
            )

        logger.log("sandbox_run", "Agent code executed successfully.", user_id=user.get("uid"), metadata={"request": get_sanitized_request_data(req)})
        return RunCodeResponse(
            result=result,
            schema_warnings=schema_warnings or None,
            ops_log=ops_log or None,
            trace=trace.events or None,
        )

    except Exception as e:
        error_str = f"{type(e).__name__}: {e}"
        tb_str = traceback.format_exc()

        logger.log(
            "ERROR", "sandbox_run_failure", f"Error running agent code: {error_str}",
            metadata={"traceback": tb_str, "request": get_sanitized_request_data(req)}
        )

        raise e


@router.post("/rest/{friendly_name}")
async def run_deployed_agent_route(
    friendly_name: str, 
    request: Request, 
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Run a deployed agent by its friendly_name. Requires authentication."""
    input_dict = await request.json()
    user_basic_info = {
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }
    return await run_deployed_agent_logic(
        friendly_name, 
        input_dict, 
        db, 
        user_id=user.get("uid"),
        user_basic_info=user_basic_info,
    )


@router.post("/rest/{friendly_name}/start", status_code=202)
async def start_deployed_agent_run(
    friendly_name: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: DatabaseService = Depends(get_db),
    logger: ObservabilityService = Depends(get_logger),
):
    """Run a DEPLOYED agent by friendly_name, detached. Returns ``{runId}``.

    This is the pairing of the two halves that already existed separately:

      * ``POST /rest/{friendly_name}`` has the right STATE model -- it loads
        code, tools, gofannon_agents and env_vars from the stored agent
        record, so the caller sends only inputs. But it awaits the result
        inline, which for a multi-hour pipeline means holding one HTTP
        connection open with no runId, no trace, and no way to stop it.

      * ``POST /agents/run-code/start`` has the right EXECUTION model --
        registry record, background task, replay-then-live streaming,
        stoppable -- but takes code and env_vars as a request payload, so
        every caller re-sends the agent (and its secrets) on every run.

    This endpoint loads from the record AND registers the run, so
    /runs/{runId}/stream and /runs/{runId}/stop work on it for free.

    Body is the agent's input_dict, exactly as for the synchronous route:

        POST /rest/asvs_orchestrate/start
        {"sourceRepo": "apache/apisix", "level": "L3", ...}

    Secrets that are genuinely per-run (source/output tokens) still travel
    in the body. Everything configured on the agent -- API keys, model
    tiers, timeouts -- does not.
    """
    from services.log_redaction import redact_in_place
    from services.run_registry import get_run_registry

    input_dict = await request.json()
    if not isinstance(input_dict, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object")

    # Resolve the deployment BEFORE registering a run, so an unknown
    # friendly_name is a clean 404 rather than a run that instantly fails.
    try:
        deployment_doc = db.get("deployments", friendly_name)
        agent_id = deployment_doc["agentId"]
        agent_data = db.get("agents", agent_id)
        agent = Agent(**agent_data)
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"No deployed agent named '{friendly_name}'. "
                       f"Deploy it first via POST /agents/{{agent_id}}/deploy.",
            )
        raise
    except KeyError:
        raise HTTPException(
            status_code=500,
            detail=f"Deployment '{friendly_name}' has no agentId; record is malformed.",
        )

    registry = get_run_registry()
    record = registry.new_record(
        user_id=user.get("uid") or "anonymous",
        agent_name=friendly_name,
        agent_id=agent_id,
        # The registry persists input_dict to CouchDB verbatim and returns it
        # from GET /runs/{run_id}, so the raw dict would write live tokens to
        # the database. redact_in_place() is the same filter agent_trace and
        # observability_service already use -- it matches on token SHAPE
        # (github_pat_, sk-ant-, AKIA..., JWT triplets, secret-shaped k=v)
        # rather than on key name, so it catches a credential wherever it sits.
        # copy.deepcopy first: the function mutates dicts in place, and the
        # agent below needs the unredacted inputs.
        input_dict=redact_in_place(copy.deepcopy(input_dict)),
    )

    user_basic_info = {
        "email": user.get("email"),
        "name": user.get("name") or user.get("displayName"),
    }

    async def runner():
        try:
            result, ops_log = await _execute_agent_code(
                code=agent.code,
                input_dict=input_dict,
                tools=agent.tools,
                gofannon_agents=agent.gofannon_agents,
                db=db,
                user_id=user.get("uid"),
                user_basic_info=user_basic_info,
                env_vars=getattr(agent, "env_vars", []),
                agent_name=friendly_name,
                trace=record.trace,
            )
            warnings = validate_output_against_schema(
                result, getattr(agent, "output_schema", None)
            )
            registry.mark_complete(
                record,
                status="success",
                result=result,
                schema_warnings=warnings or None,
                ops_log=ops_log or None,
            )
        except Exception as e:
            logger.log(
                "ERROR",
                "deployed_run_failure",
                f"Deployed run {record.run_id} ({friendly_name}) failed: {type(e).__name__}",
                metadata={"traceback": traceback.format_exc(),
                          "run_id": record.run_id,
                          "friendly_name": friendly_name},
            )
            registry.mark_complete(
                record,
                status="error",
                error=f"{type(e).__name__}: {e}",
            )

    task = asyncio.create_task(runner())
    # Strong reference; see the note at the streaming endpoint. Without this
    # the task is GC-eligible as soon as this handler returns.
    registry.bind_task(record, task)

    logger.log(
        "user_action",
        "deployed_run_started",
        f"Started deployed agent '{friendly_name}' as run {record.run_id}",
        user_id=user.get("uid"),
        metadata={"run_id": record.run_id, "friendly_name": friendly_name,
                  "agent_id": agent_id},
    )
    return {"runId": record.run_id, "status": record.status,
            "agentId": agent_id, "friendlyName": friendly_name}


@router.post("/demos/generate-code", response_model=GenerateDemoCodeResponse)
async def generate_demo_app_code(request: GenerateDemoCodeRequest, user: dict = Depends(get_current_user)):
    """
    Generates HTML/CSS/JS for a demo app based on a prompt and selected APIs.
    """
    from agent_factory.demo_factory import generate_demo_code
    try:
        user_basic_info = {
            "email": user.get("email"),
            "name": user.get("name") or user.get("displayName"),
        }
        code_response = await generate_demo_code(
            request,
            user_id=user.get("uid"),
            user_basic_info=user_basic_info,
        )
        return code_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating demo code: {e}")


@router.post("/demos", response_model=DemoApp, status_code=201)
async def create_demo_app(request: CreateDemoAppRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Saves a new demo app configuration."""
    demo_app_data = request.model_dump(by_alias=True)
    demo_app = DemoApp(**demo_app_data)
    saved_doc_data = demo_app.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("demos", demo_app.id, saved_doc_data)
    demo_app.rev = saved_doc.get("rev")
    return demo_app


@router.get("/demos", response_model=List[DemoApp])
async def list_demo_apps(db = Depends(get_async_db), user: dict = Depends(get_current_user)):
    """Lists all saved demo apps."""
    all_docs = await db.list_all("demos")
    return [DemoApp(**doc) for doc in all_docs]


@router.get("/demos/{demo_id}", response_model=DemoApp)
async def get_demo_app(demo_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Retrieves a specific demo app."""
    doc = db.get("demos", demo_id)
    return DemoApp(**doc)


@router.put("/demos/{demo_id}", response_model=DemoApp)
async def update_demo_app(demo_id: str, request: CreateDemoAppRequest, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Updates an existing demo app."""
    demo_app_data = request.model_dump(by_alias=True)
    updated_model = DemoApp(_id=demo_id, **demo_app_data)
    saved_doc_data = updated_model.model_dump(by_alias=True, mode="json")
    saved_doc = db.save("demos", demo_id, saved_doc_data)
    updated_model.rev = saved_doc.get("rev")
    return updated_model


@router.delete("/demos/{demo_id}", status_code=204)
async def delete_demo_app(demo_id: str, db: DatabaseService = Depends(get_db), user: dict = Depends(get_current_user)):
    """Deletes a demo app."""
    db.delete("demos", demo_id)
    return


# ---------------------------------------------------------------------------
# Data store routes
#
# The underlying DataStoreService is also used directly by the agent runtime
# (see AgentDataStoreProxy). These HTTP routes expose the same service for
# the Data Store Viewer UI: browsing namespaces, inspecting records, and
# admin edits.
# ---------------------------------------------------------------------------

def _get_data_store_dep(db: DatabaseService = Depends(get_db)) -> DataStoreService:
    return get_data_store_service(db)


def _namespace_stats_from_docs(docs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Aggregate raw record docs into per-namespace stats.

    Returned shape:
      { namespace: {recordCount, sizeBytes, agents, updatedAt} }

    Agents are the deduped union of createdByAgent and lastAccessedByAgent
    across every record. sizeBytes is a JSON-size estimate — cheap to compute
    and good enough for the UI's "1.2 MB" chips.
    """
    import json as _json
    buckets: Dict[str, Dict[str, Any]] = {}
    for doc in docs:
        ns = doc.get("namespace") or "default"
        b = buckets.setdefault(ns, {
            "recordCount": 0, "sizeBytes": 0, "agents": set(), "updatedAt": None,
        })
        b["recordCount"] += 1
        try:
            b["sizeBytes"] += len(_json.dumps(doc.get("value")))
        except (TypeError, ValueError):
            pass
        for agent_field in ("createdByAgent", "lastAccessedByAgent"):
            v = doc.get(agent_field)
            if v:
                b["agents"].add(v)
        updated = doc.get("updatedAt")
        if updated and (b["updatedAt"] is None or updated > b["updatedAt"]):
            b["updatedAt"] = updated
    # Convert sets to sorted lists for serialization stability
    return {
        ns: {**b, "agents": sorted(b["agents"])}
        for ns, b in buckets.items()
    }


@router.get("/data-store/namespaces", response_model=NamespaceListResponse)
async def list_data_store_namespaces(
    db = Depends(get_async_db),
    user: dict = Depends(get_current_user),
):
    """List every namespace with aggregate stats for the current user."""
    user_id = user.get("uid", "anonymous")
    # list_all + filter: simpler than adding a new service method, and
    # record counts are typically small. Could move to indexed query later.
    all_docs = await db.find("agent_data_store", {"userId": user_id})
    stats_map = _namespace_stats_from_docs(all_docs)
    namespaces = [
        NamespaceStats(namespace=ns, **data)
        for ns, data in sorted(stats_map.items())
    ]
    total_count = sum(ns.record_count for ns in namespaces)
    total_size = sum(ns.size_bytes for ns in namespaces)
    return NamespaceListResponse(
        namespaces=namespaces,
        total_record_count=total_count,
        total_size_bytes=total_size,
    )


@router.get("/data-store/namespaces/{namespace}", response_model=NamespaceStats)
async def get_namespace_stats(
    namespace: str,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Stats for a single namespace (record count, size, agents, last update)."""
    user_id = user.get("uid", "anonymous")
    docs = db.find("agent_data_store", {"userId": user_id, "namespace": namespace})
    stats = _namespace_stats_from_docs(docs)
    if namespace not in stats:
        return NamespaceStats(namespace=namespace, recordCount=0, sizeBytes=0, agents=[])
    return NamespaceStats(namespace=namespace, **stats[namespace])


@router.get("/data-store/namespaces/{namespace}/records", response_model=List[DataStoreRecord])
async def list_records(
    namespace: str,
    db: DatabaseService = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List every record in a namespace (full docs, not paginated).

    Returns the raw records including values. For large namespaces a paginated
    endpoint may be needed later; for now the UI handles up-to-several-thousand
    rows without issue.
    """
    user_id = user.get("uid", "anonymous")
    docs = db.find("agent_data_store", {"userId": user_id, "namespace": namespace})
    return [DataStoreRecord(**doc) for doc in docs]


@router.get("/data-store/namespaces/{namespace}/records/{key:path}", response_model=DataStoreRecord)
async def get_record(
    namespace: str,
    key: str,
    store: DataStoreService = Depends(_get_data_store_dep),
    user: dict = Depends(get_current_user),
):
    """Get a single record by key. Uses :path so keys can contain slashes."""
    user_id = user.get("uid", "anonymous")
    doc = store.get(user_id, namespace, key)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Record '{key}' not found in '{namespace}'")
    return DataStoreRecord(**doc)


@router.put("/data-store/namespaces/{namespace}/records/{key:path}", response_model=DataStoreRecord)
async def set_record(
    namespace: str,
    key: str,
    request: SetRecordRequest,
    store: DataStoreService = Depends(_get_data_store_dep),
    user: dict = Depends(get_current_user),
):
    """Admin edit of a record. Not intended for agent writes — those go
    through AgentDataStoreProxy during execution.
    """
    user_id = user.get("uid", "anonymous")
    doc = store.set(
        user_id=user_id,
        namespace=namespace,
        key=key,
        value=request.value,
        agent_name=None,  # admin edit, not an agent write
        metadata=request.metadata,
    )
    return DataStoreRecord(**doc)


@router.delete("/data-store/namespaces/{namespace}/records/{key:path}", status_code=204)
async def delete_record(
    namespace: str,
    key: str,
    store: DataStoreService = Depends(_get_data_store_dep),
    user: dict = Depends(get_current_user),
):
    """Delete a single record."""
    user_id = user.get("uid", "anonymous")
    deleted = store.delete(user_id, namespace, key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Record '{key}' not found in '{namespace}'")
    return


@router.delete("/data-store/namespaces/{namespace}", response_model=ClearNamespaceResponse)
async def clear_namespace(
    namespace: str,
    store: DataStoreService = Depends(_get_data_store_dep),
    user: dict = Depends(get_current_user),
):
    """Delete every record in a namespace."""
    user_id = user.get("uid", "anonymous")
    count = store.clear_namespace(user_id, namespace)
    return ClearNamespaceResponse(namespace=namespace, deleted_count=count)