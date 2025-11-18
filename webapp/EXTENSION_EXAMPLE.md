# External extension example: Echo card, page, and API

This example shows how an external repository can add a new **Echo** feature by copying the `webapp` directory, dropping in new files, and wiring the existing extension points. The Echo card links to a page that calls a new API endpoint and renders the echoed text.

## 1) Add a custom API endpoint

Create `webapp/packages/api/user-service/extensions/echo_router.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EchoRequest(BaseModel):
    message: str


@router.post("/echo")
async def echo(request: EchoRequest):
    return {"echo": request.message}
```

Expose the router through a config module so the API knows to include it. Create `webapp/packages/api/user-service/extensions/echo_router_config.py`:

```python
from config.routes_config import RouterConfig

ROUTER_CONFIG_MODE = "append"
ROUTER_CONFIGS = [
    {
        "router": "extensions.echo_router:router",
        "prefix": "/extensions",  # becomes /extensions/echo
        "tags": ["echo-demo"],
    }
]
```

When running the API, point the loader at this module:

```bash
export APP_ROUTER_CONFIG=extensions.echo_router_config
cd webapp/packages/api/user-service
uvicorn main:app --reload
```

The new endpoint will be available at `POST /extensions/echo` and will be merged with all built-in routes because the default router list is still applied.

## 2) Add the Echo page

Create `webapp/packages/webui/src/extensions/echo/EchoPage.jsx`:

```jsx
import React, { useState } from 'react';
import { Box, Button, Stack, TextField, Typography } from '@mui/material';
import config from '../../config';

const EchoPage = () => {
  const [value, setValue] = useState('');
  const [echo, setEcho] = useState('');
  const [isSending, setIsSending] = useState(false);

  const sendEcho = async () => {
    setIsSending(true);
    try {
      const response = await fetch(`${config.api.baseUrl}/extensions/echo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value }),
      });
      const payload = await response.json();
      setEcho(payload.echo ?? '');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Echo
      </Typography>
      <Typography color="text.secondary" paragraph>
        Type any message and the API will echo it back.
      </Typography>
      <Stack direction="row" spacing={2} alignItems="center">
        <TextField
          fullWidth
          label="Message"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
        <Button variant="contained" onClick={sendEcho} disabled={isSending}>
          {isSending ? 'Sending…' : 'Send'}
        </Button>
      </Stack>
      {echo && (
        <Typography sx={{ mt: 2 }}>
          Echoed: <strong>{echo}</strong>
        </Typography>
      )}
    </Box>
  );
};

export default EchoPage;
```

Also add the EchoCard.
Create `webapp/packages/webui/src/extensions/echo/EchoCard.jsx`:
```jsx
// webapp/packages/webui/src/extensions/echo/EchoCard.jsx
import CampaignIcon from '@mui/icons-material/Campaign';

export const card = {
  id: 'echo',
  title: 'Echo Chamber',
  description: 'An example of a custom card that links to a new page and API.',
  buttonText: 'Try It',
  icon: <CampaignIcon />,
  iconColor: 'primary.main',
  onAction: ({ navigate }) => navigate('/echo'),
};

```

## 3) Extend the frontend routes

Append the new route inside `webapp/packages/webui/src/extensions/echo.routes.jsx`:

```jsx
import EchoPage from '../../pages/EchoPage';

export const route = {
    path: '/echo',
    element: <EchoPage />,
    // Inherits PrivateRoute + Layout by default
  }
```

All routes defined here are merged with `src/config/routesConfig.jsx`, so the Echo page sits alongside the built-in screens.

## 4) Register the Echo card

Create `webapp/packages/webui/src/extensions/echo.card.jsx`:

```jsx
import React from 'react';
import { Button, Card, CardActions, CardContent, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

const EchoCard = () => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h5" component="div">
          Echo Extension
        </Typography>
        <Typography sx={{ mt: 1.5 }} color="text.secondary">
          An example of a custom card that links to a new page and API.
        </Typography>
      </CardContent>
      <CardActions>
        <Button component={Link} to="/echo" size="small">
          Try It
        </Button>
      </CardActions>
    </Card>
  );
};

export default EchoCard;
```

(Optional) If you want to control the card’s order or grouping, add an entry to `CARD_CONFIG_OVERRIDES` (for example via `.env` or `window.__CARD_CONFIG_OVERRIDES__`).

## 5) Build and run

1. Copy the updated `webapp` directory into your external repository.
2. Add the new files above and set `APP_ROUTER_CONFIG=extensions.echo_router_config` when you launch the API.
3. Build the UI (from the `webapp` folder):

   ```bash
   pnpm install
   pnpm --filter webui build
   ```

You will see a new Echo card on the home page. Clicking it loads the Echo page; submitting text hits `/extensions/echo`, and the response is rendered immediately.
