# microsoft-opentelemetry-distro-python

## Repository Setup

The GitHub repository was provisioned with an onboarding placeholder that indicates repository setup and access control configuration may still need to be completed in the onboarding portal.

Until that setup is complete, some repository settings or access-management actions may remain restricted.

Python package for a Microsoft OpenTelemetry distribution that provides a single onboarding experience for observability across Azure Monitor, OTLP-compatible backends, and Microsoft Agent 365 style integrations.

This repository starts from the POC described in `hectorhdzg/microsoft-opentelemetry-poc`, but is intentionally kept minimal while the package shape and delivery plan are being defined.

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

- POC repo: https://github.com/hectorhdzg/microsoft-opentelemetry-poc
- Planning document: [PLANNING.md](/c:/Repos/microsoft-opentelemetry-distro-python/PLANNING.md)

## Repository Policies

- [CODE_OF_CONDUCT.md](/c:/Repos/microsoft-opentelemetry-distro-python/CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](/c:/Repos/microsoft-opentelemetry-distro-python/CONTRIBUTING.md)
- [SECURITY.md](/c:/Repos/microsoft-opentelemetry-distro-python/SECURITY.md)
- [SUPPORT.md](/c:/Repos/microsoft-opentelemetry-distro-python/SUPPORT.md)
- [PRIVACY.md](/c:/Repos/microsoft-opentelemetry-distro-python/PRIVACY.md)
- [NOTICE.md](/c:/Repos/microsoft-opentelemetry-distro-python/NOTICE.md)
- [LICENSE](/c:/Repos/microsoft-opentelemetry-distro-python/LICENSE)
