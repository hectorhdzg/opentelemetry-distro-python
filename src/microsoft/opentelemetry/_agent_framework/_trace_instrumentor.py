# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import annotations

import logging
from collections.abc import Collection
from typing import Any

from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore[attr-defined]
from opentelemetry.trace import get_tracer_provider

from microsoft.opentelemetry._agent_framework._span_processor import AgentFrameworkSpanProcessor

_logger = logging.getLogger(__name__)
_instruments = ("agent-framework >= 1.0.0",)


class AgentFrameworkInstrumentor(BaseInstrumentor):
    """Instruments Agent Framework with OpenTelemetry observability.

    Automatically calls ``agent_framework.observability.enable_instrumentation()``
    so the Agent Framework SDK emits OpenTelemetry spans. When the A365 span
    enricher pipeline is available, also registers a span enricher for
    attribute normalization.
    """

    _processor: AgentFrameworkSpanProcessor | None = None
    _owns_enricher: bool = False
    _af_instrumentation_enabled: bool = False

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs: Any) -> None:
        # Enable the Agent Framework SDK's built-in span generation so users
        # don't need to call enable_instrumentation() manually.
        try:
            from agent_framework.observability import enable_instrumentation

            enable_instrumentation()
            self._af_instrumentation_enabled = True
        except ImportError as exc:
            _logger.debug(
                "Failed to import Agent Framework SDK instrumentation components. "
                + "Skipping Agent Framework SDK instrumentation enablement.",
                exc_info=exc,
            )

        provider = kwargs.get("tracer_provider") or get_tracer_provider()

        self._processor = AgentFrameworkSpanProcessor()
        provider.add_span_processor(self._processor)  # type: ignore[union-attr, attr-defined]

        # Register the A365 span enricher when the A365 pipeline is available.
        try:
            from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import register_span_enricher
            from microsoft.opentelemetry._agent_framework._span_enricher import enrich_agent_framework_span

            register_span_enricher(enrich_agent_framework_span)
            self._owns_enricher = True
        except ImportError:
            _logger.debug("A365 enricher modules not available. Skipping enricher registration.")
        except RuntimeError:
            _logger.debug("A span enricher is already registered. Skipping Agent Framework enricher registration.")

    def _uninstrument(self, **kwargs: Any) -> None:
        if self._owns_enricher:
            try:
                from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import (
                    unregister_span_enricher,
                )

                unregister_span_enricher()
            except ImportError:
                pass
            self._owns_enricher = False

        if self._processor is not None:
            self._processor.shutdown()
