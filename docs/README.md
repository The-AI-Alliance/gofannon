# Gofannon Documentation

Gofannon is an open-source platform for rapidly prototyping AI agents and their web UIs. Build agent flows, preview interactions, and deploy—without framework lock-in.

## Quick Links

| I want to... | Go to... |
|--------------|----------|
| Get started using Gofannon | [Quickstart Guide](quickstart/README.md) |
| Set up a dev environment | [Developer Setup](developers-quickstart.md) |
| Configure LLM providers | [LLM Configuration](llm-provider-configuration.md) |
| Set up a database | [Database Guide](database/README.md) |
| Run tests | [Testing Guide](testing/README.md) |
| Understand the API | [API Reference](api.md) |

## Getting Started

- **[Quickstart Guide](quickstart/README.md)** - Install Gofannon with Docker and create your first agent in 5 minutes.

- **[Developer Setup](developers-quickstart.md)** - Set up a local development environment for contributing.

## Configuration

- **[LLM Provider Configuration](llm-provider-configuration.md)** - Configure OpenAI, Anthropic, Gemini, Bedrock, and other providers. Covers model parameters, extended thinking, and adding new providers.

- **[API Key Management](api-key-management.md)** - User-specific API keys and the key priority system.

- **[Database Guide](database/README.md)** - Set up CouchDB, Firestore, DynamoDB, or in-memory storage.
  - [Configuration](database/configuration.md) - Environment variables and provider setup
  - [Schema](database/schema.md) - Document structures and collections
  - [Troubleshooting](database/troubleshooting.md) - Common issues and solutions

## Features

- **[Agent Data Store](data-store.md)** - Persistent key-value storage for agents to save and share data across executions.

## Reference

- **[API Reference](api.md)** - HTTP API documentation for the user-service backend.

- **[Observability](observability.md)** - Logging, tracing, and monitoring.

## Development

- **[Testing Guide](testing/README.md)** - Running unit, integration, and E2E tests.
  - [Unit Testing](testing/unit-testing.md) - Detailed patterns and examples
  - [Backend Testing](testing/backend-testing.md) - Python/pytest guide
  - [Frontend Testing](testing/frontend-testing.md) - React/Vitest guide
  - [Integration Testing](testing/integration-testing.md) - Multi-component and E2E tests
  - [CI/CD](testing/ci-cd.md) - GitHub Actions and coverage
  - [Contributing Tests](testing/contributing.md) - PR requirements

- **[Extension Example](EXTENSION_EXAMPLE.md)** - How to add custom pages, cards, and API endpoints.

- **[LLM Service](developers/llm-service.md)** - Architecture of the centralized LLM service, cost tracking, and why all LLM calls must go through it.

- **[Website Development](developers/website.md)** - Building the Docusaurus marketing website.

- **[Architecture](architecture.md)** - System design overview.

## About

- **[Why "Gofannon"?](about-name-origin.md)** - The story behind our Celtic deity namesake.

- **[Roadmap](roadmap.md)** - Planned features and design discussions.

## Project Structure

```
gofannon/
├── webapp/
│   ├── packages/
│   │   ├── api/user-service/    # Python FastAPI backend
│   │   ├── webui/               # React frontend
│   │   └── config/              # Shared configuration
│   ├── infra/
│   │   ├── docker/              # Docker Compose setup
│   │   └── firebase/            # Firebase deployment
│   └── tests/e2e/               # Playwright E2E tests
├── docs/                        # This documentation
└── website/                     # Marketing site
```

## Getting Help

- **Issues**: [Report bugs or request features](https://github.com/The-AI-Alliance/gofannon/issues)
- **Discussions**: [Ask questions](https://github.com/The-AI-Alliance/gofannon/discussions)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)

## License

Apache 2.0 - See [LICENSE](../LICENSE)