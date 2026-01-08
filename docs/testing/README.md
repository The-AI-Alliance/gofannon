# Testing Documentation

This directory contains comprehensive documentation for testing the Gofannon project.

## Quick Links

- [Testing Overview](./overview.md) - Introduction to the testing strategy
- [Unit Testing Guide](./unit-testing.md) - How to write and run unit tests
- [Integration Testing Guide](./integration-testing.md) - How to write and run integration tests
- [Frontend Testing Guide](./frontend-testing.md) - React component testing with Vitest
- [Backend Testing Guide](./backend-testing.md) - Python API testing with pytest
- [CI/CD Testing](./ci-cd.md) - GitHub Actions workflows and automation
- [Coverage Requirements](./coverage.md) - Coverage thresholds and reporting
- [Contributing Tests](./contributing.md) - Guidelines for writing tests in PRs

## Testing Philosophy

Gofannon maintains a comprehensive testing strategy with:

- **95% minimum code coverage** for all new code (goal not enforced yet)
- **Unit tests** run on every PR
- **Integration tests** run nightly
- **Fast feedback** - unit tests complete in under 2 minutes
- **Isolated tests** - no dependencies between test cases
- **Clear test structure** - easy to understand and maintain

## Quick Start

### Running All Tests

```bash
# From the webapp directory
cd webapp

# Run all unit tests (frontend + backend)
pnpm test:unit

# Run all integration tests (backend + E2E)
pnpm test:integration

# Run everything
pnpm test
```

### Running Tests with Coverage

```bash
# Frontend coverage
pnpm test:coverage:frontend

# Backend coverage
pnpm test:coverage:backend

# All coverage
pnpm test:coverage
```

### Running Specific Test Suites

```bash
# Frontend unit tests only
pnpm test:unit:frontend

# Backend unit tests only
pnpm test:unit:backend

# Backend integration tests only
pnpm test:integration:backend

# E2E tests only
pnpm test:e2e
```

## Project Structure

```
webapp/
├── packages/
│   ├── webui/                          # Frontend React app
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── ActionCard.jsx
│   │   │   │   └── ActionCard.test.jsx  # Component unit tests
│   │   │   └── test/
│   │   │       ├── setup.ts             # Vitest setup
│   │   │       └── utils.test.js        # Utility tests
│   │   ├── vitest.config.ts             # Vitest configuration
│   │   └── package.json
│   │
│   └── api/
│       └── user-service/                # Backend Python API
│           ├── tests/
│           │   ├── conftest.py          # Pytest fixtures
│           │   ├── unit/                # Unit tests
│           │   │   ├── test_user_service.py
│           │   │   └── test_user_model.py
│           │   ├── integration/         # Integration tests
│           │   │   └── test_health_endpoint.py
│           │   └── factories/           # Test data factories
│           │       ├── agent_factory.py
│           │       ├── user_factory.py
│           │       └── chat_factory.py
│           ├── pytest.ini               # Pytest configuration
│           ├── .coveragerc              # Coverage configuration
│           └── requirements.txt
│
├── tests/
│   └── e2e/                            # Playwright E2E tests
│
└── playwright.config.js                # Playwright configuration

.github/
└── workflows/
    ├── pr-unit-tests.yml               # Runs on every PR
    └── nightly-integration-tests.yml   # Runs every night at 2 AM UTC
```

## Test Types

### Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual functions, classes, and components in isolation
- **Mocking**: Use mocks for external dependencies (DB, API calls, etc.)
- **Speed**: Fast (< 100ms per test)
- **Run**: On every PR via GitHub Actions

### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test multiple components working together
- **Services**: Require running Docker services (CouchDB, MinIO, etc.)
- **Speed**: Slower (500ms - 5s per test)
- **Run**: Nightly via GitHub Actions

### E2E Tests
- **Location**: `webapp/tests/e2e/`
- **Purpose**: Test complete user workflows in the browser
- **Tool**: Playwright
- **Speed**: Slow (5s - 30s per test)
- **Run**: Nightly via GitHub Actions

## Coverage Requirements

- **Minimum Coverage**: 95% for lines, functions, branches, and statements
- **Enforcement**: Automated checks in CI/CD
- **Reports**: Generated in HTML, XML, and LCOV formats
- **Uploads**: Coverage data uploaded to Codecov

### Viewing Coverage Reports

#### Frontend (Vitest)
```bash
cd webapp/packages/webui
pnpm test:coverage
# Open ./coverage/index.html in browser
```

#### Backend (pytest)
```bash
cd webapp/packages/api/user-service
python -m pytest tests/unit --cov=. --cov-report=html
# Open ./htmlcov/index.html in browser
```

## CI/CD Integration

### PR Checks (Automatic)
When you open a PR, the following tests run automatically:
- Frontend unit tests with coverage
- Backend unit tests with coverage
- Lint checks
- Coverage threshold validation (must be ≥95%)

**PR will be blocked if**:
- Any test fails
- Coverage drops below 95%
- Lint errors exist

### Nightly Tests (Scheduled)
Every night at 2 AM UTC, comprehensive tests run:
- Backend integration tests with full Docker stack
- E2E tests with Playwright
- Full coverage reports uploaded

**Team is notified if**:
- Any nightly test fails
- Services fail to start
- Tests timeout

## Best Practices

1. **Write tests before code** (TDD when possible)
2. **One assertion per test** (makes failures clear)
3. **Use descriptive test names** (`test_user_creation_with_valid_data`)
4. **Keep tests independent** (no shared state)
5. **Use factories for test data** (don't repeat yourself)
6. **Mock external services** in unit tests
7. **Test edge cases** (null, empty, invalid input)
8. **Test error handling** (exceptions, validation failures)

## Getting Help

- Check the specific testing guides in this directory
- Review example tests in the codebase
- Ask in the team chat for testing questions
- Open an issue for testing infrastructure problems

## Next Steps

- Read the [Unit Testing Guide](./unit-testing.md) to write your first test
- Review [Contributing Tests](./contributing.md) before submitting a PR
- Explore [Frontend Testing Guide](./frontend-testing.md) for React testing patterns
