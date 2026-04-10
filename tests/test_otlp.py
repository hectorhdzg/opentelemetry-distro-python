# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Tests for the OTLP handler module.

Validates:
  1. ``is_otlp_enabled()`` correctly reads OTLP endpoint env vars.
  2. ``create_otlp_components()`` returns the expected processor/reader types.
  3. OTLP components are wired into the distro's provider setup functions.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from microsoft.opentelemetry._otlp.handler import (
    OtlpHandlers,
    is_otlp_enabled,
    create_otlp_components,
)
from microsoft.opentelemetry._constants import (
    _OTEL_EXPORTER_OTLP_ENDPOINT,
    _OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
    _OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
    _OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
)


class TestIsOtlpEnabled(unittest.TestCase):
    """Tests for is_otlp_enabled()."""

    def _clear_otlp_env(self):
        for var in (
            _OTEL_EXPORTER_OTLP_ENDPOINT,
            _OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
            _OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
            _OTEL_EXPORTER_OTLP_LOGS_ENDPOINT,
        ):
            os.environ.pop(var, None)

    def setUp(self):
        self._clear_otlp_env()

    def tearDown(self):
        self._clear_otlp_env()

    def test_disabled_when_no_env_vars_set(self):
        self.assertFalse(is_otlp_enabled())

    def test_enabled_with_general_endpoint(self):
        os.environ[_OTEL_EXPORTER_OTLP_ENDPOINT] = "http://localhost:4318"
        self.assertTrue(is_otlp_enabled())

    def test_enabled_with_traces_endpoint(self):
        os.environ[_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT] = "http://localhost:4318/v1/traces"
        self.assertTrue(is_otlp_enabled())

    def test_enabled_with_metrics_endpoint(self):
        os.environ[_OTEL_EXPORTER_OTLP_METRICS_ENDPOINT] = "http://localhost:4318/v1/metrics"
        self.assertTrue(is_otlp_enabled())

    def test_enabled_with_logs_endpoint(self):
        os.environ[_OTEL_EXPORTER_OTLP_LOGS_ENDPOINT] = "http://localhost:4318/v1/logs"
        self.assertTrue(is_otlp_enabled())

    def test_disabled_when_env_var_is_empty(self):
        os.environ[_OTEL_EXPORTER_OTLP_ENDPOINT] = ""
        self.assertFalse(is_otlp_enabled())

    def test_enabled_with_multiple_env_vars(self):
        os.environ[_OTEL_EXPORTER_OTLP_ENDPOINT] = "http://localhost:4318"
        os.environ[_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT] = "http://localhost:4318/v1/traces"
        self.assertTrue(is_otlp_enabled())


def _install_fake_otlp_modules():
    """Insert stub modules into sys.modules so lazy imports inside
    create_otlp_components() find mock exporters instead of raising
    ModuleNotFoundError when the OTLP exporter package is not installed."""
    import sys
    import types

    mock_span_exporter = MagicMock()
    mock_metric_exporter = MagicMock()
    mock_log_exporter = MagicMock()

    module_chain = [
        "opentelemetry.exporter",
        "opentelemetry.exporter.otlp",
        "opentelemetry.exporter.otlp.proto",
        "opentelemetry.exporter.otlp.proto.http",
    ]
    for mod_name in module_chain:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    trace_name = "opentelemetry.exporter.otlp.proto.http.trace_exporter"
    trace_mod = types.ModuleType(trace_name)
    trace_mod.OTLPSpanExporter = mock_span_exporter
    sys.modules[trace_name] = trace_mod

    metric_name = "opentelemetry.exporter.otlp.proto.http.metric_exporter"
    metric_mod = types.ModuleType(metric_name)
    metric_mod.OTLPMetricExporter = mock_metric_exporter
    sys.modules[metric_name] = metric_mod

    log_name = "opentelemetry.exporter.otlp.proto.http._log_exporter"
    log_mod = types.ModuleType(log_name)
    log_mod.OTLPLogExporter = mock_log_exporter
    sys.modules[log_name] = log_mod

    return mock_span_exporter, mock_metric_exporter, mock_log_exporter


