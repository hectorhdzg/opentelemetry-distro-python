# azure-monitor-opentelemetry (Temporary)

> **This is a temporary copy of the `azure-monitor-opentelemetry` package source.**

This directory exists solely to validate the integration between the Microsoft OpenTelemetry distro and the Azure Monitor OpenTelemetry pipeline. It allows us to iterate on the distro configuration surface and understand the required changes before they are finalized upstream.

## Important

- **This is not the source of truth.** The canonical source for `azure-monitor-opentelemetry` lives in the [Azure SDK for Python](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/monitor/azure-monitor-opentelemetry) repository.
- **Do not make long-lived changes here.** Any changes required in `azure-monitor-opentelemetry` should be developed in parallel in the actual Azure SDK repository.
- **This copy will be removed** once the upstream package exposes the necessary APIs and the distro can depend on a published release.
