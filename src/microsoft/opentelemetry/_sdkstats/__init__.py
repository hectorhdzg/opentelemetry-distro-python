# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""SDK self-telemetry (SDKStats) for the Microsoft OpenTelemetry Distro.

This module provides backend-agnostic SDK health and usage telemetry that
works regardless of which export backends are enabled (Azure Monitor, OTLP,
A365, Console).  It tracks:

- **Features**: which distro features are active (disk retry, AAD, live
  metrics, browser SDK loader, etc.)
- **Instrumentations**: which library instrumentations are enabled (Django,
  FastAPI, OpenAI, LangChain, etc.)

The module is initialised by :func:`use_microsoft_opentelemetry` during
distro setup and sends metrics to the Application Insights statsbeat
ingestion endpoint via ``AzureMonitorMetricExporter``.
"""

from microsoft.opentelemetry._sdkstats._state import (
    get_sdkstats_feature_flags,
    get_sdkstats_instrumentation_flags,
    is_sdkstats_enabled,
    set_sdkstats_feature,
    set_sdkstats_instrumentation,
    set_sdkstats_shutdown,
)
from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

__all__ = [
    "SdkStatsManager",
    "get_sdkstats_feature_flags",
    "get_sdkstats_instrumentation_flags",
    "is_sdkstats_enabled",
    "set_sdkstats_feature",
    "set_sdkstats_instrumentation",
    "set_sdkstats_shutdown",
]
