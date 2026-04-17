# A365 Observability (`microsoft.opentelemetry.a365`)

Agent365 observability SDK for OpenTelemetry-based tracing of AI agent operations. Provides scopes, exporters, middleware, and utilities for instrumenting agent invocations, LLM inference calls, tool executions, and output messages.

## Package Structure

### Root

| File | Description |
|------|-------------|
| `__init__.py` | Package entry point. Exports `A365Handlers`, `create_a365_components`, and `is_a365_enabled`. |
| `constants.py` | Distro-level constants: span operation names, OTel semantic convention keys, feature switches, GenAI conventions, tool/user/agent attribute keys, and environment variable names. |

### `core/`

Core tracing primitives — scopes, configuration, data models, and internal utilities.

| File | Description |
|------|-------------|
| `__init__.py` | Public API surface. Re-exports 40+ classes/functions from submodules (scopes, models, config, exporters). |
| `agent_details.py` | `AgentDetails` dataclass — metadata about an AI agent (ID, name, description, blueprint/platform IDs, tenant, version). |
| `channel.py` | `Channel` dataclass — channel context (name, link) for agent execution. |
| `config.py` | `TelemetryManager` singleton — thread-safe telemetry configuration. Sets up tracers, span processors, and exporters (Agent365 or Spectra). Provides `configure()`, `get_tracer()`, etc. |
| `constants.py` | Core-level constants for span operations, OTel conventions, feature switches, and error types. |
| `execute_tool_scope.py` | `ExecuteToolScope` — tracing scope for AI tool executions. Records tool name, arguments, call ID, type, and endpoint. |
| `inference_call_details.py` | `InferenceCallDetails` dataclass — LLM call metadata (model, provider, token counts, finish reasons, endpoint). |
| `inference_operation_type.py` | `InferenceOperationType` enum — Chat, TextCompletion, GenerateContent. |
| `inference_scope.py` | `InferenceScope` — tracing scope for LLM/AI inference operations. Records input/output messages, model details, token usage, and user info. |
| `invoke_agent_details.py` | `InvokeAgentScopeDetails` dataclass — configuration for agent invocation tracing (endpoint). |
| `invoke_agent_scope.py` | `InvokeAgentScope` — tracing scope for agent invocations. Records request/response, caller details (human and agent-to-agent), channel, and endpoint info. |
| `message_utils.py` | Conversion and serialization helpers for OTel gen-ai message format. Normalizes strings/lists to structured `InputMessages`/`OutputMessages`. |
| `opentelemetry_scope.py` | `OpenTelemetryScope` — base class for all tracing scopes. Manages span creation, attribute setting, context management, and baggage building. |
| `request.py` | `Request` dataclass — request details (content, session ID, channel, conversation ID). |
| `span_details.py` | `SpanDetails` dataclass — span configuration (kind override, parent context, start/end times, links). |
| `tool_call_details.py` | `ToolCallDetails` dataclass — tool call info (name, arguments, call ID, description, type, endpoint). |
| `tool_type.py` | `ToolType` enum — Function, Extension, Datastore. |
| `utils.py` | Utility functions: W3C context extraction, safe JSON serialization, IP validation, baggage manipulation, version retrieval. |

### `core/exporters/`

Span export pipeline — processors and exporters for Agent365 and Spectra backends.

| File | Description |
|------|-------------|
| `agent365_exporter.py` | `_Agent365Exporter` — SpanExporter that partitions spans by (tenantId, agentId), builds OTLP-like JSON payloads, and POSTs to Agent365 with Bearer token auth and retry logic. |
| `agent365_exporter_options.py` | `Agent365ExporterOptions` — configuration for the Agent365 exporter (cluster category, token resolver, endpoint flags, batch settings). |
| `enriched_span.py` | `EnrichedReadableSpan` — wrapper allowing extra attributes on immutable `ReadableSpan` objects. |
| `enriching_span_processor.py` | Span enrichment support with registration for platform instrumentors (LangChain, Semantic Kernel, OpenAI Agents). `_EnrichingBatchSpanProcessor` applies enrichers before batching. |
| `span_processor.py` | `A365SpanProcessor` — propagates OpenTelemetry baggage entries onto spans as attributes, with special handling for invoke_agent spans. |
| `spectra_exporter_options.py` | `SpectraExporterOptions` — configuration for OTLP export to a Spectra Collector sidecar (gRPC or HTTP, tuned for Kubernetes). |
| `utils.py` | Exporter utilities: hex encoding for trace/span IDs, span size truncation, span partitioning, environment variable handling, payload building helpers. |

