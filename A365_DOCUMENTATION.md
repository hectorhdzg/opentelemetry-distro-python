# Agent 365 Observability

> **Official docs:** [Microsoft OpenTelemetry on Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/microsoft-opentelemetry?tabs=python)

This guide covers A365-specific setup, configuration, and concepts for the `microsoft-opentelemetry` distro.
For general distro options (Azure Monitor, OTLP, sampling), see the [main README](README.md).
For migrating from standalone A365 packages, see [MIGRATION_A365.md](MIGRATION_A365.md).

## Installation

```bash
pip install microsoft-opentelemetry
```

If you are migrating from the standalone `microsoft-agents-a365-observability-*` packages, see [MIGRATION_A365.md](MIGRATION_A365.md) for step-by-step instructions.

## Configuration

Call `use_microsoft_opentelemetry()` once at startup to initialize the distro. All keyword arguments are optional; any passed-in value takes priority over the corresponding environment variable.

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    a365_token_resolver=my_token_resolver,
)
```

### A365 Keyword Arguments

| Keyword argument | Type | Default | Env var | Description |
|---|---|---|---|---|
| `enable_a365` | `bool` | `False` | — | Enable A365 span enrichment and exporter setup. |
| `a365_token_resolver` | `Callable` | `None` | — | `(agent_id, tenant_id) -> token` sync callable. If omitted, defaults to FIC / `DefaultAzureCredential`. |
| `a365_cluster_category` | `str` | `"prod"` | `A365_CLUSTER_CATEGORY` | Cluster category (`prod`, `gov`, `dod`, `mooncake`). |
| `a365_use_s2s_endpoint` | `bool` | `False` | `A365_USE_S2S_ENDPOINT` | Use the S2S endpoint. |
| `a365_suppress_invoke_agent_input` | `bool` | `False` | `A365_SUPPRESS_INVOKE_AGENT_INPUT` | Strip input messages from InvokeAgent spans. |
| `a365_enable_observability_exporter` | `bool` | `False` | `ENABLE_A365_OBSERVABILITY_EXPORTER` | Enable the A365 HTTP exporter. When `false`, spans are enriched but not exported to A365. |
| `a365_observability_scope_override` | `str` | `None` | `A365_OBSERVABILITY_SCOPE_OVERRIDE` | Override the authentication scope for the A365 observability service. |
| `a365_max_queue_size` | `int` | `2048` | — | Maximum queue size for the A365 batch span processor. |
| `a365_scheduled_delay_ms` | `int` | `5000` | — | Delay between A365 export batches in milliseconds. |
| `a365_exporter_timeout_ms` | `int` | `30000` | — | Timeout for a single A365 export operation in milliseconds. |
| `a365_max_export_batch_size` | `int` | `512` | — | Maximum batch size for a single A365 export operation. |

### Resource / Service Name

Set `service.name` and `service.namespace` via a `Resource` or environment variables:

```python
from opentelemetry.sdk.resources import Resource
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    resource=Resource.create({
        "service.name": "my-agent",
        "service.namespace": "my-namespace",
    }),
    a365_token_resolver=my_token_resolver,
)
```

Or using environment variables:

```bash
export OTEL_SERVICE_NAME=my-agent
export OTEL_RESOURCE_ATTRIBUTES="service.namespace=my-namespace"
```

### Exporter Batch Options

The A365 exporter batch processor defaults can be overridden via the `a365_*` kwargs listed in the table above.

```python
use_microsoft_opentelemetry(
    enable_a365=True,
    a365_token_resolver=my_token_resolver,
    a365_max_queue_size=4096,
    a365_scheduled_delay_ms=2000,
    a365_exporter_timeout_ms=15000,
    a365_max_export_batch_size=256,
)
```

## Auto-Instrumented Libraries

The distro auto-discovers and activates supported instrumentors via OpenTelemetry entry points. No manual `instrument()` calls are needed.

Supported instrumentors:

| Library | Instrumentor | Package |
|---|---|---|
| Semantic Kernel | `SemanticKernelInstrumentor` | Bundled in distro |
| OpenAI Agents SDK | Via `opentelemetry-instrumentation-openai-agents-v2` | Dependency of distro |
| Agent Framework | `AgentFrameworkInstrumentor` | Bundled in distro |
| LangChain | `LangChainInstrumentor` | Bundled in distro |

### Noisy Spans — A365-Only Mode

When `enable_a365=True` (and `enable_azure_monitor` is **not** set), the distro **disables web-framework and HTTP-client instrumentations by default** so only GenAI-related spans appear:

| Library | Default with A365 only |
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

> **Note:** When both `enable_a365=True` and `enable_azure_monitor=True` are set, all instrumentations remain **enabled** so Azure Monitor continues to receive web/HTTP telemetry.

To re-enable a disabled instrumentation:

```python
use_microsoft_opentelemetry(
    enable_a365=True,
    instrumentation_options={
        "fastapi": {"enabled": True},
    },
)
```

To disable a specific instrumentation:

```python
use_microsoft_opentelemetry(
    enable_a365=True,
    instrumentation_options={
        "langchain": {"enabled": False},
    },
)
```

## Hosting Middleware

If your agent uses the Agent Hosting framework, use `ObservabilityHostingManager` to register middleware automatically.

> **Important:** Both `enable_baggage` and `enable_output_logging` default to `False`. You must explicitly enable them or baggage won't propagate and `output_messages` spans won't be emitted.

```python
from microsoft.opentelemetry.a365.hosting import (
    ObservabilityHostingManager,
    ObservabilityHostingOptions,
)

