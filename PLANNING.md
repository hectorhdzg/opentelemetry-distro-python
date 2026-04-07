# Planning

This document captures the minimum work needed to turn this repository into a working Python distribution for Microsoft OpenTelemetry based on the referenced POC.

## Target Outcome

Provide a Python package that exposes a single `use_microsoft_opentelemetry()` entry point and can wire together:

- Azure Monitor export
- OTLP export
- Microsoft-specific exporter and span enrichment hooks
- optional GenAI instrumentations
- environment-variable based configuration

## Timeline

| Milestone | Target Date |
|-----------|-------------|
| **1.0.0-alpha** | April 20, 2026 |
| **1.0.0-beta** | April 28, 2026 |
| **1.0.0** | May 2026 |

Phases 1–8 must be completed before the 1.0.0 release. Optional phases (9–10) can be worked on after the May 2026 release.

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

## Phase 4: Core OpenTelemetry Setup (This Package)

- Use the in-repo Azure Monitor code directly for provider creation and standard instrumentation
- When Azure Monitor export is requested, attach the Azure Monitor exporter using the migrated code
- When Azure Monitor export is not requested, create providers without the exporter (now trivial since the code is in-repo)
- Add OTLP export for traces, logs, and metrics on top of the providers
- Add hooks for custom span processors, log processors, metric readers, and views
- Add sampling configuration support

## Phase 5: Additional Instrumentation (This Package Only)

### GenAI Semantic Conventions Reference

All GenAI instrumentations in this package (both direct dependencies and internal implementations) must conform to the **OpenTelemetry Semantic Conventions for Generative AI**: https://opentelemetry.io/docs/specs/semconv/gen-ai/

- The current semantic conventions version at time of writing is **v1.40.0**
- Version **v1.36.0** is the breaking-change boundary — instrumentations written against v1.36.0 or prior should use `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` to opt into the latest conventions
- This package should target the **latest experimental GenAI conventions** (post-v1.36.0) and update as new versions are released
- When evaluating upstream instrumentations for adoption, verify they target the same conventions version we do — do not adopt instrumentations still emitting v1.36.0 or older attributes/spans

### GenAI Instrumentations

- Add GenAI instrumentations:
  - OpenAI instrumentation from `opentelemetry-instrumentation-openai` (contrib) — **direct dependency**
  - OpenAI Agents SDK v2 instrumentation from `opentelemetry-instrumentation-openai-agents` (contrib) — **direct dependency**
  - LangChain instrumentation — **internal implementation in this repo** (see below)
- Do NOT include Traceloop instrumentations (these use the `opentelemetry` namespace but are not official OpenTelemetry contrib packages)
- Do NOT include Arize instrumentations as direct dependencies
- Standard Python instrumentations (Flask, Django, FastAPI, requests, urllib, etc.) are provided by the in-repo Azure Monitor code — do NOT reimplement them in a separate layer
- Decide whether GenAI instrumentations are hard dependencies or optional extras
- Make instrumentation enablement explicit and debuggable

### Internal LangChain Instrumentation

Upstream OpenTelemetry contrib does not yet publish a LangChain instrumentation to PyPI. Rather than wait, we will build an internal LangChain instrumentation in this repository as a hybrid of three sources:

1. **A365 LangChain instrumentation** — existing internal instrumentation used in A365 agent observability scenarios
2. **OpenTelemetry contrib LangChain instrumentation** — the unreleased/in-progress instrumentation from the OpenTelemetry Python contrib repository
3. **Azure LangChain SDK observability** — the observability hooks and tracing surface from the Azure LangChain SDK

Design guidelines for the internal instrumentation:

- Conform to the GenAI Semantic Conventions Reference defined above
- Structure the code as a standard OpenTelemetry instrumentor (implement `BaseInstrumentor`) so it can be swapped out cleanly
- Keep the instrumentation in a clearly marked internal module (e.g., `_langchain/`) with explicit documentation that it is temporary
- Migration to the upstream OpenTelemetry contrib LangChain instrumentation should only happen when **all** of the following criteria are met:
  1. The upstream package is published to PyPI
  2. The upstream instrumentation follows the **latest** OpenTelemetry GenAI semantic conventions (not an outdated or draft version)
  3. The upstream instrumentation is functionally mature and in good shape (stable API, reasonable test coverage, no critical open bugs)
