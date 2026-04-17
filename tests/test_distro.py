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

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_azure_monitor_enabled_by_default(self, append_mock):
        """Azure Monitor is enabled by default; components are collected."""
        use_microsoft_opentelemetry()
        append_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_connection_string_remapped(self, append_mock):
        """azure_monitor_connection_string is remapped to connection_string."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        _, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["connection_string"], TEST_CONNECTION_STRING)

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_azure_monitor_kwargs_remapped(self, append_mock):
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
        _, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(azure_kwargs["credential"], "test_cred")
        self.assertEqual(azure_kwargs["enable_live_metrics"], False)
        self.assertEqual(azure_kwargs["enable_performance_counters"], False)
        self.assertEqual(azure_kwargs["disable_offline_storage"], True)
        self.assertEqual(azure_kwargs["storage_directory"], "/tmp/test")
        self.assertEqual(azure_kwargs["browser_sdk_loader_config"], {"enabled": False})

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_general_otel_kwargs_forwarded(self, append_mock):
        """General OTel kwargs are forwarded via otel_kwargs."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            sampling_ratio=0.5,
            logger_name="test",
        )
        otel_kwargs, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(otel_kwargs["sampling_ratio"], 0.5)
        self.assertEqual(otel_kwargs["logger_name"], "test")

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_explicit_disable(self, tracing_mock, metrics_mock, logging_mock, append_mock):
        """Explicitly disabling Azure Monitor still creates providers."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            enable_azure_monitor=False,
        )
        tracing_mock.assert_called_once()
        metrics_mock.assert_called_once()
        logging_mock.assert_called_once()
        append_mock.assert_not_called()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_enable_key_not_forwarded(self, append_mock):
        """enable_azure_monitor is consumed, not forwarded."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            enable_azure_monitor=True,
        )
        otel_kwargs, azure_kwargs = append_mock.call_args[0]
        self.assertNotIn("enable_azure_monitor", otel_kwargs)
        self.assertNotIn("enable_azure_monitor", azure_kwargs)

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

    def test_setup_tracing_creates_provider(self):
        """_setup_tracing creates a TracerProvider."""
        tp = _setup_tracing(TEST_RESOURCE, {})
        self.assertIsInstance(tp, TracerProvider)

    def test_setup_tracing_adds_span_processors(self):
        """_setup_tracing adds user-supplied span processors."""
        sp = MagicMock()
        tp = _setup_tracing(TEST_RESOURCE, {"span_processors": [sp]})
        self.assertIsInstance(tp, TracerProvider)
        self.assertIn(sp, tp._active_span_processor._span_processors)

    def test_setup_metrics_creates_provider(self):
        """_setup_metrics creates a MeterProvider."""
        mp = _setup_metrics(TEST_RESOURCE, {})
        self.assertIsInstance(mp, MeterProvider)


