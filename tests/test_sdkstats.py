# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Tests for the _sdkstats package — state, metrics, and manager."""

import os
import threading
import unittest
from unittest.mock import MagicMock, patch

from microsoft.opentelemetry._sdkstats._state import (
    SdkStatsFeature,
    SdkStatsInstrumentation,
    _INSTRUMENTATION_NAME_MAP,
    _SDKSTATS_DISABLED_ENV,
    _APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL,
    _SDKSTATS_STATE,
    _STATE_LOCK,
    get_sdkstats_feature_flags,
    get_sdkstats_instrumentation_flags,
    get_sdkstats_shutdown,
    is_sdkstats_enabled,
    set_sdkstats_feature,
    set_sdkstats_instrumentation,
    set_sdkstats_instrumentation_by_name,
    set_sdkstats_shutdown,
)


def _reset_state():
    """Reset module-level state between tests."""
    with _STATE_LOCK:
        _SDKSTATS_STATE["SHUTDOWN"] = False
        _SDKSTATS_STATE["FEATURE_FLAGS"] = SdkStatsFeature.NONE
        _SDKSTATS_STATE["INSTRUMENTATION_FLAGS"] = SdkStatsInstrumentation.NONE


class TestSdkStatsEnabled(unittest.TestCase):
    """Tests for is_sdkstats_enabled()."""

    def setUp(self):
        _reset_state()
        # Clean env
        os.environ.pop(_SDKSTATS_DISABLED_ENV, None)
        os.environ.pop(_APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL, None)

    def tearDown(self):
        os.environ.pop(_SDKSTATS_DISABLED_ENV, None)
        os.environ.pop(_APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL, None)

    def test_enabled_by_default(self):
        self.assertTrue(is_sdkstats_enabled())

    def test_disabled_by_new_env_var(self):
        os.environ[_SDKSTATS_DISABLED_ENV] = "true"
        self.assertFalse(is_sdkstats_enabled())

    def test_disabled_by_legacy_env_var(self):
        os.environ[_APPLICATIONINSIGHTS_STATSBEAT_DISABLED_ALL] = "True"
        self.assertFalse(is_sdkstats_enabled())

    def test_disabled_by_1(self):
        os.environ[_SDKSTATS_DISABLED_ENV] = "1"
        self.assertFalse(is_sdkstats_enabled())

    def test_disabled_by_on(self):
        os.environ[_SDKSTATS_DISABLED_ENV] = "on"
        self.assertFalse(is_sdkstats_enabled())

    def test_enabled_with_random_value(self):
        os.environ[_SDKSTATS_DISABLED_ENV] = "banana"
        self.assertTrue(is_sdkstats_enabled())


class TestSdkStatsShutdown(unittest.TestCase):
    """Tests for shutdown state."""

    def setUp(self):
        _reset_state()

    def test_shutdown_default_false(self):
        self.assertFalse(get_sdkstats_shutdown())

    def test_set_shutdown(self):
        set_sdkstats_shutdown(True)
        self.assertTrue(get_sdkstats_shutdown())

    def test_set_shutdown_false(self):
        set_sdkstats_shutdown(True)
        set_sdkstats_shutdown(False)
        self.assertFalse(get_sdkstats_shutdown())


class TestSdkStatsFeatureFlags(unittest.TestCase):
    """Tests for feature flag state."""

    def setUp(self):
        _reset_state()

    def test_default_none(self):
        self.assertEqual(get_sdkstats_feature_flags(), 0)

    def test_set_single_flag(self):
        set_sdkstats_feature(SdkStatsFeature.DISTRO)
        self.assertEqual(get_sdkstats_feature_flags(), SdkStatsFeature.DISTRO)

    def test_set_multiple_flags(self):
        set_sdkstats_feature(SdkStatsFeature.DISTRO)
        set_sdkstats_feature(SdkStatsFeature.OTLP_EXPORT)
        expected = SdkStatsFeature.DISTRO | SdkStatsFeature.OTLP_EXPORT
        self.assertEqual(get_sdkstats_feature_flags(), expected)

    def test_idempotent_set(self):
        set_sdkstats_feature(SdkStatsFeature.A365_EXPORT)
        set_sdkstats_feature(SdkStatsFeature.A365_EXPORT)
        self.assertEqual(get_sdkstats_feature_flags(), SdkStatsFeature.A365_EXPORT)

    def test_all_features_have_unique_bits(self):
        seen = set()
        for member in SdkStatsFeature:
            if member == SdkStatsFeature.NONE:
                continue
            self.assertNotIn(int(member), seen, f"Duplicate bit for {member.name}")
            seen.add(int(member))


