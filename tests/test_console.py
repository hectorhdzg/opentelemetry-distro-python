# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Tests for the console exporter handler module.

Validates:
  1. ``create_console_components()`` returns the expected processor/reader types.
  2. Console components are wired into the distro's provider setup functions.
"""

import unittest
from unittest.mock import patch

from microsoft.opentelemetry._console.handler import (
    ConsoleHandlers,
    create_console_components,
)


class TestCreateConsoleComponents(unittest.TestCase):
    """Tests for create_console_components()."""

    def test_all_signals_enabled(self):
        components = create_console_components(enable_traces=True, enable_metrics=True, enable_logs=True)
        self.assertIsInstance(components, ConsoleHandlers)
        self.assertIsNotNone(components.span_processor)
        self.assertIsNotNone(components.metric_reader)
        self.assertIsNotNone(components.log_record_processor)

    def test_traces_only(self):
        components = create_console_components(enable_traces=True, enable_metrics=False, enable_logs=False)
        self.assertIsNotNone(components.span_processor)
        self.assertIsNone(components.metric_reader)
        self.assertIsNone(components.log_record_processor)

    def test_metrics_only(self):
        components = create_console_components(enable_traces=False, enable_metrics=True, enable_logs=False)
        self.assertIsNone(components.span_processor)
        self.assertIsNotNone(components.metric_reader)
        self.assertIsNone(components.log_record_processor)

    def test_logs_only(self):
        components = create_console_components(enable_traces=False, enable_metrics=False, enable_logs=True)
        self.assertIsNone(components.span_processor)
        self.assertIsNone(components.metric_reader)
        self.assertIsNotNone(components.log_record_processor)

    def test_all_disabled(self):
        components = create_console_components(enable_traces=False, enable_metrics=False, enable_logs=False)
        self.assertIsNone(components.span_processor)
        self.assertIsNone(components.metric_reader)
        self.assertIsNone(components.log_record_processor)

    def test_span_processor_is_simple(self):
        """Console uses SimpleSpanProcessor for immediate stdout output."""
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        components = create_console_components(enable_traces=True, enable_metrics=False, enable_logs=False)
        self.assertIsInstance(components.span_processor, SimpleSpanProcessor)

    def test_log_processor_is_simple(self):
        """Console uses SimpleLogRecordProcessor for immediate stdout output."""
        from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

        components = create_console_components(enable_traces=False, enable_metrics=False, enable_logs=True)
        self.assertIsInstance(components.log_record_processor, SimpleLogRecordProcessor)


class TestConsoleDistroIntegration(unittest.TestCase):
    """Tests that console components are wired into use_microsoft_opentelemetry()."""

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_console_not_enabled_when_azure_monitor_on(self, append_mock, otlp_utils_mock, otlp_distro_mock):
        """Console export is NOT auto-enabled when Azure Monitor is active."""
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_azure_monitor=True)
        otel_kwargs = append_mock.call_args[0][0]
        span_processors = otel_kwargs.get("span_processors", [])
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        self.assertFalse(any(isinstance(sp, SimpleSpanProcessor) for sp in span_processors))

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=True)
    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=True)
    @patch("microsoft.opentelemetry._utils.create_otlp_components")
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_console_not_enabled_when_otlp_on(
        self, tracing_mock, metrics_mock, logging_mock, otlp_create_mock, otlp_utils_mock, otlp_distro_mock
    ):
        """Console export is NOT auto-enabled when OTLP is active."""
        from microsoft.opentelemetry._otlp.handler import OtlpHandlers
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        otlp_create_mock.return_value = OtlpHandlers()

        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_azure_monitor=False)
        call_kwargs = tracing_mock.call_args[0][1]
        span_processors = call_kwargs.get("span_processors", [])
        self.assertFalse(any(isinstance(sp, SimpleSpanProcessor) for sp in span_processors))

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_console_auto_enables_when_all_off(
        self, tracing_mock, metrics_mock, logging_mock, otlp_utils_mock, otlp_distro_mock
    ):
        """Console auto-enables when Azure Monitor, OTLP, and A365 are all off."""
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        use_microsoft_opentelemetry(enable_azure_monitor=False, enable_a365=False)
        call_kwargs = tracing_mock.call_args[0][1]
        span_processors = call_kwargs.get("span_processors", [])
        self.assertTrue(any(isinstance(sp, SimpleSpanProcessor) for sp in span_processors))

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_console_enabled_via_kwarg(self, append_mock, otlp_utils_mock, otlp_distro_mock):
        """enable_console=True adds console processors even with Azure Monitor on."""
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_console=True, enable_azure_monitor=True)
        otel_kwargs = append_mock.call_args[0][0]
        span_processors = otel_kwargs.get("span_processors", [])
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        self.assertTrue(any(isinstance(sp, SimpleSpanProcessor) for sp in span_processors))

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._append_azure_monitor_components", return_value=(None, None, None))
    def test_console_kwarg_not_forwarded(self, append_mock, otlp_utils_mock, otlp_distro_mock):
        """enable_console is consumed, not forwarded to otel_kwargs."""
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_console=True)
        otel_kwargs = append_mock.call_args[0][0]
        self.assertNotIn("enable_console", otel_kwargs)

    @patch("microsoft.opentelemetry._distro.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._utils.is_otlp_enabled", return_value=False)
    @patch("microsoft.opentelemetry._distro._setup_logging")
    @patch("microsoft.opentelemetry._distro._setup_metrics")
    @patch("microsoft.opentelemetry._distro._setup_tracing")
    def test_console_respects_disable_tracing(
        self, tracing_mock, metrics_mock, logging_mock, otlp_utils_mock, otlp_distro_mock
    ):
        """Console does not add span processor when tracing is disabled."""
        from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

        use_microsoft_opentelemetry(enable_console=True, disable_tracing=True, enable_azure_monitor=False)
        tracing_mock.assert_not_called()
