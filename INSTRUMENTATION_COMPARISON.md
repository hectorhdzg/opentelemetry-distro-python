# Instrumentation Comparison: Microsoft Distro vs OpenInference (Arize)

This document compares the OpenAI and LangChain instrumentations between:
- **Microsoft OpenTelemetry Distro** (`opentelemetry-distro-python`)
- **OpenInference** (`Arize-ai/openinference`)

---

## Table of Contents

1. [OpenAI Instrumentation](#openai-instrumentation)
2. [LangChain Instrumentation](#langchain-instrumentation)
3. [Summary of Key Differences](#summary-of-key-differences)

---

## OpenAI Instrumentation

### Hooking Mechanism

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Target** | OpenAI **Agents SDK** tracing system (`TracingProcessor` interface) | OpenAI **client SDK** (`OpenAI.request()` / `AsyncOpenAI.request()`) |
| **Technique** | Registers a `TracingProcessor` with the Agents SDK's trace provider | `wrapt.wrap_function_wrapper()` on sync/async request methods |
| **Scope** | Agent orchestration layer (agents, tools, handoffs, generations) | Raw API calls (chat completions, embeddings, completions, responses API) |
| **SDK Dependency** | `openai-agents >= 0.0.7` | `openai >= 1.69.0` |

**Key difference:** Microsoft hooks into the higher-level Agents SDK orchestration framework, while OpenInference intercepts the low-level HTTP request layer of the base OpenAI client. This means:
- Microsoft captures agent workflows, handoffs, and multi-agent orchestration natively
- OpenInference captures every raw API call regardless of how it was triggered

### Semantic Conventions

| Attribute | Microsoft Distro | OpenInference |
|-----------|-----------------|---------------|
| **Standard** | OTel GenAI semconv (`gen_ai.*`) | OpenInference semconv (`llm.*`, `openinference.*`) |
| **Operation name** | `gen_ai.operation.name` = `chat`, `invoke_agent`, `execute_tool` | `openinference.span.kind` = `LLM`, `EMBEDDING` |
| **Model** | `gen_ai.request.model` | `llm.model_name` |
| **Provider** | `gen_ai.provider.name` | `llm.provider` + `llm.system` |
| **Input messages** | `gen_ai.input.messages` (JSON array) | `llm.input_messages.{i}.message.role`, `.content` (indexed attributes) |
| **Output messages** | `gen_ai.output.messages` (JSON array) | `llm.output_messages.{i}.message.role`, `.content` (indexed attributes) |
| **Input value** | — | `input.value` (full JSON dump of request params) |
| **Output value** | — | `output.value` (full JSON dump of response) |
| **MIME types** | — | `input.mime_type`, `output.mime_type` = `application/json` |

**Key difference:** Microsoft follows the emerging OTel GenAI semantic conventions using flat JSON arrays for messages. OpenInference uses its own convention with indexed span attributes (e.g., `llm.input_messages.0.message.role`), which can result in many more attributes per span.

### Token Usage

| Token Metric | Microsoft Distro | OpenInference |
|-------------|-----------------|---------------|
| **Input tokens** | `gen_ai.usage.input_tokens` | `llm.token_count.prompt` |
| **Output tokens** | `gen_ai.usage.output_tokens` | `llm.token_count.completion` |
| **Total tokens** | `llm_token_count_total` (custom) | `llm.token_count.total` |
| **Cached tokens** | `llm_token_count_prompt_details_cached_read` | `llm.token_count.prompt_details.cache_read` |
| **Reasoning tokens** | `llm_token_count_completion_details_reasoning` | `llm.token_count.completion_details.reasoning` |
| **Audio tokens** | — | `llm.token_count.prompt_details.audio`, `llm.token_count.completion_details.audio` |

### Streaming Support

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Approach** | No per-chunk spans; Agents SDK delivers complete `GenerationSpanData` / `ResponseSpanData` | Wraps stream iterator with `wrapt.ObjectProxy`; accumulates chunks via `_ChatCompletionAccumulator` |
| **Chunk tracking** | Not applicable | Each chunk processed as it yields, span ends on `StopIteration` |
| **First token event** | — | Records `"First Token Stream Event"` span event |
| **Token counts** | Captured complete from final response | Requires `stream_options={"include_usage": True}` for streaming usage |

**Key difference:** OpenInference has deep streaming support with chunk-level accumulation, while Microsoft relies on the Agents SDK to deliver complete data.

### Tool / Function Call Handling

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Tool capture** | Dedicated `FunctionSpanData` and `HandoffSpanData` spans | Inline attributes on message spans (`llm.input_messages.{i}.message.tool_calls.{j}.*`) |
| **Tool call ID correlation** | Two-phase: capture IDs from `GenerationSpanData` output, match to `FunctionSpanData` by `(trace_id, name, args)` key | Direct extraction from request/response message structures |
| **Tool attributes** | `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`, `gen_ai.tool.type` | `llm.tools.{i}.tool.json_schema` (tool definitions), tool_call data in messages |
| **Handoffs** | Native `HandoffSpanData` with `gen_ai.graph.node_parent_id` for multi-agent graphs | Not supported (no agent orchestration concept) |

### Span Hierarchy

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Structure** | Multi-level tree: Root → Agent → Generation/Function/Handoff | Flat: one span per API call |
| **Root span** | `"Agent workflow"` created at trace start | No root span concept |
| **Agent spans** | `"invoke_agent <AgentName>"` | — |
| **LLM spans** | `"chat <model>"` | `"ChatCompletion"`, `"Completion"`, `"CreateEmbeddings"` |
| **Tool spans** | `"execute_tool <tool_name>"` | — (tool calls are attributes on LLM spans) |
| **Handoff spans** | `"handoff to <AgentB>"` | — |
| **Graph topology** | `custom.parent.span.id`, `gen_ai.graph.node_parent_id` | — |

### Configuration

| Feature | Microsoft Distro | OpenInference |
|---------|-----------------|---------------|
| **Content capture** | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=SPAN_AND_EVENT` | `TraceConfig(hide_inputs=True, hide_outputs=True, ...)` |
| **Agent identity** | `agent_id`, `agent_name` via `instrumentation_options` | — |
| **Image handling** | — | `hide_input_images`, `base64_image_max_length` |
| **Granular hiding** | — | `hide_input_messages`, `hide_output_messages`, `hide_input_text`, `hide_output_text`, `hide_embeddings_vectors`, etc. |
| **Semconv toggle** | `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` | `enable_genai_semconv=True` (dual-emit OI + GenAI) |
| **Env var overrides** | Standard OTel env vars | All config options have `OPENINFERENCE_*` env var equivalents |

### OTel Span Kind

| | Microsoft Distro | OpenInference |
|---|---|---|
| **SpanKind** | Not explicitly set (uses OTel default `INTERNAL`) | Not explicitly set (uses OTel default `INTERNAL`) |
| **Logical kind** | `gen_ai.operation.name` attribute (`chat`, `invoke_agent`, `execute_tool`) | `openinference.span.kind` attribute (`LLM`, `EMBEDDING`) |

---

## LangChain Instrumentation

### Hooking Mechanism

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Technique** | Wraps `BaseCallbackManager.__init__` to inject tracer | Wraps `BaseCallbackManager.__init__` to inject tracer |
| **Tracer class** | Custom `LangChainTracer` extends `BaseTracer` | Custom `OpenInferenceTracer` extends `BaseTracer` |
| **Injection** | Adds tracer as inheritable handler | Adds tracer as inheritable handler |
| **SDK Dependency** | `langchain-core >= 0.2.0` | `langchain_core >= 0.1.0` |

**Key similarity:** Both projects use the exact same injection pattern — wrapping `BaseCallbackManager.__init__` to automatically add their tracer as a callback handler. The fundamental architecture is identical.

### Semantic Conventions

| Attribute | Microsoft Distro | OpenInference |
|-----------|-----------------|---------------|
| **Standard** | OTel GenAI semconv (`gen_ai.*`) | OpenInference semconv (`llm.*`, `openinference.*`) |
| **Operation name** | `gen_ai.operation.name` = `chat`, `invoke_agent`, `execute_tool` | `openinference.span.kind` = `LLM`, `CHAIN`, `TOOL`, `AGENT`, `RETRIEVER`, `EMBEDDING` |
| **Model** | `gen_ai.request.model` | `llm.model_name` |
| **Provider** | `gen_ai.provider.name` | `llm.provider` + `llm.system` (with provider-to-system mapping) |
| **Input messages** | `gen_ai.input.messages` (JSON array) | `llm.input_messages.{i}.message.role`, `.content` (indexed) |
| **Output messages** | `gen_ai.output.messages` (JSON array) | `llm.output_messages.{i}.message.role`, `.content` (indexed) |
| **Invocation params** | — | `llm.invocation_parameters` (JSON string with temp, max_tokens, etc.) |
| **Input/Output value** | — | `input.value`, `output.value` (full serialized I/O) |
| **Retrieval docs** | — | `retrieval.documents.{i}.document.content`, `.metadata` |

### Components Instrumented

| Component | Microsoft Distro | OpenInference |
|-----------|-----------------|---------------|
| **LLMs** | `chat` operation, `SpanKind.CLIENT` | `LLM` span kind |
| **Chat Models** | Same as LLMs | Same as LLMs |
| **Chains** | `SpanKind.INTERNAL`, detected as agent-like if LangGraph | `CHAIN` span kind |
| **Agents** | Dual-span: wrapper (`invoke_agent`) + inner (framework name) | `AGENT` span kind (detected by `"agent"` in name) |
| **Tools** | `execute_tool` operation, aggregated into parent agent | `TOOL` span kind |
| **Retrievers** | `SpanKind.INTERNAL` | `RETRIEVER` span kind with `retrieval.documents` |
| **Embeddings** | — | `EMBEDDING` span kind |

### Agent Detection & Hierarchy

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Agent detection** | Checks: run name `"LangGraph"`, serialized graph type (`CompiledGraph`, `StateGraph`), `"agent"` in name, `lc_agent_name` metadata | Checks: `"agent"` in `run.name.lower()` |
| **Agent span structure** | **Dual-span**: wrapper span (`invoke_agent <AgentName>`) + inner span (`invoke_agent <FrameworkName>`) | **Single span**: one span per run with `AGENT` kind |
| **Content aggregation** | Child LLM/tool spans aggregate token counts, messages, and model info into parent agent wrapper | No aggregation; each span is independent |
| **Agent identity** | `gen_ai.agent.name`, `gen_ai.agent.id`, `gen_ai.agent.description`, `gen_ai.agent.version` | No dedicated agent identity attributes |
| **Conversation tracking** | `gen_ai.conversation.id` | — |

**Key difference:** Microsoft creates a **dual-span hierarchy** for agents with content aggregation from children, while OpenInference creates a **flat span-per-run** model. Microsoft's approach gives a unified view of agent behavior at the wrapper span level.

### Token Usage

| Token Metric | Microsoft Distro | OpenInference |
|-------------|-----------------|---------------|
| **Input tokens** | `gen_ai.usage.input_tokens` | `llm.token_count.prompt` |
| **Output tokens** | `gen_ai.usage.output_tokens` | `llm.token_count.completion` |
| **Total tokens** | — | `llm.token_count.total` |
| **Cache read** | `gen_ai.usage.cache_read_input_tokens` | `llm.token_count.prompt_details.cache_read` |
| **Cache creation** | `gen_ai.usage.cache_creation_input_tokens` | `llm.token_count.prompt_details.cache_write` |
| **Reasoning tokens** | `gen_ai.usage.reasoning.output_tokens` | `llm.token_count.completion_details.reasoning` |
| **Audio tokens** | — | `llm.token_count.prompt_details.audio`, `llm.token_count.completion_details.audio` |

**Parsing sources** (both handle multiple formats):
- Microsoft: `llm_output.token_usage`, `usage_metadata`, `response_metadata.token_usage`, `generation_info.token_usage`
- OpenInference: `llm_output.token_usage`, streaming `usage_metadata`, Vertex AI `generation_info`, Anthropic cache tokens

### Provider Detection

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Source** | LangChain `ls_provider` metadata, model name inference | LangChain `ls_provider` metadata, model name inference |
| **Provider mapping** | Maps to `gen_ai.provider.name` | Maps to both `llm.provider` and `llm.system` |
| **Supported providers** | OpenAI, Anthropic, Azure, Bedrock/AWS, Google/Vertex | OpenAI, Anthropic, Azure, Bedrock, Google/Vertex, Cohere, Mistral |

### Span Names & Kinds

| Run Type | Microsoft Distro | OpenInference |
|----------|-----------------|---------------|
| **LLM** | `"chat <model>"` / `SpanKind.CLIENT` | `run.name` (e.g., `"OpenAI"`) / `INTERNAL` |
| **Agent** | `"invoke_agent <Name>"` (wrapper) + `"invoke_agent <Framework>"` (inner) / `INTERNAL` | `run.name` / `INTERNAL` |
| **Tool** | `"execute_tool <tool_name>"` / `INTERNAL` | `run.name` / `INTERNAL` |
| **Chain** | `run.name` / `INTERNAL` | `run.name` / `INTERNAL` |
| **Retriever** | `run.name` / `INTERNAL` | `run.name` / `INTERNAL` |

### Message Handling

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Role mapping** | `human` → `user`, `ai` → `assistant` (simple map) | Multi-strategy: class name → role, `type` field → role, direct `role` field, context inference |
| **Message parts** | `Text`, `ToolCall`, `ToolCallResponse` structured parts | Flat content + tool_calls attributes |
| **Agent message flow** | Incremental: seed → LLM pending → promote to history → tool result → finalize | Direct: capture from run inputs/outputs per span |
| **JSON serialization** | Standard `json.dumps` with basic type handling | Custom `_OpenInferenceJSONEncoder` supporting `BaseMessage`, Pydantic, dataclasses, datetime, UUID, Decimal, Enum, etc. |

### Configuration

| Feature | Microsoft Distro | OpenInference |
|---------|-----------------|---------------|
| **Content capture** | Via `instrumentation_options` dict | `TraceConfig` dataclass |
| **Agent identity** | `agent_id`, `agent_name`, `agent_description`, `agent_version` | — |
| **Content hiding** | — | `hide_inputs`, `hide_outputs`, `hide_input_messages`, `hide_output_messages`, `hide_input_text`, `hide_output_text`, etc. |
| **Image handling** | — | `hide_input_images`, `base64_image_max_length` |
| **Context separation** | `separate_trace_from_runtime_context` | `separate_trace_from_runtime_context` |
| **Env vars** | Standard OTel env vars | `OPENINFERENCE_*` env vars for each config option |

### Memory Management

| Aspect | Microsoft Distro | OpenInference |
|--------|-----------------|---------------|
| **Tracking limit** | `_MAX_TRACKED_RUNS = 10000` with LRU eviction | `_DictWithLock` (dict with thread safety) |
| **Eviction** | `OrderedDict.popitem(last=False)` evicts oldest runs with cleanup of auxiliary dicts | No explicit eviction |
| **Thread safety** | `RLock` for concurrent access | `RLock` for concurrent access |

### A365 Pipeline (Microsoft-specific)

Microsoft has an additional A365-specific enrichment layer (`a365/langchain/_span_enricher.py`) that:
- Maps `gen_ai.conversation.id` → `microsoft.session.id`
- Converts structured OTel messages to plain content arrays for A365 consumers
- Passes through tool arguments/results for `execute_tool` spans

This layer does not exist in OpenInference.

---

## Summary of Key Differences

### Architecture Philosophy

| | Microsoft Distro | OpenInference |
|---|---|---|
| **Design goal** | OTel-native with GenAI semconv, Azure/A365 integration | Observability-first with custom OpenInference semconv |
| **Semconv standard** | OTel GenAI (`gen_ai.*`) — emerging standard | OpenInference (`llm.*`, `openinference.*`) — established custom |
| **Message format** | JSON arrays as single attributes | Indexed per-attribute (can produce 100s of attributes) |
| **Agent support** | First-class with identity, aggregation, dual-span hierarchy | Basic name-based detection, flat hierarchy |
| **Multi-agent** | Handoff tracking, graph node parent IDs | Not supported |
| **Content privacy** | Basic capture toggle | Fine-grained: per-field hiding (text, images, embeddings, tools, prompts) |
| **Streaming** | Delegated to SDK | Deep chunk-level accumulation with stream wrapping |
| **Azure integration** | Built-in A365 pipeline, Azure Monitor export | None |
| **Vendor lock-in** | Minimal (uses OTel standards) | None (custom semconv but vendor-neutral) |

### What Microsoft Distro Has That OpenInference Doesn't

1. **Agent orchestration tracking** — handoffs, graph topology, multi-agent parent IDs
2. **Dual-span agent hierarchy** — wrapper + inner span for agents with content aggregation
3. **Agent identity attributes** — `agent.name`, `agent.id`, `agent.description`, `agent.version`
4. **Conversation tracking** — `gen_ai.conversation.id`
5. **A365/Azure Monitor pipeline** — enrichment, session mapping
6. **OpenAI Agents SDK integration** — native support for the Agents framework
7. **Memory-bounded tracking** — LRU eviction for long-running agents

### What OpenInference Has That Microsoft Distro Doesn't

1. **Low-level OpenAI client instrumentation** — captures all API calls (not just Agents SDK)
2. **Embeddings instrumentation** — dedicated `EMBEDDING` span kind with vector capture
3. **Retriever document capture** — `retrieval.documents` with content and metadata
4. **Fine-grained privacy controls** — per-field hiding (images, text, embeddings, vectors, tools)
5. **Deep streaming support** — chunk accumulation, first-token events
6. **Image redaction** — base64 length thresholds, automatic redaction
7. **Rich JSON serialization** — custom encoder for LangChain types, Pydantic, dataclasses, etc.
8. **Broader provider mapping** — Cohere, Mistral, and more providers mapped
9. **Dual semconv emission** — can emit both OpenInference and OTel GenAI conventions simultaneously
10. **Full request/response capture** — `input.value` / `output.value` with complete serialized payloads
