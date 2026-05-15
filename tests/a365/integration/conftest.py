# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# pylint: disable=redefined-outer-name

"""Shared fixtures for A365 integration tests.

Uses ``use_microsoft_opentelemetry(enable_a365=True)`` so tests exercise
the real distro pipeline: providers, baggage propagation, auto-instrumentation,
span enrichment — exactly as production code would.
"""

import os
import typing
from pathlib import Path
from typing import Any

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import get_tracer_provider

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv

    current_file = Path(__file__)
    repo_root = current_file.parent.parent.parent.parent
    env_file = repo_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# Ensure A365 observability scopes are active for tests
os.environ["ENABLE_A365_OBSERVABILITY"] = "true"


class SpanCapturingExporter(SpanExporter):
    """In-memory exporter that collects spans after enrichment.

    When wired behind ``_EnrichingBatchSpanProcessor``, spans arrive
    here after the registered enricher has run — matching the real
    A365 export path without sending data to a real endpoint.
    """

    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def pytest_configure(config: pytest.Config) -> None:
    """Add integration marker."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture(scope="session")
def azure_openai_config() -> dict[str, Any]:
    """Azure OpenAI configuration for integration tests."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    if not api_key or not endpoint:
        pytest.skip("Integration tests require AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")

    return {
        "api_key": api_key,
        "endpoint": endpoint,
        "deployment": deployment,
        "api_version": api_version,
    }


@pytest.fixture(scope="session")
def agent365_config() -> dict[str, Any]:
    """Microsoft Agent 365 configuration for integration tests."""
    tenant_id = os.getenv("AGENT365_TEST_TENANT_ID", "4d44f041-f91e-4d00-b107-61e47b26f5a8")
    agent_id = os.getenv("AGENT365_TEST_AGENT_ID", "3bccd52b-daaa-4b11-af40-47443852137c")

    if not tenant_id:
        pytest.skip("Integration tests require AGENT365_TEST_TENANT_ID")

    return {"tenant_id": tenant_id, "agent_id": agent_id}


@pytest.fixture(scope="session")
def distro_exporter() -> SpanCapturingExporter:
    """Configure the distro once per session and return the capturing exporter.

    Calls ``use_microsoft_opentelemetry(enable_a365=True, ...)`` which:
    - Creates and registers global TracerProvider / MeterProvider / LoggerProvider
    - Adds A365SpanProcessor for baggage-to-attribute propagation
    - Auto-instruments openai_agents, agent_framework, langchain (via entry points)
    - Sets ``OpenTelemetryScope._enabled_by_distro = True``

    Then adds an ``_EnrichingBatchSpanProcessor(SpanCapturingExporter())``
    to capture spans **after** enrichment, matching the real export path.
    """
    from microsoft.opentelemetry import use_microsoft_opentelemetry
    from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import (
        _EnrichingBatchSpanProcessor,
    )

    exporter = SpanCapturingExporter()

    use_microsoft_opentelemetry(
        enable_a365=True,
        enable_sensitive_data=True,
    )

    # Add a capturing enriching processor after the distro call so
    # we see spans exactly as the real A365 exporter would.
    provider = get_tracer_provider()
    provider.add_span_processor(  # type: ignore[union-attr]
        _EnrichingBatchSpanProcessor(
            exporter,
            max_queue_size=100,
            schedule_delay_millis=100,
            max_export_batch_size=100,
        )
    )

    return exporter


@pytest.fixture(autouse=True)
def _clear_captured_spans(distro_exporter: SpanCapturingExporter) -> None:
    """Flush pending spans and clear the exporter before each test."""
    provider = get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush()
    distro_exporter.spans.clear()