ObservabilityHostingManager.configure(
    adapter.middleware_set,
    ObservabilityHostingOptions(
        enable_baggage=True,         # Required for baggage propagation
        enable_output_logging=True,  # Required for output_messages spans
    ),
)
```

| Option | Default | Description |
|---|---|---|
| `enable_baggage` | `False` | Enable baggage middleware that extracts tenant, agent, user, channel from `TurnContext`. |
| `enable_output_logging` | `False` | Enable output logging middleware that records `output_messages` spans. |

## Baggage

Baggage sets per-request context (tenant, agent, user) that flows to all spans. **Without `tenant_id` and `agent_id`, the exporter silently drops spans.**

### BaggageBuilder

```python
from microsoft.opentelemetry.a365.core import BaggageBuilder, InvokeAgentScope

with (
    BaggageBuilder()
    .tenant_id("contoso-tenant")
    .agent_id("weather-agent-001")
    .user_id("user-42")
    .user_email("alice@contoso.com")
    .channel_name("msteams")
    .session_id("session-abc")
    .conversation_id("conv-789")
    .build()
):
    # All spans created here inherit these attributes
    with InvokeAgentScope.start(...) as scope:
        ...
```

### From TurnContext (Hosting Framework)

```python
from microsoft.opentelemetry.a365.core import BaggageBuilder
from microsoft.opentelemetry.a365.hosting.scope_helpers.populate_baggage import populate

async def on_message(context: TurnContext, _state: TurnState):
    builder = BaggageBuilder()
    populate(builder, context)  # Extracts tenant, agent, user, channel from activity

    with builder.build():
        ...
```

### Baggage Middleware (Automatic)

```python
from microsoft.opentelemetry.a365.hosting import (
    ObservabilityHostingManager,
    ObservabilityHostingOptions,
)

ObservabilityHostingManager.configure(
    adapter.middleware_set,
    ObservabilityHostingOptions(enable_baggage=True),
)
```

## Token Resolver

The exporter authenticates with a Bearer token. Provide a sync callable `(agent_id, tenant_id) -> str | None`.

### Manual

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.runtime import get_observability_authentication_scope

_cached_token: str | None = None

def my_token_resolver(agent_id: str, tenant_id: str) -> str | None:
    return _cached_token

use_microsoft_opentelemetry(enable_a365=True, a365_token_resolver=my_token_resolver)

@AGENT_APP.activity("message", auth_handlers=["AGENTIC"])
async def on_message(context: TurnContext, _state: TurnState):
    global _cached_token
    _cached_token = await AGENT_APP.auth.exchange_token(
        context,
        scopes=get_observability_authentication_scope(),
        auth_handler_id="AGENTIC",
    )
```

### Agentic Token Cache (Agent Framework Apps)

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.hosting.token_cache_helpers import AgenticTokenCache, AgenticTokenStruct
from microsoft.opentelemetry.a365.runtime import get_observability_authentication_scope

token_cache = AgenticTokenCache()

_cached_tokens: dict[tuple[str, str], str | None] = {}

# Keep the sync resolver side-effect free; refresh the cache in the async request handler.
def sync_token_resolver(agent_id: str, tenant_id: str) -> str | None:
    return _cached_tokens.get((agent_id, tenant_id))

use_microsoft_opentelemetry(enable_a365=True, a365_token_resolver=sync_token_resolver)

@AGENT_APP.activity("message", auth_handlers=["AGENTIC"])
async def on_message(context: TurnContext, _state: TurnState):
    agent_id = context.activity.recipient.id
    tenant_id = context.activity.recipient.tenant_id
    token_cache.register_observability(
        agent_id=agent_id,
        tenant_id=tenant_id,
        token_generator=AgenticTokenStruct(authorization=AGENT_APP.auth, turn_context=context),
        observability_scopes=get_observability_authentication_scope(),
    )
    _cached_tokens[(agent_id, tenant_id)] = await token_cache.get_observability_token(
        agent_id,
        tenant_id,
    )
