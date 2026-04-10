# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Tests for use_microsoft_opentelemetry() -- OTel provider init + Azure Monitor.

Validates that the microsoft distro wrapper:
  1. Initialises OTel global providers (tracing, metrics, logging).
  2. Optionally delegates Azure Monitor exporter setup.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

from microsoft.opentelemetry._distro import (
    use_microsoft_opentelemetry,
    _setup_tracing,
    _setup_metrics,
    _setup_logging,
)

TEST_RESOURCE = Resource({"service.name": "test-service"})
TEST_CONNECTION_STRING = "InstrumentationKey=test-key;IngestionEndpoint=https://test.in.ai.azure.com/"


class TestUseMicrosoftOpenTelemetry(unittest.TestCase):
    """Tests for use_microsoft_opentelemetry() orchestration."""

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    def test_azure_monitor_enabled_by_default(self, azure_monitor_mock):
        """Azure Monitor is enabled by default; providers are created through Azure Monitor setup."""
        use_microsoft_opentelemetry()
        azure_monitor_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_connection_string_remapped(self, tracing_mock, metrics_mock, logging_mock, azure_monitor_mock):
        """azure_monitor_connection_string is remapped to connection_string."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        actual_kwargs = azure_monitor_mock.call_args[1]
        self.assertEqual(actual_kwargs["connection_string"], TEST_CONNECTION_STRING)

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_azure_monitor_kwargs_remapped(self, tracing_mock, metrics_mock, logging_mock, azure_monitor_mock):
        """azure_monitor_ prefixed kwargs are remapped to internal names."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_exporter_credential="test_cred",
            azure_monitor_enable_live_metrics=False,
            azure_monitor_enable_performance_counters=False,
            azure_monitor_exporter_disable_offline_storage=True,
            azure_monitor_exporter_storage_directory="/tmp/test",
            azure_monitor_browser_sdk_loader_config={"enabled": False},
        )
        actual_kwargs = azure_monitor_mock.call_args[1]
        self.assertEqual(actual_kwargs["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(actual_kwargs["credential"], "test_cred")
        self.assertEqual(actual_kwargs["enable_live_metrics"], False)
        self.assertEqual(actual_kwargs["enable_performance_counters"], False)
        self.assertEqual(actual_kwargs["disable_offline_storage"], True)
        self.assertEqual(actual_kwargs["storage_directory"], "/tmp/test")
        self.assertEqual(actual_kwargs["browser_sdk_loader_config"], {"enabled": False})

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_general_otel_kwargs_forwarded(self, tracing_mock, metrics_mock, logging_mock, azure_monitor_mock):
        """General OTel kwargs are forwarded to Azure Monitor."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            sampling_ratio=0.5,
            logger_name="test",
        )
        actual_kwargs = azure_monitor_mock.call_args[1]
        self.assertEqual(actual_kwargs["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(actual_kwargs["sampling_ratio"], 0.5)
        self.assertEqual(actual_kwargs["logger_name"], "test")

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_explicit_disable(self, tracing_mock, metrics_mock, logging_mock, azure_monitor_mock):
        """Explicitly disabling Azure Monitor still creates providers."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            enable_azure_monitor=False,
        )
        tracing_mock.assert_called_once()
        metrics_mock.assert_called_once()
        logging_mock.assert_called_once()
        azure_monitor_mock.assert_not_called()

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    def test_enable_key_not_forwarded(self, azure_monitor_mock):
        """enable_azure_monitor is consumed, not forwarded."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            enable_azure_monitor=True,
        )
        actual_kwargs = azure_monitor_mock.call_args[1]
        self.assertNotIn("enable_azure_monitor", actual_kwargs)

    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_disable_tracing_skips_tracing(self, tracing_mock, metrics_mock, logging_mock):
        """disable_tracing=True skips TracerProvider creation."""
        use_microsoft_opentelemetry(disable_tracing=True, enable_azure_monitor=False)
        tracing_mock.assert_not_called()
        metrics_mock.assert_called_once()
        logging_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_disable_metrics_skips_metrics(self, tracing_mock, metrics_mock, logging_mock):
        """disable_metrics=True skips MeterProvider creation."""
        use_microsoft_opentelemetry(disable_metrics=True, enable_azure_monitor=False)
        tracing_mock.assert_called_once()
        metrics_mock.assert_not_called()
        logging_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_disable_logging_skips_logging(self, tracing_mock, metrics_mock, logging_mock):
        """disable_logging=True skips LoggerProvider creation."""
        use_microsoft_opentelemetry(disable_logging=True, enable_azure_monitor=False)
        tracing_mock.assert_called_once()
        metrics_mock.assert_called_once()
        logging_mock.assert_not_called()


class TestOTelProviderSetup(unittest.TestCase):
    """Tests for core OTel provider initialisation functions."""

    @patch("microsoft.opentelemetry._distro.set_tracer_provider")
    def test_setup_tracing_creates_provider(self, set_tp_mock):
        """_setup_tracing creates a TracerProvider and registers it."""
        tp = _setup_tracing(TEST_RESOURCE, {})
        self.assertIsInstance(tp, TracerProvider)
        set_tp_mock.assert_called_once_with(tp)

    def test_setup_tracing_adds_span_processors(self):
        """_setup_tracing adds user-supplied span processors."""
        sp = MagicMock()
        tp = _setup_tracing(TEST_RESOURCE, {"span_processors": [sp]})
        self.assertIsInstance(tp, TracerProvider)
        self.assertIn(sp, tp._active_span_processor._span_processors)

    @patch("microsoft.opentelemetry._distro.set_meter_provider")
    def test_setup_metrics_creates_provider(self, set_mp_mock):
        """_setup_metrics creates a MeterProvider and registers it."""
        mp = _setup_metrics(TEST_RESOURCE, {})
        self.assertIsInstance(mp, MeterProvider)
        set_mp_mock.assert_called_once_with(mp)


class TestSetupAzureMonitor(unittest.TestCase):
    """Tests for _setup_azure_monitor() delegation."""

    def _make_mock_modules(self):
        """Create mock microsoft.opentelemetry._azure_monitor module hierarchy."""
        mock_module = MagicMock()
        return {
            "microsoft": MagicMock(),
            "microsoft.opentelemetry._azure_monitor": mock_module,
        }, mock_module

    def test_delegates_to_configure_azure_monitor(self):
        """_setup_azure_monitor calls configure_azure_monitor with the given kwargs."""
        mods, mock_module = self._make_mock_modules()
        with patch.dict(sys.modules, mods):
            from microsoft.opentelemetry._distro import _setup_azure_monitor

            result = _setup_azure_monitor(
                connection_string=TEST_CONNECTION_STRING,
                resource=TEST_RESOURCE,
            )
            self.assertTrue(result)
            mock_module.configure_azure_monitor.assert_called_once_with(
                connection_string=TEST_CONNECTION_STRING,
                resource=TEST_RESOURCE,
            )

    def test_forwards_standard_config_keys(self):
        """Standard config keys (resource, sampling, processors, etc.) are forwarded."""
        mods, mock_module = self._make_mock_modules()
        with patch.dict(sys.modules, mods):
            from microsoft.opentelemetry._distro import _setup_azure_monitor

            _setup_azure_monitor(
                connection_string=TEST_CONNECTION_STRING,
                resource=TEST_RESOURCE,
                disable_tracing=False,
                disable_logging=False,
                disable_metrics=False,
                span_processors=["sp1"],
                log_record_processors=["lrp1"],
                metric_readers=["mr1"],
                views=["v1"],
                enable_live_metrics=True,
                enable_performance_counters=True,
                sampling_ratio=0.5,
                logger_name="test",
            )
            actual_kwargs = mock_module.configure_azure_monitor.call_args[1]

            self.assertEqual(actual_kwargs["connection_string"], TEST_CONNECTION_STRING)
            self.assertEqual(actual_kwargs["resource"], TEST_RESOURCE)
            self.assertEqual(actual_kwargs["disable_tracing"], False)
            self.assertEqual(actual_kwargs["span_processors"], ["sp1"])
            self.assertEqual(actual_kwargs["sampling_ratio"], 0.5)
            self.assertEqual(actual_kwargs["logger_name"], "test")

    def test_exception_handled_gracefully(self):
        """If configure_azure_monitor raises, it is caught and logged; returns False."""
        mods, mock_module = self._make_mock_modules()
        mock_module.configure_azure_monitor.side_effect = Exception("config error")
        with patch.dict(sys.modules, mods):
            from microsoft.opentelemetry._distro import _setup_azure_monitor

            # Should not raise
            result = _setup_azure_monitor(connection_string=TEST_CONNECTION_STRING)
            self.assertFalse(result)

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor", return_value=False)
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_fallback_providers_created_on_azure_monitor_failure(
        self, tracing_mock, metrics_mock, logging_mock, azure_monitor_mock
    ):
        """When Azure Monitor setup fails, bare providers are created as fallback."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        azure_monitor_mock.assert_called_once()
        tracing_mock.assert_called_once()
        metrics_mock.assert_called_once()
        logging_mock.assert_called_once()


class TestEnableKwargsPassthrough(unittest.TestCase):
    """Tests that azure_monitor_ kwargs are remapped and passed through."""

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    def test_enable_live_metrics_passed_through(self, azure_monitor_mock):
        """azure_monitor_enable_live_metrics is remapped and forwarded."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_enable_live_metrics=False,
        )
        actual_kwargs = azure_monitor_mock.call_args[1]
        self.assertEqual(actual_kwargs["enable_live_metrics"], False)

    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    def test_enable_performance_counters_passed_through(self, azure_monitor_mock):
        """azure_monitor_enable_performance_counters is remapped and forwarded."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_enable_performance_counters=False,
        )
        actual_kwargs = azure_monitor_mock.call_args[1]
        self.assertEqual(actual_kwargs["enable_performance_counters"], False)