class TestSdkStatsInstrumentationFlags(unittest.TestCase):
    """Tests for instrumentation flag state."""

    def setUp(self):
        _reset_state()

    def test_default_none(self):
        self.assertEqual(get_sdkstats_instrumentation_flags(), 0)

    def test_set_by_enum(self):
        set_sdkstats_instrumentation(SdkStatsInstrumentation.DJANGO)
        self.assertEqual(
            get_sdkstats_instrumentation_flags(),
            SdkStatsInstrumentation.DJANGO,
        )

    def test_set_by_name(self):
        set_sdkstats_instrumentation_by_name("fastapi")
        self.assertEqual(
            get_sdkstats_instrumentation_flags(),
            SdkStatsInstrumentation.FASTAPI,
        )

    def test_set_unknown_name_ignored(self):
        set_sdkstats_instrumentation_by_name("nonexistent_lib")
        self.assertEqual(get_sdkstats_instrumentation_flags(), 0)

    def test_multiple_instrumentations(self):
        set_sdkstats_instrumentation_by_name("django")
        set_sdkstats_instrumentation_by_name("openai")
        expected = SdkStatsInstrumentation.DJANGO | SdkStatsInstrumentation.OPENAI_V2
        self.assertEqual(get_sdkstats_instrumentation_flags(), expected)

    def test_name_map_covers_supported_libraries(self):
        """Every name in the map resolves to a non-zero flag."""
        for name, flag in _INSTRUMENTATION_NAME_MAP.items():
            self.assertNotEqual(flag, 0, f"Flag for {name} is zero")


class TestSdkStatsThreadSafety(unittest.TestCase):
    """Ensure concurrent flag updates are safe."""

    def setUp(self):
        _reset_state()

    def test_concurrent_feature_flag_updates(self):
        flags = list(SdkStatsFeature)
        flags = [f for f in flags if f != SdkStatsFeature.NONE]
        errors = []

        def worker(flag):
            try:
                for _ in range(100):
                    set_sdkstats_feature(flag)
            except Exception as e:  # pylint: disable=broad-exception-caught
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f,)) for f in flags]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

        # All flags should be set
        expected = SdkStatsFeature.NONE
        for f in flags:
            expected |= f
        self.assertEqual(get_sdkstats_feature_flags(), expected)


class TestSdkStatsMetrics(unittest.TestCase):
    """Tests for the SdkStatsMetrics observable gauges."""

    def setUp(self):
        _reset_state()

    def test_feature_observation_empty_when_no_flags(self):
        from opentelemetry.sdk.metrics import MeterProvider
        from microsoft.opentelemetry._sdkstats._metrics import SdkStatsMetrics

        mp = MeterProvider()
        try:
            metrics = SdkStatsMetrics(mp)
            obs = list(metrics._observe_features(MagicMock()))
            self.assertEqual(obs, [])
        finally:
            mp.shutdown()

    def test_feature_observation_emitted_with_flags(self):
        from opentelemetry.sdk.metrics import MeterProvider
        from microsoft.opentelemetry._sdkstats._metrics import SdkStatsMetrics

        set_sdkstats_feature(SdkStatsFeature.DISTRO)
        mp = MeterProvider()
        try:
            metrics = SdkStatsMetrics(mp)
            obs = list(metrics._observe_features(MagicMock()))
            self.assertEqual(len(obs), 1)
            self.assertEqual(obs[0].value, 1)
            attrs = obs[0].attributes
            assert attrs is not None
            self.assertEqual(attrs["feature"], int(SdkStatsFeature.DISTRO))
            self.assertEqual(attrs["type"], 0)  # FEATURE
        finally:
            mp.shutdown()

    def test_instrumentation_observation_emitted(self):
        from opentelemetry.sdk.metrics import MeterProvider
        from microsoft.opentelemetry._sdkstats._metrics import SdkStatsMetrics

        set_sdkstats_instrumentation(SdkStatsInstrumentation.FASTAPI)
        mp = MeterProvider()
        try:
            metrics = SdkStatsMetrics(mp)
            obs = list(metrics._observe_instrumentations(MagicMock()))
            self.assertEqual(len(obs), 1)
            attrs = obs[0].attributes
            assert attrs is not None
            self.assertEqual(attrs["feature"], int(SdkStatsInstrumentation.FASTAPI))
            self.assertEqual(attrs["type"], 1)  # INSTRUMENTATION
        finally:
            mp.shutdown()


