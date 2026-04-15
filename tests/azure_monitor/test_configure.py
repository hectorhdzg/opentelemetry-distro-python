# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import unittest
from unittest.mock import Mock, patch

from opentelemetry.sdk.resources import Resource

from microsoft.opentelemetry._azure_monitor._configure import (
    _send_attach_warning,
    _setup_logging,
    _setup_live_metrics,
    _setup_metrics,
    _setup_tracing,
    configure_azure_monitor,
)
from microsoft.opentelemetry._azure_monitor._diagnostics.diagnostic_logging import _DISTRO_DETECTS_ATTACH
from microsoft.opentelemetry._distro import _setup_instrumentations

TEST_RESOURCE = Resource({"foo": "bar"})


# pylint: disable=too-many-public-methods
class TestConfigure(unittest.TestCase):
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_browser_sdk_loader")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_azure_instrumentations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_live_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_logging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_tracing")
    @patch("microsoft.opentelemetry._azure_monitor._configure._get_configurations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._send_attach_warning")
    def test_configure_azure_monitor(
        self,
        attach_mock,
        get_config_mock,
        setup_tracing_mock,
        setup_metrics_mock,
        setup_logging_mock,
        setup_live_metrics_mock,
        setup_azure_instr_mock,
        setup_browser_mock,
    ):
        configurations = {
            "disable_tracing": False,
            "disable_logging": False,
            "disable_metrics": False,
            "enable_live_metrics": True,
            "resource": TEST_RESOURCE,
        }
        get_config_mock.return_value = configurations
        configure_azure_monitor(connection_string="test_cs")
        attach_mock.assert_called_once()
        get_config_mock.assert_called_once_with(connection_string="test_cs")
        setup_metrics_mock.assert_called_once_with(configurations)
        setup_live_metrics_mock.assert_called_once_with(configurations)
        setup_tracing_mock.assert_called_once_with(configurations)
        setup_logging_mock.assert_called_once_with(configurations)
        setup_azure_instr_mock.assert_called_once_with(configurations)
        setup_browser_mock.assert_called_once_with(configurations)

    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_browser_sdk_loader")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_azure_instrumentations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_live_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_logging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_tracing")
    @patch("microsoft.opentelemetry._azure_monitor._configure._get_configurations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._send_attach_warning")
    def test_configure_azure_monitor_disable_tracing(
        self,
        attach_mock,
        get_config_mock,
        setup_tracing_mock,
        setup_metrics_mock,
        setup_logging_mock,
        setup_live_metrics_mock,
        setup_azure_instr_mock,
        setup_browser_mock,
    ):
        configurations = {
            "disable_tracing": True,
            "disable_logging": False,
            "disable_metrics": False,
            "enable_live_metrics": True,
            "resource": TEST_RESOURCE,
        }
        get_config_mock.return_value = configurations
        configure_azure_monitor()
        setup_tracing_mock.assert_not_called()
        setup_metrics_mock.assert_called_once_with(configurations)
        setup_logging_mock.assert_called_once_with(configurations)
        setup_live_metrics_mock.assert_called_once_with(configurations)
        setup_azure_instr_mock.assert_called_once_with(configurations)
        setup_browser_mock.assert_called_once_with(configurations)

    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_browser_sdk_loader")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_azure_instrumentations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_live_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_logging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_tracing")
    @patch("microsoft.opentelemetry._azure_monitor._configure._get_configurations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._send_attach_warning")
    def test_configure_azure_monitor_disable_logging(
        self,
        attach_mock,
        get_config_mock,
        setup_tracing_mock,
        setup_metrics_mock,
        setup_logging_mock,
        setup_live_metrics_mock,
        setup_azure_instr_mock,
        setup_browser_mock,
    ):
        configurations = {
            "disable_tracing": False,
            "disable_logging": True,
            "disable_metrics": False,
            "enable_live_metrics": True,
            "resource": TEST_RESOURCE,
        }
        get_config_mock.return_value = configurations
        configure_azure_monitor()
        setup_tracing_mock.assert_called_once_with(configurations)
        setup_logging_mock.assert_not_called()
        setup_metrics_mock.assert_called_once_with(configurations)
        setup_live_metrics_mock.assert_called_once_with(configurations)
        setup_azure_instr_mock.assert_called_once_with(configurations)
        setup_browser_mock.assert_called_once_with(configurations)

    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_browser_sdk_loader")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_azure_instrumentations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_live_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_logging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_tracing")
    @patch("microsoft.opentelemetry._azure_monitor._configure._get_configurations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._send_attach_warning")
    def test_configure_azure_monitor_disable_metrics(
        self,
        attach_mock,
        get_config_mock,
        setup_tracing_mock,
        setup_metrics_mock,
        setup_logging_mock,
        setup_live_metrics_mock,
        setup_azure_instr_mock,
        setup_browser_mock,
    ):
        configurations = {
            "disable_tracing": False,
            "disable_logging": False,
            "disable_metrics": True,
            "enable_live_metrics": True,
            "resource": TEST_RESOURCE,
        }
        get_config_mock.return_value = configurations
        configure_azure_monitor()
        setup_tracing_mock.assert_called_once_with(configurations)
        setup_metrics_mock.assert_not_called()
        setup_logging_mock.assert_called_once_with(configurations)
        setup_live_metrics_mock.assert_called_once_with(configurations)
        setup_azure_instr_mock.assert_called_once_with(configurations)
        setup_browser_mock.assert_called_once_with(configurations)

    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_browser_sdk_loader")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_azure_instrumentations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_live_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_logging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_tracing")
    @patch("microsoft.opentelemetry._azure_monitor._configure._get_configurations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._send_attach_warning")
    def test_configure_azure_monitor_enable_live_metrics(
        self,
        attach_mock,
        get_config_mock,
        setup_tracing_mock,
        setup_metrics_mock,
        setup_logging_mock,
        setup_live_metrics_mock,
        setup_azure_instr_mock,
        setup_browser_mock,
    ):
        configurations = {
            "disable_tracing": False,
            "disable_logging": False,
            "disable_metrics": False,
            "enable_live_metrics": True,
            "resource": TEST_RESOURCE,
        }
        get_config_mock.return_value = configurations
        configure_azure_monitor()
        setup_live_metrics_mock.assert_called_once_with(configurations)
        setup_tracing_mock.assert_called_once_with(configurations)
        setup_metrics_mock.assert_called_once_with(configurations)
        setup_logging_mock.assert_called_once_with(configurations)
        setup_azure_instr_mock.assert_called_once_with(configurations)
        setup_browser_mock.assert_called_once_with(configurations)

    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_browser_sdk_loader")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_azure_instrumentations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_live_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_logging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_metrics")
    @patch("microsoft.opentelemetry._azure_monitor._configure._setup_tracing")
    @patch("microsoft.opentelemetry._azure_monitor._configure._get_configurations")
    @patch("microsoft.opentelemetry._azure_monitor._configure._send_attach_warning")
    def test_configure_azure_monitor_disable_live_metrics(
        self,
        attach_mock,
        get_config_mock,
        setup_tracing_mock,
        setup_metrics_mock,
        setup_logging_mock,
        setup_live_metrics_mock,
        setup_azure_instr_mock,
        setup_browser_mock,
    ):
        configurations = {
            "disable_tracing": False,
            "disable_logging": False,
            "disable_metrics": False,
            "enable_live_metrics": False,
            "enable_performance_counters": False,
            "resource": TEST_RESOURCE,
        }
        get_config_mock.return_value = configurations
        configure_azure_monitor()
        setup_live_metrics_mock.assert_not_called()
        setup_tracing_mock.assert_called_once_with(configurations)
        setup_metrics_mock.assert_called_once_with(configurations)
        setup_logging_mock.assert_called_once_with(configurations)
        setup_azure_instr_mock.assert_called_once_with(configurations)
        setup_browser_mock.assert_called_once_with(configurations)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure._PerformanceCountersSpanProcessor",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.BatchSpanProcessor",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.AzureMonitorTraceExporter",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.ApplicationInsightsSampler",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.TracerProvider",
    )
    def test_setup_tracing(
        self,
        tp_mock,
        sampler_mock,
        trace_exporter_mock,
        bsp_mock,
        pcsp_mock,
    ):
        sampler_init_mock = Mock()
        sampler_mock.return_value = sampler_init_mock
        tp_init_mock = Mock()
        tp_mock.return_value = tp_init_mock
        trace_exp_init_mock = Mock()
        trace_exporter_mock.return_value = trace_exp_init_mock
        bsp_init_mock = Mock()
        bsp_mock.return_value = bsp_init_mock
        pcsp_init_mock = Mock()
        pcsp_mock.return_value = pcsp_init_mock

        custom_sp = Mock()
        configurations = {
            "connection_string": "test_cs",
            "enable_performance_counters": True,
            "instrumentation_options": {"azure_sdk": {"enabled": True}},
            "sampling_ratio": 0.5,
            "resource": TEST_RESOURCE,
            "span_processors": [custom_sp],
            "enable_live_metrics": False,
        }
        result = _setup_tracing(configurations)
        sampler_mock.assert_called_once_with(sampling_ratio=0.5)
        tp_mock.assert_called_once_with(sampler=sampler_init_mock, resource=TEST_RESOURCE)
        # Custom processor added first, then perf counters, then BSP
        tp_init_mock.add_span_processor.assert_any_call(custom_sp)
        trace_exporter_mock.assert_called_once_with(**configurations)
        bsp_mock.assert_called_once_with(trace_exp_init_mock)
        pcsp_mock.assert_called_once_with()
        self.assertEqual(result, tp_init_mock)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure._PerformanceCountersSpanProcessor",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.BatchSpanProcessor",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.AzureMonitorTraceExporter",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.RateLimitedSampler",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.TracerProvider",
    )
    def test_setup_tracing_rate_limited_sampler(
        self,
        tp_mock,
        sampler_mock,
        trace_exporter_mock,
        bsp_mock,
        pcsp_mock,
    ):
        sampler_init_mock = Mock()
        sampler_mock.return_value = sampler_init_mock
        tp_init_mock = Mock()
        tp_mock.return_value = tp_init_mock
        trace_exp_init_mock = Mock()
        trace_exporter_mock.return_value = trace_exp_init_mock
        bsp_init_mock = Mock()
        bsp_mock.return_value = bsp_init_mock
        pcsp_init_mock = Mock()
        pcsp_mock.return_value = pcsp_init_mock

        custom_sp = Mock()
        configurations = {
            "connection_string": "test_cs",
            "enable_performance_counters": True,
            "instrumentation_options": {"azure_sdk": {"enabled": True}},
            "traces_per_second": 2.0,
            "resource": TEST_RESOURCE,
            "span_processors": [custom_sp],
            "enable_live_metrics": False,
        }
        result = _setup_tracing(configurations)
        sampler_mock.assert_called_once_with(target_spans_per_second_limit=2.0)
        tp_mock.assert_called_once_with(sampler=sampler_init_mock, resource=TEST_RESOURCE)
        tp_init_mock.add_span_processor.assert_any_call(custom_sp)
        trace_exporter_mock.assert_called_once_with(**configurations)
        bsp_mock.assert_called_once_with(trace_exp_init_mock)
        pcsp_mock.assert_called_once_with()
        self.assertEqual(result, tp_init_mock)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure._PerformanceCountersSpanProcessor",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.BatchSpanProcessor",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.AzureMonitorTraceExporter",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.ApplicationInsightsSampler",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.TracerProvider",
    )
    def test_setup_tracing_perf_counters_disabled(
        self,
        tp_mock,
        sampler_mock,
        trace_exporter_mock,
        bsp_mock,
        pcsp_mock,
    ):
        sampler_init_mock = Mock()
        sampler_mock.return_value = sampler_init_mock
        tp_init_mock = Mock()
        tp_mock.return_value = tp_init_mock
        trace_exp_init_mock = Mock()
        trace_exporter_mock.return_value = trace_exp_init_mock
        bsp_init_mock = Mock()
        bsp_mock.return_value = bsp_init_mock

        custom_sp = Mock()
        configurations = {
            "connection_string": "test_cs",
            "enable_performance_counters": False,
            "instrumentation_options": {"azure_sdk": {"enabled": True}},
            "sampling_ratio": 0.5,
            "resource": TEST_RESOURCE,
            "span_processors": [custom_sp],
            "enable_live_metrics": False,
        }
        result = _setup_tracing(configurations)
        sampler_mock.assert_called_once_with(sampling_ratio=0.5)
        tp_mock.assert_called_once_with(sampler=sampler_init_mock, resource=TEST_RESOURCE)
        tp_init_mock.add_span_processor.assert_any_call(custom_sp)
        trace_exporter_mock.assert_called_once_with(**configurations)
        bsp_mock.assert_called_once_with(trace_exp_init_mock)
        pcsp_mock.assert_not_called()
        self.assertEqual(result, tp_init_mock)

    @patch("microsoft.opentelemetry._azure_monitor._configure._PerformanceCountersLogRecordProcessor")
    def test_setup_logging(self, pclp_mock):
        log_exporter_mock = Mock()
        blrp_mock = Mock()

        log_exp_init_mock = Mock()
        log_exporter_mock.return_value = log_exp_init_mock
        blrp_init_mock = Mock()
        blrp_mock.return_value = blrp_init_mock
        pclp_init_mock = Mock()
        pclp_mock.return_value = pclp_init_mock
        custom_lrp = Mock()

        configurations = {
            "connection_string": "test_cs",
            "enable_performance_counters": True,
            "resource": TEST_RESOURCE,
            "enable_trace_based_sampling_for_logs": False,
            "log_record_processors": [custom_lrp],
            "enable_live_metrics": False,
            "logger_name": "",
        }

        with patch.dict(
            "sys.modules",
            {
                "azure.monitor.opentelemetry.exporter.export.logs._processor": Mock(
                    _AzureBatchLogRecordProcessor=blrp_mock
                ),
                "azure.monitor.opentelemetry.exporter": Mock(AzureMonitorLogExporter=log_exporter_mock),
            },
        ):
            result = _setup_logging(configurations)

        log_exporter_mock.assert_called_once_with(**configurations)
        blrp_mock.assert_called_once_with(log_exp_init_mock, {"enable_trace_based_sampling_for_logs": False})
        pclp_mock.assert_called_once_with()
        self.assertIsNotNone(result)

    @patch("microsoft.opentelemetry._azure_monitor._configure._PerformanceCountersLogRecordProcessor")
    def test_setup_logging_duplicate_logger(self, pclp_mock):
        log_exporter_mock = Mock()
        blrp_mock = Mock()

        log_exp_init_mock = Mock()
        log_exporter_mock.return_value = log_exp_init_mock
        blrp_init_mock = Mock()
        blrp_mock.return_value = blrp_init_mock
        pclp_init_mock = Mock()
        pclp_mock.return_value = pclp_init_mock
        custom_lrp = Mock()

        configurations = {
            "connection_string": "test_cs",
            "enable_performance_counters": True,
            "resource": TEST_RESOURCE,
            "enable_trace_based_sampling_for_logs": True,
            "log_record_processors": [custom_lrp],
            "enable_live_metrics": False,
            "logger_name": "",
        }

        with patch.dict(
            "sys.modules",
            {
                "azure.monitor.opentelemetry.exporter.export.logs._processor": Mock(
                    _AzureBatchLogRecordProcessor=blrp_mock
                ),
                "azure.monitor.opentelemetry.exporter": Mock(AzureMonitorLogExporter=log_exporter_mock),
            },
        ):
            result = _setup_logging(configurations)

        log_exporter_mock.assert_called_once_with(**configurations)
        blrp_mock.assert_called_once_with(log_exp_init_mock, {"enable_trace_based_sampling_for_logs": True})
        pclp_mock.assert_called_once_with()
        self.assertIsNotNone(result)

    @patch("microsoft.opentelemetry._azure_monitor._configure._PerformanceCountersLogRecordProcessor")
    def test_setup_logging_disable_performance_counters(self, pclp_mock):
        log_exporter_mock = Mock()
        blrp_mock = Mock()

        log_exp_init_mock = Mock()
        log_exporter_mock.return_value = log_exp_init_mock
        blrp_init_mock = Mock()
        blrp_mock.return_value = blrp_init_mock
        custom_lrp = Mock()

        configurations = {
            "connection_string": "test_cs",
            "enable_performance_counters": False,
            "resource": TEST_RESOURCE,
            "enable_trace_based_sampling_for_logs": False,
            "log_record_processors": [custom_lrp],
            "enable_live_metrics": False,
            "logger_name": "",
        }

        with patch.dict(
            "sys.modules",
            {
                "azure.monitor.opentelemetry.exporter.export.logs._processor": Mock(
                    _AzureBatchLogRecordProcessor=blrp_mock
                ),
                "azure.monitor.opentelemetry.exporter": Mock(AzureMonitorLogExporter=log_exporter_mock),
            },
        ):
            result = _setup_logging(configurations)

        log_exporter_mock.assert_called_once_with(**configurations)
        blrp_mock.assert_called_once_with(log_exp_init_mock, {"enable_trace_based_sampling_for_logs": False})
        pclp_mock.assert_not_called()
        self.assertIsNotNone(result)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.enable_performance_counters",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.MeterProvider",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.PeriodicExportingMetricReader",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.AzureMonitorMetricExporter",
    )
    def test_setup_metrics(self, metric_exporter_mock, reader_mock, mp_mock, perf_mock):
        metric_exp_init_mock = Mock()
        metric_exporter_mock.return_value = metric_exp_init_mock
        reader_init_mock = Mock()
        reader_mock.return_value = reader_init_mock
        mp_init_mock = Mock()
        mp_mock.return_value = mp_init_mock
        custom_reader = Mock()

        configurations = {
            "connection_string": "test_cs",
            "resource": TEST_RESOURCE,
            "views": [],
            "metric_readers": [custom_reader],
            "enable_performance_counters": True,
        }
        result = _setup_metrics(configurations)
        metric_exporter_mock.assert_called_once_with(**configurations)
        reader_mock.assert_called_once_with(metric_exp_init_mock)
        mp_mock.assert_called_once_with(
            metric_readers=[custom_reader, reader_init_mock],
            resource=TEST_RESOURCE,
            views=[],
        )
        perf_mock.assert_called_once_with(meter_provider=mp_init_mock)
        self.assertEqual(result, mp_init_mock)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.enable_performance_counters",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.MeterProvider",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.PeriodicExportingMetricReader",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.AzureMonitorMetricExporter",
    )
    def test_setup_metrics_views(self, metric_exporter_mock, reader_mock, mp_mock, perf_mock):
        metric_exp_init_mock = Mock()
        metric_exporter_mock.return_value = metric_exp_init_mock
        reader_init_mock = Mock()
        reader_mock.return_value = reader_init_mock
        mp_init_mock = Mock()
        mp_mock.return_value = mp_init_mock
        mock_view = Mock()
        custom_reader = Mock()

        configurations = {
            "connection_string": "test_cs",
            "resource": TEST_RESOURCE,
            "views": [mock_view],
            "metric_readers": [custom_reader],
            "enable_performance_counters": True,
        }
        result = _setup_metrics(configurations)
        metric_exporter_mock.assert_called_once_with(**configurations)
        reader_mock.assert_called_once_with(metric_exp_init_mock)
        mp_mock.assert_called_once_with(
            metric_readers=[custom_reader, reader_init_mock],
            resource=TEST_RESOURCE,
            views=[mock_view],
        )
        perf_mock.assert_called_once_with(meter_provider=mp_init_mock)
        self.assertEqual(result, mp_init_mock)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.enable_performance_counters",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.MeterProvider",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.PeriodicExportingMetricReader",
    )
    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.AzureMonitorMetricExporter",
    )
    def test_setup_metrics_perf_counters_disabled(self, metric_exporter_mock, reader_mock, mp_mock, perf_mock):
        metric_exp_init_mock = Mock()
        metric_exporter_mock.return_value = metric_exp_init_mock
        reader_init_mock = Mock()
        reader_mock.return_value = reader_init_mock
        mp_init_mock = Mock()
        mp_mock.return_value = mp_init_mock
        custom_reader = Mock()

        configurations = {
            "connection_string": "test_cs",
            "resource": TEST_RESOURCE,
            "views": [],
            "metric_readers": [custom_reader],
            "enable_performance_counters": False,
        }
        result = _setup_metrics(configurations)
        metric_exporter_mock.assert_called_once_with(**configurations)
        reader_mock.assert_called_once_with(metric_exp_init_mock)
        mp_mock.assert_called_once_with(
            metric_readers=[custom_reader, reader_init_mock],
            resource=TEST_RESOURCE,
            views=[],
        )
        perf_mock.assert_not_called()
        self.assertEqual(result, mp_init_mock)

    @patch(
        "microsoft.opentelemetry._azure_monitor._configure.enable_live_metrics",
    )
    def test_setup_live_metrics(
        self,
        enable_live_metrics_mock,
    ):
        configurations = {
            "connection_string": "test_cs",
            "resource": TEST_RESOURCE,
        }
        _setup_live_metrics(configurations)

        enable_live_metrics_mock.assert_called_once_with(**configurations)

    @patch("microsoft.opentelemetry._distro._SUPPORTED_INSTRUMENTED_LIBRARIES", ("test_instr2",))
    @patch("microsoft.opentelemetry._distro._is_instrumentation_enabled")
    @patch("microsoft.opentelemetry._distro.get_dist_dependency_conflicts")
    @patch("microsoft.opentelemetry._distro.entry_points")
    def test_setup_instrumentations_lib_not_supported(
        self,
        iter_mock,
        dep_mock,
        enabled_mock,
    ):
        ep_mock = Mock()
        ep2_mock = Mock()
        iter_mock.return_value = (ep_mock, ep2_mock)
        instrumentor_mock = Mock()
        instr_class_mock = Mock()
        instr_class_mock.return_value = instrumentor_mock
        ep_mock.name = "test_instr1"
        ep2_mock.name = "test_instr2"
        ep2_mock.load.return_value = instr_class_mock
        dep_mock.return_value = None
        enabled_mock.return_value = True
        _setup_instrumentations({})
        ep_mock.load.assert_not_called()
        ep2_mock.load.assert_called_once()
        instrumentor_mock.instrument.assert_called_once()

    @patch("microsoft.opentelemetry._distro._SUPPORTED_INSTRUMENTED_LIBRARIES", ("test_instr",))
    @patch("microsoft.opentelemetry._distro._is_instrumentation_enabled")
    @patch("microsoft.opentelemetry._distro._logger")
    @patch("microsoft.opentelemetry._distro.get_dist_dependency_conflicts")
    @patch("microsoft.opentelemetry._distro.entry_points")
    def test_setup_instrumentations_conflict(
        self,
        iter_mock,
        dep_mock,
        logger_mock,
        enabled_mock,
    ):
        ep_mock = Mock()
        iter_mock.return_value = (ep_mock,)
        instrumentor_mock = Mock()
        instr_class_mock = Mock()
        instr_class_mock.return_value = instrumentor_mock
        ep_mock.name = "test_instr"
        ep_mock.load.return_value = instr_class_mock
        dep_mock.return_value = True
        enabled_mock.return_value = True
        _setup_instrumentations({})
        ep_mock.load.assert_not_called()
        instrumentor_mock.instrument.assert_not_called()
        logger_mock.debug.assert_called_once()

    @patch("microsoft.opentelemetry._distro._SUPPORTED_INSTRUMENTED_LIBRARIES", ("test_instr",))
    @patch("microsoft.opentelemetry._distro._is_instrumentation_enabled")
    @patch("microsoft.opentelemetry._distro._logger")
    @patch("microsoft.opentelemetry._distro.get_dist_dependency_conflicts")
    @patch("microsoft.opentelemetry._distro.entry_points")
    def test_setup_instrumentations_exception(
        self,
        iter_mock,
        dep_mock,
        logger_mock,
        enabled_mock,
    ):
        ep_mock = Mock()
        iter_mock.return_value = (ep_mock,)
        instrumentor_mock = Mock()
        instr_class_mock = Mock()
        instr_class_mock.return_value = instrumentor_mock
        ep_mock.name = "test_instr"
        ep_mock.load.side_effect = Exception()
        dep_mock.return_value = None
        enabled_mock.return_value = True
        _setup_instrumentations({})
        ep_mock.load.assert_called_once()
        instrumentor_mock.instrument.assert_not_called()
        logger_mock.warning.assert_called_once()

    @patch(
        "microsoft.opentelemetry._distro._SUPPORTED_INSTRUMENTED_LIBRARIES",
        ("test_instr1", "test_instr2"),
    )
    @patch("microsoft.opentelemetry._distro._is_instrumentation_enabled")
    @patch("microsoft.opentelemetry._distro._logger")
    @patch("microsoft.opentelemetry._distro.get_dist_dependency_conflicts")
    @patch("microsoft.opentelemetry._distro.entry_points")
    def test_setup_instrumentations_disabled(
        self,
        iter_mock,
        dep_mock,
        logger_mock,
        enabled_mock,
    ):
        ep_mock = Mock()
        ep2_mock = Mock()
        iter_mock.return_value = (ep_mock, ep2_mock)
        instrumentor_mock = Mock()
        instr_class_mock = Mock()
        instr_class_mock.return_value = instrumentor_mock
        ep_mock.name = "test_instr1"
        ep2_mock.name = "test_instr2"
        ep2_mock.load.return_value = instr_class_mock
        dep_mock.return_value = None
        enabled_mock.side_effect = [False, True]
        _setup_instrumentations({})
        ep_mock.load.assert_not_called()
        ep2_mock.load.assert_called_once()
        instrumentor_mock.instrument.assert_called_once()
        logger_mock.debug.assert_called_once()

    @patch("microsoft.opentelemetry._azure_monitor._configure._logger")
    @patch("microsoft.opentelemetry._azure_monitor._configure.AzureDiagnosticLogging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._is_on_functions")
    @patch("microsoft.opentelemetry._azure_monitor._configure._is_attach_enabled")
    def test_send_attach_warning_true(
        self,
        is_attach_enabled_mock,
        is_on_functions_mock,
        mock_diagnostics,
        mock_logger,
    ):
        is_attach_enabled_mock.return_value = True
        is_on_functions_mock.return_value = False
        _send_attach_warning()
        message = (
            "Distro detected that automatic instrumentation may have occurred. Only use autoinstrumentation if you "
            "are not using manual instrumentation of OpenTelemetry in your code, such as with "
            "azure-monitor-opentelemetry or azure-monitor-opentelemetry-exporter. For App Service resources, disable "
            "autoinstrumentation in the Application Insights experience on your App Service resource or by setting "
            "the ApplicationInsightsAgent_EXTENSION_VERSION app setting to 'disabled'."
        )
        mock_logger.warning.assert_called_once_with(message)
        mock_diagnostics.warning.assert_called_once_with(
            message,
            _DISTRO_DETECTS_ATTACH,
        )

    @patch("microsoft.opentelemetry._azure_monitor._configure.AzureDiagnosticLogging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._is_on_functions")
    @patch("microsoft.opentelemetry._azure_monitor._configure._is_attach_enabled")
    def test_send_attach_warning_false(
        self,
        is_attach_enabled_mock,
        is_on_functions_mock,
        mock_diagnostics,
    ):
        is_attach_enabled_mock.return_value = False
        is_on_functions_mock.return_value = False
        _send_attach_warning()
        mock_diagnostics.warning.assert_not_called()

    @patch("microsoft.opentelemetry._azure_monitor._configure.AzureDiagnosticLogging")
    @patch("microsoft.opentelemetry._azure_monitor._configure._is_on_functions")
    @patch("microsoft.opentelemetry._azure_monitor._configure._is_attach_enabled")
    def test_send_attach_warning_false_on_functions(
        self,
        is_attach_enabled_mock,
        is_on_functions_mock,
        mock_diagnostics,
    ):
        is_attach_enabled_mock.return_value = True
        is_on_functions_mock.return_value = True
        _send_attach_warning()
        mock_diagnostics.warning.assert_not_called()
