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
    ENABLE_LIVE_METRICS_ARG,
    LOG_RECORD_PROCESSORS_ARG,
    METRIC_READERS_ARG,
    SPAN_PROCESSORS_ARG,
)
from microsoft.opentelemetry._otlp import is_otlp_enabled, create_otlp_components
from microsoft.opentelemetry._console import create_console_components

_logger = getLogger(__name__)


# ---------------------------------------------------------------------------
# OTLP helper functions
# ---------------------------------------------------------------------------


def _append_otlp_components(otel_kwargs: Dict[str, Any]) -> None:
    """Append OTLP processors/readers to otel_kwargs when OTLP is enabled.

    Respects per-signal disable flags so that disabled pipelines do not
    get unnecessary exporters.
    """
    if not is_otlp_enabled():
        return

    otlp = create_otlp_components(
        enable_traces=not otel_kwargs.get(DISABLE_TRACING_ARG, False),
        enable_metrics=not otel_kwargs.get(DISABLE_METRICS_ARG, False),
        enable_logs=not otel_kwargs.get(DISABLE_LOGGING_ARG, False),
    )
    if otlp.span_processor:
        otel_kwargs[SPAN_PROCESSORS_ARG] = list(otel_kwargs.get(SPAN_PROCESSORS_ARG) or [])
        otel_kwargs[SPAN_PROCESSORS_ARG].append(otlp.span_processor)
    if otlp.log_record_processor:
        otel_kwargs[LOG_RECORD_PROCESSORS_ARG] = list(otel_kwargs.get(LOG_RECORD_PROCESSORS_ARG) or [])
        otel_kwargs[LOG_RECORD_PROCESSORS_ARG].append(otlp.log_record_processor)
    if otlp.metric_reader:
        otel_kwargs[METRIC_READERS_ARG] = list(otel_kwargs.get(METRIC_READERS_ARG) or [])
        otel_kwargs[METRIC_READERS_ARG].append(otlp.metric_reader)


# ---------------------------------------------------------------------------
# Console helper functions
# ---------------------------------------------------------------------------


def _append_console_components(otel_kwargs: Dict[str, Any], enable_console: bool) -> None:
    """Append console exporters to otel_kwargs when console export is enabled.

    Console export is enabled when ``enable_console=True`` is passed as a
    kwarg or auto-enabled by the distro when no other exporter is active.
    This mirrors the ``ExportTarget.Console`` flag from the .NET distro
    and is intended for local development and debugging.

    Respects per-signal disable flags so that disabled pipelines do not
    get unnecessary exporters.
    """
    if not enable_console:
        return

    console = create_console_components(
        enable_traces=not otel_kwargs.get(DISABLE_TRACING_ARG, False),
        enable_metrics=not otel_kwargs.get(DISABLE_METRICS_ARG, False),
        enable_logs=not otel_kwargs.get(DISABLE_LOGGING_ARG, False),
    )
    if console.span_processor:
        otel_kwargs[SPAN_PROCESSORS_ARG] = list(otel_kwargs.get(SPAN_PROCESSORS_ARG) or [])
        otel_kwargs[SPAN_PROCESSORS_ARG].append(console.span_processor)
    if console.log_record_processor:
        otel_kwargs[LOG_RECORD_PROCESSORS_ARG] = list(otel_kwargs.get(LOG_RECORD_PROCESSORS_ARG) or [])
        otel_kwargs[LOG_RECORD_PROCESSORS_ARG].append(console.log_record_processor)
    if console.metric_reader:
        otel_kwargs[METRIC_READERS_ARG] = list(otel_kwargs.get(METRIC_READERS_ARG) or [])
        otel_kwargs[METRIC_READERS_ARG].append(console.metric_reader)


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
    # Lazy imports to avoid pulling in the Azure Monitor exporter stack
    # when Azure Monitor is not enabled.
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
        enable_live_metrics_config = configurations.get(ENABLE_LIVE_METRICS_ARG, False)

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
