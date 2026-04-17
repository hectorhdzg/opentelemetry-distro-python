# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Enriched ReadableSpan wrapper for adding attributes to immutable spans.

Vendored from microsoft-agents-a365-observability-core exporters/enriched_span.py.
"""

from __future__ import annotations

from typing import Any, Optional, Set

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.util import types

# mypy: disable-error-code="no-untyped-def"

# pylint:disable=super-init-not-called
class EnrichedReadableSpan(ReadableSpan):
    """Wrapper to add attributes to an immutable ReadableSpan.

    Since ReadableSpan is immutable after a span ends, this wrapper allows
    extensions to add additional attributes before export without modifying
    the original span.
    """

    def __init__(
        self,
        span: ReadableSpan,
        extra_attributes: dict[str, Any],
        excluded_attribute_keys: Optional[Set[str]] = None,
    ):
        self._span = span
        self._extra_attributes = extra_attributes
        self._excluded_attribute_keys = excluded_attribute_keys or set()

    @property
    def attributes(self) -> types.Attributes:
        """Return merged attributes from original span and extra attributes."""
        original = dict(self._span.attributes or {})
        original.update(self._extra_attributes)
        for key in self._excluded_attribute_keys:
            original.pop(key, None)
        return original

    @property
    def name(self):  # type: ignore[override]
        return self._span.name

    @property
    def context(self):  # type: ignore[override]
        return self._span.context

    @property
    def parent(self):  # type: ignore[override]
        return self._span.parent

    @property
    def start_time(self):  # type: ignore[override]
        return self._span.start_time

    @property
    def end_time(self):  # type: ignore[override]
        return self._span.end_time

    @property
    def status(self):  # type: ignore[override]
        return self._span.status

    @property
    def kind(self):  # type: ignore[override]
        return self._span.kind

    @property
    def events(self):  # type: ignore[override]
        return self._span.events

    @property
    def links(self):  # type: ignore[override]
        return self._span.links

    @property
    def resource(self):  # type: ignore[override]
        return self._span.resource

    @property
    def instrumentation_scope(self):  # type: ignore[override]
        return self._span.instrumentation_scope
