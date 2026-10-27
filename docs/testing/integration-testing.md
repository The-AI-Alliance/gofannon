# Integration Testing Guide

This guide covers how to write and run integration tests for Gofannon.

## Overview

Integration tests verify that multiple components work together correctly. Unlike unit tests, they may involve real database connections, API calls, and Docker services.

## Running Integration Tests

```bash
# From webapp directory
cd webapp

# Run all integration tests
pnpm test:integration

# Run backend integration tests only
pnpm test:integration:backend
```

## Test Location

Integration tests are located in:
- Backend: `webapp/packages/api/user-service/tests/integration/`
- E2E: `webapp/tests/e2e/`

## Docker Services

Integration tests require running Docker services:

```bash
# Start required services
docker compose up -d couchdb seaweedfs
```

## Writing Integration Tests

Integration tests should:
- Test realistic scenarios with multiple components
- Use real (or containerized) services when appropriate
- Clean up test data after each test
- Be idempotent (can run multiple times safely)

## Related Documentation

- [Unit Testing Guide](./unit-testing.md)
- [Backend Testing Guide](./backend-testing.md)
- [CI/CD Testing](./ci-cd.md)