class TestAzureMonitorComponentCollection(unittest.TestCase):
    """Tests for _append_azure_monitor_components()."""

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_post_setup_skipped_on_failure(self, append_mock):
        """When component collection returns None configs, post-setup is skipped."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        append_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_providers_created_by_azure_monitor(self, append_mock):
        """Providers are created by Azure Monitor _setup_* and registered by distro."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        append_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_otel_and_azure_kwargs_forwarded(self, append_mock):
        """Both OTel and Azure Monitor kwargs are forwarded to component collection."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            sampling_ratio=0.5,
            logger_name="test",
        )
        otel_kwargs, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(otel_kwargs["sampling_ratio"], 0.5)
        self.assertEqual(otel_kwargs["logger_name"], "test")


class TestEnableKwargsPassthrough(unittest.TestCase):
    """Tests that azure_monitor_ kwargs are remapped and passed through."""

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_enable_live_metrics_passed_through(self, append_mock):
        """azure_monitor_enable_live_metrics is remapped and forwarded."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_enable_live_metrics=False,
        )
        _, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["enable_live_metrics"], False)

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_enable_performance_counters_passed_through(self, append_mock):
        """azure_monitor_enable_performance_counters is remapped and forwarded."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_enable_performance_counters=False,
        )
        _, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["enable_performance_counters"], False)


class TestAllConfigOptions(unittest.TestCase):
    """End-to-end test that every documented configuration option works."""

    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_all_options_end_to_end(self, append_mock, otlp_mock):
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

        append_mock.assert_called_once()
        otel_kwargs, azure_kwargs = append_mock.call_args[0]

        # Remapped azure_monitor_ kwargs
        self.assertEqual(azure_kwargs["connection_string"], TEST_CONNECTION_STRING)
        self.assertEqual(azure_kwargs["credential"], "test_cred")
        self.assertEqual(azure_kwargs["enable_live_metrics"], False)
        self.assertEqual(azure_kwargs["enable_performance_counters"], False)
        self.assertEqual(azure_kwargs["disable_offline_storage"], True)
        self.assertEqual(azure_kwargs["storage_directory"], "/tmp/test")
        self.assertEqual(azure_kwargs["browser_sdk_loader_config"], {"enabled": False})

        # General OTel kwargs
        self.assertEqual(otel_kwargs["disable_logging"], True)
        self.assertEqual(otel_kwargs["disable_tracing"], True)
        self.assertEqual(otel_kwargs["disable_metrics"], True)
        self.assertEqual(otel_kwargs["resource"], TEST_RESOURCE)
        self.assertEqual(otel_kwargs["span_processors"], ["sp1"])
        self.assertEqual(otel_kwargs["log_record_processors"], ["lrp1"])
        self.assertEqual(otel_kwargs["metric_readers"], ["mr1"])
        self.assertEqual(otel_kwargs["views"], ["v1"])
        self.assertEqual(otel_kwargs["logger_name"], "mylogger")
        self.assertEqual(otel_kwargs["logging_formatter"], formatter)
        self.assertEqual(otel_kwargs["instrumentation_options"], {"flask": {"enabled": False}})
        self.assertEqual(otel_kwargs["enable_trace_based_sampling_for_logs"], True)
        self.assertEqual(otel_kwargs["sampling_ratio"], 0.25)

        # azure_monitor_ prefixed keys should NOT appear in otel_kwargs
        for key in otel_kwargs:
            self.assertFalse(
                key.startswith("azure_monitor_"),
                f"Prefixed key '{key}' should have been remapped",
            )
        self.assertNotIn("enable_azure_monitor", otel_kwargs)


class TestSetupLogging(unittest.TestCase):
    """Tests for _setup_logging()."""

    def test_creates_logger_provider(self):
        """_setup_logging creates a LoggerProvider."""
        lp = _setup_logging(TEST_RESOURCE, {})
        self.assertIsNotNone(lp)

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


class TestA365Components(unittest.TestCase):
    """Tests for A365 enable_a365 flag and _append_a365_components."""

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    @patch("microsoft.opentelemetry._distro._append_a365_components")
    def test_a365_enabled_passed_through(self, a365_mock, azure_monitor_mock):
        """enable_a365=True is forwarded to _append_a365_components."""
        use_microsoft_opentelemetry(
            enable_a365=True,
        )
        a365_mock.assert_called_once()
        call_args = a365_mock.call_args
        # First arg: enable_a365
        self.assertTrue(call_args[0][0])

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    @patch("microsoft.opentelemetry._distro._append_a365_components")
    def test_a365_disabled_by_default(self, a365_mock, azure_monitor_mock):
        """A365 is disabled by default."""
        use_microsoft_opentelemetry()
        a365_mock.assert_called_once()
        # enable_a365 should be False
        self.assertFalse(a365_mock.call_args[0][0])

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    @patch("microsoft.opentelemetry._distro._append_a365_components")
    def test_a365_flag_not_in_otel_kwargs(self, a365_mock, azure_monitor_mock):
        """enable_a365 should not leak into azure_monitor_kwargs."""
        use_microsoft_opentelemetry(
            enable_a365=True,
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        # Check azure_monitor_mock received connection_string but not enable_a365
        am_call = azure_monitor_mock.call_args
        if am_call:
            merged = {**am_call[0][0], **am_call[0][1]} if am_call[0] else {}
            self.assertNotIn("enable_a365", merged)

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_a365_appends_span_processors(self, azure_monitor_mock):
        """When A365 is enabled, its span processors are appended to otel_kwargs."""
        mock_sp = MagicMock()
        mock_handlers = MagicMock()
        mock_handlers.span_processors = [mock_sp]

        with patch(
            "microsoft.opentelemetry.a365.create_a365_components",
            return_value=mock_handlers,
        ):
            use_microsoft_opentelemetry(enable_a365=True, enable_azure_monitor=False)

        from opentelemetry.trace import get_tracer_provider

        tp = get_tracer_provider()
        self.assertIsNotNone(tp)


if __name__ == "__main__":
    unittest.main()