class TestAllConfigOptions(unittest.TestCase):
    """End-to-end test that every documented configuration option works."""

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._setup_azure_monitor")
    def test_all_options_end_to_end(self, azure_monitor_mock, otlp_mock):
        """Every documented kwarg is accepted, remapped if needed, and forwarded."""
        from logging import Formatter

        formatter = Formatter("%(message)s")

        use_microsoft_opentelemetry(
            # Azure Monitor options (remapped)
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_exporter_credential="test_cred",
            azure_monitor_enable_live_metrics=False,
            azure_monitor_enable_performance_counters=False,
            azure_monitor_exporter_disable_offline_storage=True,
            azure_monitor_exporter_storage_directory="/tmp/test",
            azure_monitor_browser_sdk_loader_config={"enabled": False},
            # General OTel options (passed through unchanged)
            disable_logging=True,
            disable_tracing=True,
            disable_metrics=True,
            resource=TEST_RESOURCE,
            span_processors=["sp1"],
            log_record_processors=["lrp1"],
            metric_readers=["mr1"],
            views=["v1"],
            logger_name="mylogger",
            logging_formatter=formatter,
            instrumentation_options={"flask": {"enabled": False}},
            enable_trace_based_sampling_for_logs=True,
            sampling_ratio=0.25,
        )

        azure_monitor_mock.assert_called_once()
        actual = azure_monitor_mock.call_args[1]

        # Remapped azure_monitor_ kwargs
        self.assertEqual(actual["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(actual["credential"], "test_cred")
        self.assertEqual(actual["enable_live_metrics"], False)
        self.assertEqual(actual["enable_performance_counters"], False)
        self.assertEqual(actual["disable_offline_storage"], True)
        self.assertEqual(actual["storage_directory"], "/tmp/test")
        self.assertEqual(actual["browser_sdk_loader_config"], {"enabled": False})

        # General OTel kwargs passed through to Azure Monitor
        self.assertEqual(actual["disable_logging"], True)
        self.assertEqual(actual["disable_tracing"], True)
        self.assertEqual(actual["disable_metrics"], True)
        self.assertEqual(actual["resource"], TEST_RESOURCE)
        self.assertEqual(actual["span_processors"], ["sp1"])
        self.assertEqual(actual["log_record_processors"], ["lrp1"])
        self.assertEqual(actual["metric_readers"], ["mr1"])
        self.assertEqual(actual["views"], ["v1"])
        self.assertEqual(actual["logger_name"], "mylogger")
        self.assertEqual(actual["logging_formatter"], formatter)
        self.assertEqual(actual["instrumentation_options"], {"flask": {"enabled": False}})
        self.assertEqual(actual["enable_trace_based_sampling_for_logs"], True)
        self.assertEqual(actual["sampling_ratio"], 0.25)

        # azure_monitor_ prefixed keys should NOT appear in forwarded kwargs
        for key in actual:
            self.assertFalse(
                key.startswith("azure_monitor_"),
                f"Prefixed key '{key}' should have been remapped",
            )
        self.assertNotIn("enable_azure_monitor", actual)


class TestSetupLogging(unittest.TestCase):
    """Tests for _setup_logging()."""

    @patch("opentelemetry._logs.set_logger_provider")
    def test_creates_logger_provider(self, set_lp_mock):
        """_setup_logging creates and registers a LoggerProvider."""
        lp = _setup_logging(TEST_RESOURCE, {})
        self.assertIsNotNone(lp)
        set_lp_mock.assert_called_once()

    @patch("opentelemetry._logs.set_logger_provider")
    def test_adds_log_record_processors(self, set_lp_mock):
        """_setup_logging adds user-supplied log record processors."""
        lrp = MagicMock()
        lp = _setup_logging(TEST_RESOURCE, {"log_record_processors": [lrp]})
        self.assertIsNotNone(lp)

    @patch("opentelemetry._logs.set_logger_provider")
    def test_attaches_handler_for_logger_name(self, set_lp_mock):
        """_setup_logging attaches a LoggingHandler when logger_name is specified."""
        import logging

        test_logger_name = "test_distro_logging_handler"
        test_logger = logging.getLogger(test_logger_name)
        original_handlers = list(test_logger.handlers)

        try:
            _setup_logging(TEST_RESOURCE, {"logger_name": test_logger_name})
            # Should have added a handler
            self.assertGreater(len(test_logger.handlers), len(original_handlers))
        finally:
            # Cleanup: remove any handlers we added
            for h in list(test_logger.handlers):
                if h not in original_handlers:
                    test_logger.removeHandler(h)

    @patch("opentelemetry._logs.set_logger_provider")
    def test_attaches_handler_with_formatter(self, set_lp_mock):
        """_setup_logging sets formatter on handler when logging_formatter is provided."""
        import logging

        test_logger_name = "test_distro_logging_formatter"
        test_logger = logging.getLogger(test_logger_name)
        original_handlers = list(test_logger.handlers)
        formatter = logging.Formatter("%(message)s")

        try:
            _setup_logging(
                TEST_RESOURCE,
                {
                    "logger_name": test_logger_name,
                    "logging_formatter": formatter,
                },
            )
            new_handlers = [h for h in test_logger.handlers if h not in original_handlers]
            self.assertTrue(len(new_handlers) > 0)
            self.assertEqual(new_handlers[0].formatter, formatter)
        finally:
            for h in list(test_logger.handlers):
                if h not in original_handlers:
                    test_logger.removeHandler(h)


if __name__ == "__main__":
    unittest.main()
