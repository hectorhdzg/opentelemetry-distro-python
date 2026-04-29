---
description: "Use when migrating code from the standalone Agent365 Python SDK packages (microsoft-agents-a365-*) to the Microsoft OpenTelemetry Distro (microsoft-opentelemetry). Covers pip dependency changes, import path rewrites, configure() removal, exporter options, and environment variable mappings."
applyTo: "**/*.py"
---

# Agent365 Python SDK → Microsoft OpenTelemetry Distro Migration

Users are migrating from the standalone A365 observability PyPI packages under
`microsoft-agents-a365-observability-*` to a single distro package: `microsoft-opentelemetry`.

This migration covers the **observability** packages, along with the related **hosting** and **runtime** packages.
Other A365 packages, such as notifications and tooling, are not part of this distro.

The distro bundles:
- **`a365/core`** — Scope classes, span enrichment, A365 exporter, baggage middleware
- **`a365/hosting`** — Hosting middleware (baggage, output logging, invoke-agent scope helpers).
- **`a365/runtime`** — Standalone utilities (Power Platform API discovery, JWT token introspection, environment detection).

## Step 1 — Replace pip Dependencies

Remove the standalone A365 observability packages and install the distro:

```
# ❌ OLD — multiple observability packages
pip install microsoft-agents-a365-observability-core
pip install microsoft-agents-a365-observability-extensions-langchain
pip install microsoft-agents-a365-observability-extensions-openai
pip install microsoft-agents-a365-observability-extensions-semantickernel
pip install microsoft-agents-a365-observability-extensions-agentframework

# ✅ NEW — single package
pip install microsoft-opentelemetry
```

## Step 2 — Rewrite Import Paths

The old packages used `microsoft_agents_a365.*` namespace.
The new distro uses `microsoft.opentelemetry.*`.

### Core (observability-core)

| Old import path | New import path |
|-----------------|-----------------|
| `microsoft_agents_a365.observability.core` | `microsoft.opentelemetry.a365.core` |
| `from microsoft_agents_a365.observability.core import configure` | `from microsoft.opentelemetry import use_microsoft_opentelemetry` |
| `from microsoft_agents_a365.observability.core import is_configured` | Remove — not needed |
| `from microsoft_agents_a365.observability.core import get_tracer` | `from opentelemetry import trace; trace.get_tracer(...)` |
| `from microsoft_agents_a365.observability.core import get_tracer_provider` | `from opentelemetry import trace; trace.get_tracer_provider()` |
| `from microsoft_agents_a365.observability.core import Agent365ExporterOptions` | Use kwargs or env vars (see below) |
| `from microsoft_agents_a365.observability.core import SpectraExporterOptions` | Use OTLP env vars (see below) |
| `from microsoft_agents_a365.observability.core import SpanProcessor` | Remove — handled internally by distro |
| `from microsoft_agents_a365.observability.core import register_span_enricher` | Remove — handled internally |
| `from microsoft_agents_a365.observability.core import unregister_span_enricher` | Remove — handled internally |
| `from microsoft_agents_a365.observability.core import get_span_enricher` | Remove — handled internally |
| `from microsoft_agents_a365.observability.core import EnrichedReadableSpan` | Remove — handled internally |
| `from microsoft_agents_a365.observability.core import extract_context_from_headers` | Remove — use OTel propagation APIs |
| `from microsoft_agents_a365.observability.core import get_traceparent` | Remove — use OTel propagation APIs |

Scope classes, data models, and enums keep working — just change the package prefix:

```python
# ❌ OLD
from microsoft_agents_a365.observability.core import (
    AgentDetails,
    BaggageBuilder,
    CallerDetails,
    Channel,
    ChatMessage,
    ExecuteToolScope,
    InferenceCallDetails,
    InferenceOperationType,
    InferenceScope,
    InputMessages,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    MessageRole,
    OutputMessage,
    OutputMessages,
    OutputScope,
    Request,
    Response,
    ServiceEndpoint,
    SpanDetails,
    TextPart,
    ToolCallDetails,
    ToolType,
    UserDetails,
)

# ✅ NEW — same symbols, different package path
from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    BaggageBuilder,
    CallerDetails,
    Channel,
    ChatMessage,
    ExecuteToolScope,
    InferenceCallDetails,
    InferenceOperationType,
    InferenceScope,
    InputMessages,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    MessageRole,
    OutputMessage,
    OutputMessages,
    OutputScope,
    Request,
    Response,
    ServiceEndpoint,
    SpanDetails,
    TextPart,
    ToolCallDetails,
    ToolType,
    UserDetails,
)
```