- Simply being available on PyPI is not sufficient — an upstream instrumentation that uses outdated semantic conventions or has significant quality gaps should not replace the internal version
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
- Audit migrated A365 instrumentations and determine which can be contributed to upstream OpenTelemetry contrib — for those with existing upstream equivalents, plan a migration path and deprecation timeline; for those with no upstream equivalent (e.g., Microsoft Agent Framework), keep as Microsoft-specific extensions and evaluate contributing them
- Validate that existing A365 telemetry pipelines continue to work under the new distro setup with the in-repo code
- Coordinate with the A365 team on dual maintenance during the transition period (similar to the Azure Monitor Distro approach)

## Phase 7: Integration and End-to-End Testing

Unit tests are expected to be written alongside every phase — each phase must include comprehensive unit test coverage for its own code. This phase focuses exclusively on integration and end-to-end tests that validate cross-phase interactions and full pipeline behavior.

- Integration tests for the full `use_microsoft_opentelemetry()` setup across exporter combinations (Azure Monitor only, OTLP only, A365 only, all combined)
- End-to-end tests that verify telemetry flows from instrumented code through providers, processors, and exporters to a mock backend
- Integration tests for configuration interactions (e.g., enabling A365 + Azure Monitor together, conflicting environment variables, exporter-optional paths)
- End-to-end tests for auto-instrumentation scenarios (distro entry point wires everything correctly)
- Integration tests for GenAI instrumentations producing expected spans through the full pipeline
- End-to-end tests for sdkstats emitting self-telemetry across different transport backends (if Phase 9 is implemented)
- Integration tests for graceful degradation when optional dependencies are missing at runtime
- Smoke tests for the public import path and basic configuration call
- End-to-end sample-app-based tests that exercise the sample applications from Phase 8 as validation fixtures

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

---

## Optional Phases

The following phases are not required for the 1.0.0 release and can be worked on after the May 2026 timeline. They provide additional value and can be prioritized independently based on customer demand.

## Phase 9 (Optional): SDKStats (SdkStats) Decoupling

The SDK self-telemetry feature (sdkstats) currently lives in the Azure Monitor Exporter package (`azure.monitor.opentelemetry.exporter.statsbeat`) and is only active when the Azure Monitor Exporter is configured. This creates a gap for customers who use the distro exclusively for A365 scenarios — they lose SDK health and usage telemetry because sdkstats is never initialized without the Azure Monitor export path.

### Goal

Provide SDK self-telemetry (sdkstats) as a standalone capability that works regardless of which export backends are enabled, so A365-only customers still get SDK usage metrics, error rates, and health diagnostics.

### Work Items

- Migrate the core sdkstats logic into this repository under a backend-agnostic internal module (e.g., `_statsbeat/`)
- Decouple sdkstats initialization from the Azure Monitor Exporter — it should be triggered by the distro setup regardless of which exporters are active
- Define a pluggable transport layer so sdkstats data can be emitted to different backends:
  - Azure Monitor ingestion (current behavior, for customers using Azure Monitor)
  - A365 telemetry pipeline (for A365-only customers)
  - OTLP endpoint (for customers using only OTLP export)
- Preserve backward compatibility: when Azure Monitor Exporter is present, sdkstats should behave identically to the current implementation
- Ensure sdkstats tracks usage metrics relevant to all enabled features (A365 exporter, OTLP export, GenAI instrumentations) — not just Azure Monitor-specific features
- Update the browser SDK loader sdkstats integration (`_browser_sdk_loader/snippet_injector.py`) to use the in-repo sdkstats module instead of importing from the exporter package
- Add configuration options to control sdkstats behavior:
  - Enable/disable sdkstats globally
  - Select sdkstats transport backend(s)
  - Configure sdkstats endpoint when not using the default Azure Monitor ingestion
- Validate that existing Azure Monitor sdkstats consumers see no behavioral change after the migration
- Coordinate with the Azure Monitor Exporter team on deprecation of the sdkstats module in the exporter package once the in-repo version is stable

## Phase 10 (Optional): External Instrumentation Normalization

- Define a normalization layer that can consume telemetry from third-party GenAI instrumentations (Traceloop, Arize, etc.) and align it to the expected semantic conventions
- Map external instrumentation span attributes and naming to OpenTelemetry GenAI semantic conventions
- Provide adapters or processors that normalize non-standard telemetry without taking a direct dependency on external instrumentation packages
- Document which external instrumentations are supported for normalization and any known gaps

