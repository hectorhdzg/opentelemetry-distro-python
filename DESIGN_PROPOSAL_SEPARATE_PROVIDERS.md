# Design Proposal: Separate TracerProviders for A365 and Azure Monitor/OTLP

**Status:** Draft — for team discussion  
**Date:** 2026-05-13  
**Author:** *(fill in)*

---

## 1. Problem Statement

Today, the distro uses a **single global `TracerProvider`** for all export destinations (Azure Monitor, OTLP, A365, Console). All span processors, samplers, and instrumentors operate on this shared provider. This creates several entangled problems when A365 and Azure Monitor/OTLP coexist:

### 1.1 Azure Monitor Sampler Drops A365 Spans

When `enable_azure_monitor=True`, the provider is created with a rate-limited or fixed-percentage sampler (e.g., `RateLimitedSampler` at 5 spans/sec). Because A365 processors are on the **same provider**, the sampler drops spans before A365 ever sees them. A365 has no independent sampling control.

```
┌──────────────────────────────────────────────────────────────────┐
│                  Single TracerProvider                            │
│  ┌──────────┐                                                    │
│  │ Sampler  │──▶ span dropped ──▶ A365 never sees it             │
│  │ (AzMon)  │──▶ span sampled ──▶ AzMon processor + A365 proc   │
│  └──────────┘                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Content Capture Settings Are Conflated

Content capture is controlled by the standard OTel env var `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` (values: `SPAN_ONLY`, `EVENT_ONLY`, `SPAN_AND_EVENT`). This is a **global setting** — it applies to all instrumentors and all exporters equally. There is no way to say "capture content for Azure Monitor but not for A365" or vice versa.

The only A365-specific content control is `a365_suppress_invoke_agent_input`, which is an export-time hack that strips `gen_ai.input.messages` from `InvokeAgent` spans in the A365 processor — it doesn't cover other span types or output messages, and it doesn't affect other exporters.

The fundamental problem: content is recorded as span attributes at instrumentation time (before any processor sees the span). With a single provider, all exporters see the same attributes. The A365 team wants content policy to be **independent of the OTel instrumentation settings** — i.e., A365 should control what sensitive data it receives regardless of what `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` is set to.

> **Upstream OTel opportunity:** The OTel GenAI semconv could benefit from per-instrumentation content capture control (e.g. `OTEL_INSTRUMENTATION_GENAI_<LIBRARY>_CAPTURE_MESSAGE_CONTENT`). This doesn't exist today — it's worth proposing.

### 1.3 A365 Custom Attributes Pollute Azure Monitor / OTLP Spans

`A365SpanProcessor.on_start()` stamps **32+ custom attributes** (baggage-propagated tenant ID, agent ID, session ID, channel, caller-agent details, etc.) onto every span. These are A365-specific attributes in the `microsoft.*` namespace that add noise when viewed in Azure Monitor or an OTLP backend.

### 1.4 A365 Uses Non-Standard GenAI Conventions

A365 scope classes use a mix of standard OTel GenAI semconv and custom Microsoft attributes:
- `microsoft.a365.agent.thought.process`, `microsoft.a365.agent.platform.id`
- `gen_ai.agent365.icon_uri` (non-standard `gen_ai.` key)
- `custom.parent.span.id`, `custom.span.name` (overrides OTel span relationships)
- `telemetry.sdk.name = "A365ObservabilitySDK"` (clashes with OTel resource conventions)

Auto-instrumentors (OpenAI, LangChain, Semantic Kernel) emit standard OTel GenAI semconv. The A365 enricher then transforms/adds attributes for A365 consumption, but these transformations bleed into Azure Monitor/OTLP.

### 1.5 Instrumentation Enable/Disable Is a Workaround

The distro currently auto-disables web-framework instrumentations when `enable_a365=True` alone, then re-enables them when Azure Monitor is also active. This heuristic is fragile and doesn't solve the fundamental problem: A365 only cares about GenAI spans, while Azure Monitor cares about everything.

---

## 2. Proposed Architecture: Dual TracerProvider

Create **two independent `TracerProvider` instances** — one for general-purpose observability (Azure Monitor + OTLP + Console) and one dedicated to A365.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       use_microsoft_opentelemetry()                      │
│                                                                         │
│  ┌─────────────────────────────┐   ┌──────────────────────────────────┐ │
│  │  Primary TracerProvider     │   │  A365 TracerProvider             │ │
│  │  (set as global)            │   │  (internal, not global)          │ │
│  │                             │   │                                  │ │
│  │  Sampler: AzMon / user      │   │  Sampler: AlwaysOn (or A365     │ │
│  │                             │   │           specific config)       │ │
│  │  Processors:                │   │                                  │ │
│  │   - AzMon BatchSP           │   │  Processors:                    │ │
│  │   - OTLP BatchSP            │   │   - A365SpanProcessor (baggage) │ │
│  │   - Console SimpleSP        │   │   - _EnrichingBatchSP (export)  │ │
│  │   - User-supplied SPs       │   │                                  │ │
│  │                             │   │  Content policy:                 │ │
│  │  Content: per OTEL settings │   │   Independent of primary        │ │
│  └─────────────────────────────┘   └──────────────────────────────────┘ │
│                                                                         │
│  Auto-instrumentors ──▶ Primary provider (global)                       │
│  A365 scope classes  ──▶ A365 provider (explicit tracer)                │
│  A365SpanProcessor   ──▶ A365 provider only (no attribute pollution)    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Primary Provider (Global)

- Registered as the **OTel global singleton** via `set_tracer_provider()`.
- All auto-instrumentors (Django, FastAPI, OpenAI, LangChain, etc.) use this provider.
- Sampler configured per user settings (Azure Monitor rate-limited, `OTEL_TRACES_SAMPLER`, etc.).
- Span processors: Azure Monitor, OTLP, Console, user-supplied.
- Content capture follows per-instrumentor settings (no distro-level content policy exists today).
- **No A365-specific processors or attributes.**

### 2.2 A365 Provider (Internal)

- **Not** registered as the global provider — only used by A365 components.
- Created with its own `Resource` (can include `telemetry.sdk.name = "A365ObservabilitySDK"`).
- Sampler: `AlwaysOn` by default, or a new `a365_sampler` / `A365_TRACES_SAMPLER` setting.
- Span processors: `A365SpanProcessor` (baggage), `_EnrichingBatchSpanProcessor` (enricher + export).
- Content capture controlled independently via `a365_suppress_invoke_agent_input` (expanded — see §3.2).

### 2.3 How A365 Scopes Use the A365 Provider

Currently `OpenTelemetryScope._get_tracer()` calls `trace.get_tracer(SOURCE_NAME)` which returns a tracer from the global provider. Change this to:

```python
class OpenTelemetryScope:
    _a365_provider: TracerProvider | None = None

    @classmethod
    def _set_provider(cls, provider: TracerProvider) -> None:
        cls._a365_provider = provider

    @classmethod
    def _get_tracer(cls) -> Tracer:
        if cls._a365_provider is not None:
            return cls._a365_provider.get_tracer(SOURCE_NAME)
        # Fallback to global (backward compat for standalone A365 usage)
        return trace.get_tracer(SOURCE_NAME)
