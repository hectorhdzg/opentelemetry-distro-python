# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Thread-safe global state for SDK self-telemetry (SDKStats).

Feature and instrumentation flags are stored as bitmasks so they can be
combined and reported efficiently.  The bitmask values are intentionally
compatible with the Azure Monitor Exporter statsbeat encoding so that
Azure Monitor consumers see no behavioural change.
"""

import os
import threading
from enum import IntFlag

# ---------------------------------------------------------------------------
# Environment variable to disable SDKStats globally
# ---------------------------------------------------------------------------

_SDKSTATS_DISABLED_ENV = "MICROSOFT_OTEL_SDKSTATS_DISABLED"

# Also honour the legacy Azure Monitor variable
_APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL = "APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL"


# ---------------------------------------------------------------------------
# Feature flags — bitmask values compatible with Azure Monitor statsbeat
# ---------------------------------------------------------------------------


class SdkStatsFeature(IntFlag):
    """Bit flags for distro features tracked by SDKStats."""

    NONE = 0
    AZURE_MONITOR_DISK_RETRY = 1
    AZURE_MONITOR_AAD = 2
    AZURE_MONITOR_CUSTOM_EVENTS_EXTENSION = 4
    DISTRO = 8
    AZURE_MONITOR_LIVE_METRICS = 16
    AZURE_MONITOR_CUSTOMER_SDKSTATS = 32
    AZURE_MONITOR_BROWSER_SDK_LOADER = 64
    A365_EXPORT = 128
    OTLP_EXPORT = 256
    CONSOLE_EXPORT = 512
    SPECTRA_EXPORT = 1024


# ---------------------------------------------------------------------------
# Instrumentation flags — bitmask values compatible with Azure Monitor
# ---------------------------------------------------------------------------


class SdkStatsInstrumentation(IntFlag):
    """Bit flags for library instrumentations tracked by SDKStats.

    Values are kept in sync with the Azure Monitor Exporter
    ``_INSTRUMENTATIONS_BIT_MAP`` so metrics are interoperable.
    """

    NONE = 0
    DJANGO = 1
    FLASK = 2
    PSYCOPG2 = 64
    REQUESTS = 1024
    FASTAPI = 4194304
    URLLIB = 68719476736
    URLLIB3 = 137438953472
    OPENAI_V2 = 4503599627370496
    # GenAI / agent instrumentations tracked by this distro
    LANGCHAIN = 1 << 55
    OPENAI_AGENTS = 1 << 56
    SEMANTIC_KERNEL = 1 << 57
    AGENT_FRAMEWORK = 1 << 58


# Mapping from instrumentation entry-point name → bit flag
_INSTRUMENTATION_NAME_MAP = {
    "django": SdkStatsInstrumentation.DJANGO,
    "flask": SdkStatsInstrumentation.FLASK,
    "psycopg2": SdkStatsInstrumentation.PSYCOPG2,
    "requests": SdkStatsInstrumentation.REQUESTS,
    "fastapi": SdkStatsInstrumentation.FASTAPI,
    "urllib": SdkStatsInstrumentation.URLLIB,
    "urllib3": SdkStatsInstrumentation.URLLIB3,
    "openai": SdkStatsInstrumentation.OPENAI_V2,
    "openai_agents": SdkStatsInstrumentation.OPENAI_AGENTS,
    "langchain": SdkStatsInstrumentation.LANGCHAIN,
    "semantic_kernel": SdkStatsInstrumentation.SEMANTIC_KERNEL,
    "agent_framework": SdkStatsInstrumentation.AGENT_FRAMEWORK,
}


# ---------------------------------------------------------------------------
# Global mutable state (thread-safe)
# ---------------------------------------------------------------------------

_STATE_LOCK = threading.Lock()

_SDKSTATS_STATE = {
    "SHUTDOWN": False,
    "FEATURE_FLAGS": SdkStatsFeature.NONE,
    "INSTRUMENTATION_FLAGS": SdkStatsInstrumentation.NONE,
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def is_sdkstats_enabled() -> bool:
    """Return ``True`` unless SDKStats has been disabled via env var."""
    for env_var in (_SDKSTATS_DISABLED_ENV, _APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL):
        val = os.environ.get(env_var, "").strip().lower()
        if val in ("true", "1", "yes", "on"):
            return False
    return True


def set_sdkstats_shutdown(shutdown: bool = True) -> None:
    with _STATE_LOCK:
        _SDKSTATS_STATE["SHUTDOWN"] = shutdown


def get_sdkstats_shutdown() -> bool:
    return _SDKSTATS_STATE["SHUTDOWN"]  # type: ignore[return-value]


# ---- Feature flags ----


def set_sdkstats_feature(flag: SdkStatsFeature) -> None:
    """Enable one or more feature flags (bitwise OR)."""
    with _STATE_LOCK:
        _SDKSTATS_STATE["FEATURE_FLAGS"] |= flag  # type: ignore[operator]


def get_sdkstats_feature_flags() -> int:
    """Return the current feature bitmask."""
    return int(_SDKSTATS_STATE["FEATURE_FLAGS"])  # type: ignore[arg-type]


# ---- Instrumentation flags ----


def set_sdkstats_instrumentation(flag: SdkStatsInstrumentation) -> None:
    """Enable one or more instrumentation flags (bitwise OR)."""
    with _STATE_LOCK:
        _SDKSTATS_STATE["INSTRUMENTATION_FLAGS"] |= flag  # type: ignore[operator]


def set_sdkstats_instrumentation_by_name(name: str) -> None:
    """Enable an instrumentation flag by its entry-point name.

    Unknown names are silently ignored.
    """
    flag = _INSTRUMENTATION_NAME_MAP.get(name)
    if flag:
        set_sdkstats_instrumentation(flag)


def get_sdkstats_instrumentation_flags() -> int:
    """Return the current instrumentation bitmask."""
    return int(_SDKSTATS_STATE["INSTRUMENTATION_FLAGS"])  # type: ignore[arg-type]
