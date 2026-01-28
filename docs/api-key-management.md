# API Key Management

This guide explains how users can manage their own API keys for LLM providers in Gofannon. User-specific API keys take precedence over system-wide environment variables.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [User Interface](#user-interface)
- [API Endpoints](#api-endpoints)
- [Backend Implementation](#backend-implementation)
- [Security Considerations](#security-considerations)
- [Configuration](#configuration)

## Overview

Gofannon supports two ways to configure API keys for LLM providers:

1. **Environment Variables** (System-wide): Set by administrators for all users
2. **User Profile Keys** (User-specific): Each user can configure their own API keys

When both are available, **user-specific keys take precedence** over environment variables.

## How It Works

### Priority Order

When making an LLM API call, the system looks for API keys in this order:

1. **User's stored API key** (if configured in profile)
2. **Environment variable** (system-wide fallback)
3. **No key available** (provider unavailable)

### Example Flow

```
User requests GPT-4 completion
         ↓
Check user's profile for OpenAI API key
         ↓
    ┌────┴────┐
   Found    Not Found
    ↓          ↓
Use key   Check OPENAI_API_KEY env var
              ↓
         ┌────┴────┐
        Found    Not Found
         ↓          ↓
       Use key   Error: Provider unavailable
```

## User Interface

### Profile Page

Users can manage their API keys through the **Profile** page:

1. Navigate to **Profile** → **API Keys** tab
2. View configured providers (showing "Configured" or "Not configured" status)
3. Add, update, or remove API keys for each provider

### Available Providers

The following providers support user-specific API keys:

| Provider | Environment Variable | User Key Field |
|----------|---------------------|----------------|
| OpenAI | `OPENAI_API_KEY` | `openaiApiKey` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropicApiKey` |
| Google Gemini | `GEMINI_API_KEY` | `geminiApiKey` |
| Perplexity | `PERPLEXITYAI_API_KEY` | `perplexityApiKey` |

### UI Components

- **Status Chip**: Shows "Configured" (green) or "Not configured" (gray)
- **Add/Update Button**: Opens input field to enter a new API key
- **Remove Button**: Deletes the stored API key
- **Masked Display**: Keys are always masked (••••••••) in the UI

## API Endpoints

### Get User's API Keys

```http
GET /api/users/me/api-keys
```

Returns the user's API keys (masked for security).

**Response:**
```json
{
  "openaiApiKey": "sk-...",
  "anthropicApiKey": null,
  "geminiApiKey": null,
  "perplexityApiKey": null
}
```

### Update API Key

```http
PUT /api/users/me/api-keys
Content-Type: application/json

{
  "provider": "openai",
  "apiKey": "sk-..."
}
```

**Supported providers:** `openai`, `anthropic`, `gemini`, `perplexity`

### Delete API Key

```http
DELETE /api/users/me/api-keys/{provider}
```

Removes the stored API key for the specified provider.

### Check Effective API Key

```http
GET /api/users/me/api-keys/{provider}/effective
```

Returns whether an effective API key exists without exposing the actual key.

**Response:**
```json
{
  "provider": "openai",
  "hasKey": true,
  "source": "user"  // or "env" or null
}
```

## Backend Implementation

### User Model

The `User` model includes an `api_keys` field:

```python
class ApiKeys(BaseModel):
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None

class User(BaseModel):
    # ... other fields ...
    api_keys: ApiKeys = Field(default_factory=ApiKeys)
```

### UserService Methods

```python
# Get user's API keys
api_keys = user_service.get_api_keys(user_id)

# Update a specific API key
user_service.update_api_key(user_id, "openai", "sk-...")

# Delete a specific API key
user_service.delete_api_key(user_id, "openai")

# Get effective API key (user key first, then env var)
api_key = user_service.get_effective_api_key(user_id, "openai")
```

### LLM Service Integration

The LLM service uses `get_effective_api_key` to determine which key to use:

```python
# In call_llm() and stream_llm()
api_key = user_service.get_effective_api_key(user_id, provider)
if api_key:
    kwargs["api_key"] = api_key
```

### Provider Availability

The `get_available_providers()` function now considers user-specific keys:

```python
def get_available_providers(user_id=None, user_basic_info=None):
    # Check user-specific key first
    if user_service and user_id:
        user_key = user_service.get_effective_api_key(user_id, provider)
        if user_key:
            is_available = True
    
    # Fall back to environment variable
    if not is_available:
        is_available = os.getenv(api_key_env_var) is not None
```

## Security Considerations

### Key Storage

- API keys are stored in the user's profile in the database
- Keys are **not encrypted** at rest (recommendation: use database-level encryption)
- Keys are transmitted over HTTPS

### Key Masking

- Keys are never returned in full to the frontend
- Only the last 4 characters are shown (e.g., `sk-...abcd`)
- Status checks only return boolean `hasKey`, never the actual key

### Best Practices

1. **Use environment variables for shared deployments**: If running Gofannon as a shared service, consider using environment variables rather than user-specific keys
2. **Rotate keys regularly**: Encourage users to rotate their API keys periodically
3. **Monitor usage**: Track API usage per user to detect potential key abuse
4. **Secure database**: Ensure the database has proper access controls and encryption

## Configuration

### Database Schema

When implementing a new database backend, ensure it can store the `api_keys` field in the user document:

```json
{
  "_id": "user-id",
  "basicInfo": { ... },
  "billingInfo": { ... },
  "usageInfo": { ... },
  "apiKeys": {
    "openaiApiKey": "sk-...",
    "anthropicApiKey": null,
    "geminiApiKey": null,
    "perplexityApiKey": null
  }
}
```

### Adding New Providers

To add support for a new provider:

1. Update `ApiKeys` model in `models/user.py`:
```python
class ApiKeys(BaseModel):
    # ... existing keys ...
    new_provider_api_key: Optional[str] = None
```

2. Add to `provider_key_map` in `services/user_service.py`:
```python
provider_key_map = {
    # ... existing mappings ...
    "new_provider": "new_provider_api_key",
}
```

3. Update the UI in `components/profile/ApiKeysTab.jsx`:
```javascript
const PROVIDERS = [
  // ... existing providers ...
  { id: 'new_provider', name: 'New Provider', description: '...' },
];
```

## Troubleshooting

### Provider Not Available

If a provider shows as unavailable:

1. Check if the user has configured an API key in their profile
2. Verify the environment variable is set (for fallback)
3. Check the provider configuration in `config/provider_config.py`

### Key Not Working

If API calls fail with an authentication error:

1. Verify the API key is valid by testing directly with the provider
2. Check for typos or extra whitespace in the stored key
3. Ensure the key has the necessary permissions/scopes

### Migration from Environment Variables

To migrate from environment variables to user-specific keys:

1. Leave environment variables in place as fallback
2. Users can add their own keys in their profile
3. User keys will automatically take precedence

---

**Last Updated**: January 2026
**Maintainer**: AI Alliance Gofannon Team
