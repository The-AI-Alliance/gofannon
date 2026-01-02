# User Service API

This document describes the HTTP surface of the user-service FastAPI app. The service powers provider discovery, chat orchestration, agent lifecycle management, demo generation, and deployment management. All routes are relative to the service root (e.g., `http://localhost:8000`).

## Authentication and headers
- In non-Firebase environments (`APP_ENV != "firebase"`), authentication is bypassed and requests run as `local-dev-user`.
- In Firebase deployments, send `Authorization: Bearer <ID token>`; the token is verified with Firebase and the decoded user is attached to `request.state.user`.
- Most routes rely on dependency injection for authorization; admin-only routes require `require_admin_access`.

## Error handling
- Standard FastAPI error responses are returned with a JSON body shaped as `{"detail": <message>}` when validation or downstream services fail.
- Background tasks (e.g., chat processing) store status and errors in the database; clients should poll for completion.

## Endpoint summary
- **Service metadata:** `GET /`, `GET /health`
- **Logging:** `POST /log/client`
- **Provider catalog:** `GET /providers`, `/providers/{provider}`, `/providers/{provider}/models`, `/providers/{provider}/models/{model}`
- **User profile & usage:** `GET /users/me`, `PUT /users/me/monthly-allowance`, `PUT /users/me/allowance-reset-date`, `PUT /users/me/spend-remaining`, `POST /users/me/usage`, `POST /users/me/reset-allowance`
- **Admin users:** `GET /admin/users`, `PUT /admin/users/{user_id}`
- **Chat:** `POST /chat`, `GET /chat/{ticket_id}`
- **Session configuration:** `POST /sessions/{session_id}/config`, `GET /sessions/{session_id}/config`, `DELETE /sessions/{session_id}`
- **Agents:** CRUD at `/agents` plus `POST /agents/generate-code`, `POST /agents/run-code`
- **Deployments:** `POST /agents/{agent_id}/deploy`, `DELETE /agents/{agent_id}/undeploy`, `GET /agents/{agent_id}/deployment`, `GET /deployments`, `POST /rest/{friendly_name}`
- **MCP connectors:** `POST /mcp/tools`
- **Specs:** `POST /specs/fetch`
- **Demos:** `POST /demos/generate-code`, CRUD at `/demos`

## Endpoint details

### Service metadata
- `GET /` → Simple heartbeat payload with service name.
- `GET /health` → `{ "status": "healthy", "service": "user-service" }` for readiness probes.

### Logging
- `POST /log/client`
  - Body: `{ "eventType": string, "message": string, "level": "INFO"|"WARN"|..., "metadata": object? }`
  - Behavior: Enriches metadata with `client_host` and `user_agent`, then writes to observability service. Returns `{ "status": "logged" }`.

### Provider catalog
- `GET /providers` → Map of provider configurations keyed by provider slug.
- `GET /providers/{provider}` → Provider config, 404 if missing.
- `GET /providers/{provider}/models` → List of model slugs for the provider.
- `GET /providers/{provider}/models/{model}` → Model configuration, 404 if provider or model missing.

### User profile & usage
- `GET /users/me` → Current user profile (`User` schema with `basicInfo`, `billingInfo`, `usageInfo`).
- `PUT /users/me/monthly-allowance`
  - Body: `{ "monthlyAllowance": number }`
  - Effect: Updates allowance limit.
- `PUT /users/me/allowance-reset-date`
  - Body: `{ "allowanceResetDate": number }`
  - Effect: Updates reset timestamp.
- `PUT /users/me/spend-remaining`
  - Body: `{ "spendRemaining": number }`
  - Effect: Updates remaining spend.
- `POST /users/me/usage`
  - Body: `{ "responseCost": number, "metadata"?: object }`
  - Effect: Appends usage entry and updates spend remaining.
- `POST /users/me/reset-allowance` → Resets usage tracking for the current user.