### Hosting (microsoft-agents-a365-observability-hosting)

```python
# ❌ OLD
from microsoft_agents_a365.hosting import (
    BaggageMiddleware,
    OutputLoggingMiddleware,
    A365_PARENT_TRACEPARENT_KEY,
    ObservabilityHostingManager,
    ObservabilityHostingOptions,
)
from microsoft_agents_a365.hosting.middleware.baggage_middleware import BaggageMiddleware
from microsoft_agents_a365.hosting.scope_helpers.populate_baggage import populate_baggage
from microsoft_agents_a365.hosting.scope_helpers.populate_invoke_agent_scope import populate_invoke_agent_scope

# ✅ NEW — same symbols, different package path
from microsoft.opentelemetry.a365.hosting import (
    BaggageMiddleware,
    OutputLoggingMiddleware,
    A365_PARENT_TRACEPARENT_KEY,
    ObservabilityHostingManager,
    ObservabilityHostingOptions,
)
from microsoft.opentelemetry.a365.hosting.scope_helpers.populate_baggage import populate_baggage
from microsoft.opentelemetry.a365.hosting.scope_helpers.populate_invoke_agent_scope import populate_invoke_agent_scope
```

### Runtime (microsoft-agents-a365-runtime)

```python
# ❌ OLD
from microsoft_agents_a365.runtime import (
    get_observability_authentication_scope,
    PowerPlatformApiDiscovery,
    ClusterCategory,
    Utility,
    OperationError,
    OperationResult,
)

# ✅ NEW — same symbols, different package path
from microsoft.opentelemetry.a365.runtime import (
    get_observability_authentication_scope,
    PowerPlatformApiDiscovery,
    ClusterCategory,
    Utility,
    OperationError,
    OperationResult,
)
```

### Extensions — LangChain (observability-extensions-langchain)

```python
# ❌ OLD — manual instrumentor setup
from microsoft_agents_a365.observability.extensions.langchain import CustomLangChainInstrumentor

CustomLangChainInstrumentor().instrument()

# ✅ NEW — auto-instrumented by distro, no manual setup needed
# Set ENABLE_A365_OBSERVABILITY_EXPORTER=true in env
use_microsoft_opentelemetry(enable_a365=True)
# LangChain is auto-instrumented if installed
```

### Extensions — OpenAI (observability-extensions-openai)

```python
# ❌ OLD — manual instrumentor setup
from microsoft_agents_a365.observability.extensions.openai import OpenAIAgentsTraceInstrumentor

OpenAIAgentsTraceInstrumentor().instrument()

# ✅ NEW — auto-instrumented by distro, no manual setup needed
# Set ENABLE_A365_OBSERVABILITY_EXPORTER=true in env
use_microsoft_opentelemetry(enable_a365=True)
# OpenAI instrumentation is handled automatically
```

### Extensions — Semantic Kernel (observability-extensions-semantickernel)

```python
# ❌ OLD
from microsoft_agents_a365.observability.extensions.semantickernel import ...

# ✅ NEW — auto-instrumented by distro
# Set ENABLE_A365_OBSERVABILITY_EXPORTER=true in env
use_microsoft_opentelemetry(enable_a365=True)
```

### Extensions — Agent Framework (observability-extensions-agentframework)

```python
# ❌ OLD — manual instrumentor setup
from microsoft_agents_a365.observability.extensions.agentframework import AgentFrameworkTraceInstrumentor

AgentFrameworkTraceInstrumentor().instrument()

# ✅ NEW — auto-instrumented by distro, no manual setup needed
# Set ENABLE_A365_OBSERVABILITY_EXPORTER=true in env
use_microsoft_opentelemetry(enable_a365=True)
# Agent Framework is auto-instrumented if the agent-framework package is installed
```

## Step 3 — Replace configure() with Distro Entry Point

