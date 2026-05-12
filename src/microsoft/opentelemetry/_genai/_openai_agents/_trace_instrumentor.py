# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""A365 instrumentor for OpenAI Agents SDK.

This instrumentor registers the A365-specific ``OpenAIAgentsTraceProcessor``
with the OpenAI Agents SDK tracing system. It produces spans with the A365
versioned message format and additional attributes (``custom.parent.span.id``,
per-message indexed attributes, etc.) that A365 consumers rely on.

When A365 is enabled, this instrumentor is used **instead of** the upstream
``opentelemetry-instrumentation-openai-agents-v2`` for the A365 exporter
pipeline. The upstream instrumentor continues to handle Azure Monitor and
OTLP export.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from typing import Any

import opentelemetry.trace as trace_api
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore[attr-defined]

from ._trace_processor import OpenAIAgentsTraceProcessor

logger = logging.getLogger(__name__)

_instruments = ("openai-agents >= 0.0.7",)


class A365OpenAIAgentsInstrumentor(BaseInstrumentor):
    """Instruments the OpenAI Agents SDK with A365-compatible tracing.

    Registers an ``OpenAIAgentsTraceProcessor`` that emits spans in the
    format expected by A365 dashboards, Spectra, and observability exporters.
    """

    _processor: OpenAIAgentsTraceProcessor | None = None

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs: Any) -> None:
        if self._processor is not None:
            return

        tracer_provider = kwargs.get("tracer_provider")
        tracer = trace_api.get_tracer(
            __name__,
            tracer_provider=tracer_provider,
        )

        self._processor = OpenAIAgentsTraceProcessor(tracer)

        try:
            from agents.tracing import get_trace_provider

            provider = get_trace_provider()
            # Get existing processors to avoid replacing them
            multi = getattr(provider, "_multi_processor", None)
            existing = list(getattr(multi, "_processors", ()))
            provider.set_processors([*existing, self._processor])
        except Exception:  # pylint: disable=broad-exception-caught
            # Fallback: use set_trace_processors (replaces all processors)
            try:
                from agents import set_trace_processors

                set_trace_processors([self._processor])
            except ImportError:
                logger.warning(
                    "Could not register A365 OpenAI Agents trace processor. "
                    "Neither agents.tracing.get_trace_provider nor "
                    "agents.set_trace_processors is available."
                )

    def _uninstrument(self, **kwargs: Any) -> None:
        if self._processor is None:
            return

        try:
            from agents.tracing import get_trace_provider

            provider = get_trace_provider()
            multi = getattr(provider, "_multi_processor", None)
            current = list(getattr(multi, "_processors", ()))
            filtered = [p for p in current if p is not self._processor]
            provider.set_processors(filtered)
        except Exception:  # pylint: disable=broad-exception-caught
            try:
                from agents import set_trace_processors

                set_trace_processors([])
            except ImportError:
                pass

        self._processor = None
