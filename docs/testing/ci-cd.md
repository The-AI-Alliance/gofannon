# CI/CD Testing

This guide covers automated testing in GitHub Actions, coverage reporting, and continuous integration workflows.

## Overview

Gofannon uses GitHub Actions to run tests automatically:

| Workflow | Trigger | Tests Run | Purpose |
|----------|---------|-----------|---------|
| **PR Unit Tests** | Every PR | Unit tests + lint | Fast feedback on changes |
| **Nightly Integration** | 2 AM UTC daily | Integration + E2E | Comprehensive validation |

## Workflows

### PR Unit Tests (`pr-unit-tests.yml`)

Runs on every pull request to ensure code quality before merge.

**What runs:**
- Frontend unit tests (Vitest)
- Backend unit tests (pytest)
- Lint checks (ESLint, Ruff/Black)
- Coverage threshold validation

**PR will be blocked if:**
- Any test fails
- Coverage drops below threshold (95%)
- Lint errors exist

```yaml
# .github/workflows/pr-unit-tests.yml
name: PR Unit Tests

on:
  pull_request:
    branches: [main]

jobs:
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'pnpm'
      
      - run: pnpm install
      - run: pnpm --filter webui test:coverage
      
      - uses: codecov/codecov-action@v3
        with:
          files: ./webapp/packages/webui/coverage/lcov.info
          flags: frontend

  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd webapp/packages/api/user-service
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        run: |
          cd webapp/packages/api/user-service
          python -m pytest tests/unit --cov=. --cov-report=xml
      
      - uses: codecov/codecov-action@v3
        with:
          files: ./webapp/packages/api/user-service/coverage.xml
          flags: backend

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - run: pnpm install
      - run: pnpm lint
```

### Nightly Integration Tests (`nightly-integration-tests.yml`)

Runs comprehensive tests every night to catch integration issues.

**What runs:**
- Backend integration tests with full Docker stack
- E2E tests with Playwright
- Full coverage reports
- Performance regression checks

**Team is notified if:**
- Any test fails
- Services fail to start
- Tests timeout (>30 minutes)

```yaml
# .github/workflows/nightly-integration-tests.yml
name: Nightly Integration Tests

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Allow manual trigger

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      couchdb:
        image: couchdb:latest
        ports:
          - 5984:5984
        env:
          COUCHDB_USER: admin
          COUCHDB_PASSWORD: password
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          cd webapp/packages/api/user-service
          pip install -r requirements.txt
      
      - name: Wait for CouchDB
        run: |
          until curl -s http://localhost:5984/_up; do sleep 1; done
      
      - name: Run integration tests
        env:
          DATABASE_PROVIDER: couchdb
          COUCHDB_URL: http://localhost:5984
          COUCHDB_USER: admin
          COUCHDB_PASSWORD: password
        run: |
          cd webapp/packages/api/user-service
          python -m pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      
      - run: pnpm install
      - run: npx playwright install --with-deps
      
      - name: Start services
        run: |
          cd webapp/infra/docker
          docker compose up -d
          sleep 30  # Wait for services
      
      - name: Run E2E tests
        run: pnpm test:e2e
      
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## Coverage

### Thresholds

| Metric | Minimum |
|--------|---------|
| Lines | 95% |
| Functions | 95% |
| Branches | 95% |
| Statements | 95% |

### Coverage Reports

Coverage is generated in multiple formats:

| Format | Purpose |
|--------|---------|
| **HTML** | Interactive local viewing |
| **XML** | CI/CD integration |
| **LCOV** | Codecov uploads |

### Codecov Integration

Coverage data is automatically uploaded to Codecov:

- **PR Coverage Diffs:** See which lines your changes cover
- **Historical Trends:** Track coverage over time
- **Per-File Breakdown:** Identify under-tested files

View reports at: `https://codecov.io/gh/The-AI-Alliance/gofannon`

### Running Coverage Locally

```bash
cd webapp

# All coverage
pnpm test:coverage

# Frontend only
cd packages/webui
pnpm test:coverage
open coverage/index.html

# Backend only
cd packages/api/user-service
python -m pytest tests/unit --cov=. --cov-report=html
open htmlcov/index.html
```

## Workflow Files

Located in `.github/workflows/`:

```
.github/workflows/
├── pr-unit-tests.yml           # Runs on every PR
├── nightly-integration-tests.yml  # Runs every night
└── release.yml                 # Runs on releases
```

## Viewing Results

### GitHub Actions UI

1. Go to the repository on GitHub
2. Click the "Actions" tab
3. Select a workflow to see runs
4. Click a run to see logs and artifacts

### PR Status Checks

PRs show status checks at the bottom:

- ✅ Green check: All tests passed
- ❌ Red X: Tests failed (click for details)
- 🟡 Yellow dot: Tests running

### Downloading Artifacts

Failed E2E tests upload screenshots and traces:

1. Go to the failed workflow run
2. Scroll to "Artifacts"
3. Download `playwright-report`
4. Extract and open `index.html`

## Troubleshooting CI Failures

### Tests Pass Locally but Fail in CI

Common causes:
- **Missing environment variables:** Check workflow env section
- **Different Node/Python versions:** Match CI versions locally
- **Timing issues:** CI may be slower, increase timeouts
- **Missing dependencies:** Ensure all deps are in requirements.txt/package.json

### Flaky Tests

Tests that sometimes pass, sometimes fail:

1. Check for race conditions
2. Remove time-dependent assertions
3. Ensure proper test isolation
4. Add retries for network-dependent tests

### Coverage Threshold Failures

If coverage drops below 95%:

1. Run coverage locally to identify gaps
2. Add tests for uncovered lines
3. Or use `# pragma: no cover` for unreachable code

## Adding New Workflows

1. Create YAML file in `.github/workflows/`
2. Define trigger (`on:`)
3. Define jobs and steps
4. Test with `workflow_dispatch` trigger first

## Related Documentation

- [Unit Testing Guide](unit-testing.md)
- [Integration Testing Guide](integration-testing.md)
- [Contributing Tests](contributing.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)