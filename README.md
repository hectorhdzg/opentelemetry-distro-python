# microsoft-opentelemetry

[![PyPI version](https://img.shields.io/pypi/v/microsoft-opentelemetry)](https://pypi.org/project/microsoft-opentelemetry/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python versions](https://img.shields.io/pypi/pyversions/microsoft-opentelemetry)](https://pypi.org/project/microsoft-opentelemetry/)

Python package for a Microsoft OpenTelemetry distribution that provides a single onboarding experience for observability across Azure Monitor, OTLP-compatible backends, and Microsoft Agent 365 integrations.

## Getting Started

### Prerequisites

- Python 3.10 or later — [Install Python](https://www.python.org/downloads/)
- Azure subscription (optional, for Azure Monitor) — [Create a free account](https://azure.microsoft.com/free/)
- Application Insights resource (optional) — [How to use Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview)

### Install the Package

```bash
pip install microsoft-opentelemetry
```

### Quick Start

Use `use_microsoft_opentelemetry` to set up instrumentation for your application. All passed-in parameters take priority over any related environment variables.

**Azure Monitor:**

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_azure_monitor=True,
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
)
```

The connection string can also be set via `APPLICATIONINSIGHTS_CONNECTION_STRING` env var. For Entra-based auth:

```python
from azure.identity import DefaultAzureCredential

use_microsoft_opentelemetry(
    enable_azure_monitor=True,
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
    azure_monitor_exporter_credential=DefaultAzureCredential(),
)
```

**Agent 365:**

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    a365_token_resolver=my_token_resolver,
)
```

**Both + OTLP:**

```python
# Set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 for OTLP
use_microsoft_opentelemetry(
    enable_azure_monitor=True,
    enable_a365=True,
    a365_token_resolver=my_token_resolver,
)
```

See the [A365 guide](A365_DOCUMENTATION.md) for A365-specific configuration.

---

## Configuration Reference

### All Options

| Keyword argument | Type | Default | Description |
|---|---|---|---|
| **General** | | | |
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
| `enable_console` | `bool` | `False` | Console exporter (dev only). Auto-enables when no other exporter is active. |
| **Azure Monitor** | | | |
| `enable_azure_monitor` | `bool` | `False` | Enable Azure Monitor export. |
| `azure_monitor_connection_string` | `str` | `None` | Connection string. Also read from `APPLICATIONINSIGHTS_CONNECTION_STRING`. |
| `azure_monitor_exporter_credential` | `TokenCredential` | `None` | Azure AD token credential. |
| `azure_monitor_enable_live_metrics` | `bool` | `True` | Enable live metrics. |
| `azure_monitor_enable_performance_counters` | `bool` | `True` | Enable performance counters. |
| `azure_monitor_exporter_disable_offline_storage` | `bool` | `False` | Disable offline retry storage. |
| `azure_monitor_exporter_storage_directory` | `str` | `None` | Custom offline storage directory. |
| `azure_monitor_browser_sdk_loader_config` | `dict` | `None` | Browser SDK loader configuration. |
| **Agent 365** | | | |
| `enable_a365` | `bool` | `False` | Enable A365 telemetry export. |
| `a365_token_resolver` | `Callable` | `None` | `(agent_id, tenant_id) -> token` callable. If omitted, defaults to FIC/DefaultAzureCredential. |
| `a365_cluster_category` | `str` | `"prod"` | Cluster category (`prod`, `gov`, `dod`, `mooncake`). |
| `a365_use_s2s_endpoint` | `bool` | `False` | Use the S2S endpoint. |
| `a365_suppress_invoke_agent_input` | `bool` | `False` | Strip input messages from InvokeAgent spans. |
| `a365_enable_observability_exporter` | `bool` | `None` | Enable the A365 HTTP exporter. Also read from `ENABLE_A365_OBSERVABILITY_EXPORTER` env var. Defaults to `false` when neither is set. |
| `a365_observability_scope_override` | `str` | `None` | Override the default Entra scope used by the built-in token resolvers. Also read from `A365_OBSERVABILITY_SCOPE_OVERRIDE`. |
| `a365_max_queue_size` | `int` | `2048` | Maximum queue size for the A365 batch span processor. |
| `a365_scheduled_delay_ms` | `int` | `5000` | Delay between A365 export batches (ms). |
| `a365_exporter_timeout_ms` | `int` | `30000` | Timeout for a single A365 export operation (ms). |
| `a365_max_export_batch_size` | `int` | `512` | Maximum batch size for a single A365 export operation. |

> For A365 token resolver patterns, baggage, and scope classes, see the [A365 guide](A365_DOCUMENTATION.md).

### Sampling

Configured via standard OpenTelemetry environment variables:

| Environment variable | Description |
|---|---|
| `OTEL_TRACES_SAMPLER` | Sampler type (see values below). |
| `OTEL_TRACES_SAMPLER_ARG` | Sampler argument (e.g. ratio or traces per second). |

**Supported sampler values:**

| Value | Description |
|---|---|
| `always_on` | Sample every trace. |
| `always_off` | Drop every trace. |
| `trace_id_ratio` | Fixed percentage by trace ID. Set ratio with `OTEL_TRACES_SAMPLER_ARG` (0–1). |
| `parentbased_always_on` | Parent-based, defaults to always on. |
| `parentbased_always_off` | Parent-based, defaults to always off. |
| `parentbased_trace_id_ratio` | Parent-based with trace ID ratio fallback. |
| `microsoft.fixed_percentage` | Azure Monitor fixed-percentage sampler (0–1). |
| `microsoft.rate_limited` | Azure Monitor rate-limited sampler (traces/sec, default 5). |

```bash
export OTEL_TRACES_SAMPLER=trace_id_ratio
export OTEL_TRACES_SAMPLER_ARG=0.1
```

### A365 Exporter Environment Variables

When `enable_a365=True`, the distro adds A365 span processors to the tracing pipeline. A365 exporter behavior is configured via environment variables:

| Environment variable | Default | Description |
|---|---|---|
| `ENABLE_A365_OBSERVABILITY_EXPORTER` | `false` | Enable the A365 HTTP exporter. Equivalent to the `a365_enable_observability_exporter` kwarg — either source being truthy (along with `enable_a365=True`) enables export to the A365 endpoint. When neither is set, the A365 span processors still register and propagate baggage attributes (e.g. `gen_ai.agent.id`, `microsoft.tenant.id`, `user.name`) to spans for any other configured exporter (Azure Monitor, OTLP, console), but no data is sent to A365. |
| `A365_CLUSTER_CATEGORY` | `prod` | Cluster category for endpoint discovery (`prod`, `gov`, `dod`, `mooncake`). |
| `A365_USE_S2S_ENDPOINT` | `false` | Use the S2S endpoint instead of the standard endpoint. |
| `A365_SUPPRESS_INVOKE_AGENT_INPUT` | `false` | Strip input messages from InvokeAgent spans before export. |
| `A365_OBSERVABILITY_SCOPE_OVERRIDE` | _(unset)_ | Override the default Entra scope used by the built-in FIC / DefaultAzureCredential token resolvers. |
| `ENABLE_OBSERVABILITY` | `false` | Master switch for A365 scope telemetry. Must be `true` for scope classes to emit spans. |

**Example:**

```bash
export ENABLE_OBSERVABILITY=true
export ENABLE_A365_OBSERVABILITY_EXPORTER=true
```

### OTLP Export

Automatically enabled when any `OTEL_EXPORTER_OTLP_*` endpoint variable is set:

| Environment variable | Description |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Base endpoint URL (e.g. `http://localhost:4318`). |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | Per-signal override for traces. |
| `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | Per-signal override for metrics. |
| `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` | Per-signal override for logs. |
| `OTEL_EXPORTER_OTLP_HEADERS` | Comma-separated `key=value` headers. |
| `OTEL_EXPORTER_OTLP_TIMEOUT` | Max time in milliseconds per request. |
| `OTEL_EXPORTER_OTLP_COMPRESSION` | `gzip` or `none`. |

Per-signal overrides follow the pattern `OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_{ENDPOINT,HEADERS,TIMEOUT,COMPRESSION}`.

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
python my_app.py
```

### Console Exporter (Development)

Writes traces, metrics, and logs to stdout. Auto-enables when no other exporter is active. Can also be enabled explicitly alongside other exporters:

```python
use_microsoft_opentelemetry(enable_console=True)
```

---

## Auto-Instrumented Libraries

Microsoft OpenTelemetry automatically instruments the following libraries when installed:

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
| `semantic_kernel` | GenAI |
| `agent_framework` | GenAI |
| `azure_sdk` | Azure (enabled when Azure Monitor is active) |

Toggle individual instrumentations:

```python
use_microsoft_opentelemetry(
    instrumentation_options={
        "flask": {"enabled": False},
        "openai": {"enabled": True},
    },
)
```

### Default Instrumentations When `enable_a365=True`

The distro **automatically disables the
following instrumentations by default** when `enable_a365=True`:

| Library | Default with A365 |
|---|---|
| `django` | disabled |
| `fastapi` | disabled |
| `flask` | disabled |
| `psycopg2` | disabled |
| `requests` | disabled |
| `urllib` | disabled |
| `urllib3` | disabled |
| `azure_sdk` | disabled |
| `openai` | enabled |
| `openai_agents` | enabled |
| `langchain` | enabled |
| `semantic_kernel` | enabled |
| `agent_framework` | enabled |

> **Note:** When both `enable_a365=True` and `enable_azure_monitor=True` are
> set, the original (non-A365) defaults are used and the disabled libraries
> above remain **enabled** so Azure Monitor continues to receive web/HTTP
> telemetry.

You can re-enable any of these explicitly via `instrumentation_options`:

```python
use_microsoft_opentelemetry(
    enable_a365=True,
    instrumentation_options={
        "fastapi": {"enabled": True},     # opt back in to FastAPI
    },
)
```

When `enable_a365=False` (the default), all supported instrumentations
remain enabled by default.

---

## Samples

| Sample | Scenario | Description |
|---|---|---|
| [samples/a365/exporter.py](samples/a365/exporter.py) | A365 | LangChain with A365 auto-instrumentation |
| [samples/a365/manual_telemetry.py](samples/a365/manual_telemetry.py) | A365 | Manual instrumentation using all scope classes |
| [samples/distro/tracing.py](samples/distro/tracing.py) | Azure Monitor | Basic tracing |
| [samples/distro/metrics.py](samples/distro/metrics.py) | Azure Monitor | Metrics collection |
| [samples/distro/logging_sample.py](samples/distro/logging_sample.py) | Azure Monitor | Log export |
| [samples/distro/custom_events.py](samples/distro/custom_events.py) | Azure Monitor | Custom event logging |
| [samples/distro/fastapi_app.py](samples/distro/fastapi_app.py) | Azure Monitor | FastAPI web app |
| [samples/openai/](samples/openai/) | GenAI | OpenAI chat + Agents SDK |
| [samples/langchain/](samples/langchain/) | GenAI | LangChain auto-instrumentation |
| [samples/otlp/](samples/otlp/) | OTLP | Export to a local collector |




## Troubleshooting

Enable SDK-level logging to diagnose issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

For A365-specific issues, see the [A365 guide](A365_DOCUMENTATION.md) and the [official troubleshooting docs](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/troubleshooting).


## Next Steps

- [Agent 365 Observability guide](A365_DOCUMENTATION.md)
- [Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/overview)
- [Microsoft OpenTelemetry SDK docs](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/microsoft-opentelemetry?tabs=python)
- [OpenTelemetry Python docs](https://opentelemetry.io/docs/instrumentation/python/)
- [Samples](./samples/)

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

Read our [contributing guide](./CONTRIBUTING.md) to learn about our development process, how to propose bugfixes and improvements, and how to build and test your changes to this distribution.

This project has adopted the
[Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more
information see the
[Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
or contact [opencode@microsoft.com](mailto:opencode@microsoft.com)
with any additional questions or comments.

## Data Collection

As this SDK is designed to enable applications to perform data collection which is sent to the Microsoft collection endpoints the following is required to identify our privacy statement.

The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.

### Internal Telemetry

SDK self-telemetry (Statsbeat) can be disabled by setting the environment variable `APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL` to `true`.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft’s Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos are subject to those third-party’s policies.

## Reporting Security Issues

See [SECURITY.md](./SECURITY.md) for information on reporting vulnerabilities.

## License

[MIT](LICENSE)
