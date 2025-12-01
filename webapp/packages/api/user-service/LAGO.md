# Lago Usage Billing with LiteLLM

This service now wires [LiteLLM's Lago callbacks](https://docs.litellm.ai/docs/observability/lago) so that every model call can emit usage events to a Lago workspace. Set three environment variables and the callbacks will automatically register during FastAPI startup (`services/lago_service.configure_lago_logging`).

## Required environment

Add these to the backend environment (e.g., `.env`, Cloud Function secrets, or your docker compose overrides):

```ini
LAGO_API_BASE=https://api.getlago.com          # Or your self-hosted Lago URL
LAGO_API_KEY=<lago_api_key>                    # Bearer token for Lago API
LAGO_API_EVENT_CODE=<lago_event_code>          # Matches the event code configured in Lago
LAGO_API_CHARGE_BY=user_id                     # Recommended so we bill by the authenticated user
```

Notes:

- `LAGO_API_CHARGE_BY` defaults to `end_user_id` in LiteLLM, but this service passes the authenticated Firebase/oidc `uid` as `user_api_key_user_id` metadata on every LiteLLM call. Setting `LAGO_API_CHARGE_BY=user_id` ensures Lago accepts the external customer id we send (`anonymous` is used for unauthenticated/local calls).
- If any of the required variables are missing, the server skips registration and logs a debug message (`lago_logging_disabled`).

## How it works in code

- `services/lago_service.py` builds a `LagoLogger` and appends it to `litellm.success_callback` and `litellm.failure_callback` when all required env vars are present.
- `services/llm_service.call_llm` attaches LiteLLM `metadata` with the calling user's id so Lago can attribute spend.
- `services/chat_service` and the agent composer use the same metadata helper to keep callbacks satisfied even during streaming or background generation.

## Verifying locally

1. Export the variables above (you can point `LAGO_API_BASE` at a local Lago dev server if you have one running).
2. Start the API: `cd webapp/packages/api/user-service && uvicorn main:app --reload`.
3. Trigger a chat from the UI or by POSTing to `/api/chat`.
4. Check Lago's Events list — each model call should arrive with the event code you supplied and a `properties` payload containing the model id and token usage.

If anything fails during registration, the backend will log an `lago_logging_error` event with details so you can correct the configuration and retry.
