# Gofannon Web UI

This package contains the front-end for the Gofannon web application. It uses Vite and React, and is designed to be the foundation for downstream distributions that may add their own extensions and configuration.

## Card extension system

The home page tiles are implemented as **card extensions**. Each card implements a minimal interface (see `src/extensions/cards/types.js`) and is registered in a central registry (`src/extensions/cards/cardRegistry.js`). Built-in cards live in `src/extensions/cards/builtInCards.js` and are registered automatically, but additional cards can be added at runtime by calling `registerCard` or by supplying registrars through `window.__CARD_EXTENSION_REGISTRARS__`.

### Configuration-driven ordering and visibility

Default card ordering and enablement are defined in `src/extensions/cards/config/defaultCardsConfig.js`. Configuration is merged in `src/extensions/cards/config/configLoader.js`, which layers the defaults with optional overrides from:

- `VITE_CARD_CONFIG_OVERRIDES` (JSON string)
- `CARD_CONFIG_OVERRIDES` (JSON string when running in Node contexts)
- `window.__CARD_CONFIG_OVERRIDES__` (object provided by the embedding page)

Overrides can disable cards (`enabled: false`), change order (`order`), or add metadata such as `group`. New cards registered by extensions can supply their own defaults and be controlled by these overrides without modifying the OSS codebase.

## How external distributions can extend the UI

External code can add cards and configuration without changing this repository by:

1. Providing a registrar function (e.g., `window.__CARD_EXTENSION_REGISTRARS__ = [({ registerCard }) => registerCard({...})];`).
2. Supplying configuration overrides through the supported environment variables or globals documented above.
3. Building images or bundles that include additional extension modules and set the desired config at runtime.

## Application configuration

The shared configuration package (`@gofannon/config`) still provides environment-specific values such as API endpoints and theme settings. The card registry builds on top of this by keeping presentation cards configuration-driven and extension-aware.


## Development

Install dependencies and start the development server from the `webapp` root:

```bash
pnpm install
pnpm dev --filter webui
```
If you want to exercise the UI against the local API instead of mocks, run the FastAPI user-service in another terminal:
```bash
cd packages/api/user-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API defaults to a local environment with permissive CORS. Adjust environment variables in a `.env` file in `packages/api/user-service` if you need to point at external services. Refer to the repository root README for broader project setup instructions.
