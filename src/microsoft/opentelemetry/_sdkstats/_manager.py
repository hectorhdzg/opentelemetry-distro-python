# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""SDKStats manager — sends SDK self-telemetry to Application Insights.

SDKStats always sends metrics to the Application Insights statsbeat
ingestion endpoint via ``AzureMonitorMetricExporter``.  This is
independent of the customer's telemetry pipeline — the exporter
targets a well-known Microsoft-owned iKey/endpoint used for SDK
health monitoring.

When the full Azure Monitor pipeline is enabled the exporter package's
own ``StatsbeatManager`` handles everything.  For A365-only, OTLP-only,
or Console-only customers this manager creates a standalone
``MeterProvider`` → ``AzureMonitorMetricExporter(is_sdkstats=True)``
pipeline so usage/feature metrics are still collected.
"""

import logging
import threading
from typing import Optional

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource

from microsoft.opentelemetry._sdkstats._state import (
    is_sdkstats_enabled,
    set_sdkstats_shutdown,
)
from microsoft.opentelemetry._sdkstats._metrics import SdkStatsMetrics

_logger = logging.getLogger(__name__)


class SdkStatsManager:
    """Singleton manager for SDK self-telemetry metrics.

    Creates a standalone ``MeterProvider`` with an
    ``AzureMonitorMetricExporter(is_sdkstats=True)`` that sends
    feature/instrumentation gauges to the well-known statsbeat
    ingestion endpoint.  This is completely independent of any
    customer-facing Azure Monitor configuration.

    Call :meth:`initialize` once during distro setup.  The manager is
    safe to initialise from multiple threads — only the first call
    takes effect.
    """

    _instance: Optional["SdkStatsManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "SdkStatsManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False  # type: ignore[attr-defined]
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-init on repeated __init__ calls from __new__
        if getattr(self, "_init_done", False):
            return
        self._init_done = True
        self._lock = threading.Lock()
        self._initialized = False
        self._meter_provider: Optional[MeterProvider] = None
        self._metrics: Optional[SdkStatsMetrics] = None

    # ------------------------------------------------------------------
    # Public initialisation
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """Set up SDKStats export via Azure Monitor statsbeat endpoint.

        Uses ``AzureMonitorMetricExporter`` with ``is_sdkstats=True``
        pointed at the default (non-EU) statsbeat connection string.
        The exporter package resolves EU vs non-EU automatically when
        a customer endpoint hint is provided.
        """
        if not is_sdkstats_enabled():
            return False

        with self._lock:
            if self._initialized:
                return True
            return self._do_initialize()

    def initialize_standalone(self, metric_reader: MetricReader) -> bool:
        """Set up SDKStats with a caller-supplied metric reader.

        Intended for tests or future transports.
        """
        if not is_sdkstats_enabled():
            return False

        with self._lock:
            if self._initialized:
                return True
            return self._do_initialize_with_reader(metric_reader)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> bool:
        with self._lock:
            if not self._initialized:
                return False
            try:
                if self._meter_provider is not None:
                    self._meter_provider.shutdown()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            self._meter_provider = None
            self._metrics = None
            self._initialized = False
            set_sdkstats_shutdown(True)
            return True

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_initialize(self) -> bool:
        """Create an AzureMonitorMetricExporter for statsbeat."""
        try:
            from azure.monitor.opentelemetry.exporter.statsbeat._utils import (
                _get_stats_connection_string,
                _get_stats_short_export_interval,
            )
            from azure.monitor.opentelemetry.exporter.export.metrics._exporter import (
                AzureMonitorMetricExporter,
            )

            # Use the well-known non-EU statsbeat endpoint as default.
            # The helper honours APPLICATIONINSIGHTS_STATS_CONNECTION_STRING
            # env-var overrides automatically.
            stats_connection_string = _get_stats_connection_string(
                "https://defaultendpoint.in.applicationinsights.azure.com/"
            )
            export_interval_secs = _get_stats_short_export_interval()

            exporter = AzureMonitorMetricExporter(
                connection_string=stats_connection_string,
                disable_offline_storage=True,
                is_sdkstats=True,
            )

            reader = PeriodicExportingMetricReader(
                exporter,
                export_interval_millis=export_interval_secs * 1000,
            )
            return self._do_initialize_with_reader(reader)

        except ImportError:
            _logger.debug("azure-monitor-opentelemetry-exporter is not available; SDKStats will not be exported.")
            return False
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.warning("Failed to create SDKStats Azure Monitor exporter.", exc_info=True)
            return False

    def _do_initialize_with_reader(self, reader: MetricReader) -> bool:
        try:
            self._meter_provider = MeterProvider(
                metric_readers=[reader],
                resource=Resource.get_empty(),
            )
            self._metrics = SdkStatsMetrics(self._meter_provider)
            self._initialized = True
            _logger.debug("SDKStats initialised.")
            return True
        except Exception:  # pylint: disable=broad-exception-caught
            _logger.warning("Failed to initialise SDKStats.", exc_info=True)
            self._cleanup()
            return False

    def _cleanup(self) -> None:
        if self._meter_provider:
            try:
                self._meter_provider.shutdown()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
        self._meter_provider = None
        self._metrics = None
        self._initialized = False

    @classmethod
    def _reset(cls) -> None:
        """Reset the singleton — intended for tests only."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.shutdown()
            cls._instance = None
