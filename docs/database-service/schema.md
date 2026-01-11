# Collections and Schema

## Required Collections

The Gofannon system uses the following collections/tables. Each must be supported by your database implementation:

| Collection Name | Purpose | Primary Key | Description |
|-----------------|---------|-------------|-------------|
| `agents` | AI Agents | `_id` (UUID) | Stores agent definitions including code, tools, and schemas |
| `deployments` | Deployment Mappings | `_id` (friendly_name) | Maps friendly endpoint names to agent IDs |
| `users` | User Profiles | `_id` (user_id) | User information, billing plans, and usage tracking |
| `sessions` | Chat Sessions | `_id` (session_id) | Conversation sessions and interaction history |
| `tickets` | Async Jobs | `_id` (ticket_id) | Asynchronous task tracking and results |
| `demos` | Demo Apps | `_id` (demo_id) | Demo application configurations |

## Document Schemas

### Agent Document

Location: [models/agent.py](../../../webapp/packages/api/user-service/models/agent.py)

```python
{
    "_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID string
    "name": "MyAgent",                              # Agent name
    "description": "Description of what agent does",
    "code": "def handler(event):\n    return {}",  # Python execution code
    "friendly_name": "my-agent",                    # URL-safe deployment name
    "tools": {                                       # Available tools by category
        "web": ["web_search", "web_fetch"],
        "data": ["sql_query"]
    },
    "input_schema": {                               # Expected input structure
        "query": "string",
        "max_results": "integer"
    },
    "output_schema": {                              # Expected output structure
        "results": "array",
        "count": "integer"
    },
    "gofannon_agents": [                            # Dependent Gofannon agents
        "agent-id-1",
        "agent-id-2"
    ],
    "created_at": "2024-01-15T10:30:00Z",          # ISO 8601 datetime
    "updated_at": "2024-01-15T10:30:00Z"           # ISO 8601 datetime
}
```

**Key Fields:**
- `_id`: Unique identifier (UUID v4)
- `code`: Executable Python code for the agent
- `friendly_name`: Used in deployment URLs (`/api/agents/{friendly_name}/run`)
- `tools`: Nested dictionary of tool categories and available tools
- Schemas define input/output validation contracts

### Deployment Document

Location: [models/deployment.py](../../../webapp/packages/api/user-service/models/deployment.py)

```python
{
    "_id": "my-friendly-name",                      # Deployment endpoint name
    "agentId": "550e8400-e29b-41d4-a716-446655440000"  # References agent._id
}
```

**Key Fields:**
- `_id`: The friendly name used in API URLs
- `agentId`: Foreign key to agents collection

**Usage**: Enables agents to be deployed at human-readable endpoints like `/api/agents/my-friendly-name/run`

### User Document

Location: [models/user.py](../../../webapp/packages/api/user-service/models/user.py)

```python
{
    "_id": "user_google_123456789",                 # Provider-specific user ID
    "basic_info": {
        "display_name": "John Doe",
        "email": "john@example.com",
        "picture_url": "https://...",               # Optional profile picture
        "provider": "google"                         # Authentication provider
    },
    "billing_info": {
        "plan": "free",                              # Subscription tier
        "status": "active",                          # Billing status
        "stripe_customer_id": "cus_...",            # Optional Stripe reference
        "subscription_id": "sub_..."                # Optional subscription ID
    },
    "usage_info": {
        "monthly_allowance": 100.0,                 # USD allowance per month
        "spend_remaining": 87.50,                   # USD remaining this period
        "usage": [                                   # Usage history
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "response_cost": 0.05,              # Cost in USD
                "agent_id": "agent-id",             # Optional agent reference
                "session_id": "session-id"          # Optional session reference
            }
        ],
        "last_reset": "2024-01-01T00:00:00Z"       # Last billing period reset
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

**Key Fields:**
- `_id`: Composite of provider and provider user ID
- `usage_info.usage`: Array that grows with each API call
- Cost tracking in USD for billing/quota enforcement

### Session Document

Location: [models/session.py](../../../webapp/packages/api/user-service/models/session.py)

```python
{
    "_id": "session_abc123",                        # Unique session identifier
    "user_id": "user_google_123456789",            # References user._id
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",  # References agent._id
    "messages": [                                   # Conversation history
        {
            "role": "user",
            "content": "Hello, agent!",
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "role": "assistant",
            "content": "Hello! How can I help?",
            "timestamp": "2024-01-15T10:30:05Z"
        }
    ],
    "metadata": {                                   # Additional context
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "tags": ["support", "billing"]
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "expires_at": "2024-01-16T10:30:00Z"          # Optional session expiry
}
```

**Key Fields:**
- `messages`: Append-only conversation array
- Foreign keys to `users` and `agents`
- Optional expiry for automatic cleanup

### Ticket Document

Location: [models/ticket.py](../../../webapp/packages/api/user-service/models/ticket.py)

```python
{
    "_id": "ticket_xyz789",                         # Unique ticket identifier
    "status": "pending",                            # "pending" | "processing" | "completed" | "failed"
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "request": {                                     # Original request data
        "agent_id": "agent-id",
        "input": {"query": "..."},
        "user_id": "user_id"
    },
    "result": {                                      # Populated when completed
        "output": {"results": [...]},
        "cost": 0.05,
        "completed_at": "2024-01-15T10:35:00Z"
    },
    "error": null                                    # Populated if failed
}
```

**Key Fields:**
- `status`: Tracks async job lifecycle
- `result`: Only present after successful completion
- `error`: Only present if job failed

### Demo Document

Location: [models/demo.py](../../../webapp/packages/api/user-service/models/demo.py)

```python
{
    "_id": "demo_chat_app",                         # Demo identifier
    "name": "Interactive Chat Demo",
    "description": "A demo showing chat capabilities",
    "agent_id": "agent-id",                        # References agent to use
    "config": {                                     # Demo-specific settings
        "theme": "dark",
        "max_messages": 50,
        "features": ["markdown", "code_highlighting"]
    },
    "is_public": true,                             # Visibility flag
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

## Schema Conventions

1. **ID Field**: All documents must include an `_id` field
2. **Timestamps**: Use ISO 8601 format strings (`"2024-01-15T10:30:00Z"`)
3. **Foreign Keys**: Reference other documents by their `_id` value
4. **Optional Fields**: Fields may be `null` or omitted entirely
5. **Arrays**: Use lists for collections (messages, usage history, etc.)
6. **Nested Objects**: Use dictionaries for grouped related fields

## Related Documentation

- [Database Interface](interface.md) - Abstract base class and method specifications
- [Configuration](configuration.md) - Database provider configuration
- [Database Service README](README.md) - Overview and getting started

---

Last Updated: 2026-01-11
