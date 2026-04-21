# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
from functools import cached_property
from logging import getLogger, Formatter
from typing import Any, Dict, List, Optional

from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging.handler import LoggingHandler
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
    ENABLE_A365_ARG,
    A365_TOKEN_RESOLVER_ARG,
    A365_TENANT_ID_ARG,
    A365_AGENT_ID_ARG,
    A365_CLUSTER_CATEGORY_ARG,
    A365_USE_S2S_ENDPOINT_ARG,
    A365_SUPPRESS_INVOKE_AGENT_INPUT_ARG,
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
from microsoft.opentelemetry._utils import (
    _append_azure_monitor_components,
    _append_otlp_components,
)

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
    :keyword bool enable_a365:
        Enable Agent365 trace export. Defaults to False.
    :keyword a365_token_resolver:
        Optional callable ``(agent_id: str, tenant_id: str) -> str | None``
        used to authenticate with the Agent365 endpoint.  When omitted,
        ``DefaultAzureCredential`` is used.
    :keyword str a365_tenant_id:
        Tenant ID stamped on every span. Also read from ``A365_TENANT_ID`` env var.
    :keyword str a365_agent_id:
        Agent ID stamped on every span. Also read from ``A365_AGENT_ID`` env var.
    :keyword str a365_cluster_category:
        Cluster category for endpoint discovery. Also read from ``A365_CLUSTER_CATEGORY``
        env var. Defaults to ``"prod"``.
    :keyword bool a365_use_s2s_endpoint:
        Use the S2S endpoint. Also read from ``A365_USE_S2S_ENDPOINT`` env var.
        Defaults to False.
    :keyword bool a365_suppress_invoke_agent_input:
        Strip input messages from InvokeAgent spans before export. Also read from
        ``A365_SUPPRESS_INVOKE_AGENT_INPUT`` env var. Defaults to False.
    :rtype: None
    """

    enable_azure_monitor = kwargs.pop(ENABLE_AZURE_MONITOR_ARG, True)
    enable_a365: bool = bool(kwargs.pop(ENABLE_A365_ARG, False))
    a365_token_resolver = kwargs.pop(A365_TOKEN_RESOLVER_ARG, None)
    a365_tenant_id = kwargs.pop(A365_TENANT_ID_ARG, None)
    a365_agent_id = kwargs.pop(A365_AGENT_ID_ARG, None)
    a365_cluster_category = kwargs.pop(A365_CLUSTER_CATEGORY_ARG, None)
    a365_use_s2s_endpoint = kwargs.pop(A365_USE_S2S_ENDPOINT_ARG, None)
    a365_suppress_invoke_agent_input = kwargs.pop(A365_SUPPRESS_INVOKE_AGENT_INPUT_ARG, None)

    # Separate Azure Monitor kwargs from generic OTel kwargs
    otel_kwargs: Dict[str, Any] = {k: v for k, v in kwargs.items() if k not in _AZURE_MONITOR_KWARG_MAP}
    azure_monitor_kwargs: Dict[str, Any] = {
        _AZURE_MONITOR_KWARG_MAP[k]: v for k, v in kwargs.items() if k in _AZURE_MONITOR_KWARG_MAP
    }  # pylint: disable=line-too-long

    # ---- OTLP exporters (append to user-supplied processors/readers) ----
    _append_otlp_components(otel_kwargs)

    # ---- A365 exporters (append span processors — traces only) ----
    _append_a365_components(
        enable_a365,
        otel_kwargs,
        token_resolver=a365_token_resolver,
        tenant_id=a365_tenant_id,
        agent_id=a365_agent_id,
        cluster_category=a365_cluster_category,
        use_s2s_endpoint=a365_use_s2s_endpoint,
        suppress_invoke_agent_input=a365_suppress_invoke_agent_input,
    )

    # ---- Build and register providers ----
    tracer_provider: Optional[TracerProvider] = None
    meter_provider: Optional[MeterProvider] = None
    logger_provider: Optional[LoggerProvider] = None

    if enable_azure_monitor:
        tracer_provider, meter_provider, logger_provider = _append_azure_monitor_components(
            otel_kwargs, azure_monitor_kwargs
        )

    # If Azure Monitor was disabled or failed to create a provider for a
    # signal, fall back to creating a plain provider from otel_kwargs so
    # that OTLP (and any user-supplied processors) still work.
    resource = otel_kwargs.get(RESOURCE_ARG) or Resource.create()
    disable_tracing = otel_kwargs.get(DISABLE_TRACING_ARG, False)
    disable_logging = otel_kwargs.get(DISABLE_LOGGING_ARG, False)
    disable_metrics = otel_kwargs.get(DISABLE_METRICS_ARG, False)

    # When Azure Monitor is enabled, its _setup_* functions already create
    # providers that include OTLP + user-supplied components, so the checks
    # below are no-ops. These only run when Azure Monitor is disabled or
    # its setup failed, to create bare providers and register them.
    if tracer_provider is None and not disable_tracing:
        tracer_provider = _setup_tracing(resource, otel_kwargs)
    if meter_provider is None and not disable_metrics:
        meter_provider = _setup_metrics(resource, otel_kwargs)
    if logger_provider is None and not disable_logging:
        logger_provider = _setup_logging(resource, otel_kwargs)

    # Register the created providers as the OTel global singletons
    if tracer_provider is not None:
        set_tracer_provider(tracer_provider)
    if meter_provider is not None:
        set_meter_provider(meter_provider)
    if logger_provider is not None:
        set_logger_provider(logger_provider)

    # ---- Instrumentations (always, after providers are set) ----
    _setup_instrumentations(otel_kwargs)

    # Log when Azure Monitor is explicitly opted out, so users can
    # confirm the setting took effect.
    if not enable_azure_monitor:
        _logger.info("Azure Monitor exporter explicitly disabled.")


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean from an environment variable."""
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val in ("true", "1", "yes", "on")


