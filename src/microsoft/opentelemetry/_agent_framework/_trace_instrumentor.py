# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import annotations

import logging
from collections.abc import Collection
from typing import Any

from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import (
    register_span_enricher,
    unregister_span_enricher,
)
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore[attr-defined]
from opentelemetry.trace import get_tracer_provider

from microsoft.opentelemetry._agent_framework._span_enricher import enrich_agent_framework_span
from microsoft.opentelemetry._agent_framework._span_processor import AgentFrameworkSpanProcessor

_logger = logging.getLogger(__name__)
_instruments = ("agent-framework >= 1.0.0",)


class AgentFrameworkInstrumentor(BaseInstrumentor):
    """Instruments Agent Framework with Agent365 observability."""

    _processor: AgentFrameworkSpanProcessor | None = None
    _owns_enricher: bool = False

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs: Any) -> None:
        provider = kwargs.get("tracer_provider") or get_tracer_provider()

        self._processor = AgentFrameworkSpanProcessor()
        provider.add_span_processor(self._processor)  # type: ignore[union-attr, attr-defined]

        try:
            register_span_enricher(enrich_agent_framework_span)
            self._owns_enricher = True
        except RuntimeError:
            _logger.debug("A span enricher is already registered. Skipping Agent Framework enricher registration.")

    def _uninstrument(self, **kwargs: Any) -> None:
        if self._owns_enricher:
            unregister_span_enricher()
            self._owns_enricher = False

        if self._processor is not None:
            self._processor.shutdown()