class TestCreateOtlpComponents(unittest.TestCase):
    """Tests for create_otlp_components()."""

    def setUp(self):
        import sys

        self._saved_modules = {}
        fake_modules = [
            "opentelemetry.exporter",
            "opentelemetry.exporter.otlp",
            "opentelemetry.exporter.otlp.proto",
            "opentelemetry.exporter.otlp.proto.http",
            "opentelemetry.exporter.otlp.proto.http.trace_exporter",
            "opentelemetry.exporter.otlp.proto.http.metric_exporter",
            "opentelemetry.exporter.otlp.proto.http._log_exporter",
        ]
        for mod in fake_modules:
            self._saved_modules[mod] = sys.modules.get(mod)
        self._mock_span_exp, self._mock_metric_exp, self._mock_log_exp = _install_fake_otlp_modules()

    def tearDown(self):
        import sys

        for mod, original in self._saved_modules.items():
            if original is None:
                sys.modules.pop(mod, None)
            else:
                sys.modules[mod] = original

    def test_returns_otlp_components(self):
        """create_otlp_components returns an OtlpHandlers with all three fields set."""
        components = create_otlp_components()
        self.assertIsInstance(components, OtlpHandlers)
        self.assertIsNotNone(components.span_processor)
        self.assertIsNotNone(components.metric_reader)
        self.assertIsNotNone(components.log_record_processor)

    def test_span_processor_is_batch(self):
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        components = create_otlp_components()
        self.assertIsInstance(components.span_processor, BatchSpanProcessor)

    def test_metric_reader_is_periodic(self):
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        components = create_otlp_components()
        self.assertIsInstance(components.metric_reader, PeriodicExportingMetricReader)

    def test_log_processor_is_batch(self):
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        components = create_otlp_components()
        self.assertIsInstance(components.log_record_processor, BatchLogRecordProcessor)


class TestOtlpHandlersDefault(unittest.TestCase):
    """Tests for the OtlpHandlers dataclass defaults."""

    def test_defaults_are_none(self):
        components = OtlpHandlers()
        self.assertIsNone(components.span_processor)
        self.assertIsNone(components.metric_reader)
        self.assertIsNone(components.log_record_processor)


class TestOtlpIntegrationWithDistro(unittest.TestCase):
    """Tests that OTLP components are collected and included in provider construction."""

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=True)
    @patch("microsoft.opentelemetry._distro.create_otlp_components")
    def test_otlp_components_created_when_enabled(
        self, mock_create, mock_enabled, mock_tracing, mock_metrics, mock_logging, mock_instr, mock_azure
    ):
        """When OTLP is enabled, create_otlp_components is called once."""
        mock_create.return_value = OtlpHandlers()
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_azure_monitor=False)
        mock_create.assert_called_once()

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro.create_otlp_components")
    def test_otlp_components_not_created_when_disabled(
        self, mock_create, mock_enabled, mock_tracing, mock_metrics, mock_logging, mock_instr, mock_azure
    ):
        """When OTLP is disabled, create_otlp_components is not called."""
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_azure_monitor=False)
        mock_create.assert_not_called()

    @patch("microsoft.opentelemetry._distro.set_tracer_provider")
    def test_otlp_span_processor_in_tracer_provider(self, mock_set_tp):
        """OTLP span processor is included in TracerProvider at construction."""
        from opentelemetry.sdk.resources import Resource
        from microsoft.opentelemetry._distro import _setup_tracing

        mock_sp = MagicMock()
        tp = _setup_tracing(Resource.create(), {"span_processors": [mock_sp]})

        self.assertIn(mock_sp, tp._active_span_processor._span_processors)

    def test_otlp_log_processor_in_logger_provider(self):
        """OTLP log processor is included in LoggerProvider at construction."""
        from opentelemetry.sdk.resources import Resource
        from microsoft.opentelemetry._distro import _setup_logging

        mock_lrp = MagicMock()
        lp = _setup_logging(Resource.create(), {"log_record_processors": [mock_lrp]})

        self.assertIn(mock_lrp, lp._multi_log_record_processor._log_record_processors)

    @patch("microsoft.opentelemetry._distro.set_meter_provider")
    def test_otlp_metric_reader_in_meter_provider(self, mock_set_mp):
        """OTLP metric reader is included in MeterProvider at construction."""
        from opentelemetry.sdk.resources import Resource
        from microsoft.opentelemetry._distro import _setup_metrics

        mock_reader = MagicMock()
        mp = _setup_metrics(Resource.create(), {"metric_readers": [mock_reader]})

        self.assertIn(mock_reader, mp._all_metric_readers)

    @patch("microsoft.opentelemetry._distro.set_tracer_provider")
    def test_no_extra_processors_when_otlp_disabled(self, mock_set_tp):
        """When no OTLP, no extra processors are added."""
        from opentelemetry.sdk.resources import Resource
        from microsoft.opentelemetry._distro import _setup_tracing

        tp = _setup_tracing(Resource.create(), {})
        self.assertEqual(len(tp._active_span_processor._span_processors), 0)

    @patch("microsoft.opentelemetry._distro.set_tracer_provider")
    def test_user_and_otlp_processors_both_included(self, mock_set_tp):
        """Both user-supplied and OTLP span processors are included."""
        from opentelemetry.sdk.resources import Resource
        from microsoft.opentelemetry._distro import _setup_tracing

        user_sp = MagicMock()
        otlp_sp = MagicMock()
        tp = _setup_tracing(Resource.create(), {"span_processors": [user_sp, otlp_sp]})

        processors = tp._active_span_processor._span_processors
        self.assertIn(user_sp, processors)
        self.assertIn(otlp_sp, processors)


if __name__ == "__main__":
    unittest.main()
