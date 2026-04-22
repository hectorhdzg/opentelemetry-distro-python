# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for SemanticKernelInstrumentor and SemanticKernelSpanProcessor."""

import unittest
from unittest.mock import MagicMock, patch

from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import unregister_span_enricher

from microsoft.opentelemetry._semantic_kernel._span_processor import SemanticKernelSpanProcessor
from microsoft.opentelemetry._semantic_kernel._trace_instrumentor import SemanticKernelInstrumentor


class TestSemanticKernelInstrumentor(unittest.TestCase):
    """Unit tests for SemanticKernelInstrumentor class."""

    def setUp(self):
        # Clear any globally registered enricher to avoid cross-test pollution
        unregister_span_enricher()

    def tearDown(self):
        unregister_span_enricher()

    def test_instrumentor_initialization(self):
        instrumentor = SemanticKernelInstrumentor()
        self.assertIsNotNone(instrumentor)
        self.assertIsInstance(instrumentor, SemanticKernelInstrumentor)

    def test_instrumentation_dependencies(self):
        instrumentor = SemanticKernelInstrumentor()
        dependencies = instrumentor.instrumentation_dependencies()
        self.assertIsInstance(dependencies, (list, tuple))
        dependency_strings = list(dependencies)
        sk_deps = [dep for dep in dependency_strings if "semantic-kernel" in dep]
        self.assertGreater(len(sk_deps), 0)

    @patch("microsoft.opentelemetry._semantic_kernel._trace_instrumentor.get_tracer_provider")
    def test_instrumentor_adds_span_processor(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        instrumentor = SemanticKernelInstrumentor()
        instrumentor._instrument()

        mock_provider.add_span_processor.assert_called_once()
        args, _ = mock_provider.add_span_processor.call_args
        self.assertIsInstance(args[0], SemanticKernelSpanProcessor)

    @patch("microsoft.opentelemetry._semantic_kernel._trace_instrumentor.register_span_enricher")
    @patch("microsoft.opentelemetry._semantic_kernel._trace_instrumentor.get_tracer_provider")
    def test_instrumentor_registers_enricher(self, mock_get_provider, mock_register):
        mock_get_provider.return_value = MagicMock()

        instrumentor = SemanticKernelInstrumentor()
        instrumentor._instrument()

        mock_register.assert_called_once()

    @patch("microsoft.opentelemetry._semantic_kernel._trace_instrumentor.unregister_span_enricher")
    @patch("microsoft.opentelemetry._semantic_kernel._trace_instrumentor.register_span_enricher")
    @patch("microsoft.opentelemetry._semantic_kernel._trace_instrumentor.get_tracer_provider")
    def test_uninstrument(self, mock_get_provider, mock_register, mock_unregister):
        mock_get_provider.return_value = MagicMock()

        instrumentor = SemanticKernelInstrumentor()
        instrumentor._instrument()
        instrumentor._uninstrument()

        mock_unregister.assert_called_once()


class TestSemanticKernelSpanProcessor(unittest.TestCase):
    """Unit tests for SemanticKernelSpanProcessor."""

    def test_chat_span_gets_renamed(self):
        processor = SemanticKernelSpanProcessor()
        mock_span = MagicMock()
        mock_span.name = "chat.completions gpt-4o"

        processor.on_start(mock_span, None)

        mock_span.set_attribute.assert_called_once()
        mock_span.update_name.assert_called_once()
        args, _ = mock_span.update_name.call_args
        self.assertIn("chat", args[0].lower())

    def test_non_chat_span_unchanged(self):
        processor = SemanticKernelSpanProcessor()
        mock_span = MagicMock()
        mock_span.name = "function.call"

        processor.on_start(mock_span, None)

        mock_span.set_attribute.assert_not_called()
        mock_span.update_name.assert_not_called()

    def test_force_flush_returns_true(self):
        processor = SemanticKernelSpanProcessor()
        self.assertTrue(processor.force_flush())


if __name__ == "__main__":
    unittest.main()
