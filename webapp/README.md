# Gofannon Web Application

This monorepo contains the complete scaffolding for the Gofannon web application, including the React Web UI, Python API microservices, and infrastructure configurations.

## Project Structure

- **`/infra`**: Contains infrastructure-as-code for all deployment targets.
  - `/docker`: Local development environment using Docker Compose.
  - `/firebase`, `/amplify`, `/kubernetes`: Placeholders for target-specific configurations.
- **`/packages`**: Contains the source code for different parts of the application.
  - `/api`: Python-based microservices.
  - `/config`: Centralized, environment-aware configuration package.
  - `/webui`: The React (Vite + Material-UI) frontend.
- **`/tests`**: Houses end-to-end tests that span across the entire stack.

## Getting Started (Local Development)

### Prerequisites

- [Node.js](https://nodejs.org/en/) (v18+)
- [pnpm](https://pnpm.io/installation)
- [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose

### Installation

1.  Install project-wide dependencies from the root directory:
    ```bash
    pnpm install
    ```

### Running Locally

1.  Start all services using Docker Compose:
    ```bash
    cd infra/docker
    cp example.env .env  # also edit example key(s)
    docker-compose up --build
    ```

2.  Access the application:
    - Web UI: [http://localhost:3000](http://localhost:3000)
    - API: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

This setup uses a mock authentication provider, allowing you to bypass login and develop features directly. Storage is handled by a local MinIO container that simulates an S3-compatible service.

## Extending from an external repository

External repositories can copy the `webapp` directory and layer in new UI routes, cards, and API endpoints by updating configuration files instead of rewriting core code.

- **Web UI routes:** Add or override entries in `packages/webui/src/config/routes/overrides.js`. Each route can specify an `element`, whether it should render inside the shared `Layout`, whether it requires authentication, and any wrapper providers.
- **Cards:** Register new cards via `packages/webui/src/extensions/index.js` (imported automatically on startup) and give them an ordering entry in `packages/webui/src/extensions/cards/config/defaultCardsConfig.js`.
- **API endpoints:** Provide additional FastAPI registrars and list them with the `GOFANNON_API_ROUTE_REGISTRARS` environment variable or by editing `packages/api/user-service/config/routes_config.py`.

### Example: adding an "Echo" experience

Below is a full example of what an external repository would add after copying `webapp/` to introduce a new Echo card, page, and API endpoint. File paths are relative to the copied `webapp` directory.

1. **Add a new page at `packages/webui/src/pages/EchoPage.jsx`:**
    ```jsx
    import React, { useState } from 'react';
    import { Box, Button, Stack, TextField, Typography } from '@mui/material';
    import apiClient from '../services/apiClient';

    const EchoPage = () => {
      const [input, setInput] = useState('');
      const [result, setResult] = useState('');

      const sendEcho = async () => {
        const response = await apiClient.post('/echo', { text: input });
        setResult(response.data.echo);
      };

      return (
        <Stack spacing={3} maxWidth={520}>
          <Typography variant="h4">Echo</Typography>
          <TextField label="Message" value={input} onChange={(e) => setInput(e.target.value)} fullWidth />
          <Button variant="contained" onClick={sendEcho}>Send</Button>
          {result && (
            <Box p={2} bgcolor="grey.100" borderRadius={1}>
              <Typography variant="subtitle2">Response</Typography>
              <Typography>{result}</Typography>
            </Box>
          )}
        </Stack>
      );
    };

    export default EchoPage;
    ```

2. **Expose the route in `packages/webui/src/config/routes/overrides.js`:**
    ```js
    import EchoPage from '../../pages/EchoPage';

    const overrideRoutesConfig = {
      routes: [
        {
          id: 'echo',
          path: '/echo',
          element: <EchoPage />, // Renders inside the shared Layout + PrivateRoute by default
        },
      ],
    };

    export default overrideRoutesConfig;
    ```

3. **Register a card in `packages/webui/src/extensions/cards/EchoCard.jsx` and wire it up in `packages/webui/src/extensions/index.js`:**
    ```jsx
    // packages/webui/src/extensions/cards/EchoCard.jsx
    import RecordVoiceOverIcon from '@mui/icons-material/RecordVoiceOver';

    const EchoCard = {
      id: 'echo',
      title: 'Try Echo',
      description: 'Send a message and see it echoed back by the API.',
      buttonText: 'Open Echo',
      icon: <RecordVoiceOverIcon />,
      defaultOrder: 7,
      onAction: ({ navigate }) => navigate('/echo'),
    };

    export default EchoCard;
    ```

    ```js
    // packages/webui/src/extensions/index.js
    import EchoCard from './cards/EchoCard';
    import { registerExternalCardRegistrar } from './cards/cardRegistry';

    registerExternalCardRegistrar(({ registerCard }) => registerCard(EchoCard));
    ```

    Also add the card to the ordering config (or set `CARD_CONFIG_OVERRIDES` in the environment):
    ```js
    // packages/webui/src/extensions/cards/config/defaultCardsConfig.js
    const defaultCardsConfig = {
      cards: [
        // ...existing cards
        { id: 'echo', order: 7, enabled: true },
      ],
    };

    export default defaultCardsConfig;
    ```

4. **Add the API endpoint via a registrar (`packages/api/user-service/routes/echo.py`):**
    ```python
    from fastapi import APIRouter

    router = APIRouter()

    @router.post("/echo")
    async def echo(payload: dict):
        return {"echo": payload.get("text", "")}

    def register_echo_routes(app):
        app.include_router(router)
    ```

    Reference the registrar when launching the API:
    ```bash
    export GOFANNON_API_ROUTE_REGISTRARS='["main:register_builtin_routes", "routes.echo:register_echo_routes"]'
    uvicorn main:app --reload
    ```

With those files in place, running the normal build commands will surface the Echo card on the home screen, route users to the new `/echo` page, and round-trip their text through the `/echo` API endpoint.
