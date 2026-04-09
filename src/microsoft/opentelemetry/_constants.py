# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Shared constants for the Microsoft OpenTelemetry Distro.

Defines configuration argument names used by :func:`use_microsoft_opentelemetry`,
the mapping of public kwarg names to Azure Monitor internal keys, and the list
of supported auto-instrumented libraries.
"""

# --- Generic OTel Provider Constants ---

DISABLE_LOGGING_ARG = "disable_logging"
DISABLE_METRICS_ARG = "disable_metrics"
DISABLE_TRACING_ARG = "disable_tracing"
LOGGER_NAME_ARG = "logger_name"
LOGGING_FORMATTER_ARG = "logging_formatter"
LOG_RECORD_PROCESSORS_ARG = "log_record_processors"
METRIC_READERS_ARG = "metric_readers"
RESOURCE_ARG = "resource"
SPAN_PROCESSORS_ARG = "span_processors"
VIEWS_ARG = "views"
INSTRUMENTATION_OPTIONS_ARG = "instrumentation_options"

# --- Instrumentation Constants ---

_SUPPORTED_INSTRUMENTED_LIBRARIES = (
    "django",
    "fastapi",
    "flask",
    "psycopg2",
    "requests",
    "urllib",
    "urllib3",
)

# --- Microsoft Distro Constants ---

ENABLE_AZURE_MONITOR_ARG = "enable_azure_monitor"

# Mapping from azure_monitor_ prefixed public kwargs to internal
# configure_azure_monitor() kwargs.
_AZURE_MONITOR_KWARG_MAP = {
    "azure_monitor_connection_string": "connection_string",
    "azure_monitor_exporter_credential": "credential",
    "azure_monitor_enable_live_metrics": "enable_live_metrics",
    "azure_monitor_enable_performance_counters": "enable_performance_counters",
    "azure_monitor_exporter_disable_offline_storage": "disable_offline_storage",
    "azure_monitor_exporter_storage_directory": "storage_directory",
    "azure_monitor_browser_sdk_loader_config": "browser_sdk_loader_config",
}