class TestSdkStatsManager(unittest.TestCase):
    """Tests for the SdkStatsManager singleton."""

    def setUp(self):
        _reset_state()
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        SdkStatsManager._reset()

    def tearDown(self):
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        SdkStatsManager._reset()

    def test_singleton(self):
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        a = SdkStatsManager()
        b = SdkStatsManager()
        self.assertIs(a, b)

    def test_initialize_standalone(self):
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        reader = InMemoryMetricReader()
        manager = SdkStatsManager()
        result = manager.initialize_standalone(reader)
        self.assertTrue(result)
        self.assertTrue(manager.is_initialized)

    def test_initialize_standalone_disabled(self):
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        os.environ[_SDKSTATS_DISABLED_ENV] = "true"
        try:
            reader = InMemoryMetricReader()
            manager = SdkStatsManager()
            result = manager.initialize_standalone(reader)
            self.assertFalse(result)
            self.assertFalse(manager.is_initialized)
        finally:
            os.environ.pop(_SDKSTATS_DISABLED_ENV, None)

    def test_shutdown(self):
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        reader = InMemoryMetricReader()
        manager = SdkStatsManager()
        manager.initialize_standalone(reader)
        result = manager.shutdown()
        self.assertTrue(result)
        self.assertFalse(manager.is_initialized)
        self.assertTrue(get_sdkstats_shutdown())

    def test_shutdown_when_not_initialized(self):
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        manager = SdkStatsManager()
        result = manager.shutdown()
        self.assertFalse(result)

    def test_double_initialize_is_idempotent(self):
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        reader1 = InMemoryMetricReader()
        reader2 = InMemoryMetricReader()
        manager = SdkStatsManager()
        self.assertTrue(manager.initialize_standalone(reader1))
        self.assertTrue(manager.initialize_standalone(reader2))  # Should return True (already init)

    _FAKE_STATS_CS = "InstrumentationKey=fake;" + "IngestionEndpoint=https://test.in.applicationinsights.azure.com/"

    @patch("azure.monitor.opentelemetry.exporter.export.metrics._exporter.AzureMonitorMetricExporter")
    @patch(
        "azure.monitor.opentelemetry.exporter.statsbeat._utils._get_stats_connection_string",
        return_value=_FAKE_STATS_CS,
    )
    @patch(
        "azure.monitor.opentelemetry.exporter.statsbeat._utils._get_stats_short_export_interval",
        return_value=900,
    )
    def test_initialize_uses_azure_monitor_exporter(self, mock_interval, mock_cs, mock_exporter):
        """initialize() must use AzureMonitorMetricExporter with is_sdkstats=True."""
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        manager = SdkStatsManager()
        result = manager.initialize()
        self.assertTrue(result)
        self.assertTrue(manager.is_initialized)

        mock_exporter.assert_called_once_with(
            connection_string=self._FAKE_STATS_CS,
            disable_offline_storage=True,
            is_sdkstats=True,
        )

    def test_metrics_collected_after_initialize(self):
        from opentelemetry.sdk.metrics.export import InMemoryMetricReader
        from microsoft.opentelemetry._sdkstats._manager import SdkStatsManager

        set_sdkstats_feature(SdkStatsFeature.DISTRO)
        set_sdkstats_feature(SdkStatsFeature.A365_EXPORT)
        set_sdkstats_instrumentation(SdkStatsInstrumentation.OPENAI_V2)

        reader = InMemoryMetricReader()
        manager = SdkStatsManager()
        manager.initialize_standalone(reader)

        metrics_data = reader.get_metrics_data()
        self.assertIsNotNone(metrics_data)
        metric_names = set()
        for resource_metrics in metrics_data.resource_metrics:
            for scope_metrics in resource_metrics.scope_metrics:
                for metric in scope_metrics.metrics:
                    metric_names.add(metric.name)

        self.assertIn("feature", metric_names)
        self.assertIn("feature", metric_names)


