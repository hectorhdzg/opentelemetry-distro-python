# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Trace Processors
"""

from microsoft.opentelemetry.a365.core.trace_processor.span_processor import SpanProcessor

# Export public API
__all__ = [
    # Span processor
    "SpanProcessor",
]
