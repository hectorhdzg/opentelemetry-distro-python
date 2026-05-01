# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Observable metric callbacks for SDK self-telemetry.

Mirrors the Azure Monitor Exporter ``_StatsbeatMetrics`` feature/
instrumentation gauge pattern, but is backend-agnostic — the metrics are
collected into a caller-supplied ``MeterProvider``.
"""

from enum import Enum
import platform
from typing import Any, Dict, Iterable, List

from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider

from microsoft.opentelemetry._sdkstats._state import (
    get_sdkstats_feature_flags,
    get_sdkstats_instrumentation_flags,
)
from microsoft.opentelemetry._version import VERSION


class _RP_Names(Enum):
    APP_SERVICE = "appsvc"
    FUNCTIONS = "functions"
    AKS = "aks"
    VM = "vm"
    UNKNOWN = "unknown"


class _AttachTypes(Enum):
    MANUAL = "Manual"
    INTEGRATED = "IntegratedAuto"
    STANDALONE = "StandaloneAuto"


class _FeatureTypes(Enum):
    FEATURE = 0
    INSTRUMENTATION = 1


_FEATURE_METRIC_NAME = "feature"


class SdkStatsMetrics:
    """Registers observable gauges that emit feature/instrumentation data."""

    def __init__(
        self,
        meter_provider: MeterProvider,
        *,
        distro_version: str = "",
    ) -> None:
        self._meter = meter_provider.get_meter("microsoft.opentelemetry.sdkstats")
        self._distro_version = distro_version or VERSION

        self._common_attributes: Dict[str, Any] = {
            "rp": _RP_Names.UNKNOWN.value,
            "attach": _AttachTypes.MANUAL.value,
            "cikey": None,
            "runtimeVersion": platform.python_version(),
            "os": platform.system(),
            "language": "python",
            "version": self._distro_version,
        }

        # Feature gauge
        self._meter.create_observable_gauge(
            _FEATURE_METRIC_NAME,
            callbacks=[self._observe_features],
            unit="",
            description="SDKStats metric tracking enabled features",
        )

        # Instrumentation gauge
        self._meter.create_observable_gauge(
            _FEATURE_METRIC_NAME,
            callbacks=[self._observe_instrumentations],
            unit="",
            description="SDKStats metric tracking enabled instrumentations",
        )

    # ---- callbacks ----

    def _observe_features(self, options: CallbackOptions) -> Iterable[Observation]:
        observations: List[Observation] = []
        feature_bits = get_sdkstats_feature_flags()
        if feature_bits != 0:
            attrs = dict(self._common_attributes)
            attrs["feature"] = feature_bits
            attrs["type"] = _FeatureTypes.FEATURE.value
            observations.append(Observation(1, attrs))
        return observations

    def _observe_instrumentations(self, options: CallbackOptions) -> Iterable[Observation]:
        observations: List[Observation] = []
        instr_bits = get_sdkstats_instrumentation_flags()
        if instr_bits != 0:
            attrs = dict(self._common_attributes)
            attrs["feature"] = instr_bits
            attrs["type"] = _FeatureTypes.INSTRUMENTATION.value
            observations.append(Observation(1, attrs))
        return observations
