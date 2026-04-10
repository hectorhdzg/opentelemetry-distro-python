# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -------------------------------------------------------------------------

import os
from dataclasses import dataclass, field
from logging import getLogger
from typing import Optional

from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanProcessor
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LogRecordProcessor

from microsoft.opentelemetry._constants import (
    _OTEL_EXPORTER_OTLP_ENDPOINT,
    _OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    _OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    _OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
)

_logger = getLogger(__name__)


@dataclass
class OtlpHandlers:
    span_processor: Optional[SpanProcessor] = field(default=None)
    metric_reader: Optional[MetricReader] = field(default=None)
    log_record_processor: Optional[LogRecordProcessor] = field(default=None)


def is_otlp_enabled() -> bool:
    """Determines whether OTLP export should be enabled.

    OTLP is enabled when any supported OTLP endpoint environment variable is set:
    ``OTEL_EXPORTER_OTLP_ENDPOINT``, ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``,
    ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT``, or ``OTEL_EXPORTER_OTLP_LOGS_ENDPOINT``.
    """
    return any(
        os.environ.get(env_var)
        for env_var in (
            _OTEL_EXPORTER_OTLP_ENDPOINT,
            _OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
            _OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
            _OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
        )
    )


def create_otlp_components() -> OtlpHandlers:
    """Creates OTLP HTTP exporters for traces, metrics, and logs.

    All configuration is driven by the standard OpenTelemetry OTLP environment
    variables.  The underlying ``opentelemetry-exporter-otlp-proto-http``
    packages read these variables automatically -- no programmatic config is
    required.

    Supported environment variables
    ===============================

    General (apply to all signals)
    ------------------------------
    - ``OTEL_EXPORTER_OTLP_ENDPOINT`` -- Base endpoint URL for all signals.
    - ``OTEL_EXPORTER_OTLP_HEADERS`` -- Comma-separated key=value pairs.
    - ``OTEL_EXPORTER_OTLP_TIMEOUT`` -- Max time in milliseconds per export.
    - ``OTEL_EXPORTER_OTLP_COMPRESSION`` -- ``gzip`` or ``none``.

    Per-signal overrides follow the pattern
    ``OTEL_EXPORTER_OTLP_{TRACES,METRICS,LOGS}_{ENDPOINT,HEADERS,TIMEOUT,COMPRESSION}``.
    """
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    components = OtlpHandlers()

    _logger.info("OTLP export enabled for traces, metrics, and logs.")

    # Trace exporter
    trace_exporter = OTLPSpanExporter()
    components.span_processor = BatchSpanProcessor(trace_exporter)

    # Metric exporter
    metric_exporter = OTLPMetricExporter()
    components.metric_reader = PeriodicExportingMetricReader(metric_exporter)

    # Log exporter
    log_exporter = OTLPLogExporter()
    components.log_record_processor = BatchLogRecordProcessor(log_exporter)

    return components