def _append_a365_components(
    enable_a365: bool,
    otel_kwargs: Dict[str, Any],
    token_resolver: Any = None,
    tenant_id: Any = None,
    agent_id: Any = None,
    cluster_category: Any = None,
    use_s2s_endpoint: Any = None,
    suppress_invoke_agent_input: Any = None,
) -> None:
    """Build and append Agent365 span processors to ``otel_kwargs``.

    A365 only produces span processors (traces).  They are added to the
    same list that the distro uses when creating the TracerProvider, so
    the distro registers a single provider for all exporters.

    Kwargs take precedence over environment variables.
    """
    if not enable_a365:
        return

    disable_tracing = otel_kwargs.get(DISABLE_TRACING_ARG, False)
    if disable_tracing:
        return

    from microsoft.opentelemetry.a365.constants import (
        A365_TENANT_ID_ENV,
        A365_AGENT_ID_ENV,
        A365_CLUSTER_CATEGORY_ENV,
        A365_USE_S2S_ENDPOINT_ENV,
        A365_SUPPRESS_INVOKE_AGENT_INPUT_ENV,
        ENABLE_A365_OBSERVABILITY_EXPORTER,
    )
    from microsoft.opentelemetry.a365.core.exporters.agent365_exporter import _Agent365Exporter
    from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import (
        _EnrichingBatchSpanProcessor,
    )
    from microsoft.opentelemetry.a365.core.exporters.span_processor import A365SpanProcessor
    from microsoft.opentelemetry.a365.core.exporters.utils import (
        _create_default_token_resolver,
        is_agent365_exporter_enabled,
    )

    try:
        # Resolve configuration: kwargs > env vars > defaults
        resolved_token_resolver = token_resolver or _create_default_token_resolver()
        resolved_tenant_id = tenant_id or os.environ.get(A365_TENANT_ID_ENV)
        resolved_agent_id = agent_id or os.environ.get(A365_AGENT_ID_ENV)
        resolved_cluster_category = cluster_category or os.environ.get(A365_CLUSTER_CATEGORY_ENV, "prod")
        resolved_use_s2s = use_s2s_endpoint if use_s2s_endpoint is not None else _env_bool(A365_USE_S2S_ENDPOINT_ENV)
        resolved_suppress_input = (
            suppress_invoke_agent_input
            if suppress_invoke_agent_input is not None
            else _env_bool(A365_SUPPRESS_INVOKE_AGENT_INPUT_ENV)
        )

        # Build the exporter (A365 HTTP or skip if not enabled)
        if not is_agent365_exporter_enabled() or resolved_token_resolver is None:
            _logger.warning(
                "%s not set or token_resolver not provided. A365 exporter will not be active.",
                ENABLE_A365_OBSERVABILITY_EXPORTER,
            )
            return

        exporter = _Agent365Exporter(
            token_resolver=resolved_token_resolver,
            cluster_category=resolved_cluster_category,
            use_s2s_endpoint=resolved_use_s2s,
        )

        # Enriching batch processor wrapping the exporter
        batch_processor = _EnrichingBatchSpanProcessor(
            exporter,
            suppress_invoke_agent_input=resolved_suppress_input,
        )

        # Identity stamping + baggage-to-span attribute propagation
        baggage_processor = A365SpanProcessor(
            tenant_id=resolved_tenant_id,
            agent_id=resolved_agent_id,
        )

        otel_kwargs[SPAN_PROCESSORS_ARG] = list(otel_kwargs.get(SPAN_PROCESSORS_ARG) or [])
        otel_kwargs[SPAN_PROCESSORS_ARG].append(batch_processor)
        otel_kwargs[SPAN_PROCESSORS_ARG].append(baggage_processor)

    except Exception:  # pylint: disable=broad-exception-caught
        _logger.exception("Failed to create A365 components.")


# ---------------------------------------------------------------------------
# Core OTel provider setup
# ---------------------------------------------------------------------------


def _setup_tracing(
    resource: Resource,
    otel_kwargs: Dict[str, Any],
) -> TracerProvider:
    """Create a TracerProvider with user-supplied span processors."""
    tracer_provider = TracerProvider(resource=resource)
    for sp in otel_kwargs.get(SPAN_PROCESSORS_ARG) or []:
        tracer_provider.add_span_processor(sp)
    return tracer_provider


def _setup_metrics(
    resource: Resource,
    otel_kwargs: Dict[str, Any],
) -> MeterProvider:
    """Create a MeterProvider with user-supplied readers/views."""
    readers: List[MetricReader] = list(otel_kwargs.get(METRIC_READERS_ARG) or [])
    views: List[View] = list(otel_kwargs.get(VIEWS_ARG) or [])
    meter_provider = MeterProvider(
        metric_readers=readers,
        resource=resource,
        views=views,
    )
    return meter_provider


def _setup_logging(
    resource: Resource,
    otel_kwargs: Dict[str, Any],
) -> LoggerProvider | None:
    """Create a LoggerProvider with user-supplied processors."""
    logger_provider = LoggerProvider(resource=resource)
    for lrp in otel_kwargs.get(LOG_RECORD_PROCESSORS_ARG) or []:
        logger_provider.add_log_record_processor(lrp)

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
