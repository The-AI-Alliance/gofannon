# Testing Guide

Gofannon uses a comprehensive testing strategy with unit tests, integration tests, and E2E tests.

## Quick Reference

```bash
cd webapp

# Run all unit tests (recommended before PRs)
pnpm test:unit

# Run specific test suites
pnpm test:unit:backend     # Python tests
pnpm test:unit:frontend    # React tests

# Run with coverage
pnpm test:coverage

# Run integration tests (requires Docker services)
pnpm test:integration

# Run E2E tests (requires running app)
pnpm test:e2e
```

## Documentation

| Guide | Description |
|-------|-------------|
| [Unit Testing](unit-testing.md) | Testing functions and components in isolation |
| [Backend Testing](backend-testing.md) | Python/pytest patterns and examples |
| [Frontend Testing](frontend-testing.md) | React/Vitest component testing |
| [Integration Testing](integration-testing.md) | Multi-component and E2E testing |
| [CI/CD](ci-cd.md) | GitHub Actions, workflows, and coverage |
| [Contributing Tests](contributing.md) | PR requirements and checklist |

## Test Structure

```
webapp/
├── packages/
│   ├── api/user-service/
│   │   └── tests/
│   │       ├── conftest.py          # Pytest fixtures
│   │       ├── unit/                # Unit tests
│   │       │   ├── test_user_service.py
│   │       │   └── test_llm_service.py
│   │       ├── integration/         # Integration tests
│   │       │   └── test_health_endpoint.py
│   │       └── factories/           # Test data factories
│   │           ├── agent_factory.py
│   │           └── user_factory.py
│   │
│   └── webui/
│       └── src/
│           └── components/
│               ├── ActionCard.jsx
│               └── ActionCard.test.jsx  # Co-located tests
│
└── tests/
    └── e2e/                         # Playwright E2E tests
```

## Test Types

| Type | Location | Purpose | Speed | When Run |
|------|----------|---------|-------|----------|
| **Unit** | `tests/unit/` | Test functions/components in isolation | Fast (<100ms) | Every PR |
| **Integration** | `tests/integration/` | Test services working together | Medium (500ms-5s) | Nightly |
| **E2E** | `tests/e2e/` | Test complete user workflows | Slow (5-30s) | Nightly |

## Coverage Requirements

We aim for **95% coverage** on new code.

| Metric | Minimum |
|--------|---------|
| Lines | 95% |
| Functions | 95% |
| Branches | 95% |
| Statements | 95% |

### Viewing Coverage Reports

```bash
# Backend
cd webapp/packages/api/user-service
python -m pytest tests/unit --cov=. --cov-report=html
open htmlcov/index.html

# Frontend
cd webapp/packages/webui
pnpm test:coverage
open coverage/index.html
```

## Troubleshooting

### Tests Hanging

- Check for missing `await` on async functions
- Verify mocks are properly configured
- Look for infinite loops or blocking calls

### Import Errors

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Flaky Tests

- Remove time-based assertions
- Ensure test isolation (no shared state)
- Check for race conditions in async code

### Coverage Not Increasing

- Verify test markers are correct (`@pytest.mark.unit`)
- Check `.coveragerc` exclusions
- Run coverage report to identify uncovered lines