class TestBridgeSdkStatsToAzureMonitor(unittest.TestCase):
    """Tests for _bridge_sdkstats_to_azure_monitor in _distro.py."""

    def setUp(self):
        _reset_state()
        # Reset exporter state that the bridge touches
        try:
            from azure.monitor.opentelemetry.exporter.statsbeat._statsbeat_metrics import (
                _StatsbeatMetrics,
            )
            import azure.monitor.opentelemetry.exporter._utils as _exporter_utils

            _StatsbeatMetrics._FEATURE_ATTRIBUTES["feature"] = None
            with _exporter_utils._INSTRUMENTATIONS_BIT_MASK_LOCK:
                _exporter_utils._INSTRUMENTATIONS_BIT_MASK = 0
        except ImportError:
            pass

    def tearDown(self):
        _reset_state()
        # Reset exporter state touched by the bridge
        try:
            from azure.monitor.opentelemetry.exporter.statsbeat._statsbeat_metrics import (
                _StatsbeatMetrics,
            )
            import azure.monitor.opentelemetry.exporter._utils as _exporter_utils

            _StatsbeatMetrics._FEATURE_ATTRIBUTES["feature"] = None
            with _exporter_utils._INSTRUMENTATIONS_BIT_MASK_LOCK:
                _exporter_utils._INSTRUMENTATIONS_BIT_MASK = 0
        except ImportError:
            pass

    def test_bridge_feature_flags_into_exporter(self):
        """Distro feature flags are OR'd into the exporter's _FEATURE_ATTRIBUTES."""
        from azure.monitor.opentelemetry.exporter.statsbeat._statsbeat_metrics import (
            _StatsbeatMetrics,
        )
        from microsoft.opentelemetry._distro import _bridge_sdkstats_to_azure_monitor

        set_sdkstats_feature(SdkStatsFeature.DISTRO)
        set_sdkstats_feature(SdkStatsFeature.A365_EXPORT)
        _bridge_sdkstats_to_azure_monitor()

        expected = int(SdkStatsFeature.DISTRO | SdkStatsFeature.A365_EXPORT)
        self.assertEqual(_StatsbeatMetrics._FEATURE_ATTRIBUTES["feature"], expected)

    def test_bridge_preserves_existing_exporter_feature_flags(self):
        """Bridge OR's into existing exporter bits, doesn't overwrite."""
        from azure.monitor.opentelemetry.exporter.statsbeat._statsbeat_metrics import (
            _StatsbeatMetrics,
        )
        from microsoft.opentelemetry._distro import _bridge_sdkstats_to_azure_monitor

        # Simulate exporter has already set DISK_RETRY=1 and AAD=2
        _StatsbeatMetrics._FEATURE_ATTRIBUTES["feature"] = 3
        set_sdkstats_feature(SdkStatsFeature.OTLP_EXPORT)

        _bridge_sdkstats_to_azure_monitor()

        # 3 (existing) | 256 (OTLP_EXPORT) = 259
        self.assertEqual(_StatsbeatMetrics._FEATURE_ATTRIBUTES["feature"], 3 | 256)

    def test_bridge_instrumentation_flags_into_exporter(self):
        """Distro instrumentation flags are OR'd into the exporter's bitmask."""
        import azure.monitor.opentelemetry.exporter._utils as _exporter_utils
        from microsoft.opentelemetry._distro import _bridge_sdkstats_to_azure_monitor

        set_sdkstats_instrumentation(SdkStatsInstrumentation.FASTAPI)
        set_sdkstats_instrumentation(SdkStatsInstrumentation.LANGCHAIN)
        _bridge_sdkstats_to_azure_monitor()

        expected = int(SdkStatsInstrumentation.FASTAPI | SdkStatsInstrumentation.LANGCHAIN)
        self.assertEqual(_exporter_utils._INSTRUMENTATIONS_BIT_MASK, expected)

    def test_bridge_noop_when_no_flags(self):
        """Bridge does nothing when no flags are set."""
        from azure.monitor.opentelemetry.exporter.statsbeat._statsbeat_metrics import (
            _StatsbeatMetrics,
        )
        import azure.monitor.opentelemetry.exporter._utils as _exporter_utils
        from microsoft.opentelemetry._distro import _bridge_sdkstats_to_azure_monitor

        _bridge_sdkstats_to_azure_monitor()

        self.assertIsNone(_StatsbeatMetrics._FEATURE_ATTRIBUTES["feature"])
        self.assertEqual(_exporter_utils._INSTRUMENTATIONS_BIT_MASK, 0)

    def test_initialize_sdkstats_bridges_when_azure_monitor_enabled(self):
        """_initialize_sdkstats calls the bridge when enable_azure_monitor=True."""
        from microsoft.opentelemetry._distro import _initialize_sdkstats

        set_sdkstats_feature(SdkStatsFeature.DISTRO)
        set_sdkstats_feature(SdkStatsFeature.A365_EXPORT)

        with patch("microsoft.opentelemetry._distro._bridge_sdkstats_to_azure_monitor") as mock_bridge:
            _initialize_sdkstats(enable_azure_monitor=True)
            mock_bridge.assert_called_once()

    def test_initialize_sdkstats_uses_manager_when_azure_monitor_disabled(self):
        """_initialize_sdkstats creates SdkStatsManager when Azure Monitor is off."""
        from microsoft.opentelemetry._distro import _initialize_sdkstats

        set_sdkstats_feature(SdkStatsFeature.DISTRO)

        with patch("microsoft.opentelemetry._sdkstats._manager.SdkStatsManager") as mock_cls:
            mock_manager = MagicMock()
            mock_cls.return_value = mock_manager
            _initialize_sdkstats(enable_azure_monitor=False)
            mock_manager.initialize.assert_called_once()


if __name__ == "__main__":
    unittest.main()
