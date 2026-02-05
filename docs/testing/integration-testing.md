# Integration Testing Guide

This guide covers integration tests and end-to-end (E2E) tests that verify multiple components working together.

## Overview

Integration tests verify that components work together correctly. Unlike unit tests, they may use real database connections, actual API calls, and running services.

| Test Type | Scope | Services | Speed |
|-----------|-------|----------|-------|
| **Unit** | Single function/component | All mocked | Fast (<100ms) |
| **Integration** | Multiple components | Some real | Medium (500ms-5s) |
| **E2E** | Full user workflow | All real | Slow (5-30s) |

## Running Integration Tests

### Backend Integration Tests

```bash
cd webapp

# Start required services
docker compose -f infra/docker/docker-compose.yml up -d couchdb

# Run integration tests
pnpm test:integration:backend

# Or directly with pytest
cd packages/api/user-service
python -m pytest tests/integration/ -v
```

### E2E Tests (Playwright)

```bash
cd webapp

# Start the full application
docker compose -f infra/docker/docker-compose.yml up -d

# Run E2E tests
pnpm test:e2e

# Run with UI (for debugging)
pnpm test:e2e -- --ui

# Run specific test file
pnpm test:e2e -- tests/e2e/login.spec.js

# Run headed (see browser)
pnpm test:e2e -- --headed
```

## Test Location

```
webapp/
├── packages/
│   └── api/user-service/
│       └── tests/
│           └── integration/              # Backend integration tests
│               ├── test_health_endpoint.py
│               ├── test_agent_crud.py
│               └── test_chat_workflow.py
│
└── tests/
    └── e2e/                              # Playwright E2E tests
        ├── login.spec.js
        ├── agent-creation.spec.js
        └── chat-workflow.spec.js
```

## Writing Backend Integration Tests

### Testing with Real Database

```python
import pytest
from fastapi.testclient import TestClient
from main import app
from services.database_service import get_database_service

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    """Create test client with real database."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_data(client):
    """Clean up test data after each test."""
    yield
    # Cleanup code here
    db = get_database_service()
    # Delete test documents...


class TestAgentCRUD:
    """Integration tests for agent CRUD operations."""

    def test_create_and_retrieve_agent(self, client):
        """Test full create-retrieve cycle."""
        # Create
        create_response = client.post("/api/agents", json={
            "name": "Integration Test Agent",
            "description": "Created by integration test",
        })
        assert create_response.status_code == 201
        agent_id = create_response.json()["id"]

        # Retrieve
        get_response = client.get(f"/api/agents/{agent_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Integration Test Agent"

    def test_update_agent(self, client):
        """Test updating an agent."""
        # Create
        create_response = client.post("/api/agents", json={
            "name": "Original Name",
            "description": "Original description",
        })
        agent_id = create_response.json()["id"]

        # Update
        update_response = client.put(f"/api/agents/{agent_id}", json={
            "name": "Updated Name",
            "description": "Updated description",
        })
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Name"

    def test_delete_agent(self, client):
        """Test deleting an agent."""
        # Create
        create_response = client.post("/api/agents", json={
            "name": "To Be Deleted",
            "description": "This agent will be deleted",
        })
        agent_id = create_response.json()["id"]

        # Delete
        delete_response = client.delete(f"/api/agents/{agent_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/agents/{agent_id}")
        assert get_response.status_code == 404
```

### Testing Multi-Service Workflows

```python
import pytest

pytestmark = pytest.mark.integration


class TestChatWorkflow:
    """Test complete chat workflow across services."""

    def test_chat_session_lifecycle(self, client, test_user):
        """Test creating a session, sending messages, and retrieving history."""
        # Create agent
        agent = client.post("/api/agents", json={
            "name": "Chat Agent",
            "code": "async def run(input_dict, tools): return {'response': 'Hello!'}"
        }).json()

        # Start session
        session = client.post("/api/sessions", json={
            "agent_id": agent["id"],
            "user_id": test_user["id"],
        }).json()

        # Send message
        response = client.post(f"/api/sessions/{session['id']}/messages", json={
            "content": "Hi there!"
        })
        assert response.status_code == 200
        assert "Hello!" in response.json()["content"]

        # Get history
        history = client.get(f"/api/sessions/{session['id']}/messages").json()
        assert len(history) == 2  # User message + agent response
```

