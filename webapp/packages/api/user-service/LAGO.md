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

## Optional: spin up Lago locally with docker compose

The repo's `webapp/infra/docker/docker-compose.yml` now includes a Lago stack that runs under the `lago` profile so it does not interfere with the default services.

1. Export the Lago secrets (at minimum: `LAGO_SECRET_KEY_BASE`, `LAGO_RSA_PRIVATE_KEY`, and the encryption keys above).
2. Start everything: `cd webapp/infra/docker && docker compose --profile lago up -d`.
3. Browse the Lago UI at `http://localhost:4000` (API on `http://localhost:3000`).
4. Point `LAGO_API_BASE=http://localhost:3000` in your `.env` to wire LiteLLM events into the local Lago workspace.

### Example `.env` snippet for local Lago + LiteLLM

Place these values in `webapp/infra/docker/.env` (same folder as `docker-compose.yml`) before starting the `lago` profile. Keep the RSA keypair in files (multi-line PEMs do not serialize well into `.env`); see the note after the table for how to load them:

```ini
# Lago application secrets (used by the Lago containers)
LAGO_SECRET_KEY_BASE=<output of `docker compose --profile lago run --rm lago-api bundle exec rails secret`>
LAGO_ENCRYPTION_PRIMARY_KEY=<32-byte hex from `openssl rand -hex 32`>
LAGO_ENCRYPTION_DETERMINISTIC_KEY=<32-byte hex from `openssl rand -hex 32`>
LAGO_ENCRYPTION_KEY_DERIVATION_SALT=<32-byte hex from `openssl rand -hex 32`>
# LiteLLM → Lago wiring (used by the user-service when it sends usage events)
LAGO_API_BASE=http://localhost:3000
LAGO_API_KEY=<API key from Lago UI: Settings → Developers → API Keys → Create API key>
LAGO_API_EVENT_CODE=<event code of your Lago Billable Metric, e.g., `litellm-call`>
LAGO_API_CHARGE_BY=user_id
```

How to obtain the values:

- `LAGO_SECRET_KEY_BASE`: in the compose directory, run `docker compose --profile lago run --rm --no-deps lago-api bundle exec rails secret` (the `--no-deps` flag skips `lago-migrate`, which can fail before you have secrets/DB ready).
- `LAGO_ENCRYPTION_*`: generate three 32-byte hex strings: `openssl rand -hex 32` (run three times).
- `LAGO_RSA_PRIVATE_KEY` and `LAGO_RSA_PUBLIC_KEY` (both are required for migrations to boot): generate a keypair with `openssl genrsa -out lago_rsa_private.pem 2048` and `openssl rsa -in lago_rsa_private.pem -pubout -out lago_rsa_public.pem`. Because PEMs are multi-line, keep them as files and load them into environment variables when you run compose:

  ```bash
  # Run in webapp/infra/docker
  export LAGO_RSA_PRIVATE_KEY="$(cat lago_rsa_private.pem)"
  export LAGO_RSA_PUBLIC_KEY="$(cat lago_rsa_public.pem)"
  docker compose --profile lago up -d
  ```

  You can keep all the other keys (API base/key, event code, encryption secrets) in `.env`; just export the two PEMs from files so Docker Compose receives the exact newline-delimited values Lago expects.
- `LAGO_API_KEY`: once the Lago UI is up (`http://localhost:4000`), go to **Settings → Developers → API Keys**, click **Create API key**, and copy the value.
- `LAGO_API_EVENT_CODE`: in the Lago UI, create or open a **Billable Metric** (e.g., "LiteLLM Calls") and copy its **Event code** field; this must match `LAGO_API_EVENT_CODE` so incoming events are accepted.

### Troubleshooting `lago-migrate`

- If `lago-migrate` exits immediately, confirm both RSA env vars (`LAGO_RSA_PRIVATE_KEY` **and** `LAGO_RSA_PUBLIC_KEY`) are exported — the migrate/start scripts require both keys at boot.
- Check container logs with `docker compose --profile lago logs lago-migrate`.
- After fixing secrets, rerun the migration step directly to verify it succeeds before bringing the rest of the stack up:

  ```bash
  docker compose --profile lago run --rm --no-deps lago-migrate ./scripts/migrate.sh
  docker compose --profile lago up -d
  ```
