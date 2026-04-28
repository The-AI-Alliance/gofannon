<p align="center">
  <img src="https://raw.githubusercontent.com/The-AI-Alliance/gofannon/main/website/static/img/logo_1000x1260.png" alt="Gofannon" width="200">
</p>

# Gofannon

[![PyPI](https://img.shields.io/pypi/v/gofannon)](https://pypi.org/project/gofannon/)
[![License](https://img.shields.io/github/license/The-AI-Alliance/gofannon)](LICENSE)
[![Issues](https://img.shields.io/github/issues/The-AI-Alliance/gofannon)](https://github.com/The-AI-Alliance/gofannon/issues)

Gofannon is a provider- and model-agnostic toolkit and web application for prototyping AI agents and the lightweight web UIs that wrap them. Subject matter experts compose tools, data sources, and decision paths through a guided interface, preview agent interactions in real time, and hand off working agent-driven experiences without committing to a single AI framework or model provider.

## What you can do

- **Prototype agents quickly.** Compose tools, data sources, and decision paths through a guided interface, and iterate with real-time feedback.
- **Design lightweight web UIs.** Pair agents with forms, chat surfaces, and dashboards to validate user journeys; export or embed prototypes to share with stakeholders.
- **Stay flexible.** Gofannon supports multiple model providers (OpenAI, Anthropic, Gemini, and others via LiteLLM) and is designed to keep your work portable across them.

## Quickstart

```bash
git clone https://github.com/The-AI-Alliance/gofannon.git
cd gofannon/webapp/infra/docker
docker-compose up --build
```

See the [quickstart guide](docs/quickstart/README.md) for details, including required environment configuration.

## Documentation

Full documentation lives in [`docs/`](docs/) and is published at <https://the-ai-alliance.github.io/gofannon/>. Highlights:

- [Quickstart](docs/quickstart/README.md)
- [Developer quickstart](docs/developers-quickstart.md)
- [API reference](docs/api.md)
- [LLM provider configuration](docs/llm-provider-configuration.md)
- [Testing](docs/testing/README.md)

## About the name

Gofannon is the Welsh god of smithcraft. See [About the name](docs/about-name-origin.md) for the story behind the choice.

## Roadmap

Planned features and their current status are tracked in [ROADMAP.md](ROADMAP.md).

## Community

- Report bugs or request features in [GitHub Issues](https://github.com/The-AI-Alliance/gofannon/issues).
- Ask questions and discuss ideas in [GitHub Discussions](https://github.com/The-AI-Alliance/gofannon/discussions).

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started, including the "good first issue" label for newcomers and contribution guides for adding tools, integrating new agentic frameworks, and extending the web UI.

## Acknowledgments

Thanks to the open-source community for contributions and support that have made this project possible.

[![Contributors](https://contrib.rocks/image?repo=The-AI-Alliance/gofannon)](https://github.com/The-AI-Alliance/gofannon/graphs/contributors)

## License

Gofannon is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
