# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for AgentFrameworkInstrumentor and AgentFrameworkSpanProcessor."""

import unittest
from unittest.mock import MagicMock, patch

from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import unregister_span_enricher

from microsoft.opentelemetry._agent_framework._span_processor import AgentFrameworkSpanProcessor
from microsoft.opentelemetry._agent_framework._trace_instrumentor import AgentFrameworkInstrumentor


class TestAgentFrameworkInstrumentor(unittest.TestCase):
    """Unit tests for AgentFrameworkInstrumentor class."""

    def setUp(self):
        unregister_span_enricher()
        # Reset the BaseInstrumentor singleton so each test gets a fresh instance.
        AgentFrameworkInstrumentor._instance = None
        AgentFrameworkInstrumentor._is_instrumented_by_opentelemetry = False

    def tearDown(self):
        unregister_span_enricher()
        AgentFrameworkInstrumentor._instance = None
        AgentFrameworkInstrumentor._is_instrumented_by_opentelemetry = False

    def test_instrumentor_initialization(self):
        instrumentor = AgentFrameworkInstrumentor()
        self.assertIsNotNone(instrumentor)
        self.assertIsInstance(instrumentor, AgentFrameworkInstrumentor)

    def test_instrumentation_dependencies(self):
        instrumentor = AgentFrameworkInstrumentor()
        dependencies = instrumentor.instrumentation_dependencies()
        self.assertIsInstance(dependencies, (list, tuple))
        dependency_strings = list(dependencies)
        af_deps = [dep for dep in dependency_strings if "agent-framework" in dep]
        self.assertGreater(len(af_deps), 0)

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_instrumentor_adds_span_processor(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        instrumentor = AgentFrameworkInstrumentor()
        instrumentor._instrument()

        mock_provider.add_span_processor.assert_called_once()
        args, _ = mock_provider.add_span_processor.call_args
        self.assertIsInstance(args[0], AgentFrameworkSpanProcessor)

    @patch("microsoft.opentelemetry.a365.core.exporters.enriching_span_processor.register_span_enricher")
    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_instrumentor_registers_enricher(self, mock_get_provider, mock_register):
        mock_get_provider.return_value = MagicMock()

        instrumentor = AgentFrameworkInstrumentor()
        instrumentor._instrument()

        mock_register.assert_called_once()

    @patch("microsoft.opentelemetry.a365.core.exporters.enriching_span_processor.unregister_span_enricher")
    @patch("microsoft.opentelemetry.a365.core.exporters.enriching_span_processor.register_span_enricher")
    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_uninstrument(self, mock_get_provider, mock_register, mock_unregister):
        mock_get_provider.return_value = MagicMock()

        instrumentor = AgentFrameworkInstrumentor()
        instrumentor._instrument()
        instrumentor._uninstrument()

        mock_unregister.assert_called_once()

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_instrument_calls_enable_instrumentation_when_available(self, mock_get_provider):
        mock_get_provider.return_value = MagicMock()
        mock_enable = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "agent_framework": MagicMock(),
                "agent_framework.observability": MagicMock(enable_instrumentation=mock_enable),
            },
        ):
            instrumentor = AgentFrameworkInstrumentor()
            instrumentor._instrument()

        mock_enable.assert_called_once()
        self.assertTrue(instrumentor._af_instrumentation_enabled)

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_instrument_skips_enable_when_af_not_installed(self, mock_get_provider):
        mock_get_provider.return_value = MagicMock()

        import sys

        # Temporarily hide all agent_framework modules and block re-import
        # by setting them to None in sys.modules.
        saved = {}
        keys_to_remove = [k for k in list(sys.modules) if k == "agent_framework" or k.startswith("agent_framework.")]
        for k in keys_to_remove:
            saved[k] = sys.modules.pop(k)

        try:
            sys.modules["agent_framework"] = None  # type: ignore[assignment]
            sys.modules["agent_framework.observability"] = None  # type: ignore[assignment]

            instrumentor = AgentFrameworkInstrumentor()
            instrumentor._instrument()

            self.assertFalse(instrumentor._af_instrumentation_enabled)
        finally:
            sys.modules.pop("agent_framework", None)
            sys.modules.pop("agent_framework.observability", None)
            sys.modules.update(saved)

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_instrument_works_without_a365_modules(self, mock_get_provider):
        """When A365 modules cannot be imported (e.g. azure-monitor-only setup),
        the instrumentor must still add the span processor and not raise."""
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        import sys

        a365_keys = [k for k in list(sys.modules) if k.startswith("microsoft.opentelemetry.a365")]
        saved = {k: sys.modules.pop(k) for k in a365_keys}

        try:
            # Block A365 imports
            sys.modules["microsoft.opentelemetry.a365"] = None  # type: ignore[assignment]
            sys.modules["microsoft.opentelemetry.a365.core"] = None  # type: ignore[assignment]
            sys.modules["microsoft.opentelemetry.a365.core.exporters"] = None  # type: ignore[assignment]
            _enr_key = "microsoft.opentelemetry.a365.core.exporters.enriching_span_processor"
            sys.modules[_enr_key] = None  # type: ignore[assignment]

            instrumentor = AgentFrameworkInstrumentor()
            instrumentor._instrument()

            # Span processor must still be added even without A365 available.
            mock_provider.add_span_processor.assert_called_once()
            args, _ = mock_provider.add_span_processor.call_args
            self.assertIsInstance(args[0], AgentFrameworkSpanProcessor)
            # Enricher ownership must be False when A365 import fails.
            self.assertFalse(instrumentor._owns_enricher)

            # _uninstrument must also degrade gracefully.
            instrumentor._uninstrument()
        finally:
            for k in [
                "microsoft.opentelemetry.a365",
                "microsoft.opentelemetry.a365.core",
                "microsoft.opentelemetry.a365.core.exporters",
                "microsoft.opentelemetry.a365.core.exporters.enriching_span_processor",
            ]:
                sys.modules.pop(k, None)
            sys.modules.update(saved)

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_enable_instrumentation_called_in_azure_monitor_only_scenario(self, mock_get_provider):
        """The AF SDK must be enabled even when A365 isn't available — this is
        the Azure-Monitor-only scenario where users want AF spans in App Insights."""
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        mock_enable = MagicMock()

        import sys

        # Hide A365 modules to simulate azure-monitor-only setup
        a365_keys = [k for k in list(sys.modules) if k.startswith("microsoft.opentelemetry.a365")]
        saved_a365 = {k: sys.modules.pop(k) for k in a365_keys}

        try:
            _enr_key = "microsoft.opentelemetry.a365.core.exporters.enriching_span_processor"
            sys.modules[_enr_key] = None  # type: ignore[assignment]

            with patch.dict(
                "sys.modules",
                {
                    "agent_framework": MagicMock(),
                    "agent_framework.observability": MagicMock(enable_instrumentation=mock_enable),
                },
            ):
                instrumentor = AgentFrameworkInstrumentor()
                instrumentor._instrument()

            # AF SDK enabled, span processor added, enricher NOT registered.
            mock_enable.assert_called_once()
            self.assertTrue(instrumentor._af_instrumentation_enabled)
            mock_provider.add_span_processor.assert_called_once()
            self.assertFalse(instrumentor._owns_enricher)
        finally:
            sys.modules.pop("microsoft.opentelemetry.a365.core.exporters.enriching_span_processor", None)
            sys.modules.update(saved_a365)

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_uninstrument_when_enricher_not_owned(self, mock_get_provider):
        """_uninstrument must not call unregister_span_enricher when the
        instrumentor doesn't own the enricher (e.g. another instrumentor
        registered first, or A365 modules weren't available)."""
        mock_get_provider.return_value = MagicMock()

        with patch(
            "microsoft.opentelemetry.a365.core.exporters.enriching_span_processor.unregister_span_enricher"
        ) as mock_unregister:
            instrumentor = AgentFrameworkInstrumentor()
            # Don't call _instrument(); _owns_enricher stays False.
            instrumentor._uninstrument()

            mock_unregister.assert_not_called()


class TestAgentFrameworkSpanProcessor(unittest.TestCase):
    """Unit tests for AgentFrameworkSpanProcessor (no-op)."""

    def test_on_start_is_noop(self):
        processor = AgentFrameworkSpanProcessor()
        mock_span = MagicMock()
        processor.on_start(mock_span, None)
        mock_span.set_attribute.assert_not_called()

    def test_on_end_is_noop(self):
        processor = AgentFrameworkSpanProcessor()
        mock_span = MagicMock()
        processor.on_end(mock_span)


if __name__ == "__main__":
    unittest.main()
