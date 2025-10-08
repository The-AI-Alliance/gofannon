# Gofannon Web Application: Testing Guide

This document outlines the testing strategy for the Gofannon monorepo and provides instructions for running the various test suites. Our approach prioritizes end-to-end and integration tests to ensure the entire system functions correctly as a whole.

## Testing Philosophy

The testing suite is divided into three main categories:

1.  **End-to-End (E2E) Tests:** These tests simulate a full user journey in a real browser. They run against the complete application stack (frontend, backend, and all services) launched via Docker Compose. We use **Playwright** for this.

2.  **API Integration Tests:** These tests target the Python FastAPI backend. They make real HTTP requests to the API endpoints and verify their behavior, including interactions with other services like the MinIO S3 storage. We use **Pytest** with `httpx` for this.

3.  **Web UI Component Tests:** These tests focus on the React components, verifying their rendering and user interactions. Following a "no mocks" principle, these tests run against the live backend API, making them a form of focused integration testing. We use **Vitest** and **React Testing Library** for this.

## Prerequisites

Before running any tests, ensure you have the following installed on your system:
*   [Node.js](https://nodejs.org/en/) (v18+)
*   [pnpm](https://pnpm.io/installation) (v8+)
*   [Python](https://www.python.org/downloads/) (v3.10+)
*   [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose

## Running Tests Locally

All tests are designed to be run against the services defined in `infra/docker/docker-compose.yml`.

### Step 1: Install Dependencies

First, install all project dependencies from the root of the `webapp` directory:

```bash
pnpm install
```

This command will install Node.js dependencies for all workspaces and you will also need to install Python dependencies for the API service:

```bash
pip install -r packages/api/user-service/requirements.txt
```

### Step 2: Start Services

Navigate to the Docker directory and start all application services in detached mode. This includes the Web UI, API, MinIO storage, and a dedicated `test-mcp-server` used for testing tool integration.

```bash
cd infra/docker
docker-compose up --build -d
```

Wait a few moments for all containers to start up and initialize. You can check the status with `docker-compose ps`.

### Step 3: Run the Test Suites

With the services running, you can now execute the desired test suite from the **root of the `webapp` directory**.

#### End-to-End Tests (Playwright)

These tests cover the full agent creation flow, from adding a tool to running the generated code in the sandbox.

```bash
# Run all E2E tests
pnpm test:e2e
```

After the run, you can view a detailed HTML report:

```bash
# Open the Playwright report
pnpm test:e2e:report
```

#### API Integration Tests (Pytest)

These tests validate the API endpoints directly.

```bash
# Run all API integration tests
pnpm test:api
```

#### Web UI Component Tests (Vitest)

These tests validate React component behavior. They require the backend API to be running.

```bash
# Run all Web UI tests
pnpm test:webui
```

### Step 4: Stop Services

Once you are finished with testing, shut down the Docker containers:

```bash
cd infra/docker
docker-compose down
```

## Continuous Integration (CI)

A GitHub Actions workflow is configured to run the full test suite. This workflow is located at:
`.github/workflows/run-tests.yml`

This workflow is triggered manually. To run it:
1.  Navigate to the **Actions** tab in the GitHub repository.
2.  Select the **"Run E2E and Integration Tests"** workflow from the sidebar.
3.  Click the **"Run workflow"** button.

The CI job will perform all the steps outlined above: install dependencies, start services, run all three test suites, and finally shut down the services.