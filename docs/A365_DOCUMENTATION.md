# Agent 365 Observability

> **Official docs:** [Agent observability on Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/observability?tabs=python)

This guide covers A365-specific concepts: baggage, token resolution, and manual scope classes.
For setup, configuration options, and auto-instrumented libraries, see the [main README](../README.md).
For migrating from standalone A365 packages, see [MIGRATION_A365.md](../MIGRATION_A365.md).

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

### AgenticTokenCache

```python
from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.hosting.token_cache_helpers import AgenticTokenCache, AgenticTokenStruct
from microsoft.opentelemetry.a365.runtime import get_observability_authentication_scope

token_cache = AgenticTokenCache()

_cached_tokens: dict[tuple[str, str], str | None] = {}

# Keep the sync resolver side-effect free; refresh the cache in async request handling.
def sync_token_resolver(agent_id: str, tenant_id: str) -> str | None:
    return _cached_tokens.get((agent_id, tenant_id))

use_microsoft_opentelemetry(enable_a365=True, a365_token_resolver=sync_token_resolver)

@AGENT_APP.activity("message", auth_handlers=["AGENTIC"])
async def on_message(context: TurnContext, _state: TurnState):
    agent_id = "agent-456"
    tenant_id = "tenant-123"
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

## Samples

See the [samples/a365/](../samples/a365/) directory for runnable examples.
