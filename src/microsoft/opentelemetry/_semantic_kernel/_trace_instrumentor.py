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

from microsoft.opentelemetry._semantic_kernel._span_enricher import enrich_semantic_kernel_span
from microsoft.opentelemetry._semantic_kernel._span_processor import SemanticKernelSpanProcessor

_logger = logging.getLogger(__name__)
_instruments = ("semantic-kernel >= 1.0.0",)


class SemanticKernelInstrumentor(BaseInstrumentor):
    """Instruments Semantic Kernel with Agent365 observability."""

    _processor: SemanticKernelSpanProcessor | None = None
    _owns_enricher: bool = False

    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs: Any) -> None:
        provider = kwargs.get("tracer_provider") or get_tracer_provider()

        self._processor = SemanticKernelSpanProcessor()
        provider.add_span_processor(self._processor)  # type: ignore[union-attr, attr-defined]

        try:
            register_span_enricher(enrich_semantic_kernel_span)
            self._owns_enricher = True
        except RuntimeError:
            _logger.debug("A span enricher is already registered. Skipping Semantic Kernel enricher registration.")

    def _uninstrument(self, **kwargs: Any) -> None:
        if self._owns_enricher:
            unregister_span_enricher()
            self._owns_enricher = False

        if self._processor is not None:
            self._processor.shutdown()
