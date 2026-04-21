---
description: "Use when migrating code from the standalone Agent365 Python SDK packages (microsoft-agents-a365-*) to the Microsoft OpenTelemetry Distro (microsoft-opentelemetry). Covers pip dependency changes, import path rewrites, configure() removal, exporter options, and environment variable mappings."
applyTo: "**/*.py"
---

# Agent365 Python SDK → Microsoft OpenTelemetry Distro Migration

Users are migrating from the standalone A365 observability PyPI packages under
`microsoft-agents-a365-observability-*` to a single distro package: `microsoft-opentelemetry`.

This migration covers only the **observability** packages. Other A365 packages
(hosting, runtime, notifications, tooling) are not part of this distro.

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

# ✅ NEW — distro entry point with kwargs
# Set ENABLE_A365_OBSERVABILITY_EXPORTER=true in env
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    a365_token_resolver=my_token_resolver,
    a365_tenant_id="my-tenant",
    a365_agent_id="my-agent",
    a365_cluster_category="prod",
    a365_use_s2s_endpoint=True,
    a365_suppress_invoke_agent_input=True,
)
```

### configure() Parameter Mapping

| Old `configure()` parameter | New equivalent |
|-----------------------------|----------------|
| `service_name` | `OTEL_SERVICE_NAME` env var or `resource` kwarg |
| `service_namespace` | `resource` kwarg with `SERVICE_NAMESPACE` attribute |
| `token_resolver` | `a365_token_resolver` kwarg |
| `cluster_category` | `a365_cluster_category` kwarg or `A365_CLUSTER_CATEGORY` env var |
| `exporter_options` | Individual kwargs or env vars (see below) |
| `suppress_invoke_agent_input` | `a365_suppress_invoke_agent_input` kwarg or `A365_SUPPRESS_INVOKE_AGENT_INPUT` env var |

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

## Environment Variable Mapping

| Old env var | New env var | Notes |
|-------------|-------------|-------|
| `ENABLE_A365_OBSERVABILITY_EXPORTER` | `ENABLE_A365_OBSERVABILITY_EXPORTER` | Same — enables A365 HTTP exporter |
| `A365_TENANT_ID` | `A365_TENANT_ID` | Same — or use `a365_tenant_id` kwarg |
| `A365_AGENT_ID` | `A365_AGENT_ID` | Same — or use `a365_agent_id` kwarg |
| `A365_CLUSTER_CATEGORY` | `A365_CLUSTER_CATEGORY` | Same — or use `a365_cluster_category` kwarg |
| `A365_USE_S2S_ENDPOINT` | `A365_USE_S2S_ENDPOINT` | Same — or use `a365_use_s2s_endpoint` kwarg |
| `A365_SUPPRESS_INVOKE_AGENT_INPUT` | `A365_SUPPRESS_INVOKE_AGENT_INPUT` | Same — or use `a365_suppress_invoke_agent_input` kwarg |
| `ENABLE_OTLP_EXPORTER` | `OTEL_EXPORTER_OTLP_ENDPOINT` | Use standard OTel env var instead |

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
    a365_token_resolver=my_resolver,
    a365_tenant_id="my-tenant",
    a365_agent_id="my-agent",
    a365_cluster_category="prod",
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