### Admin users
- `GET /admin/users` → Lists all users (admin-only dependency).
- `PUT /admin/users/{user_id}`
  - Body: any combination of `monthlyAllowance`, `allowanceResetDate`, `spendRemaining`.
  - Effect: Updates targeted user's usage info (admin-only).

### Chat
- `POST /chat`
  - Body: `ChatRequest` containing `messages` (role `user|assistant|system`), `provider`, `model`, optional `parameters`, and `builtInTools`.
  - Effect: Queues background chat processing and returns `{ "ticket_id": <uuid>, "status": "pending" }`.
- `GET /chat/{ticket_id}` → `ChatResponse` with `status`, `result`, and `error` once processing completes.

### Session configuration
- `POST /sessions/{session_id}/config`
  - Body: `ProviderConfig` (`provider`, `model`, `parameters`).
  - Effect: Creates or updates session document and returns confirmation.
- `GET /sessions/{session_id}/config` → Stored `provider_config` for the session.
- `DELETE /sessions/{session_id}` → Deletes session and returns `{ "message": "Session deleted" }`.

### Agents
- `POST /agents`
  - Body: `CreateAgentRequest` (name, description, code, optional `friendlyName`, tool metadata, schemas, invokable models, composer metadata).
  - Effect: Persists agent and returns saved `Agent` with `_id` and `_rev`.
- `GET /agents` → List of all agents.
- `GET /agents/{agent_id}` → Single agent document.
- `PUT /agents/{agent_id}`
  - Body: `UpdateAgentRequest` (partial updates across the same fields as creation).
  - Effect: Merges with existing document, preserves creation metadata, returns updated agent.
- `DELETE /agents/{agent_id}` → Deletes agent, 204 on success.
- `POST /agents/generate-code`
  - Body: `GenerateCodeRequest` (description, `tools`, input/output schemas, composer `modelConfig`, optional swagger specs and invokable models).
  - Effect: Returns generated agent code and metadata.
- `POST /agents/run-code`
  - Body: `RunCodeRequest` (`code`, `inputDict`, `tools`, optional `gofannonAgents`).
  - Effect: Executes code in sandbox; response contains `result` or raises with logged failure details.

### Deployments
- `POST /agents/{agent_id}/deploy` → Registers agent for REST exposure; 201 with deployment info.
- `DELETE /agents/{agent_id}/undeploy` → Removes deployment; 204 on success.
- `GET /agents/{agent_id}/deployment` → Deployment metadata for the agent, or 404 if not deployed.
- `GET /deployments` → List of deployed APIs (`DeployedApi` objects).
- `POST /rest/{friendly_name}` → Runs a deployed agent by its public name using the JSON body as `input_dict`.

### Specs
- `POST /specs/fetch`
  - Body: `{ "url": string }`
  - Effect: Fetches and returns OpenAPI/Swagger spec content from a remote URL.

### MCP connectors
- `POST /mcp/tools`
  - Body: `{ "mcp_url": string, "auth_token"?: string }`
  - Effect: Connects to a remote MCP server and returns `{ "mcp_url": ..., "tools": [...] }`.

### Demo apps
- `POST /demos/generate-code`
  - Body: `GenerateDemoCodeRequest` (user prompt, selected deployed APIs, composer `modelConfig`, optional `builtInTools`).
  - Effect: Returns generated `html`, `css`, `js`, and optional `thoughts`.
- `POST /demos`
  - Body: `CreateDemoAppRequest` (name, description, selected APIs, composer config, prompt, generated code, optional composer thoughts).
  - Effect: Saves a demo app and returns the stored `DemoApp`.
- `GET /demos` → List of saved demo apps.
- `GET /demos/{demo_id}` → Single demo app.
- `PUT /demos/{demo_id}` → Replace demo app content using the same schema as creation.
- `DELETE /demos/{demo_id}` → Deletes demo app, 204 on success.
