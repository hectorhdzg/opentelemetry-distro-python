# Planning

This document captures the minimum work needed to turn this repository into a working Python distribution for Microsoft OpenTelemetry based on the referenced POC.

## Target Outcome

Provide a Python package that exposes a single `use_microsoft_opentelemetry()` entry point and can wire together:

- Azure Monitor export
- OTLP export
- Microsoft-specific exporter and span enrichment hooks
- optional GenAI instrumentations
- environment-variable based configuration

## Core Strategy: Migrate Azure Monitor Distro Code In-Repo

The team owns both this package and the Azure Monitor OpenTelemetry Distro (`azure-monitor-opentelemetry`). Rather than depending on the published PyPI package and coordinating upstream changes, we will **migrate the Azure Monitor OpenTelemetry code directly into this repository**. This allows rapid iteration on new features and bug fixes without waiting on separate release cycles for the Azure Monitor Distro.

Key principles:

- **In-repo copy of Azure Monitor OpenTelemetry.** The relevant code from `azure-monitor-opentelemetry` is vendored/migrated into this repository so it can be modified freely alongside the Microsoft distro code.
- **Dual maintenance during transition.** Both the standalone `azure-monitor-opentelemetry` PyPI package and the in-repo copy will be maintained in parallel for a period. Bug fixes and new features should be applied to both until the standalone package is deprecated or consumers have migrated.
- **Direct control over customization.** With the code in-repo, customization hooks (exporter-optional setup, provider exposure, instrumentation enablement) can be implemented directly without requiring upstream PRs and coordinated releases.
- **Composition with full flexibility.** The `use_microsoft_opentelemetry()` function can directly wire provider creation, standard instrumentation, and exporter attachment using the in-repo Azure Monitor code, then layer on Microsoft-specific capabilities (OTLP export, GenAI instrumentations, agent observability extensions).
- **Path to single package.** Over time, the in-repo code becomes the authoritative source and the standalone Azure Monitor Distro package can either be deprecated or become a thin wrapper that re-exports from this package.

### Dual Maintenance Guidelines

- Any bug fix applied to the in-repo Azure Monitor code must also be backported to the standalone `azure-monitor-opentelemetry` repository (and vice versa) until the transition is complete
- Keep a clear mapping between in-repo modules and their upstream counterparts to simplify cherry-picks
- Define a cutover milestone after which new features land only in this repository
- Existing users of the standalone `azure-monitor-opentelemetry` package must not be broken — deprecation notices and migration guides will be provided before any removal

## Phase 1: Package Foundation

- ~~Finalize the published package name and import path~~ — **Decided: `microsoft-opentelemetry` on PyPI**
- Decide whether the public import should be `microsoft.opentelemetry` or a repo-local transitional name
- Supported Python versions follow the OpenTelemetry SDK/API supported versions — no independent decision needed
- Add package metadata, classifiers, and Python version constraints matching OpenTelemetry
- Add lint, format, and test tooling
- Add CI for unit tests and package validation

## Phase 2: Configuration Surface

- Define the `use_microsoft_opentelemetry()` function signature
- Mirror the POC options that are core to the distro story
- Separate stable public options from experimental ones
- Add environment-variable parsing for all supported flags and endpoints
- Define validation and error messages for incompatible options

### Configuration Scoping

Each configuration option must be clearly identified by scope so consumers know which options are relevant to their scenario:

- **Global** — Options that apply to all setups regardless of backend (e.g., sampling rate, resource attributes, instrumentation enablement, log level, Python-level OTel settings)
- **Azure Monitor** — Options specific to Azure Monitor export and behavior (e.g., connection string, live metrics, browser SDK loader, Azure Monitor-specific processors)
- **A365** — Options specific to A365 agent observability (e.g., A365 exporter endpoint, baggage extensions, Microsoft Agent Framework instrumentation toggles, A365-specific span processors)
- **OTLP** — Options specific to OTLP export (e.g., OTLP endpoint, protocol, headers, compression)

Design guidelines:

- Use clear naming conventions or prefixes to signal scope (e.g., `azure_monitor_*`, `a365_*`, `otlp_*` for scoped options; no prefix for global)
- Environment variables should follow the same scoping convention (e.g., `MICROSOFT_OTEL_AZURE_MONITOR_*`, `MICROSOFT_OTEL_A365_*`)
- Validation should warn when scope-specific options are set but the corresponding backend/feature is not enabled
- Documentation and help text for each option must state its scope

## Phase 3: Azure Monitor Code Migration

- Migrate the relevant Azure Monitor OpenTelemetry Distro code into this repository under a well-defined module boundary
- Refactor the migrated code to support exporter-optional setup (skip automatic Azure Monitor exporter attachment when not needed)
- Expose provider instances (TracerProvider, MeterProvider, LoggerProvider) after setup so the distro can add exporters
- Ensure instrumentation enablement can be driven by the distro configuration without pulling in Azure Monitor-specific export
- Validate that the migrated code produces identical behavior to the standalone `azure-monitor-opentelemetry` package
- Establish a synchronization process for backporting fixes between this repo and the standalone package during the dual-maintenance period

## Phase 4: Core OpenTelemetry Setup (This Package)

- Use the in-repo Azure Monitor code directly for provider creation and standard instrumentation
- When Azure Monitor export is requested, attach the Azure Monitor exporter using the migrated code
- When Azure Monitor export is not requested, create providers without the exporter (now trivial since the code is in-repo)
- Add OTLP export for traces, logs, and metrics on top of the providers
- Add hooks for custom span processors, log processors, metric readers, and views
- Add sampling configuration support

