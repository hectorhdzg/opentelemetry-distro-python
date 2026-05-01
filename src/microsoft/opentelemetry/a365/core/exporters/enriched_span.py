# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Enriched ReadableSpan wrapper for adding attributes to immutable spans.

Vendored from microsoft-agents-a365-observability-core exporters/enriched_span.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
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

    def to_json(self, indent: int | None = 4) -> str:
        """Convert span to JSON string with enriched attributes.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string representation of the span.
        """
        return json.dumps(
            {
                "name": self.name,
                "context": (
                    {
                        "trace_id": f"0x{self.context.trace_id:032x}",
                        "span_id": f"0x{self.context.span_id:016x}",
                        "trace_state": str(self.context.trace_state),
                    }
                    if self.context
                    else None
                ),
                "kind": str(self.kind),
                "parent_id": f"0x{self.parent.span_id:016x}" if self.parent else None,
                "start_time": self._format_time(self.start_time),
                "end_time": self._format_time(self.end_time),
                "status": (
                    {
                        "status_code": str(self.status.status_code),
                        "description": self.status.description,
                    }
                    if self.status
                    else None
                ),
                "attributes": dict(self.attributes) if self.attributes else None,
                "events": [self._format_event(e) for e in self.events] if self.events else None,
                "links": [self._format_link(lnk) for lnk in self.links] if self.links else None,
                "resource": dict(self.resource.attributes) if self.resource else None,
            },
            indent=indent,
        )

    @staticmethod
    def _format_time(time_ns: int | None) -> str | None:
        """Format nanosecond timestamp to ISO string."""
        if time_ns is None:
            return None
        return datetime.fromtimestamp(time_ns / 1e9, tz=timezone.utc).isoformat()

    @staticmethod
    def _format_event(event: Any) -> dict:
        """Format a span event."""
        return {
            "name": event.name,
            "timestamp": EnrichedReadableSpan._format_time(event.timestamp),
            "attributes": dict(event.attributes) if event.attributes else None,
        }

    @staticmethod
    def _format_link(link: Any) -> dict:
        """Format a span link."""
        return {
            "context": (
                {
                    "trace_id": f"0x{link.context.trace_id:032x}",
                    "span_id": f"0x{link.context.span_id:016x}",
                }
                if link.context
                else None
            ),
            "attributes": dict(link.attributes) if link.attributes else None,
        }
