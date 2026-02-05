# Architecture

Gofannon is designed as a modular system for rapidly prototyping AI agents and their associated web UIs.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      React Frontend                              │
│                    (webapp/packages/webui)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Agent Editor│  │  Sandbox    │  │    Chat Interface       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python API (FastAPI)                          │
│               (webapp/packages/api/user-service)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ LLM Service │  │ User Service│  │   Database Service      │  │
│  └──────┬──────┘  └─────────────┘  └───────────┬─────────────┘  │
│         │                                       │                │
└─────────┼───────────────────────────────────────┼────────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────┐               ┌─────────────────────────┐
│    LLM Providers    │               │       Database          │
│  (via LiteLLM)      │               │  (CouchDB/Firestore/    │
│                     │               │   DynamoDB/Memory)      │
│  • OpenAI           │               └─────────────────────────┘
│  • Anthropic        │
│  • Google Gemini    │
│  • AWS Bedrock      │
│  • Ollama           │
└─────────────────────┘
```

## Core Components

### Frontend (React)

**Location:** `webapp/packages/webui/`

- **Framework:** React + Vite + Material-UI
- **State:** React hooks and context
- **Routing:** React Router
- **Build:** pnpm

Key features:
- Agent editor with code generation
- Sandbox for testing agents
- Chat interface for deployed agents
- Demo gallery

### Backend API (FastAPI)

**Location:** `webapp/packages/api/user-service/`

- **Framework:** FastAPI (Python 3.10+)
- **Server:** Uvicorn (ASGI)
- **Auth:** Firebase Authentication (or mock for development)

Key modules:

| Module | Purpose |
|--------|---------|
| `routes.py` | HTTP endpoint definitions |
| `dependencies.py` | Dependency injection, sandbox execution |
| `services/llm_service.py` | LLM provider abstraction via LiteLLM |
| `services/user_service.py` | User profiles, billing, API keys |
| `services/database_service/` | Pluggable database backends |
| `agent_factory/` | Agent code generation |
| `models/` | Pydantic models for data validation |
| `config/` | Provider configuration and settings |

### Agent Sandbox

Agents run in an isolated execution environment:

```python
# Simplified sandbox execution flow
async def execute_agent(agent_code: str, input_data: dict, user_id: str):
    # 1. Create isolated globals
    exec_globals = {
        "tools": available_tools,
        "data_store": DataStoreProxy(user_id),
        "call_llm": llm_service.call_llm,
    }
    
    # 2. Execute agent code
    exec(agent_code, exec_globals)
    
    # 3. Call the agent's run function
    result = await exec_globals["run"](input_data, exec_globals["tools"])
    
    return result
```

### LLM Service

All LLM calls go through `services/llm_service.py`:

```python
from services.llm_service import call_llm

response = await call_llm(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Hello"}],
    user_id=user_id,
    tools=available_tools,
)
```

Benefits:
- **Unified interface** for all providers (OpenAI, Anthropic, etc.)
- **Cost tracking** per user
- **Observability** logging
- **Extended thinking** support

See [LLM Provider Configuration](llm-provider-configuration.md) for details.

### Database Service

Pluggable database abstraction:

```python
from services.database_service import get_database_service

db = get_database_service(settings)
doc = db.get("agents", agent_id)
db.save("agents", agent_id, updated_doc)
```

Supported backends:
- In-Memory (development)
- CouchDB (self-hosted)
- Firestore (Google Cloud)
- DynamoDB (AWS)

See [Database Guide](database/README.md) for details.

## Data Flow

### Agent Creation

1. User defines agent in web UI (name, description, tools, models)
2. Frontend sends configuration to `/api/agents/generate-code`
3. Agent factory generates Python code from prompt + configuration
4. User tests in sandbox
5. User saves agent to database
6. User deploys agent (creates friendly URL mapping)

### Agent Execution

1. Request arrives at `/api/agents/{agent_name}/run`
2. Backend loads agent code from database
3. Sandbox executes agent with:
   - Input data from request
   - Available tools
   - Data store proxy
   - LLM service
4. Agent calls tools, LLM, and data store as needed
5. Result returned to caller

### Chat Sessions

1. User starts chat with deployed agent
2. Session created in database
3. Each message:
   - Appended to session history
   - Agent invoked with full context
   - Response appended to history
4. Session persists for future retrieval

## Extension Points

### Custom API Endpoints

See [Extension Example](EXTENSION_EXAMPLE.md) for adding:
- Custom API routes
- Custom UI pages
- Custom home page cards

### Custom Database Backends

See [Database Guide](database/README.md#implementing-a-new-database) for adding new storage backends.

### Custom LLM Providers

See [LLM Provider Configuration](llm-provider-configuration.md#adding-a-new-provider) for adding new model providers.

## Deployment Options

| Target | Configuration |
|--------|---------------|
| Docker Compose | `webapp/infra/docker/` |
| Firebase | `webapp/infra/firebase/` |
| Kubernetes | Planned |

## Related Documentation

- [Quickstart](quickstart/README.md) - Get running in 5 minutes
- [Developer Setup](developers-quickstart.md) - Local development environment
- [API Reference](api.md) - HTTP endpoints