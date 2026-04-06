# microsoft-opentelemetry

[![PyPI version](https://img.shields.io/pypi/v/microsoft-opentelemetry)](https://pypi.org/project/microsoft-opentelemetry/)

## Repository Setup

The GitHub repository was provisioned with an onboarding placeholder that indicates repository setup and access control configuration may still need to be completed in the onboarding portal.

Until that setup is complete, some repository settings or access-management actions may remain restricted.

Python package for a Microsoft OpenTelemetry distribution that provides a single onboarding experience for observability across Azure Monitor, OTLP-compatible backends, and Microsoft Agent 365 style integrations.

This repository starts from the POC described in `azure-data/microsoft-opentelemetry-distro-poc`, but is intentionally kept minimal while the package shape and delivery plan are being defined.

## Goal

The target package should reduce fragmented setup across multiple observability stacks to one import and one configuration function.

Intended API shape:

```python
from microsoft.opentelemetry import configure_microsoft_opentelemetry

configure_microsoft_opentelemetry(
	azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
	enable_otlp_export=True,
	enable_genai_openai_instrumentation=True,
)
```

## Planned Scope

- Azure Monitor exporter support
- OTLP exporter support
- Microsoft-specific agent observability extensions
- GenAI instrumentation toggles for OpenAI, OpenAI Agents, and LangChain
- Standard Python web and HTTP instrumentations
- Environment-variable driven configuration
- A stable package surface for downstream agent applications

## Reference POC Highlights

The source POC positions the distro around three outcomes:

- one package, one API, one documentation surface
- less duplicated exporter and instrumentation wiring across teams
- much less application boilerplate compared with manual OpenTelemetry setup

The POC also describes this execution model:

1. Configure Azure Monitor when enabled
2. Otherwise create standalone OpenTelemetry providers
3. Attach OTLP exporters when requested
4. Attach Microsoft-specific exporters when requested
5. Enable standard instrumentations
6. Enable Microsoft-specific observability instrumentations
7. Enable GenAI contrib instrumentations

## Current Repository Layout

- `src/` package source
- `tests/` test suite
- `pyproject.toml` project metadata and dependencies
- `PLANNING.md` implementation plan and open questions

## Development

Create an environment and install the project with test dependencies:

```bash
pip install -e .[test]
pytest
```

## Reference

- POC repo: https://github.com/azure-data/microsoft-opentelemetry-distro-poc
- Planning document: [PLANNING.md](./PLANNING.md)

## Contributing

Read our [contributing guide](./CONTRIBUTING.md) to learn about our development process, how to propose bugfixes and improvements, and how to build and test your changes to this distribution.

## Data Collection

As this SDK is designed to enable applications to perform data collection which is sent to the Microsoft collection endpoints the following is required to identify our privacy statement.

The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.

## License

[MIT](LICENSE)