```

The distro calls `OpenTelemetryScope._set_provider(a365_provider)` during initialization.

### 2.4 Forwarding Auto-Instrumented GenAI Spans to A365

Auto-instrumentors (OpenAI, LangChain, Semantic Kernel, Agent Framework) create spans on the **primary provider**. A365 needs to see these spans too. Two options:

**Option A — Forwarding SpanProcessor (recommended):**

Add a lightweight `_A365ForwardingSpanProcessor` to the **primary provider** that selectively copies GenAI spans to the A365 provider:

```python
class _A365ForwardingSpanProcessor(SpanProcessor):
    """Forwards GenAI spans from the primary provider to the A365 pipeline."""

    def __init__(self, a365_provider: TracerProvider):
        self._a365_provider = a365_provider

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        # Only forward GenAI spans (by operation name or instrumentor source)
        if self._is_genai_span(span):
            # Replay into A365 provider's processors
            for proc in self._a365_provider._active_span_processor._span_processors:
                proc.on_start(span, parent_context)

    def on_end(self, span: ReadableSpan) -> None:
        if self._is_genai_span(span):
            for proc in self._a365_provider._active_span_processor._span_processors:
                proc.on_end(span)
```

This lets auto-instrumented OpenAI/LangChain spans reach the A365 enricher pipeline while keeping the primary provider clean of A365 attributes.

**Option B — Dual-instrument:**

GenAI instrumentors are configured to create spans on **both** providers. This requires upstream instrumentor changes (less practical for third-party instrumentors).

**Recommendation:** Option A — it's transparent to instrumentors.

---

## 3. Expanded Design Details

### 3.1 Independent Sampling

| Setting | Scope | Default |
|---|---|---|
| `OTEL_TRACES_SAMPLER` | Primary provider | Per OTel spec |
| Azure Monitor sampler kwargs | Primary provider | `RateLimitedSampler(5)` |
| `a365_sampler` (new) | A365 provider | `AlwaysOn` |
| `A365_TRACES_SAMPLER` (new env var) | A365 provider | `always_on` |

A365 telemetry is typically low-volume (only GenAI operations) and high-value (every agent invocation matters for observability dashboards). Defaulting to `AlwaysOn` is appropriate.

### 3.2 Content Capture — Rely on OTel, Strip at Export

We should **not** invent a custom distro-level content policy. Content capture is and should remain controlled by the standard OTel env var:

```bash
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=SPAN_AND_EVENT
```

This is global and affects all instrumentors. We don't change that.

What changes with dual providers is that the A365 `_EnrichingBatchSpanProcessor` can independently strip content attributes **at export time** without affecting what Azure Monitor/OTLP see. The existing `a365_suppress_invoke_agent_input` mechanism already does this for input messages on `InvokeAgent` spans — with a separate provider, it can be cleanly extended to cover more span types if needed.

| Layer | Controls | Scope |
|---|---|---|
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Whether content is recorded on spans at all | Global (all instrumentors, all exporters) |
| `a365_suppress_invoke_agent_input` | Strip input messages from `InvokeAgent` spans before A365 export | A365 exporter only |

The key insight: with separate providers, the A365 pipeline can drop attributes the OTel config chose to capture, but it **cannot add** attributes the OTel config chose not to capture. This is the right direction — OTel controls the ceiling, A365 can only reduce.

> **Future upstream proposal:** Per-instrumentation content capture control in OTel (e.g. `OTEL_INSTRUMENTATION_GENAI_OPENAI_CAPTURE_MESSAGE_CONTENT` vs `OTEL_INSTRUMENTATION_GENAI_LANGCHAIN_CAPTURE_MESSAGE_CONTENT`) would let users fine-tune content capture without needing export-time stripping. This is worth proposing to the OTel GenAI SIG.

### 3.3 No Attribute Pollution

Since A365 baggage propagation (`A365SpanProcessor`) only runs on the A365 provider, the 32+ `microsoft.*` attributes no longer appear on spans in Azure Monitor or OTLP backends.

| Attribute category | Primary provider | A365 provider |
|---|---|---|
| Standard OTel GenAI semconv | Yes (from instrumentors) | Yes (forwarded from primary) |
| `microsoft.tenant.id`, `gen_ai.agent.id`, etc. | **No** (clean) | Yes (from `A365SpanProcessor`) |
| `microsoft.a365.*` custom attrs | **No** | Yes (from enricher) |
| `telemetry.sdk.name = "A365..."` | **No** | Yes (on A365 Resource) |

### 3.4 Instrumentation Simplification

With separate providers, the A365-specific instrumentation disable/enable heuristic becomes unnecessary:

- **Primary provider**: All instrumentors enabled by default (Django, FastAPI, OpenAI, etc.). User controls via `instrumentation_options`.
- **A365 provider**: Only receives GenAI spans via the forwarding processor. Web-framework spans are never forwarded — no need to disable them.

The `_A365_DISABLED_INSTRUMENTATIONS` list and the dual-mode logic can be removed.

---

## 4. Migration & Backward Compatibility

### 4.1 No Breaking API Changes

`use_microsoft_opentelemetry()` signature stays the same. The dual-provider setup is internal.

### 4.2 A365 Scope Classes

`InvokeAgentScope`, `ExecuteToolScope`, etc. continue to work — they just get their tracer from the A365 provider instead of the global provider. No user-facing API change.

### 4.3 Standalone A365 (No Azure Monitor)

When `enable_a365=True` alone (no Azure Monitor, no OTLP):
- Primary provider: `AlwaysOn` sampler, no exporters (or Console if enabled).
- A365 provider: `AlwaysOn` sampler, A365 exporter.
- Auto-instrumentors still use primary provider, forwarding processor sends GenAI spans to A365.

Functionally equivalent to today, but cleaner.

### 4.4 Deprecation Path

| Item | Action |
|---|---|
| `_A365_DISABLED_INSTRUMENTATIONS` heuristic | Remove — no longer needed |
| `A365SpanProcessor` on primary provider | Remove — only on A365 provider |
| Export-time input stripping hack | Keep for compat, superseded by `a365_content_recording` |

---

## 5. Implementation Plan

### Phase 1 — Dual Provider Core (low risk)

1. Create a separate `TracerProvider` in `_append_a365_components()` with its own `Resource`.
2. Move `A365SpanProcessor` and `_EnrichingBatchSpanProcessor` to the A365 provider only.
3. Wire `OpenTelemetryScope._set_provider()` to use the A365 provider.
4. Add `_A365ForwardingSpanProcessor` to the primary provider.
5. Verify existing tests pass (all A365 spans should still export correctly).

### Phase 2 — Independent Sampling

6. Add `a365_sampler` kwarg and `A365_TRACES_SAMPLER` env var support.
7. Default A365 provider to `AlwaysOn`.
8. Verify Azure Monitor sampler no longer drops A365 spans.

### Phase 3 — Content Stripping Expansion (optional)

9. If needed, extend `_EnrichingBatchSpanProcessor` to strip content attributes from additional span types beyond `InvokeAgent` (e.g. `execute_tool`, `chat`).
10. Keep `a365_suppress_invoke_agent_input` as-is — no new content policy kwargs.
11. Propose per-instrumentation content capture control upstream to OTel GenAI SIG.

### Phase 4 — Cleanup

12. Remove `_A365_DISABLED_INSTRUMENTATIONS` heuristic.
13. Remove `A365SpanProcessor` from primary provider's processor list.
14. Update documentation and samples.

---

## 6. Risks & Open Questions

| # | Question | Notes |
|---|---|---|
| 1 | **Span context propagation**: If A365 scopes create spans on a separate provider, do parent-child relationships still work across providers? | OTel context propagation is based on `Context`, not provider. Spans from different providers can share parent context. The forwarding processor preserves the original span's context. Need to verify. |
| 2 | **Forwarding processor performance**: Copying spans to a second processor pipeline — is the overhead acceptable? | A365 forwarding is lightweight (no serialization). Only GenAI spans are forwarded. The filter check is O(1) attribute lookup. |
| 3 | **Resource merging**: Should the A365 provider share the user's `Resource` or have a completely separate one? | Recommend: merge user resource + A365-specific resource attributes. This preserves `service.name` while adding `telemetry.sdk.name = "A365ObservabilitySDK"`. |
| 4 | **User-supplied span processors**: Should they go on primary only, A365 only, or both? | Primary only (current behavior). If users need A365-specific processors they can pass them via a new `a365_span_processors` kwarg. |
| 5 | **`ENABLE_OBSERVABILITY` env var**: Currently gates A365 scope classes via `_is_telemetry_enabled()`. Does this still work with a separate provider? | Yes — the check is in `OpenTelemetryScope.__init__()` and is independent of provider. No change needed. |
| 6 | **Third-party instrumentors**: The forwarding processor relies on identifying GenAI spans. What heuristic? | Filter by `gen_ai.operation.name` attribute or span name prefix matching (`invoke_agent`, `execute_tool`, `chat`, etc.). Configurable allowlist. |

---

## 7. Summary

| Problem | Current | Proposed |
|---|---|---|
| Azure Monitor sampler drops A365 spans | Single provider, one sampler for all | Separate A365 provider with independent sampler |
| Content capture settings conflated | Export-time hack on A365 processor only | OTel controls the ceiling; A365 strips at export with separate provider |
| A365 attributes pollute AzMon/OTLP | `A365SpanProcessor` on shared provider | A365 processors only on A365 provider |
| Non-standard conventions bleed across | Enricher modifies spans seen by all exporters | Enricher only runs in A365 pipeline |
| Fragile instrumentation disable heuristic | `_A365_DISABLED_INSTRUMENTATIONS` | Forwarding processor selectively routes GenAI spans |