## Phase 5: Additional Instrumentation (This Package Only)

- Add GenAI instrumentations:
  - OpenAI instrumentation from `opentelemetry-instrumentation-openai` (contrib) — **direct dependency**
  - OpenAI Agents SDK v2 instrumentation from `opentelemetry-instrumentation-openai-agents` (contrib) — **direct dependency**
  - LangChain instrumentation — **internal implementation in this repo** (see below)
- Do NOT include Traceloop instrumentations (these use the `opentelemetry` namespace but are not official OpenTelemetry contrib packages)
- Do NOT include Arize instrumentations as direct dependencies
- Add Microsoft-specific observability extensions for agent workloads
- Standard Python instrumentations (Flask, Django, FastAPI, requests, urllib, etc.) are provided by the in-repo Azure Monitor code — do NOT reimplement them in a separate layer
- Decide whether GenAI instrumentations are hard dependencies or optional extras
- Make instrumentation enablement explicit and debuggable

### Internal LangChain Instrumentation

Upstream OpenTelemetry contrib does not yet publish a LangChain instrumentation to PyPI. Rather than wait, we will build an internal LangChain instrumentation in this repository as a hybrid of three sources:

1. **A365 LangChain instrumentation** — existing internal instrumentation used in A365 agent observability scenarios
2. **OpenTelemetry contrib LangChain instrumentation** — the unreleased/in-progress instrumentation from the OpenTelemetry Python contrib repository
3. **Azure LangChain SDK observability** — the observability hooks and tracing surface from the Azure LangChain SDK

Design guidelines for the internal instrumentation:

- Follow OpenTelemetry GenAI semantic conventions so the output is compatible with any OTel-compliant backend
- Structure the code as a standard OpenTelemetry instrumentor (implement `BaseInstrumentor`) so it can be swapped out cleanly
- Keep the instrumentation in a clearly marked internal module (e.g., `_langchain/`) with explicit documentation that it is temporary
- When the upstream OpenTelemetry contrib LangChain instrumentation is published to PyPI, migrate to it and deprecate the internal version
- Track upstream progress and maintain a checklist of gaps between the internal implementation and the contrib version


## Phase 6: A365 Convergence

The A365 observability runtime will be **migrated as code into this repository**, not consumed as a PyPI dependency. This includes the A365 exporter, custom processors, and all relevant observability extensions.

### A365 Code to Migrate In-Repo

- **A365 exporter** — integrate into the distro configuration surface as an in-repo module
- **Microsoft Agent Framework instrumentation** — instrumentation for Microsoft's internal agent framework, brought in as source code
- **Baggage extensions** — A365 baggage propagation and enrichment extensions
- **Custom span processors** — processors required by A365 agent observability scenarios
- **Other internal observability extensions** — any remaining A365 runtime components needed for agent workloads

### Migration and Convergence Plan

- Migrate A365 observability runtime code under a clearly defined internal module boundary (e.g., `_a365/`)
- The A365 LangChain instrumentation is partially consumed in Phase 5 as one of the sources for the internal LangChain instrumentation — coordinate with the A365 team to avoid divergence
- Audit migrated A365 instrumentations and determine which can be contributed to upstream OpenTelemetry contrib
- For instrumentations that have OpenTelemetry equivalents, plan migration path and deprecation timeline
- For instrumentations with no upstream equivalent (e.g., Microsoft Agent Framework), keep as Microsoft-specific extensions in this repo and evaluate contributing them to OpenTelemetry
- Validate that existing A365 telemetry pipelines continue to work under the new distro setup with the in-repo code
- Coordinate with the A365 team on dual maintenance during the transition period (similar to the Azure Monitor Distro approach)

## Phase 7: Testing

- Unit tests for configuration parsing and defaults
- Unit tests for exporter and instrumentation enablement combinations
- Tests for environment-variable driven setup
- Tests for missing optional dependencies and graceful failures
- Smoke tests for the public import path and basic configuration call

## Phase 8: Documentation and Sample Apps

- Add quick start examples for Azure Monitor only, OTLP only, and combined setups
- Document supported parameters and environment variables
- Document optional dependency groups if extras are used
- Document troubleshooting for missing dependencies and duplicate instrumentation
- Add migration guidance from manual OpenTelemetry setup

### Sample Applications

Provide runnable sample apps covering the main scenarios:

- **Azure Monitor + Web App** — Flask or FastAPI app exporting to Azure Monitor (traces, metrics, logs)
- **OTLP + Web App** — Web app exporting via OTLP to a local collector or backend
- **Azure Monitor + OTLP combined** — Dual-export setup showing both backends simultaneously
- **OpenAI Agents** — App using OpenAI Agents SDK v2 with agent observability enabled
- **LangChain** — App using LangChain with the internal instrumentation
- **A365 agent workload** — Sample demonstrating A365 exporter, Microsoft Agent Framework instrumentation, and baggage extensions
- **GenAI multi-framework** — App combining multiple GenAI instrumentations (e.g., OpenAI + LangChain)

## Phase 9: External Instrumentation Normalization

- Define a normalization layer that can consume telemetry from third-party GenAI instrumentations (Traceloop, Arize, etc.) and align it to the expected semantic conventions
- Map external instrumentation span attributes and naming to OpenTelemetry GenAI semantic conventions
- Provide adapters or processors that normalize non-standard telemetry without taking a direct dependency on external instrumentation packages
- Document which external instrumentations are supported for normalization and any known gaps

