# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from logging import getLogger
from typing import Any, Dict

from microsoft.opentelemetry._constants import (
    DISABLE_LOGGING_ARG,
    DISABLE_METRICS_ARG,
    DISABLE_TRACING_ARG,
    LOG_RECORD_PROCESSORS_ARG,
    METRIC_READERS_ARG,
    SPAN_PROCESSORS_ARG,
)
from microsoft.opentelemetry._otlp import is_otlp_enabled, create_otlp_components

_logger = getLogger(__name__)


# ---------------------------------------------------------------------------
# OTLP helper functions
# ---------------------------------------------------------------------------


def _append_otlp_components(otel_kwargs: Dict[str, Any]) -> None:
    """Append OTLP processors/readers to otel_kwargs when OTLP is enabled.

    Respects per-signal disable flags so that disabled pipelines do not
    get unnecessary exporters.
    """
    disable_tracing = otel_kwargs.get(DISABLE_TRACING_ARG, False)
    disable_logging = otel_kwargs.get(DISABLE_LOGGING_ARG, False)
    disable_metrics = otel_kwargs.get(DISABLE_METRICS_ARG, False)

    if not is_otlp_enabled() or (disable_tracing and disable_logging and disable_metrics):
        return

    otlp = create_otlp_components()
    if not disable_tracing and otlp.span_processor:
        otel_kwargs[SPAN_PROCESSORS_ARG] = list(otel_kwargs.get(SPAN_PROCESSORS_ARG) or [])
        otel_kwargs[SPAN_PROCESSORS_ARG].append(otlp.span_processor)
    if not disable_logging and otlp.log_record_processor:
        otel_kwargs[LOG_RECORD_PROCESSORS_ARG] = list(otel_kwargs.get(LOG_RECORD_PROCESSORS_ARG) or [])
        otel_kwargs[LOG_RECORD_PROCESSORS_ARG].append(otlp.log_record_processor)
    if not disable_metrics and otlp.metric_reader:
        otel_kwargs[METRIC_READERS_ARG] = list(otel_kwargs.get(METRIC_READERS_ARG) or [])
        otel_kwargs[METRIC_READERS_ARG].append(otlp.metric_reader)


# ---------------------------------------------------------------------------
# Azure Monitor helper functions
# ---------------------------------------------------------------------------


def _append_azure_monitor_components(
    otel_kwargs: Dict[str, Any],
    azure_monitor_kwargs: Dict[str, Any],
) -> tuple:
    """Call Azure Monitor _setup_* functions which build fully-configured providers.

    Returns (tracer_provider, meter_provider, logger_provider) on success,
    or (None, None, None) on failure.
    """
    try:
        from microsoft.opentelemetry._azure_monitor._configure import (
            _setup_tracing,
            _setup_metrics,
            _setup_logging,
            _setup_live_metrics,
            _setup_azure_instrumentations,
            _setup_browser_sdk_loader,
            _send_attach_warning,
        )
        from microsoft.opentelemetry._azure_monitor._utils.configurations import _get_configurations
    except ImportError:
        _logger.warning(
            "Failed to import Azure Monitor components. Verify azure-monitor-opentelemetry-exporter is installed."
        )
        return None, None, None

    try:
        _send_attach_warning()
        merged = {**otel_kwargs, **azure_monitor_kwargs}
        configurations = _get_configurations(**merged)

        tracer_provider = None
        meter_provider = None
        logger_provider = None

        disable_tracing = configurations.get(DISABLE_TRACING_ARG, False)
        disable_logging = configurations.get(DISABLE_LOGGING_ARG, False)
        disable_metrics = configurations.get(DISABLE_METRICS_ARG, False)
        enable_live_metrics_config = configurations.get("enable_live_metrics", False)

        # Metrics first (before perf counters span/log processors)
        if not disable_metrics:
            meter_provider = _setup_metrics(configurations)
        if enable_live_metrics_config:
            _setup_live_metrics(configurations)
        if not disable_tracing:
            tracer_provider = _setup_tracing(configurations)
        if not disable_logging:
            logger_provider = _setup_logging(configurations)

        _setup_azure_instrumentations(configurations)
        _setup_browser_sdk_loader(configurations)
        _logger.info("Azure Monitor configured via azure-monitor-opentelemetry package")

        return tracer_provider, meter_provider, logger_provider
    except Exception as ex:  # pylint: disable=broad-except
        _logger.warning(
            "Failed to create Azure Monitor components: %s",
            ex,
            exc_info=True,
        )
        return None, None, None
