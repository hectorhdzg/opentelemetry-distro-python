# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from functools import cached_property
from logging import getLogger, Formatter
from typing import Any, Dict, List, Optional

from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import set_tracer_provider
from opentelemetry.util._importlib_metadata import (
    EntryPoint,
    distributions,
    entry_points,
)

from microsoft.opentelemetry._constants import (
    DISABLE_LOGGING_ARG,
    DISABLE_METRICS_ARG,
    DISABLE_TRACING_ARG,
    ENABLE_AZURE_MONITOR_ARG,
    INSTRUMENTATION_OPTIONS_ARG,
    LOGGER_NAME_ARG,
    LOGGING_FORMATTER_ARG,
    LOG_RECORD_PROCESSORS_ARG,
    METRIC_READERS_ARG,
    RESOURCE_ARG,
    SPAN_PROCESSORS_ARG,
    VIEWS_ARG,
    _AZURE_MONITOR_KWARG_MAP,
    _SUPPORTED_INSTRUMENTED_LIBRARIES,
)
from microsoft.opentelemetry._instrumentation import get_dist_dependency_conflicts

_logger = getLogger(__name__)


def use_microsoft_opentelemetry(**kwargs: object) -> None:
    """Configure OpenTelemetry with optional Azure Monitor support.

    This function sets up the OpenTelemetry global providers
    (TracerProvider, MeterProvider, LoggerProvider) and optionally
    configures Azure Monitor as an exporter.  Non-Azure Monitor
    scenarios are supported: disable Azure Monitor via
    ``enable_azure_monitor=False`` and the core OTel providers
    will still be initialised normally.

    :keyword bool enable_azure_monitor:
        Enable Azure Monitor export.
        Defaults to True. Set to False to skip Azure Monitor setup.
    :keyword str azure_monitor_connection_string:
        Connection string for Application Insights resource.
    :keyword azure_monitor_exporter_credential:
        Azure AD token credential for authentication.
    :keyword bool azure_monitor_enable_live_metrics:
        Enable live metrics. Defaults to True.
    :keyword bool azure_monitor_enable_performance_counters:
        Enable performance counters. Defaults to True.
    :keyword bool azure_monitor_exporter_disable_offline_storage:
        Disable offline retry storage. Defaults to False.
    :keyword str azure_monitor_exporter_storage_directory:
        Custom directory for offline telemetry storage.
    :keyword dict azure_monitor_browser_sdk_loader_config:
        Browser SDK loader configuration.
    :keyword bool disable_logging:
        Disable the logging pipeline. Defaults to False.
    :keyword bool disable_tracing:
        Disable the tracing pipeline. Defaults to False.
    :keyword bool disable_metrics:
        Disable the metrics pipeline. Defaults to False.
    :keyword resource: OpenTelemetry Resource.
    :keyword list span_processors: Additional span processors.
    :keyword list log_record_processors:
        Additional log record processors.
    :keyword list metric_readers: Additional metric readers.
    :keyword list views: Metric views.
    :keyword str logger_name: Logger name for log collection.
    :keyword logging_formatter: Formatter for collected logs.
    :keyword dict instrumentation_options:
        Per-library instrumentation enable/disable options.
    :keyword bool enable_trace_based_sampling_for_logs:
        Enable trace-based sampling for logs.
    :rtype: None
    """
    enable_azure_monitor = kwargs.pop(ENABLE_AZURE_MONITOR_ARG, True)

    # Separate Azure Monitor kwargs from generic OTel kwargs
    otel_kwargs: Dict[str, Any] = {}
    azure_monitor_kwargs: Dict[str, Any] = {}
    for key, value in kwargs.items():
        if key in _AZURE_MONITOR_KWARG_MAP:
            azure_monitor_kwargs[_AZURE_MONITOR_KWARG_MAP[key]] = value
        else:
            otel_kwargs[key] = value

    # ---- Provider initialisation ----
    setup_bare_providers = True
    if enable_azure_monitor:
        merged = {**otel_kwargs, **azure_monitor_kwargs}
        if _setup_azure_monitor(**merged):
            setup_bare_providers = False

    if setup_bare_providers:
        # Either Azure Monitor is disabled, or setup failed — create bare
        # providers so the global tracer/meter/logger are still usable.
        resource = otel_kwargs.get(RESOURCE_ARG) or Resource.create()
        disable_tracing = otel_kwargs.get(DISABLE_TRACING_ARG, False)
        disable_logging = otel_kwargs.get(DISABLE_LOGGING_ARG, False)
        disable_metrics = otel_kwargs.get(DISABLE_METRICS_ARG, False)

        if not disable_tracing:
            _setup_tracing(resource, otel_kwargs)
        if not disable_metrics:
            _setup_metrics(resource, otel_kwargs)
        if not disable_logging:
            _setup_logging(resource, otel_kwargs)
        if not enable_azure_monitor:
            _logger.info("Azure Monitor exporter explicitly disabled.")

    # ---- Instrumentations (always, after providers are set) ----
    _setup_instrumentations(otel_kwargs)


# ---------------------------------------------------------------------------
# Core OTel provider setup
# ---------------------------------------------------------------------------