### `core/middleware/`

| File | Description |
|------|-------------|
| `baggage_builder.py` | `BaggageBuilder` — fluent API for setting per-request baggage values (tenant ID, agent ID, caller/user details, session/conversation IDs, channel, endpoints). Provides context manager for baggage scope. |

### `core/models/`

Data models for messages, agents, callers, and responses.

| File | Description |
|------|-------------|
| `agent_type.py` | `AgentType` enum — EntraEmbodied, EntraNonEmbodied, MicrosoftCopilot, DeclarativeAgent, Foundry. |
| `caller_details.py` | `CallerDetails` dataclass — groups caller identity for agent-to-agent (A2A) scenarios (human user and calling agent). |
| `messages.py` | OTel gen-ai message types: enums (`MessageRole`, `FinishReason`, `Modality`), message parts (`TextPart`, `BlobPart`, `FilePart`, `UriPart`), `ChatMessage`, `OutputMessage`, and wrapper types. |
| `operation_source.py` | `OperationSource` enum — SDK, Gateway, MCPServer. |
| `response.py` | `Response` dataclass — output messages (strings, `OutputMessages`, or tool result dicts). |
| `service_endpoint.py` | `ServiceEndpoint` dataclass — hostname and optional port. |
| `user_details.py` | `UserDetails` dataclass — human user info (ID, email, name, client IP). |

### `core/spans_scopes/`

| File | Description |
|------|-------------|
| `output_scope.py` | `OutputScope` — tracing scope for output messages. Records output with agent/user details and conversation ID. |

### `core/trace_processor/`

| File | Description |
|------|-------------|
| `span_processor.py` | `SpanProcessor` — copies OpenTelemetry baggage entries to span attributes with special handling for invoke_agent spans. |
| `util.py` | Attribute lists for baggage-to-span propagation: `COMMON_ATTRIBUTES` and `INVOKE_AGENT_ATTRIBUTES`. |

### `hosting/`

Hosting-layer middleware for Bot Framework integration.

| File | Description |
|------|-------------|
| `__init__.py` | Exports `BaggageMiddleware`, `OutputLoggingMiddleware`, `ObservabilityHostingManager`, `ObservabilityHostingOptions`. |

### `hosting/middleware/`

| File | Description |
|------|-------------|
| `baggage_middleware.py` | `BaggageMiddleware` — propagates OpenTelemetry baggage context from `TurnContext`. Skips async ContinueConversation events. |
| `observability_hosting_manager.py` | `ObservabilityHostingManager` singleton — configures hosting-layer middleware. `ObservabilityHostingOptions` dataclass for enabling/disabling middleware. |
| `output_logging_middleware.py` | `OutputLoggingMiddleware` — creates `OutputScope` spans for outgoing messages. Links to parent span via traceparent in turn_state. |

### `hosting/scope_helpers/`

| File | Description |
|------|-------------|
| `populate_baggage.py` | Extracts baggage pairs from `TurnContext` activity and sets them on a `BaggageBuilder`. |
| `populate_invoke_agent_scope.py` | Extracts `TurnContext` activity data and records as `InvokeAgentScope` attributes and input messages. |
| `utils.py` | Pair extraction helpers for `TurnContext` activity: caller pairs, target agent pairs, tenant ID, channel, conversation. |

### `hosting/token_cache_helpers/`

| File | Description |
|------|-------------|
| `agent_token_cache.py` | `AgenticTokenCache` — thread-safe cache for observability tokens per (agentId, tenantId). `AgenticTokenStruct` wraps Authorization and TurnContext for token generation. |

### `runtime/`

Runtime utilities for environment discovery, error handling, and token operations.

| File | Description |
|------|-------------|
| `environment_utils.py` | Environment utilities: observability authentication scopes (with override support), dev environment detection. |
| `operation_error.py` | `OperationError` — wraps an exception with message property. |
| `operation_result.py` | `OperationResult` — represents operation success/failure with optional error list. Singleton success instance. |
| `power_platform_api_discovery.py` | `PowerPlatformApiDiscovery` — discovers Power Platform API endpoints per cluster category. `ClusterCategory` type for valid cluster strings. |
| `utility.py` | `Utility` — static methods for JWT token decoding (diagnostics only), extracting app IDs and agent blueprint IDs from tokens. |
| `version_utils.py` | Deprecated versioning utilities. `build_version()` deprecated in favor of setuptools-git-versioning. |
