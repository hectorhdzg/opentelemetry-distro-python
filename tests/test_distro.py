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

import os
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

from microsoft.opentelemetry._constants import (
    _A365_DISABLED_INSTRUMENTATIONS,
    _SUPPORTED_INSTRUMENTED_LIBRARIES,
)
from microsoft.opentelemetry._distro import (
    use_microsoft_opentelemetry,
    _append_a365_components,
    _append_spectra_components,
    _is_instrumentation_enabled,
    _setup_tracing,
    _setup_metrics,
    _setup_logging,
)

TEST_RESOURCE = Resource({"service.name": "test-service"})
TEST_CONNECTION_STRING = "InstrumentationKey=test-key;IngestionEndpoint=https://test.in.ai.azure.com/"


class TestUseMicrosoftOpenTelemetry(unittest.TestCase):
    """Tests for use_microsoft_opentelemetry() orchestration."""

    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_azure_monitor_disabled_by_default(self, append_mock, tracing_mock, metrics_mock, logging_mock):
        """Azure Monitor is disabled by default; components are not collected."""
        use_microsoft_opentelemetry()
        append_mock.assert_not_called()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_connection_string_remapped(self, append_mock):
        """azure_monitor_connection_string is remapped to connection_string."""
        use_microsoft_opentelemetry(
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            enable_azure_monitor=True,
        )
        _, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["connection_string"], TEST_CONNECTION_STRING)

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_azure_monitor_kwargs_remapped(self, append_mock):
        """azure_monitor_ prefixed kwargs are remapped to internal names."""
        use_microsoft_opentelemetry(
            enable_azure_monitor=True,
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
            enable_azure_monitor=True,
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
        use_microsoft_opentelemetry(disable_tracing=True)
        tracing_mock.assert_not_called()
        metrics_mock.assert_called_once()
        logging_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_disable_metrics_skips_metrics(self, tracing_mock, metrics_mock, logging_mock):
        """disable_metrics=True skips MeterProvider creation."""
        use_microsoft_opentelemetry(disable_metrics=True)
        tracing_mock.assert_called_once()
        metrics_mock.assert_not_called()
        logging_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_disable_logging_skips_logging(self, tracing_mock, metrics_mock, logging_mock):
        """disable_logging=True skips LoggerProvider creation."""
        use_microsoft_opentelemetry(disable_logging=True)
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
            enable_azure_monitor=True,
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        append_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_providers_created_by_azure_monitor(self, append_mock):
        """Providers are created by Azure Monitor _setup_* and registered by distro."""
        use_microsoft_opentelemetry(
            enable_azure_monitor=True,
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        append_mock.assert_called_once()

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_otel_and_azure_kwargs_forwarded(self, append_mock):
        """Both OTel and Azure Monitor kwargs are forwarded to component collection."""
        use_microsoft_opentelemetry(
            enable_azure_monitor=True,
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
            enable_azure_monitor=True,
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
            azure_monitor_enable_live_metrics=False,
        )
        _, azure_kwargs = append_mock.call_args[0]
        self.assertEqual(azure_kwargs["enable_live_metrics"], False)

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_enable_performance_counters_passed_through(self, append_mock):
        """azure_monitor_enable_performance_counters is remapped and forwarded."""
        use_microsoft_opentelemetry(
            enable_azure_monitor=True,
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
            enable_azure_monitor=True,
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


class TestA365KwargsConfiguration(unittest.TestCase):
    """Tests for A365 kwargs precedence and forwarding in _append_a365_components."""

    @patch("microsoft.opentelemetry._distro._append_a365_components")
    def test_a365_kwargs_forwarded(self, a365_mock):
        """A365 kwargs are parsed and forwarded to _append_a365_components."""

        def token_fn(aid, tid):
            return "token"

        use_microsoft_opentelemetry(
            enable_a365=True,
            a365_token_resolver=token_fn,
            a365_cluster_category="gov",
            a365_use_s2s_endpoint=True,
            a365_suppress_invoke_agent_input=True,
        )
        a365_mock.assert_called_once()
        _, kwargs = a365_mock.call_args
        self.assertEqual(kwargs["token_resolver"], token_fn)
        self.assertEqual(kwargs["cluster_category"], "gov")
        self.assertEqual(kwargs["use_s2s_endpoint"], True)
        self.assertEqual(kwargs["suppress_invoke_agent_input"], True)

    @patch("microsoft.opentelemetry._distro._append_a365_components")
    def test_a365_not_called_when_disabled(self, a365_mock):
        """_append_a365_components is called with enable_a365=False (skips internally)."""
        use_microsoft_opentelemetry()
        a365_mock.assert_called_once()
        args = a365_mock.call_args[0]
        self.assertFalse(args[0])  # enable_a365=False

    @patch("microsoft.opentelemetry._distro._append_a365_components")
    def test_a365_kwargs_not_leaked_to_otel(self, a365_mock):
        """A365 kwargs are consumed and not forwarded to OTel kwargs."""
        use_microsoft_opentelemetry(
            enable_a365=True,
            enable_azure_monitor=False,
        )
        otel_kwargs = a365_mock.call_args[0][1]
        self.assertNotIn("enable_a365", otel_kwargs)

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver")
    def test_tenant_and_agent_ids_not_sourced_from_env(self, default_resolver_mock):

        default_resolver_mock.return_value = lambda aid, tid: "token"

        env = {
            "A365_TENANT_ID": "env-tenant",
            "A365_AGENT_ID": "env-agent",
        }
        with patch.dict("os.environ", env, clear=False):
            otel_kwargs = {"span_processors": []}
            _append_a365_components(True, otel_kwargs)

        processors = otel_kwargs["span_processors"]
        self.assertEqual(len(processors), 2)

        baggage_proc = processors[0]
        self.assertIsNone(baggage_proc._tenant_id)
        self.assertIsNone(baggage_proc._agent_id)

    def test_a365_skipped_when_disabled(self):
        """No processors added when enable_a365=False."""
        otel_kwargs = {"span_processors": []}
        _append_a365_components(False, otel_kwargs)
        self.assertEqual(otel_kwargs["span_processors"], [])

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver", return_value=None)
    def test_baggage_processor_registered_when_no_token_resolver(self, resolver_mock):
        """A365SpanProcessor is registered even when no token resolver is available."""
        from microsoft.opentelemetry.a365.core.exporters.span_processor import A365SpanProcessor

        otel_kwargs = {"span_processors": []}
        _append_a365_components(True, otel_kwargs)

        processors = otel_kwargs["span_processors"]
        self.assertEqual(len(processors), 1)
        self.assertIsInstance(processors[0], A365SpanProcessor)

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver")
    def test_exporter_registered_when_a365_enabled_with_resolver(self, default_resolver_mock):
        """When enable_a365=True and a token resolver is available, the
        Agent365 exporter span processor is added alongside A365SpanProcessor."""
        default_resolver_mock.return_value = lambda aid, tid: "token"
        from microsoft.opentelemetry.a365.core.exporters.span_processor import A365SpanProcessor

        otel_kwargs = {"span_processors": []}
        _append_a365_components(True, otel_kwargs)

        processors = otel_kwargs["span_processors"]
        # Two processors: A365SpanProcessor + Agent365 exporter processor
        self.assertEqual(len(processors), 2)
        self.assertIsInstance(processors[0], A365SpanProcessor)

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver")
    def test_cluster_category_kwarg_overrides_env(self, default_resolver_mock):
        """a365_cluster_category kwarg takes precedence over A365_CLUSTER_CATEGORY env var."""
        default_resolver_mock.return_value = lambda aid, tid: "token"

        with (
            patch.dict("os.environ", {"A365_CLUSTER_CATEGORY": "mooncake"}, clear=False),
            patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter") as exporter_mock,
        ):
            otel_kwargs = {"span_processors": []}
            _append_a365_components(True, otel_kwargs, cluster_category="gov")

        _, exporter_kwargs = exporter_mock.call_args
        self.assertEqual(exporter_kwargs["cluster_category"], "gov")

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver")
    def test_cluster_category_falls_back_to_env(self, default_resolver_mock):
        """A365_CLUSTER_CATEGORY env var is used when kwarg not provided."""
        default_resolver_mock.return_value = lambda aid, tid: "token"

        with (
            patch.dict("os.environ", {"A365_CLUSTER_CATEGORY": "gov"}, clear=False),
            patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter") as exporter_mock,
        ):
            otel_kwargs = {"span_processors": []}
            _append_a365_components(True, otel_kwargs)

        _, exporter_kwargs = exporter_mock.call_args
        self.assertEqual(exporter_kwargs["cluster_category"], "gov")

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver")
    def test_cluster_category_defaults_to_prod(self, default_resolver_mock):
        """cluster_category defaults to 'prod' when neither kwarg nor env var is set."""
        default_resolver_mock.return_value = lambda aid, tid: "token"

        env = {k: v for k, v in os.environ.items() if k != "A365_CLUSTER_CATEGORY"}
        with (
            patch.dict("os.environ", env, clear=True),
            patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter") as exporter_mock,
        ):
            otel_kwargs = {"span_processors": []}
            _append_a365_components(True, otel_kwargs)

        _, exporter_kwargs = exporter_mock.call_args
        self.assertEqual(exporter_kwargs["cluster_category"], "prod")


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
            enable_azure_monitor=True,
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
            use_microsoft_opentelemetry(enable_a365=True)

        from opentelemetry.trace import get_tracer_provider

        tp = get_tracer_provider()
        self.assertIsNotNone(tp)


class TestEnabledByDistro(unittest.TestCase):
    """Tests for _enabled_by_distro flag in OpenTelemetryScope."""

    def setUp(self):
        from microsoft.opentelemetry.a365.core.opentelemetry_scope import OpenTelemetryScope

        self._scope_cls = OpenTelemetryScope
        self._original = OpenTelemetryScope._enabled_by_distro

    def tearDown(self):
        self._scope_cls._enabled_by_distro = self._original

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver", return_value=None)
    def test_enabled_by_distro_set_when_a365_enabled(self, resolver_mock):
        """_enabled_by_distro is True after _append_a365_components(True, ...)."""
        self._scope_cls._enabled_by_distro = False
        otel_kwargs = {"span_processors": []}
        _append_a365_components(True, otel_kwargs)
        self.assertTrue(self._scope_cls._enabled_by_distro)

    def test_enabled_by_distro_not_set_when_tracing_disabled(self):
        """_enabled_by_distro stays False when disable_tracing=True."""
        self._scope_cls._enabled_by_distro = False
        otel_kwargs = {"span_processors": [], "disable_tracing": True}
        _append_a365_components(True, otel_kwargs)
        self.assertFalse(self._scope_cls._enabled_by_distro)

    def test_enabled_by_distro_not_set_when_a365_disabled(self):
        """_enabled_by_distro stays False when enable_a365=False."""
        self._scope_cls._enabled_by_distro = False
        otel_kwargs = {"span_processors": []}
        _append_a365_components(False, otel_kwargs)
        self.assertFalse(self._scope_cls._enabled_by_distro)

    @patch("microsoft.opentelemetry.a365.core.exporters.utils._create_default_token_resolver", return_value=None)
    def test_telemetry_enabled_without_env_vars_when_distro_sets_flag(self, resolver_mock):
        """_is_telemetry_enabled() returns True via distro flag without env vars."""
        env = {k: v for k, v in os.environ.items() if k not in ("ENABLE_OBSERVABILITY", "ENABLE_A365_OBSERVABILITY")}
        with patch.dict("os.environ", env, clear=True):
            otel_kwargs = {"span_processors": []}
            _append_a365_components(True, otel_kwargs)
            self.assertTrue(self._scope_cls._is_telemetry_enabled())

    def test_env_false_overrides_distro_flag(self):
        """ENABLE_OBSERVABILITY=false overrides _enabled_by_distro."""
        self._scope_cls._enabled_by_distro = True
        with patch.dict("os.environ", {"ENABLE_OBSERVABILITY": "false"}, clear=False):
            self.assertFalse(self._scope_cls._is_telemetry_enabled())


class TestSpectraComponents(unittest.TestCase):
    """Tests for Spectra sidecar _append_spectra_components."""

    def test_spectra_skipped_when_disabled(self):
        """No processors added when enable_spectra=False."""
        otel_kwargs = {"span_processors": []}
        _append_spectra_components(False, otel_kwargs)
        self.assertEqual(otel_kwargs["span_processors"], [])

    def test_spectra_skipped_when_tracing_disabled(self):
        """No processors added when disable_tracing=True."""
        otel_kwargs = {"span_processors": [], "disable_tracing": True}
        _append_spectra_components(True, otel_kwargs)
        self.assertEqual(otel_kwargs["span_processors"], [])

    @patch(
        "microsoft.opentelemetry._distro.os.environ",
        {"SPECTRA_PROTOCOL": "grpc"},
    )
    def test_grpc_fallback_to_http_when_grpc_unavailable(self):
        """Falls back to HTTP when gRPC package is not installed."""
        mock_http_exporter = MagicMock()

        otel_kwargs = {}
        with patch.dict(
            "sys.modules",
            {
                "opentelemetry.exporter.otlp.proto.grpc": None,
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
            },
        ):
            with patch(
                "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
                return_value=mock_http_exporter,
            ):
                _append_spectra_components(True, otel_kwargs, protocol="grpc")

        processors = otel_kwargs.get("span_processors", [])
        self.assertEqual(len(processors), 1)

    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
    )
    def test_http_protocol_uses_http_exporter(self, mock_exporter_cls):
        """protocol='http' uses HTTP exporter directly."""
        mock_exporter_cls.return_value = MagicMock()
        otel_kwargs = {}
        _append_spectra_components(True, otel_kwargs, protocol="http")
        mock_exporter_cls.assert_called_once()
        call_kwargs = mock_exporter_cls.call_args
        self.assertIn("localhost:4318", str(call_kwargs))
        self.assertEqual(len(otel_kwargs.get("span_processors", [])), 1)

    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
    )
    def test_http_custom_endpoint(self, mock_exporter_cls):
        """Custom endpoint is forwarded to the exporter."""
        mock_exporter_cls.return_value = MagicMock()
        _append_spectra_components(True, {}, protocol="http", endpoint="http://spectra.local:9999")
        call_kwargs = mock_exporter_cls.call_args
        self.assertEqual(call_kwargs[1]["endpoint"], "http://spectra.local:9999")

    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
    )
    def test_env_var_endpoint_used_as_fallback(self, mock_exporter_cls):
        """SPECTRA_ENDPOINT env var is used when no kwarg provided."""
        mock_exporter_cls.return_value = MagicMock()
        with patch.dict("os.environ", {"SPECTRA_ENDPOINT": "http://env-spectra:4318"}):
            _append_spectra_components(True, {}, protocol="http")
        call_kwargs = mock_exporter_cls.call_args
        self.assertEqual(call_kwargs[1]["endpoint"], "http://env-spectra:4318")

    @patch(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
    )
    def test_env_var_protocol(self, mock_exporter_cls):
        """SPECTRA_PROTOCOL env var selects protocol when kwarg not provided."""
        mock_exporter_cls.return_value = MagicMock()
        with patch.dict("os.environ", {"SPECTRA_PROTOCOL": "http"}):
            _append_spectra_components(True, {})
        mock_exporter_cls.assert_called_once()

    def test_no_exporter_packages_skips_gracefully(self):
        """When neither gRPC nor HTTP packages are installed, no crash."""
        otel_kwargs = {}
        with patch.dict(
            "sys.modules",
            {
                "opentelemetry.exporter.otlp.proto.grpc": None,
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
                "opentelemetry.exporter.otlp.proto.http": None,
                "opentelemetry.exporter.otlp.proto.http.trace_exporter": None,
            },
        ):
            _append_spectra_components(True, otel_kwargs, protocol="grpc")
        self.assertEqual(otel_kwargs.get("span_processors", []), [])

    @patch("microsoft.opentelemetry._distro._append_spectra_components")
    def test_spectra_kwargs_forwarded_from_entry_point(self, spectra_mock):
        """Spectra kwargs are parsed and forwarded from use_microsoft_opentelemetry."""
        use_microsoft_opentelemetry(
            enable_spectra=True,
            spectra_endpoint="http://my-sidecar:4317",
            spectra_protocol="grpc",
            spectra_insecure=False,
        )
        spectra_mock.assert_called_once()
        _, kwargs = spectra_mock.call_args
        self.assertEqual(kwargs["endpoint"], "http://my-sidecar:4317")
        self.assertEqual(kwargs["protocol"], "grpc")
        self.assertEqual(kwargs["insecure"], False)

    @patch("microsoft.opentelemetry._distro._append_spectra_components")
    def test_spectra_disabled_by_default(self, spectra_mock):
        """Spectra is disabled by default."""
        use_microsoft_opentelemetry()
        spectra_mock.assert_called_once()
        self.assertFalse(spectra_mock.call_args[0][0])

    @patch("microsoft.opentelemetry._distro._append_spectra_components")
    def test_spectra_kwargs_not_leaked_to_otel(self, spectra_mock):
        """Spectra kwargs are consumed and not forwarded to OTel kwargs."""
        use_microsoft_opentelemetry(
            enable_spectra=True,
            spectra_endpoint="http://localhost:4317",
        )
        otel_kwargs = spectra_mock.call_args[0][1]
        self.assertNotIn("enable_spectra", otel_kwargs)
        self.assertNotIn("spectra_endpoint", otel_kwargs)
        self.assertNotIn("spectra_protocol", otel_kwargs)
        self.assertNotIn("spectra_insecure", otel_kwargs)


