# microsoft-opentelemetry

[![PyPI version](https://img.shields.io/pypi/v/microsoft-opentelemetry)](https://pypi.org/project/microsoft-opentelemetry/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/pypi/pyversions/microsoft-opentelemetry)](https://pypi.org/project/microsoft-opentelemetry/)

Python package for a Microsoft OpenTelemetry distribution that provides a single onboarding experience for observability across Azure Monitor, OTLP-compatible backends, and Microsoft Agent 365 style integrations.

## Getting Started

### Prerequisites

- Python 3.10 or later — [Install Python](https://www.python.org/downloads/)
- Azure subscription (optional, for Azure Monitor) — [Create a free account](https://azure.microsoft.com/free/)
- Application Insights resource (optional) — [How to use Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview)

### Install the package

Install the Microsoft OpenTelemetry Distro with [pip](https://pypi.org/project/pip/):

```bash
pip install microsoft-opentelemetry
```

### Usage

Use `use_microsoft_opentelemetry` to set up instrumentation for your application. All passed-in parameters take priority over any related environment variables.

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
)
```

#### Configuration Options

| Keyword argument | Type | Default | Description |
|---|---|---|---|
| `enable_azure_monitor` | `bool` | `True` | Enable Azure Monitor export. |
| `azure_monitor_connection_string` | `str` | `None` | Connection string for Application Insights. Also read from `APPLICATIONINSIGHTS_CONNECTION_STRING` env var. |
| `azure_monitor_exporter_credential` | `TokenCredential` | `None` | Azure AD token credential for authentication. |
| `azure_monitor_enable_live_metrics` | `bool` | `True` | Enable live metrics collection. |
| `azure_monitor_enable_performance_counters` | `bool` | `True` | Enable performance counter collection. |
| `azure_monitor_exporter_disable_offline_storage` | `bool` | `False` | Disable offline retry storage for failed telemetry. |
| `azure_monitor_exporter_storage_directory` | `str` | `None` | Custom directory for offline telemetry storage. |
| `azure_monitor_browser_sdk_loader_config` | `dict` | `None` | Browser SDK loader configuration. |
| `disable_logging` | `bool` | `False` | Disable the logging pipeline. |
| `disable_tracing` | `bool` | `False` | Disable the tracing pipeline. |
| `disable_metrics` | `bool` | `False` | Disable the metrics pipeline. |
| `resource` | `Resource` | auto | OpenTelemetry Resource. |
| `span_processors` | `list` | `[]` | Additional span processors. |
| `log_record_processors` | `list` | `[]` | Additional log record processors. |
| `metric_readers` | `list` | `[]` | Additional metric readers. |
| `views` | `list` | `[]` | Metric views. |
| `logger_name` | `str` | `None` | Logger name for log collection. |
| `logging_formatter` | `Formatter` | `None` | Formatter for collected logs. |
| `instrumentation_options` | `dict` | `None` | Per-library instrumentation enable/disable options. |
| `enable_trace_based_sampling_for_logs` | `bool` | `False` | Enable trace-based sampling for logs. |
| `enable_a365` | `bool` | `False` | Enable Agent365 telemetry export. |
| `a365_token_resolver` | `Callable` | `None` | `(agent_id, tenant_id) -> token` callable for A365 auth. If omitted, defaults to FIC/DefaultAzureCredential. |
| `a365_tenant_id` | `str` | `None` | Tenant ID stamped on spans. Falls back to `A365_TENANT_ID` env var. |
| `a365_agent_id` | `str` | `None` | Agent ID stamped on spans. Falls back to `A365_AGENT_ID` env var. |
| `a365_cluster_category` | `str` | `"prod"` | Cluster category for endpoint discovery. Falls back to `A365_CLUSTER_CATEGORY` env var. |
| `a365_use_s2s_endpoint` | `bool` | `False` | Use the S2S endpoint. Falls back to `A365_USE_S2S_ENDPOINT` env var. |
| `a365_suppress_invoke_agent_input` | `bool` | `False` | Strip input messages from InvokeAgent spans. Falls back to `A365_SUPPRESS_INVOKE_AGENT_INPUT` env var. |
| `enable_console` | `bool` | `False` | Enable console exporter for traces, metrics, and logs (development only). Auto-enables when no other exporter is active. Mirrors `ExportTarget.Console` from the .NET distro. |

A365 also reads additional environment variables for FIC (Federated Identity Credential) authentication. Kwargs take precedence when provided.

#### FIC Authentication Environment Variables

These are used automatically when no `a365_token_resolver` kwarg is provided and the hosting environment supplies them:

| Environment variable | Description |
|---|---|
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` | Service principal client ID for the FIC flow. |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Service principal client secret. |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID` | AAD tenant ID for the FIC authority. |
| `A365_AGENT_APP_INSTANCE_ID` | Agent application instance ID for the FIC grant. |
| `A365_AGENTIC_USER_ID` | Agentic user ID for the FIC user-assertion step. |

When FIC variables are not available, `DefaultAzureCredential` from `azure-identity` is used as a fallback.

### Sampling Configuration

Sampling is configured via standard OpenTelemetry environment variables:

| Environment variable | Description |
|---|---|
| `OTEL_TRACES_SAMPLER` | Sampler type to use (see supported values below). |
| `OTEL_TRACES_SAMPLER_ARG` | Argument for the sampler (e.g. sample ratio or traces per second). |

**Supported sampler values for `OTEL_TRACES_SAMPLER`:**

| Value | Description |
|---|---|
| `always_on` | Sample every trace. |
| `always_off` | Drop every trace. |
| `trace_id_ratio` | Sample a fixed percentage based on trace ID. Set ratio with `OTEL_TRACES_SAMPLER_ARG` (0–1). |
| `parentbased_always_on` | Parent-based, defaults to always on. |
| `parentbased_always_off` | Parent-based, defaults to always off. |
| `parentbased_trace_id_ratio` | Parent-based with trace ID ratio fallback. |
| `microsoft.fixed_percentage` | Azure Monitor fixed-percentage sampler. Set ratio with `OTEL_TRACES_SAMPLER_ARG` (0–1). |
| `microsoft.rate_limited` | Azure Monitor rate-limited sampler. Set target with `OTEL_TRACES_SAMPLER_ARG` (traces per second, default 5). |

**Example:**

```bash
export OTEL_TRACES_SAMPLER=trace_id_ratio
export OTEL_TRACES_SAMPLER_ARG=0.1
```

### Agent365 (A365) Configuration

When `enable_a365=True`, the distro adds A365 span processors to the tracing pipeline. A365 exporter behavior is configured via environment variables:

| Environment variable | Default | Description |
|---|---|---|
| `ENABLE_A365_OBSERVABILITY_EXPORTER` | `false` | Enable the A365 HTTP exporter. When `false`, no A365 span processors are added and no A365-specific processing occurs. |
| `A365_TENANT_ID` | `None` | Tenant ID stamped on every span. |
| `A365_AGENT_ID` | `None` | Agent ID stamped on every span. |
| `A365_CLUSTER_CATEGORY` | `prod` | Cluster category for endpoint discovery (`prod`, `gov`, `dod`, `mooncake`). |
| `A365_USE_S2S_ENDPOINT` | `false` | Use the S2S endpoint instead of the standard endpoint. |
| `A365_SUPPRESS_INVOKE_AGENT_INPUT` | `false` | Strip input messages from InvokeAgent spans before export. |
| `ENABLE_OBSERVABILITY` | `false` | Master switch for A365 scope telemetry. Must be `true` for scope classes to emit spans. |

**Example:**

```bash
export ENABLE_OBSERVABILITY=true
export ENABLE_A365_OBSERVABILITY_EXPORTER=true
export A365_TENANT_ID=my-tenant-id
export A365_AGENT_ID=my-agent-id
```

### OTLP Export Configuration

OTLP export is automatically enabled when any of the standard `OTEL_EXPORTER_OTLP_*` endpoint environment variables are set. No kwargs are needed.

| Environment variable | Description |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Base endpoint URL for all signals (e.g. `http://localhost:4318`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | Per-signal override for traces. |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | Per-signal override for metrics. |
| `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` | Per-signal override for logs. |
| `OTEL_EXPORTER_OTLP_HEADERS` | Comma-separated `key=value` pairs sent as headers. |
| `OTEL_EXPORTER_OTLP_TIMEOUT` | Max time in milliseconds per export request. |
| `OTEL_EXPORTER_OTLP_COMPRESSION` | `gzip` or `none`. |

Per-signal overrides follow the pattern `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_{ENDPOINT,HEADERS,TIMEOUT,COMPRESSION}`.

**Example:**

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
python my_app.py
```

### Console Exporter (Development)

The console exporter writes traces, metrics, and logs to stdout for local development and debugging. This mirrors the `ExportTarget.Console` behaviour from the [.NET distro](https://github.com/microsoft/opentelemetry-distro-dotnet).

Console export **auto-enables when no other exporter is active** (Azure Monitor off, OTLP off, A365 off). You can also enable it explicitly alongside other exporters.

**Example:**

```python
use_microsoft_opentelemetry(
    enable_console=True,
    enable_azure_monitor=False,
)
```

### Auto-Instrumented Libraries

The distro automatically instruments the following libraries when they are installed:

| Library | Category |
|---|---|
| `django` | Web framework |
| `fastapi` | Web framework |
| `flask` | Web framework |
| `psycopg2` | Database |
| `requests` | HTTP client |
| `urllib` | HTTP client |
| `urllib3` | HTTP client |
| `openai` | GenAI |
| `openai_agents` | GenAI |
| `langchain` | GenAI |
| `azure_sdk` | Azure (enabled when Azure Monitor is active) |

Individual instrumentations can be toggled via the `instrumentation_options` kwarg:

```python
use_microsoft_opentelemetry(
    instrumentation_options={
        "flask": {"enabled": False},      # disable Flask instrumentation
        "openai": {"enabled": True},      # explicitly enable (default)
    },
)
```





## Troubleshooting

Enable SDK-level logging to diagnose issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

The Azure Monitor exporter raises exceptions defined in [Azure Core](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/core/azure-core/README.md#azure-core-library-exceptions).

## Next Steps

- [Azure Monitor OpenTelemetry documentation](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable?tabs=python)
- [OpenTelemetry Python documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Samples](./samples/)

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

Read our [contributing guide](./CONTRIBUTING.md) to learn about our development process, how to propose bugfixes and improvements, and how to build and test your changes to this distribution.

## Data Collection

As this SDK is designed to enable applications to perform data collection which is sent to the Microsoft collection endpoints the following is required to identify our privacy statement.

The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.

## License

[MIT](LICENSE)
