import importlib
from importlib.metadata import entry_points, version

import pytest
from azure.monitor.opentelemetry.exporter import (
    AzureMonitorLogExporter,
    AzureMonitorMetricExporter,
    AzureMonitorTraceExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


@pytest.mark.parametrize(
    ("distribution", "module"),
    [
        ("azure-core", "azure.core"),
        ("azure-core-tracing-opentelemetry", "azure.core.tracing.ext.opentelemetry_span"),
        ("azure-monitor-opentelemetry-exporter", "azure.monitor.opentelemetry.exporter"),
        ("opentelemetry-api", "opentelemetry.trace"),
        ("opentelemetry-exporter-otlp-proto-http", "opentelemetry.exporter.otlp.proto.http"),
        ("opentelemetry-instrumentation", "opentelemetry.instrumentation"),
        ("opentelemetry-resource-detector-azure", "opentelemetry.resource.detector.azure"),
        ("opentelemetry-sdk", "opentelemetry.sdk"),
        ("opentelemetry-util-genai", "opentelemetry.util.genai"),
    ],
)
def test_direct_dependency_distribution_and_module_are_available(distribution, module):
    assert version(distribution)
    assert importlib.import_module(module)


@pytest.mark.parametrize(
    ("group", "required_names"),
    [
        (
            "opentelemetry_instrumentor",
            {
                "django",
                "fastapi",
                "flask",
                "httpx",
                "httpx2",
                "logging",
                "psycopg2",
                "requests",
                "urllib",
                "urllib3",
            },
        ),
        ("opentelemetry_logs_exporter", {"azure_monitor_opentelemetry_exporter", "otlp_proto_http"}),
        ("opentelemetry_metrics_exporter", {"azure_monitor_opentelemetry_exporter", "otlp_proto_http"}),
        ("opentelemetry_propagator", {"baggage", "tracecontext"}),
        ("opentelemetry_traces_exporter", {"azure_monitor_opentelemetry_exporter", "otlp_proto_http"}),
        ("opentelemetry_traces_sampler", {"always_off", "always_on", "parentbased_traceidratio", "traceidratio"}),
    ],
)
def test_required_plugin_entry_points_load(group, required_names):
    plugins = {plugin.name: plugin for plugin in entry_points(group=group)}

    assert required_names <= plugins.keys()
    if group == "opentelemetry_instrumentor":
        return
    for name in required_names:
        assert plugins[name].load()


@pytest.mark.parametrize(
    ("exporter_class", "endpoint"),
    [
        (OTLPSpanExporter, "http://localhost:4318/v1/traces"),
        (OTLPMetricExporter, "http://localhost:4318/v1/metrics"),
        (OTLPLogExporter, "http://localhost:4318/v1/logs"),
    ],
)
def test_otlp_http_exporters_construct_and_shutdown(exporter_class, endpoint):
    exporter = exporter_class(endpoint=endpoint)

    exporter.shutdown()


@pytest.mark.parametrize(
    "exporter_class",
    [
        AzureMonitorTraceExporter,
        AzureMonitorMetricExporter,
        AzureMonitorLogExporter,
    ],
)
def test_azure_monitor_exporters_construct_and_shutdown(exporter_class):
    exporter = exporter_class(
        connection_string=(
            "InstrumentationKey=00000000-0000-0000-0000-000000000000;" "IngestionEndpoint=https://example.test/"
        ),
        disable_offline_storage=True,
    )

    exporter.shutdown()