```python
# ❌ OLD — standalone SDK
from microsoft_agents_a365.observability.core import configure, Agent365ExporterOptions

configure(
    service_name="my-agent",
    service_namespace="my-namespace",
    exporter_options=Agent365ExporterOptions(
        cluster_category="prod",
        token_resolver=my_token_resolver,
        use_s2s_endpoint=True,
    ),
    suppress_invoke_agent_input=True,
)

# ✅ NEW — distro entry point with kwargs.
# Set ENABLE_A365_OBSERVABILITY_EXPORTER=true in env.
# `service.name` and `service.namespace` are set via an OTel Resource
# (the old `service_name` / `service_namespace` configure() args).
from opentelemetry.sdk.resources import Resource

from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    resource=Resource.create({
        "service.name": "my-agent",
        "service.namespace": "my-namespace",
    }),
    a365_token_resolver=my_token_resolver,
    a365_cluster_category="prod",
    a365_use_s2s_endpoint=True,
    a365_suppress_invoke_agent_input=True,
    a365_enable_observability_exporter=True,
    a365_observability_scope_override="api://<app-id>/.default",
    a365_max_queue_size=4096,
    a365_scheduled_delay_ms=2000,
    a365_exporter_timeout_ms=15000,
    a365_max_export_batch_size=256,
)
```

> **Note.** ``service.name`` and ``service.namespace`` can also be set via the
> ``OTEL_SERVICE_NAME`` and ``OTEL_RESOURCE_ATTRIBUTES`` environment variables
> (e.g. ``OTEL_RESOURCE_ATTRIBUTES="service.namespace=my-namespace"``). Use
> a ``Resource`` when you want to express them in code.

### configure() Parameter Mapping

| Old `configure()` parameter | New equivalent |
|-----------------------------|----------------|
| `service_name` | `OTEL_SERVICE_NAME` env var or `resource` kwarg |
| `service_namespace` | `resource` kwarg with `service.namespace` attribute |
| `token_resolver` | `a365_token_resolver` kwarg |
| `cluster_category` | `a365_cluster_category` kwarg or `A365_CLUSTER_CATEGORY` env var |
| `exporter_options` | Individual kwargs or env vars (see below) |
| `suppress_invoke_agent_input` | `a365_suppress_invoke_agent_input` kwarg or `A365_SUPPRESS_INVOKE_AGENT_INPUT` env var |
| `exporter_options.max_queue_size` | `a365_max_queue_size` kwarg |
| `exporter_options.scheduled_delay_ms` | `a365_scheduled_delay_ms` kwarg |
| `exporter_options.exporter_timeout_ms` | `a365_exporter_timeout_ms` kwarg |
| `exporter_options.max_export_batch_size` | `a365_max_export_batch_size` kwarg |
| _(env var only previously)_ `ENABLE_A365_OBSERVABILITY_EXPORTER` | `a365_enable_observability_exporter` kwarg or `ENABLE_A365_OBSERVABILITY_EXPORTER` env var |
| _(env var only previously)_ `A365_OBSERVABILITY_SCOPE_OVERRIDE` | `a365_observability_scope_override` kwarg or `A365_OBSERVABILITY_SCOPE_OVERRIDE` env var |

### Spectra Sidecar → OTLP

```python
# ❌ OLD — Spectra sidecar exporter
SpectraExporterOptions(protocol="grpc", endpoint="http://localhost:4317")

# ✅ NEW — use standard OTLP env vars
# OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
use_microsoft_opentelemetry()
```

## Step 4 — Replace get_tracer()

```python
# ❌ OLD
from microsoft_agents_a365.observability.core import get_tracer
tracer = get_tracer("my-module")

# ✅ NEW — standard OTel API
from opentelemetry import trace
tracer = trace.get_tracer("my-module")
```

## Default Instrumentations With A365 exporter enabled

The distro auto-discovers and activates supported OTel instrumentations.
When `enable_a365=True`, the distro **disables web-framework /
HTTP-client instrumentations by default**. GenAI instrumentations stay enabled.

> **Note:** When both `enable_a365=True` and `enable_azure_monitor=True` are
> set, the original (non-A365) defaults are used and the libraries below
> remain **enabled** so Azure Monitor continues to receive web/HTTP
> telemetry.

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

To re-enable any of these, pass `instrumentation_options`:

```python
use_microsoft_opentelemetry(
    enable_a365=True,
    instrumentation_options={
        "fastapi": {"enabled": True},
    },
)
```

When `enable_a365=False` (the default), all supported instrumentations
remain enabled by default.

## Custom SpanProcessors — Filtering Console Output