```

### FIC / DefaultAzureCredential (Automatic)

When no `a365_token_resolver` is provided, Microsoft OpenTelemetry tries FIC using `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__*` env vars, then falls back to `DefaultAzureCredential`.

## Manual Instrumentation

Use scope classes when auto-instrumentation isn't available or you need fine-grained control.

### InvokeAgentScope

Top-level agent invocation — wraps the entire request/response cycle:

```python
from microsoft.opentelemetry.a365.core import (
    AgentDetails, CallerDetails, Channel, InvokeAgentScope,
    InvokeAgentScopeDetails, Request, ServiceEndpoint, UserDetails,
)

agent = AgentDetails(agent_id="agent-001", agent_name="My Agent", tenant_id="t1")

with InvokeAgentScope.start(
    request=Request(content="Hello", session_id="s1", conversation_id="c1", channel=Channel(name="msteams")),
    scope_details=InvokeAgentScopeDetails(endpoint=ServiceEndpoint(hostname="agent.contoso.com")),
    agent_details=agent,
    caller_details=CallerDetails(user_details=UserDetails(user_id="u1", user_email="u@contoso.com")),
) as scope:
    # ... do work ...
    scope.record_response("Here is the answer.")
```

### ExecuteToolScope

```python
from microsoft.opentelemetry.a365.core import ExecuteToolScope, ToolCallDetails, Request

with ExecuteToolScope.start(
    request=Request(content="What's the weather?"),
    details=ToolCallDetails(tool_name="get_weather", tool_call_id="call_1", arguments={"city": "Seattle"}),
    agent_details=agent,
) as scope:
    result = get_weather("Seattle")
    scope.record_response(result)
```

### InferenceScope

```python
from microsoft.opentelemetry.a365.core import (
    InferenceCallDetails, InferenceOperationType, InferenceScope, Request, ServiceEndpoint,
)

with InferenceScope.start(
    request=Request(content="What's the weather?"),
    details=InferenceCallDetails(
        operationName=InferenceOperationType.CHAT, model="gpt-4o", providerName="openai",
        endpoint=ServiceEndpoint(hostname="api.openai.com"),
    ),
    agent_details=agent,
) as scope:
    completion = call_llm(...)
    scope.record_input_tokens(45)
    scope.record_output_tokens(20)
    scope.record_finish_reasons(["stop"])
```

### OutputScope

For async scenarios where the parent scope has ended but you need to record output later:

```python
from microsoft.opentelemetry.a365.core import OutputScope, Response, SpanDetails

parent_ctx = invoke_scope.get_context()  # Save before parent ends

with OutputScope.start(
    request, Response(messages="Final answer"), agent_details,
    span_details=SpanDetails(parent_context=parent_ctx),
):
    pass  # Output recorded from Response
```

## Validate Locally

Use the console exporter to verify spans are emitted correctly before deploying.

### Console-Only (No A365 Export)

Set `enable_a365=True` but leave the A365 HTTP exporter disabled. Spans are enriched with A365 attributes and printed to stdout:

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    enable_a365=True,
    enable_console=True,
    # a365_enable_observability_exporter defaults to False,
    # so spans are NOT sent to the A365 service.
)
```

### Console + A365 Export

To see console output **and** export to A365 simultaneously:

```python
use_microsoft_opentelemetry(
    enable_a365=True,
    enable_console=True,
    a365_enable_observability_exporter=True,
    a365_token_resolver=my_token_resolver,
)
```

### Debug Logging

Enable verbose logging to diagnose export issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("microsoft.opentelemetry.a365.core").setLevel(logging.DEBUG)

# Or target only the exporter:
logging.getLogger(
    "microsoft.opentelemetry.a365.core.exporters.agent365_exporter"
).setLevel(logging.DEBUG)
```

Key log messages to look for:

```
DEBUG  Token resolved for agent {agentId} tenant {tenantId}
DEBUG  Exporting {n} spans to {url}
DEBUG  HTTP 200 - correlation ID: abc-123
ERROR  Token resolution failed: {error}
ERROR  HTTP 401 exporting spans - correlation ID: abc-123
INFO   No spans with tenant/agent identity found; nothing exported.
```

## Troubleshooting

See the [official troubleshooting guide](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/microsoft-opentelemetry?tabs=python#troubleshooting) on Microsoft Learn.

## Samples

See the [samples/a365/](samples/a365/) directory for runnable examples.