## Writing E2E Tests (Playwright)

### Basic Page Test

```javascript
// tests/e2e/home.spec.js
import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('displays welcome message', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.getByRole('heading', { name: /welcome/i })).toBeVisible();
  });

  test('navigates to agent creation', async ({ page }) => {
    await page.goto('/');
    
    await page.click('text=Create Agent');
    
    await expect(page).toHaveURL(/.*agents\/new/);
  });
});
```

### Testing User Workflows

```javascript
// tests/e2e/agent-creation.spec.js
import { test, expect } from '@playwright/test';

test.describe('Agent Creation Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login or setup
    await page.goto('/');
  });

  test('creates a new agent', async ({ page }) => {
    // Navigate to creation
    await page.click('text=Create Agent');
    
    // Fill form
    await page.fill('[name="name"]', 'Test Agent');
    await page.fill('[name="description"]', 'A test agent');
    
    // Select model
    await page.click('[data-testid="model-selector"]');
    await page.click('text=Claude Sonnet');
    
    // Generate code
    await page.click('text=Generate Code');
    await expect(page.locator('[data-testid="code-editor"]')).toContainText('async def run');
    
    // Save
    await page.click('text=Save Agent');
    
    // Verify success
    await expect(page.getByText('Agent saved successfully')).toBeVisible();
  });

  test('validates required fields', async ({ page }) => {
    await page.click('text=Create Agent');
    
    // Try to save without filling required fields
    await page.click('text=Save Agent');
    
    // Check for validation errors
    await expect(page.getByText('Name is required')).toBeVisible();
  });
});
```

### Testing with Authentication

```javascript
// tests/e2e/auth.setup.js
import { test as setup } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '../.auth/user.json');

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  
  await page.fill('[name="email"]', process.env.TEST_USER_EMAIL);
  await page.fill('[name="password"]', process.env.TEST_USER_PASSWORD);
  await page.click('button[type="submit"]');
  
  // Wait for login to complete
  await page.waitForURL('/dashboard');
  
  // Save authentication state
  await page.context().storageState({ path: authFile });
});

// In other tests, use the authenticated state
// test.use({ storageState: authFile });
```

## Docker Services for Testing

### Required Services

```yaml
# docker-compose.test.yml
services:
  couchdb:
    image: couchdb:latest
    ports:
      - "5984:5984"
    environment:
      - COUCHDB_USER=admin
      - COUCHDB_PASSWORD=password

  api:
    build: ./packages/api/user-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_PROVIDER=couchdb
      - COUCHDB_URL=http://couchdb:5984
    depends_on:
      - couchdb

  webui:
    build: ./packages/webui
    ports:
      - "3000:3000"
    depends_on:
      - api
```

### Starting Services for Tests

```bash
# Start all services
docker compose -f infra/docker/docker-compose.yml up -d

# Wait for services to be ready
./scripts/wait-for-services.sh

# Run tests
pnpm test:e2e

# Cleanup
docker compose -f infra/docker/docker-compose.yml down
```

## Configuration

### Playwright Configuration

```javascript
// playwright.config.js
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  retries: process.env.CI ? 2 : 0,
  
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
  ],

  webServer: {
    command: 'pnpm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
```

## Best Practices

1. **Isolate test data:** Each test should create and clean up its own data
2. **Use realistic scenarios:** Test actual user workflows
3. **Handle async operations:** Wait for operations to complete before asserting
4. **Make tests idempotent:** Can run multiple times without side effects
5. **Use page objects:** Abstract page interactions for maintainability

## Debugging

### Playwright Debug Mode

```bash
# Run with debug UI
pnpm test:e2e -- --debug

# Run headed (see browser)
pnpm test:e2e -- --headed

# Pause on failure
PWDEBUG=1 pnpm test:e2e
```

### View Test Reports

```bash
# Generate and view HTML report
pnpm test:e2e -- --reporter=html
npx playwright show-report
```

## Related Documentation

- [Unit Testing Guide](unit-testing.md)
- [Backend Testing Guide](backend-testing.md)
- [CI/CD](ci-cd.md) - Automated test runs
- [Playwright Documentation](https://playwright.dev/docs/intro)