By default, when `enable_console=True` (or any additional exporter is
configured), **all** spans are exported — including framework-level spans
(`agents.app.*`, `agents.turn.*`, `agents.connector.*`,
`agents.authentication.*`). This can make local development noisy when you
only care about the 4 A365 observability scopes:

- `invoke_agent`
- `Chat` (InferenceScope)
- `execute_tool` (ExecuteToolScope)
- `output_messages` (OutputScope)

To filter output to only A365 scopes, pass a custom `SpanProcessor` via the
`span_processors` parameter:

```python
from opentelemetry.trace import SpanContext, TraceFlags
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan

from microsoft.opentelemetry import use_microsoft_opentelemetry


class A365OnlySpanProcessor(SpanProcessor):
    """Filter console/exporter output to only A365 observability scopes."""

    A365_OPS = {"invoke_agent", "chat", "execute_tool", "output_messages"}

    def on_start(self, span, parent_context=None):
        """Mark non-A365 spans as unsampled at start time."""
        op = span.attributes.get("gen_ai.operation.name")

        if op not in self.A365_OPS:
            # Create new SpanContext with trace_flags = 0 (UNSAMPLED)
            span._context = SpanContext(
                span.context.trace_id,
                span.context.span_id,
                span.context.is_remote,
                TraceFlags(0),  # UNSAMPLED
                span.context.trace_state,
            )

    def on_end(self, span: ReadableSpan):
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def shutdown(self):
        pass


use_microsoft_opentelemetry(
    enable_a365=True,
    enable_console=True,
    a365_token_resolver=my_token_resolver,
    span_processors=[A365OnlySpanProcessor()],
)
```

This leverages standard OpenTelemetry `SpanProcessor` APIs — you can adapt
the filter logic to any criteria (span name, attributes, etc.).

## Environment Variable Mapping

| Old env var | New env var | Notes |
|-------------|-------------|-------|
| `ENABLE_A365_OBSERVABILITY_EXPORTER` | `ENABLE_A365_OBSERVABILITY_EXPORTER` | Same — enables A365 HTTP exporter. Set to `false` with `enable_a365=True` to get enriched span attributes without exporting to A365. |
| `A365_CLUSTER_CATEGORY` | `A365_CLUSTER_CATEGORY` | Same — or use `a365_cluster_category` kwarg |
| `A365_USE_S2S_ENDPOINT` | `A365_USE_S2S_ENDPOINT` | Same — or use `a365_use_s2s_endpoint` kwarg |
| `A365_SUPPRESS_INVOKE_AGENT_INPUT` | `A365_SUPPRESS_INVOKE_AGENT_INPUT` | Same — or use `a365_suppress_invoke_agent_input` kwarg |
| `ENABLE_OTLP_EXPORTER` | `OTEL_EXPORTER_OTLP_ENDPOINT` | Use standard OTel env var instead |
| `ENABLE_OBSERVABILITY` | `ENABLE_OBSERVABILITY` | Same — master switch for A365 scope classes to emit spans |

## Full Migration Example

```python
# ❌ OLD — using standalone Agent365 SDK packages
from microsoft_agents_a365.observability.core import (
    configure,
    Agent365ExporterOptions,
    AgentDetails,
    BaggageBuilder,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    Request,
    get_tracer,
)
from microsoft_agents_a365.observability.extensions.langchain import CustomLangChainInstrumentor

configure(
    service_name="my-agent",
    service_namespace="my-ns",
    exporter_options=Agent365ExporterOptions(
        cluster_category="prod",
        token_resolver=my_resolver,
    ),
)

CustomLangChainInstrumentor().instrument()
tracer = get_tracer("my-module")

# ✅ NEW — using microsoft-opentelemetry distro
from opentelemetry.sdk.resources import Resource

from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    BaggageBuilder,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    Request,
)

use_microsoft_opentelemetry(
    enable_a365=True,
    resource=Resource.create({
        "service.name": "my-agent",
        "service.namespace": "my-ns",
    }),
    a365_token_resolver=my_resolver,
)
# LangChain auto-instrumented — no manual setup needed

# Scope classes work exactly the same after initialization
agent = AgentDetails(agent_id="my-agent", tenant_id="my-tenant")
with BaggageBuilder().tenant_id(agent.tenant_id).agent_id(agent.agent_id).build():
    with InvokeAgentScope.start(
        request=Request(content="hello"),
        scope_details=InvokeAgentScopeDetails(),
        agent_details=agent,
    ) as scope:
        scope.record_response("world")
```
