# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -------------------------------------------------------------------------

from dataclasses import dataclass, field
from logging import getLogger
from typing import Optional

from opentelemetry.sdk.trace.export import SpanProcessor
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk._logs import LogRecordProcessor

_logger = getLogger(__name__)


@dataclass
class ConsoleHandlers:
    span_processor: Optional[SpanProcessor] = field(default=None)
    metric_reader: Optional[MetricReader] = field(default=None)
    log_record_processor: Optional[LogRecordProcessor] = field(default=None)


def create_console_components(
    enable_traces: bool = True,
    enable_metrics: bool = True,
    enable_logs: bool = True,
) -> ConsoleHandlers:
    """Creates console exporters for the requested signals.

    Console exporters write telemetry to stdout for local development
    and debugging.  This mirrors the ``ExportTarget.Console`` behaviour
    of the .NET distro.

    No additional configuration is required -- the exporters use their
    default settings.
    """
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
    from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor, ConsoleLogRecordExporter

    components = ConsoleHandlers()

    if enable_traces:
        components.span_processor = SimpleSpanProcessor(ConsoleSpanExporter())

    if enable_metrics:
        components.metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter())

    if enable_logs:
        components.log_record_processor = SimpleLogRecordProcessor(ConsoleLogRecordExporter())

    return components
