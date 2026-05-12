# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for A365OpenAIAgentsInstrumentor."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("agents")

from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import (  # noqa: E402  # pylint: disable=wrong-import-position
    A365OpenAIAgentsInstrumentor,
)


class TestA365OpenAIAgentsInstrumentor(unittest.TestCase):
    """Unit tests for A365OpenAIAgentsInstrumentor class."""

    def setUp(self):
        # Reset singleton state between tests
        A365OpenAIAgentsInstrumentor._processor = None
        A365OpenAIAgentsInstrumentor._is_instrumented_by_opentelemetry = False

    def tearDown(self):
        A365OpenAIAgentsInstrumentor._processor = None
        A365OpenAIAgentsInstrumentor._is_instrumented_by_opentelemetry = False

    def test_instrumentor_initialization(self):
        instrumentor = A365OpenAIAgentsInstrumentor()
        self.assertIsNotNone(instrumentor)

    def test_instrumentation_dependencies(self):
        instrumentor = A365OpenAIAgentsInstrumentor()
        deps = instrumentor.instrumentation_dependencies()
        self.assertIn("openai-agents >= 0.0.7", deps)

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_instrumentor.trace_api")
    def test_instrument_creates_processor(self, mock_trace_api):
        mock_tracer = MagicMock()
        mock_trace_api.get_tracer.return_value = mock_tracer

        instrumentor = A365OpenAIAgentsInstrumentor()

        # Test the actual _instrument logic
        with patch.dict("sys.modules", {"agents.tracing": MagicMock()}):
            with patch(
                "microsoft.opentelemetry._genai._openai_agents._trace_instrumentor.OpenAIAgentsTraceProcessor"
            ) as MockProc:
                mock_proc_instance = MagicMock()
                MockProc.return_value = mock_proc_instance

                instrumentor._instrument()

                mock_trace_api.get_tracer.assert_called_once()
                MockProc.assert_called_once_with(mock_tracer)
                self.assertIs(instrumentor._processor, mock_proc_instance)

    def test_instrument_idempotent(self):
        """Calling _instrument twice should not create a second processor."""
        instrumentor = A365OpenAIAgentsInstrumentor()

        # Simulate that a processor is already set (first _instrument succeeded)
        existing_processor = MagicMock()
        instrumentor._processor = existing_processor

        with patch(
            "microsoft.opentelemetry._genai._openai_agents._trace_instrumentor.OpenAIAgentsTraceProcessor"
        ) as MockProc:
            instrumentor._instrument()

            # Should not have created a new processor
            MockProc.assert_not_called()
            # Original processor should still be in place
            self.assertIs(instrumentor._processor, existing_processor)

    def test_uninstrument_clears_processor(self):
        """_uninstrument should clear the processor reference."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        mock_proc = MagicMock()
        instrumentor._processor = mock_proc

        with patch.dict("sys.modules", {"agents.tracing": MagicMock()}):
            instrumentor._uninstrument()

        self.assertIsNone(instrumentor._processor)

    def test_uninstrument_noop_without_processor(self):
        """_uninstrument should not raise when no processor is set."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor._uninstrument()  # should not raise
