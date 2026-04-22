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

    def tearDown(self):
        unregister_span_enricher()

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

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.register_span_enricher")
    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_instrumentor_registers_enricher(self, mock_get_provider, mock_register):
        mock_get_provider.return_value = MagicMock()

        instrumentor = AgentFrameworkInstrumentor()
        instrumentor._instrument()

        mock_register.assert_called_once()

    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.unregister_span_enricher")
    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.register_span_enricher")
    @patch("microsoft.opentelemetry._agent_framework._trace_instrumentor.get_tracer_provider")
    def test_uninstrument(self, mock_get_provider, mock_register, mock_unregister):
        mock_get_provider.return_value = MagicMock()

        instrumentor = AgentFrameworkInstrumentor()
        instrumentor._instrument()
        instrumentor._uninstrument()

        mock_unregister.assert_called_once()


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
