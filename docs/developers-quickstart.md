# Developer Quickstart Guide

This guide provides instructions for setting up your development environment to contribute to Gofannon.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Operating System:** Linux, macOS, or WSL (Windows Subsystem for Linux).
- **Python:** Version 3.10 or higher.
- **Node.js:** Version 18 or higher.
- **pnpm:** Version 8 or higher (Installation: `npm install -g pnpm`).
- **Git:** For version control.

## 1. Cloning the Project

We follow a fork-based workflow.

1.  **Fork the repository** on GitHub to your own account.
2.  **Clone your fork** locally:

    ```bash
    git clone https://github.com/YOUR_USERNAME/gofannon.git
    cd gofannon
    ```

3.  **Add the upstream remote** to keep your fork in sync:

    ```bash
    git remote add upstream https://github.com/the-ai-alliance/gofannon.git
    ```

## 2. Setting Up the Environment

The project is a monorepo containing a Python backend and a React frontend. You will need to set up both.

### Backend (Python)

1.  Navigate to the user service directory:

    ```bash
    cd webapp/packages/api/user-service
    ```

2.  Create a virtual environment:

    ```bash
    python3.10 -m venv venv
    ```

3.  Activate the virtual environment:

    -   **Linux/macOS:**
        ```bash
        source venv/bin/activate
        ```
    -   **Windows (PowerShell):**
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```

4.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

### Frontend (Node.js/React)

1.  Navigate to the `gofannon/webapp` directory:

    ```bash
    cd ../../../../../ # Assuming you were in the api directory
    ```

2.  Install dependencies using pnpm:

    ```bash
    pnpm install
    ```

## 3. Running the Application Locally

The recommended workflow is `./dev-tail.sh` from the repo root, which runs the full dev stack — CouchDB, MinIO, the api in docker-compose, and the frontend on the host via vite — and tails the logs in one terminal:

```bash
./dev-tail.sh
```

The API will be at `http://localhost:8000`, the web UI at `http://localhost:3000`. Auth uses the `dev_stub` session-auth provider; pick `alice`, `bob`, or `site_admin_1` from the picker on first visit. See `docs/developers/local-auth.md` for the auth fixture details.

### Running components individually

If you want to run only the backend or only the frontend (e.g., to debug one in isolation):

**Backend.** Ensure your virtual environment is activated, then:

```bash
cd webapp/packages/api/user-service
uvicorn main:app --reload
```

API at `http://localhost:8000`.

**Frontend.** Vite is host-based and doesn't need a container:

```bash
cd webapp
pnpm --filter webui dev
```

Web UI at `http://localhost:3000`.

## 4. Running Tests

We strongly encourage running tests locally before opening a Pull Request.

### Backend Tests

From the `webapp` directory (or root), with your virtual environment from the previous step activated:

```bash
# Run backend unit tests
pnpm test:unit:backend

# Or directly from the user-service directory with active venv
cd webapp/packages/api/user-service
python -m pytest tests/unit -v
```

### Frontend Tests

From the `webapp` directory:

```bash
# Run frontend unit tests
pnpm test:unit:frontend
```

### All Tests

To run all unit tests:

```bash
cd webapp
pnpm test:unit
```

## 5. Development Conventions

To ensure a smooth collaboration process, please adhere to the following conventions:

-   **Fork & Branch:** Always work on your own fork.
-   **Branch Naming:**
    -   Use the issue number as the prefix if applicable: `XXX-short-desc` (e.g., `123-fix-login-bug`).
    -   Alternatively, use `feature/` or `fix/` prefixes if no issue exists.
-   **Commit Signing:** Sign your commits using `git commit -s` to certify the Developer Certificate of Origin (DCO).
-   **Testing:**
    -   Run existing tests to ensure no regressions.
    -   Add new tests for any new code or features you implement.
    -   Ensure `pnpm test:unit` passes before submitting a PR.
-   **Code Style:** Follow the existing coding style in the project.

Thank you for contributing!