def _setup_tracing(
    resource: Resource,
    otel_kwargs: Dict[str, Any],
) -> TracerProvider:
    """Create and register a TracerProvider with user-supplied span processors."""
    tracer_provider = TracerProvider(resource=resource)
    for sp in otel_kwargs.get(SPAN_PROCESSORS_ARG) or []:
        tracer_provider.add_span_processor(sp)
    set_tracer_provider(tracer_provider)
    return tracer_provider


def _setup_metrics(
    resource: Resource,
    otel_kwargs: Dict[str, Any],
) -> MeterProvider:
    """Create and register a MeterProvider with user-supplied readers/views."""
    readers: List[MetricReader] = list(otel_kwargs.get(METRIC_READERS_ARG) or [])
    views: List[View] = list(otel_kwargs.get(VIEWS_ARG) or [])
    meter_provider = MeterProvider(
        metric_readers=readers,
        resource=resource,
        views=views,
    )
    set_meter_provider(meter_provider)
    return meter_provider


def _setup_logging(
    resource: Resource,
    otel_kwargs: Dict[str, Any],
) -> Any:
    """Create and register a LoggerProvider with user-supplied processors."""
    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    except ImportError:
        _logger.warning(
            "OpenTelemetry logging SDK not available. "
            "Install opentelemetry-sdk and opentelemetry-instrumentation-logging."
        )
        return None

    logger_provider = LoggerProvider(resource=resource)
    for lrp in otel_kwargs.get(LOG_RECORD_PROCESSORS_ARG) or []:
        logger_provider.add_log_record_processor(lrp)
    set_logger_provider(logger_provider)

    logger_name: str = otel_kwargs.get(LOGGER_NAME_ARG, "")
    logging_formatter: Optional[Formatter] = otel_kwargs.get(LOGGING_FORMATTER_ARG)
    if logger_name:
        logger = getLogger(logger_name)
        if not any(isinstance(h, LoggingHandler) for h in logger.handlers):
            handler = LoggingHandler(logger_provider=logger_provider)
            if logging_formatter:
                handler.setFormatter(logging_formatter)
            logger.addHandler(handler)

    return logger_provider


# ---------------------------------------------------------------------------
# Instrumentations
# ---------------------------------------------------------------------------


class _EntryPointDistFinder:
    @cached_property
    def _mapping(self) -> Dict[str, Any]:
        return {self._key_for(ep): dist for dist in distributions() for ep in dist.entry_points}

    def dist_for(self, entry_point: EntryPoint) -> Any:
        dist = getattr(entry_point, "dist", None)
        if dist:
            return dist
        return self._mapping.get(self._key_for(entry_point))

    @staticmethod
    def _key_for(entry_point: EntryPoint) -> str:
        return f"{entry_point.group}:{entry_point.name}:{entry_point.value}"


def _is_instrumentation_enabled(otel_kwargs: Dict[str, Any], lib_name: str) -> bool:
    """Check if a library instrumentation is enabled via instrumentation_options."""
    options = otel_kwargs.get(INSTRUMENTATION_OPTIONS_ARG)
    if not options or lib_name not in options:
        # Default: enabled for supported libraries
        return True
    lib_options = options[lib_name]
    if "enabled" not in lib_options:
        return True
    return lib_options["enabled"] is True


def _setup_instrumentations(otel_kwargs: Dict[str, Any]) -> None:
    """Discover and activate OTel instrumentations for supported libraries."""
    entry_point_finder = _EntryPointDistFinder()
    for entry_point in entry_points(group="opentelemetry_instrumentor"):
        lib_name = entry_point.name
        if lib_name not in _SUPPORTED_INSTRUMENTED_LIBRARIES:
            continue
        if not _is_instrumentation_enabled(otel_kwargs, lib_name):
            _logger.debug("Instrumentation skipped for library %s", lib_name)
            continue
        try:
            entry_point_dist = entry_point_finder.dist_for(entry_point)  # type: ignore
            conflict = get_dist_dependency_conflicts(entry_point_dist)  # type: ignore
            if conflict:
                _logger.debug(
                    "Skipping instrumentation %s: %s",
                    entry_point.name,
                    conflict,
                )
                continue
            instrumentor: Any = entry_point.load()
            instrumentor().instrument(skip_dep_check=True)
        except Exception as ex:  # pylint: disable=broad-except
            _logger.warning(
                "Exception occurred when instrumenting: %s.",
                lib_name,
                exc_info=ex,
            )


# ---------------------------------------------------------------------------
# Azure Monitor plugin
# ---------------------------------------------------------------------------


def _setup_azure_monitor(**kwargs: object) -> bool:
    """Delegate Azure Monitor exporter setup.

    Passes the already-initialised providers to Azure Monitor so it
    can attach its exporters, samplers, and processors.

    :returns: True if Azure Monitor was configured successfully, False otherwise.
    """
    try:
        from microsoft.opentelemetry._azure_monitor import configure_azure_monitor
    except ImportError:
        _logger.warning(
            "Failed to import Azure Monitor components. Verify azure-monitor-opentelemetry-exporter is installed."
        )
        return False

    try:
        configure_azure_monitor(**kwargs)
        _logger.info("Azure Monitor configured via azure-monitor-opentelemetry package")
        return True
    except Exception as ex:  # pylint: disable=broad-exception-caught
        _logger.warning(
            "Failed to configure Azure Monitor: %s",
            ex,
            exc_info=True,
        )
        return False
