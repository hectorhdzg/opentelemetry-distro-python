# Release History
# Unreleased
### Features Added
- Add Python-native `InvokeAgentScope` request and response parameter models
  that emit OpenTelemetry GenAI semantic attributes, including structured
  system instructions and cache read/write token counts, introduced by .NET
  PR #120.

# 1.3.9 (2026-09-09)
### Features Added
- Update OpenTelemetry dependencies to latest versions, bump `langchain-core` minimum version to address S360, and support the new `httpx2` entry point exposed by `opentelemetry-instrumentation-httpx`.
  ([#254](https://github.com/microsoft/opentelemetry-distro-python/pull/254))
- Add independent dependency checks for the `httpx` and `httpx2` instrumentation entry points.
  ([#259](https://github.com/microsoft/opentelemetry-distro-python/pull/259))
- Update NOTICE to include the license declarations for external packages flagged in MPL review.
  ([#255](https://github.com/microsoft/opentelemetry-distro-python/pull/255))

# 1.3.8 (2026-08-20)
### Features Added
- Add support for agent identity propagation for compiled agents in nested graph
  ([#245](https://github.com/microsoft/opentelemetry-distro-python/pull/245))
- Add samples and documentation for LangChain special scenarios, including Foundry Responses API and nested graphs
  ([#249](https://github.com/microsoft/opentelemetry-distro-python/pull/249))
- Expose A365 offline storage options: `a365_exporter_disable_offline_storage` (default `False`)
  and `a365_exporter_storage_directory` (default `None`) on `use_microsoft_opentelemetry`,
  `Agent365ExporterOptions`, and `create_a365_components`.
  When `a365_enable_observability_exporter=True`, the exporter provides at-least-once delivery
  by persisting failed payloads to disk (up to 2 days / 50 MB) and replaying them on recovery.
  Set `a365_exporter_disable_offline_storage=True` to opt out.
  Stored payloads are unencrypted; restrict the storage path to the service account, especially
  when `enable_sensitive_data=True` (payloads may contain prompts or completions).
  Replay reconstructs the current HTTPS export endpoint and bearer token at send time rather
  than reusing a stale URL, permanently-rejected or malformed ("poison") records are discarded
  instead of retried forever, and `shutdown()` is drain-safe: it waits for any in-flight replay
  send to finish before closing the durable store and HTTP session (parity with `.NET` PR #137).
  ([#248](https://github.com/microsoft/opentelemetry-distro-python/pull/248))

### Other Changes
- Contribute Microsoft distro profile information (`component="mot"` and distro version) to the OneSettings control plane during `use_microsoft_opentelemetry()`.
  ([#244](https://github.com/microsoft/opentelemetry-distro-python/pull/244))
- Pin GitHub Actions to full-length commit SHAs
  ([#246](https://github.com/microsoft/opentelemetry-distro-python/pull/246))
- Apply formatting fixes across source and test files
  ([#241](https://github.com/microsoft/opentelemetry-distro-python/pull/241))

# 1.3.7 (2026-08-05)
### Features Added
- Mark `gen_ai.tool.description` and `gen_ai.tool.definitions` as sensitive attributes per [GenAI Spec](https://github.com/open-telemetry/semantic-conventions-genai/pull/431)
 ([#237](https://github.com/microsoft/opentelemetry-distro-python/pull/237))
- Respect RAPI headers in order to populate the `gen_ai.response.model` with the served model if available
  ([#234](https://github.com/microsoft/opentelemetry-distro-python/pull/234))
- Capture the agent's system prompt as the `gen_ai.system_instructions` span attribute in the LangChain instrumentation
  ([#232](https://github.com/microsoft/opentelemetry-distro-python/pull/232))

### Bugs Fixed
- Suppress duplicate `invoke_agent` spans for nested LangGraph agents that resolve to the same name as their agent ancestor
  ([#236](https://github.com/microsoft/opentelemetry-distro-python/pull/236))
- Parse Gemini token usage attributes and stop emitting legacy `gen_ai.tool.*` attributes on the chat span when both modern and legacy `tool_calls` are present
  ([#233](https://github.com/microsoft/opentelemetry-distro-python/pull/233))

# 1.3.6 (2026-07-22)

### Features Added
- Propagate the microsoft.foundry.project.id which the foundry SDK populates on the server spans
  ([#227](https://github.com/microsoft/opentelemetry-distro-python/pull/227))

### Bugs Fixed
- Gate sensitive data and I/O message attributes on child spans, fix `gen_ai.tool.call.arguments`, and related LangChain fixes
  ([#223](https://github.com/microsoft/opentelemetry-distro-python/pull/223))

# 1.3.5 (2026-07-01)

### Features Added
- Pass metrics observations to upstream SDKStats Manager
  ([#191](https://github.com/microsoft/opentelemetry-distro-python/pull/191))
- Enable sensitive data for LangChain programmatically
  ([#201](https://github.com/microsoft/opentelemetry-distro-python/pull/201))

### Bugs Fixed
- Add actionable 403 error message
  ([#213](https://github.com/microsoft/opentelemetry-distro-python/pull/213))
- Remove internal model/tool spans
  ([#212](https://github.com/microsoft/opentelemetry-distro-python/pull/212))

### Other Changes
- Update otel dependencies
  ([#218](https://github.com/microsoft/opentelemetry-distro-python/pull/218))
- Add pre-commit hook for auto-formatting
  ([#220](https://github.com/microsoft/opentelemetry-distro-python/pull/220))
- Remove specific co-code owners
  ([#221](https://github.com/microsoft/opentelemetry-distro-python/pull/221))
- Documentation improvements for published API reference
  ([#214](https://github.com/microsoft/opentelemetry-distro-python/pull/214))

# 1.3.4 (2026-06-17)

### Bugs Fixed
- Fix token count mismatch
  ([#195](https://github.com/microsoft/opentelemetry-distro-python/pull/195))
- Fix `microsoft.gen_ai.main_agent.*` propagation and self-promotion bugs
  ([#196](https://github.com/microsoft/opentelemetry-distro-python/pull/196))
- Comment out the OTLP wrapper
  ([#200](https://github.com/microsoft/opentelemetry-distro-python/pull/200))
- Fix `wrapt` dependency and change to positional arguments
  ([#204](https://github.com/microsoft/opentelemetry-distro-python/pull/204))

### Other Changes
- Remove distro word references
  ([#197](https://github.com/microsoft/opentelemetry-distro-python/pull/197))

# 1.3.3 (2026-06-08)

### Features Added
- Add `ContextualTokenResolver` with agentic user ID support
  ([#185](https://github.com/microsoft/opentelemetry-distro-python/pull/185))
- Network SdkStats: add request success count metric
  ([#144](https://github.com/microsoft/opentelemetry-distro-python/pull/144))
- Add remaining network sdkstats metrics for A365
  ([#192](https://github.com/microsoft/opentelemetry-distro-python/pull/192))

### Bugs Fixed
- Downgrade LangChain "not installed" log to DEBUG to silence stderr warnings for users not using LangChain
  ([#184](https://github.com/microsoft/opentelemetry-distro-python/pull/184))
- Fix LangGraph content-block serialization in `gen_ai.output.messages`
  ([#193](https://github.com/microsoft/opentelemetry-distro-python/pull/193))

### Other Changes
- ci(perf): post sticky comment for fork PRs via `workflow_run`
  ([#186](https://github.com/microsoft/opentelemetry-distro-python/pull/186))
- Refactor code to use upstream `SDKStatsManager`
  ([#182](https://github.com/microsoft/opentelemetry-distro-python/pull/182))
- Update docs with the contextual token resolver config
  ([#190](https://github.com/microsoft/opentelemetry-distro-python/pull/190))

# 1.3.2 (2026-05-29)

### Bugs Fixed
- Add an explicit `get_span_context` override on `EnrichedReadableSpan`
  ([#180](https://github.com/microsoft/opentelemetry-distro-python/pull/180))

### Other Changes
- Add GitHub Actions workflow for the `needs-author-feedback` label
  ([#178](https://github.com/microsoft/opentelemetry-distro-python/pull/178))

# 1.3.1 (2026-05-28)

### Features Added
- Add `ApplyGuardrailScope` for security guardrail evaluations
  ([#173](https://github.com/microsoft/opentelemetry-distro-python/pull/173))

### Bugs Fixed
- Fix `enable_sensitive_data` leaking to all instrumentors
  ([#176](https://github.com/microsoft/opentelemetry-distro-python/pull/176))
- Fix LangChain tracer main-agent attribute propagation timing
  ([#171](https://github.com/microsoft/opentelemetry-distro-python/pull/171))

### Other Changes
- Invoke-agent wrapper span now populates tool-call turns and `gen_ai.tool.definitions`
  ([#174](https://github.com/microsoft/opentelemetry-distro-python/pull/174))
- Add wheel build and artifact upload to PR validation
  ([#177](https://github.com/microsoft/opentelemetry-distro-python/pull/177))
- Add setter functions for feature and instrumentation bits
  ([#157](https://github.com/microsoft/opentelemetry-distro-python/pull/157))

## 1.3.0 (2026-05-27)

### Features Added
- Add circuit breaker to A365 exporter to prevent silent telemetry loss
  ([#153](https://github.com/microsoft/opentelemetry-distro-python/pull/153))
- Add token usage extraction for LangChain tracer
  ([#161](https://github.com/microsoft/opentelemetry-distro-python/pull/161))
- Add more GenAI attributes to LangChain tracer
  ([#156](https://github.com/microsoft/opentelemetry-distro-python/pull/156))
- Align message format to OTel spec: remove version envelope
  ([#162](https://github.com/microsoft/opentelemetry-distro-python/pull/162))

### Bugs Fixed
- Use `get_span_context()` instead of `.context` to support `NonRecordingSpan`
  ([#168](https://github.com/microsoft/opentelemetry-distro-python/pull/168))
- Use standard `gen_ai.conversation.id` instead of `microsoft.sessionid` in LangChain tracer
  ([#152](https://github.com/microsoft/opentelemetry-distro-python/pull/152))
- Emit OTel-spec structured messages on `invoke_agent` spans
  ([#164](https://github.com/microsoft/opentelemetry-distro-python/pull/164))
- Prevent OOM from unbounded dicts in LangChain tracer
  ([#154](https://github.com/microsoft/opentelemetry-distro-python/pull/154))
- Bump `agent-framework>=1.4.0` to resolve dependency conflict
  ([#155](https://github.com/microsoft/opentelemetry-distro-python/pull/155))
- Add 30s timeout to FIC token resolver MSAL calls
  ([#150](https://github.com/microsoft/opentelemetry-distro-python/pull/150))

### Other Changes
- Add project URLs to PyPI and fix broken relative links
  ([#169](https://github.com/microsoft/opentelemetry-distro-python/pull/169))
- Add pytest-benchmark suite and PR regression gate
  ([#165](https://github.com/microsoft/opentelemetry-distro-python/pull/165))
- Bump `mem0ai` from 1.0.11 to 2.0.0b2
  ([#163](https://github.com/microsoft/opentelemetry-distro-python/pull/163))

## 1.2.0 (2026-05-18)

### Features Added
- Forward `instrumentation_options` kwargs to instrumentors
  ([#149](https://github.com/microsoft/opentelemetry-distro-python/pull/149))
- Add A365-specific OpenAI Agents SDK instrumentor (`A365OpenAIAgentsInstrumentor`). When `enable_a365=True`, the distro uses this bundled instrumentor instead of the upstream `opentelemetry-instrumentation-openai-agents-v2`, producing spans with the A365 versioned envelope format, `custom.parent.span.id`, per-message indexed attributes, detailed token counts, and `graph_node_parent_id` for handoffs.
  ([#132](https://github.com/microsoft/opentelemetry-distro-python/pull/132))

### Bugs Fixed
- Fix duplicate chat spans and HTTP spans not propagating in LangChain
  ([#147](https://github.com/microsoft/opentelemetry-distro-python/pull/147))
- Revert: Fix `get_caller_pairs` userId fallback
  ([#141](https://github.com/microsoft/opentelemetry-distro-python/pull/141))
- Capitalize env var to avoid case-sensitive conflicts
  ([#137](https://github.com/microsoft/opentelemetry-distro-python/pull/137))
- Add product context fallback for subchannels
  ([#129](https://github.com/microsoft/opentelemetry-distro-python/pull/129))

### Other Changes
- Port Agent365 integration tests using real distro pipeline
  ([#146](https://github.com/microsoft/opentelemetry-distro-python/pull/146))
- Make `microsoft-agents-hosting-core` and `microsoft-agents-activity` optional dependencies
  ([#117](https://github.com/microsoft/opentelemetry-distro-python/pull/117))
- Pin genai util
  ([#145](https://github.com/microsoft/opentelemetry-distro-python/pull/145))
- Update telemetry SDK name to `microsoft-opentelemetry`
  ([#138](https://github.com/microsoft/opentelemetry-distro-python/pull/138))
- Update azure monitor exporter minimum version
  ([#136](https://github.com/microsoft/opentelemetry-distro-python/pull/136))

## 1.1.0 (2026-05-11)

### Features Added
- Add GenAI main-agent attribution processors
  ([#120](https://github.com/microsoft/opentelemetry-distro-python/pull/120))
- Add `enable_sensitive_data` parameter to configure sensitive data in Agent Framework
  ([#121](https://github.com/microsoft/opentelemetry-distro-python/pull/121))

### Bugs Fixed
- Fix `get_caller_pairs` to resolve `userId` across all channels
  ([#118](https://github.com/microsoft/opentelemetry-distro-python/pull/118))
- Fix response model not being set when using LangChain
  ([#116](https://github.com/microsoft/opentelemetry-distro-python/pull/116))

### Other Changes
- Add Agent Framework sample
  ([#122](https://github.com/microsoft/opentelemetry-distro-python/pull/122))
- Add auth scopes breaking change to A365 migration guide
  ([#123](https://github.com/microsoft/opentelemetry-distro-python/pull/123))
- Fix MIGRATION_A365.md documentation errors
  ([#109](https://github.com/microsoft/opentelemetry-distro-python/pull/109))
- Add issues template and notification actions
  ([#112](https://github.com/microsoft/opentelemetry-distro-python/pull/112))
- Promote new A365 owners
  ([#125](https://github.com/microsoft/opentelemetry-distro-python/pull/125))
- Add troubleshooting sections and duplicate spans guide
  ([#115](https://github.com/microsoft/opentelemetry-distro-python/pull/115))
- Drop support for Python 3.9.
  ([#110](https://github.com/microsoft/opentelemetry-distro-python/pull/110))
- Add Fabric/ADX getting started guide and sample.
  ([#104](https://github.com/microsoft/opentelemetry-distro-python/pull/104))
- Update A365 documentation and links.
  ([#101](https://github.com/microsoft/opentelemetry-distro-python/pull/101))
- Fix CODEOWNERS sub-owners.
  ([#103](https://github.com/microsoft/opentelemetry-distro-python/pull/103))

## 1.0.0 (2026-04-30)

### Features Added
- GA release of the Microsoft OpenTelemetry Distro for Python
- `use_microsoft_opentelemetry()` entry point for unified telemetry configuration
- Azure Monitor export with connection-string-based configuration
- OTLP export for traces, metrics, and logs
- A365 observability exporter with baggage propagation and scope override support
- GenAI instrumentations: OpenAI v2, OpenAI Agents SDK v2, LangChain (internal), Semantic Kernel, Microsoft Agent Framework
- Console exporter for local development and debugging
- SDK self-telemetry (sdkstats) for health and usage diagnostics
- Auto-instrumentation support via OpenTelemetry distro entry point
- Standard web-framework instrumentations (Django, FastAPI, Flask, httpx, requests, urllib, urllib3, psycopg2)
- Environment-variable-based configuration for all supported options
- Spectra Collector sidecar support with graceful fallback
- Browser SDK Loader integration for Azure Monitor
- Configurable instrumentation enablement via `instrumentation_options`
- Add documentation to include span filtering for console exporter traces

### Breaking Changes
- Package name is `microsoft-opentelemetry` (replaces all pre-release versions)
- `enable_azure_monitor` is off by default
- `tenant_id` and `agent_id` removed from configuration options
- Web-framework/HTTP-client instrumentations disabled by default when A365 is enabled; GenAI instrumentations remain enabled

## 0.1.0b3 (2026-04-29)

### Features Added
- Add configuration options for the `ENABLE_A365_OBSERVABILITY_EXPORTER` and `A365_OBSERVABILITY_SCOPE_OVERRIDE` environment variables
  ([#87](https://github.com/microsoft/opentelemetry-distro-python/pull/87))

### Bugs Fixed
- Reverted [#81](https://github.com/microsoft/opentelemetry-distro-python/pull/81): baggage propagation now requires `enable_a365=True` and respects `ENABLE_A365_OBSERVABILITY_EXPORTER` as before.
  ([#85](https://github.com/microsoft/opentelemetry-distro-python/pull/85))

### Other Changes
- Make `langchain-core` an optional dependency. The LangChain instrumentation
  is now installable via `pip install microsoft-opentelemetry[langchain]` and
  fails silently with a one-time warning when `langchain-core` is not
  installed.
  ([#80](https://github.com/microsoft/opentelemetry-distro-python/pull/80))


## 0.1.0b2 (2026-04-28)

### Bugs Fixed
- Ensure baggage properties propagate to child spans for all exporters
  ([#81](https://github.com/microsoft/opentelemetry-distro-python/pull/81))


## 0.1.0b1 (2026-04-27)

### Features Added

- Ensure baggage properties propagate to child spans when the console exporter is chosen and A365 exporter is disabled
  ([#74](https://github.com/microsoft/opentelemetry-distro-python/pull/74))
- Disable web-framework / HTTP-client instrumentations
  (`django`, `fastapi`, `flask`, `httpx`, `psycopg2`, `requests`, `urllib`, `urllib3`,
  `azure_sdk`) by default when A365 is enabled. GenAI instrumentations
  (`langchain`, `openai`, `openai_agents`, `semantic_kernel`,
  `agent_framework`) remain enabled. Users can override either default via
  `instrumentation_options`.
  ([#64](https://github.com/microsoft/opentelemetry-distro-python/pull/64))

### Bugs Fixed

- Fetch the distro version instead of the upstream core package
  ([#73](https://github.com/microsoft/opentelemetry-distro-python/pull/73))

## 0.1.0a4 (2026-04-24)

### Breaking Changes

- Remove tenant_id, agent_id from config options
  ([#59](https://github.com/microsoft/opentelemetry-distro-python/pull/59))

### Features Added

- `enable_azure_monitor` is off by default
  ([#60](https://github.com/microsoft/opentelemetry-distro-python/pull/60))
- Match Upstream Changes: Update scope value to support new exporter path
  ([#62](https://github.com/microsoft/opentelemetry-distro-python/pull/62))

## 0.1.0a3 (2026-04-22)

### Features Added

- Vendor A365 core observability code
  ([#47](https://github.com/microsoft/opentelemetry-distro-python/pull/47))
- Add agent framework and semantic kernel instrumentations
  ([#50](https://github.com/microsoft/opentelemetry-distro-python/pull/50))
- Add Spectra Collector sidecar support with graceful fallback
  ([#48](https://github.com/microsoft/opentelemetry-distro-python/pull/48))
- Add console exporter for traces, metrics, and logs
  ([#54](https://github.com/microsoft/opentelemetry-distro-python/pull/54))

## 0.1.0a2 (2026-04-20)

### Features Added

- Integrate A365 observability into distro
  ([#45](https://github.com/microsoft/opentelemetry-distro-python/pull/45))
- Support openai-v2 and openai-agents-v2
  ([#37](https://github.com/microsoft/opentelemetry-distro-python/pull/37))

### Other Changes

- Modify the logic to add providers when azure monitor config is disabled
  ([#24](https://github.com/microsoft/opentelemetry-distro-python/pull/24))


## 0.1.0a1 (2026-04-10)

### Features Added

- Add langchain instrumentation 
  ([#26](https://github.com/microsoft/opentelemetry-distro-python/pull/26))
- Add Microsoft Opentelemetry Distro Configuration
  ([#9](https://github.com/microsoft/opentelemetry-distro-python/pull/9))
- Add langchain samples
  ([#8](https://github.com/microsoft/opentelemetry-distro-python/pull/8))
- Add azure-monitor-opentelemetry distro source
  ([#7](https://github.com/microsoft/opentelemetry-distro-python/pull/7))
- Added `azure-monitor-opentelemetry` package source for Azure Monitor OpenTelemetry distro integration.
  ([#7](https://github.com/microsoft/opentelemetry-distro-python/pull/7))

### Other Changes

- Add support for local mypy, pylint, black checks
  ([#14](https://github.com/microsoft/opentelemetry-distro-python/pull/14))
- Add mypy and pyright checks
  ([#15](https://github.com/microsoft/opentelemetry-distro-python/pull/15))
- Fix lint and format on langchain samples
  ([#16](https://github.com/microsoft/opentelemetry-distro-python/pull/16))
- Update max length to 120
  ([#17](https://github.com/microsoft/opentelemetry-distro-python/pull/17))
- Add environment variables to README
  ([#12](https://github.com/microsoft/opentelemetry-distro-python/pull/12))
- Add PR build
  ([#10](https://github.com/microsoft/opentelemetry-distro-python/pull/10))
- Microsoft mandatory file
  ([#2](https://github.com/microsoft/opentelemetry-distro-python/pull/2))