class TestA365DisablesWebInstrumentations(unittest.TestCase):
    """When enable_a365=True, web/DB instrumentations are off by default."""

    _WEB_DB_LIBS = _A365_DISABLED_INSTRUMENTATIONS
    _GENAI_LIBS = tuple(lib for lib in _SUPPORTED_INSTRUMENTED_LIBRARIES if lib not in _A365_DISABLED_INSTRUMENTATIONS)

    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_web_db_disabled_when_a365_enabled(self, _trc, _met, _log, setup_inst):
        """Web/DB libs are disabled by default when A365 is on."""
        use_microsoft_opentelemetry(enable_a365=True)
        otel_kwargs = setup_inst.call_args[0][0]
        for lib in self._WEB_DB_LIBS:
            self.assertFalse(
                _is_instrumentation_enabled(otel_kwargs, lib),
                f"{lib} should be disabled when enable_a365=True",
            )

    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_genai_still_enabled_when_a365_enabled(self, _trc, _met, _log, setup_inst):
        """GenAI libs remain enabled when A365 is on."""
        use_microsoft_opentelemetry(enable_a365=True)
        otel_kwargs = setup_inst.call_args[0][0]
        for lib in self._GENAI_LIBS:
            self.assertTrue(
                _is_instrumentation_enabled(otel_kwargs, lib),
                f"{lib} should still be enabled when enable_a365=True",
            )

    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_user_can_override_disabled_lib(self, _trc, _met, _log, setup_inst):
        """User can explicitly re-enable a web lib even with A365 on."""
        use_microsoft_opentelemetry(
            enable_a365=True,
            instrumentation_options={"django": {"enabled": True}},
        )
        otel_kwargs = setup_inst.call_args[0][0]
        self.assertTrue(
            _is_instrumentation_enabled(otel_kwargs, "django"),
            "django should be enabled when user explicitly overrides",
        )
        # Other web libs should still be disabled
        self.assertFalse(
            _is_instrumentation_enabled(otel_kwargs, "flask"),
            "flask should still be disabled",
        )

    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_no_effect_when_a365_disabled(self, _trc, _met, _log, setup_inst):
        """Without enable_a365, all instrumentations remain enabled by default."""
        use_microsoft_opentelemetry()
        otel_kwargs = setup_inst.call_args[0][0]
        for lib in self._WEB_DB_LIBS:
            self.assertTrue(
                _is_instrumentation_enabled(otel_kwargs, lib),
                f"{lib} should be enabled when a365 is off",
            )

    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    @patch("microsoft.opentelemetry._distro._setup_instrumentations")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_a365_defaults_skipped_when_azure_monitor_also_enabled(self, _trc, _met, _log, setup_inst, _az):
        """When both enable_a365 and enable_azure_monitor are True, the
        non-A365 (original) defaults are preserved so web/HTTP libs stay on."""
        use_microsoft_opentelemetry(
            enable_a365=True,
            enable_azure_monitor=True,
            azure_monitor_connection_string=TEST_CONNECTION_STRING,
        )
        otel_kwargs = setup_inst.call_args[0][0]
        for lib in self._WEB_DB_LIBS:
            self.assertTrue(
                _is_instrumentation_enabled(otel_kwargs, lib),
                f"{lib} should remain enabled when both a365 and azure_monitor are on",
            )


if __name__ == "__main__":
    unittest.main()
