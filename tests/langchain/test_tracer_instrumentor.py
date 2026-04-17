# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from microsoft.opentelemetry._genai._langchain._tracer_instrumentor import (
    LangChainInstrumentor,
    _BaseCallbackManagerInit,
)


class TestLangChainInstrumentor(TestCase):
    def setUp(self):
        # Ensure clean state between tests
        inst = LangChainInstrumentor()
        if inst.is_instrumented_by_opentelemetry:
            inst._uninstrument()

    def tearDown(self):
        inst = LangChainInstrumentor()
        if inst.is_instrumented_by_opentelemetry:
            inst._uninstrument()

    def test_instrumentation_dependencies(self):
        inst = LangChainInstrumentor()
        deps = inst.instrumentation_dependencies()
        self.assertIn("langchain-core >= 0.2.0", deps)

    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.get_otel_logger")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.trace_api.get_tracer")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.wrap_function_wrapper")
    def test_instrument_creates_tracer(self, mock_wrap, mock_get_tracer, mock_get_logger):
        mock_get_tracer.return_value = MagicMock()
        mock_get_logger.return_value = MagicMock()
        inst = LangChainInstrumentor()
        inst._instrument()
        mock_get_tracer.assert_called_once()
        mock_get_logger.assert_called_once()
        mock_wrap.assert_called_once()
        wrap_kwargs = mock_wrap.call_args
        self.assertEqual(wrap_kwargs.kwargs.get("module") or wrap_kwargs[0][0], "langchain_core.callbacks")
        self.assertIsNotNone(inst._tracer)

    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.get_otel_logger")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.trace_api.get_tracer")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.wrap_function_wrapper")
    def test_instrument_passes_agent_config(self, mock_wrap, mock_get_tracer, mock_get_logger):
        mock_get_tracer.return_value = MagicMock()
        mock_get_logger.return_value = MagicMock()
        inst = LangChainInstrumentor()
        inst._instrument(agent_name="TestBot", agent_id="a-1")
        self.assertEqual(inst._tracer._agent_config["agent_name"], "TestBot")
        self.assertEqual(inst._tracer._agent_config["agent_id"], "a-1")

    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.get_otel_logger")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.trace_api.get_tracer")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.wrap_function_wrapper")
    def test_uninstrument_restores_init(self, mock_wrap, mock_get_tracer, mock_get_logger):
        mock_get_tracer.return_value = MagicMock()
        mock_get_logger.return_value = MagicMock()
        inst = LangChainInstrumentor()
        inst._instrument()
        self.assertIsNotNone(inst._tracer)
        inst._uninstrument()
        self.assertIsNone(inst._tracer)
        self.assertIsNone(inst._original_cb_init)

    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.get_otel_logger")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.trace_api.get_tracer")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.wrap_function_wrapper")
    def test_get_span_returns_none_when_not_instrumented(self, mock_wrap, mock_get_tracer, mock_get_logger):
        inst = LangChainInstrumentor()
        self.assertIsNone(inst.get_span(uuid4()))

    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.get_otel_logger")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.trace_api.get_tracer")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.wrap_function_wrapper")
    def test_get_span_delegates_to_tracer(self, mock_wrap, mock_get_tracer, mock_get_logger):
        mock_get_tracer.return_value = MagicMock()
        mock_get_logger.return_value = MagicMock()
        inst = LangChainInstrumentor()
        inst._instrument()
        run_id = uuid4()
        mock_span = MagicMock()
        with patch.object(inst._tracer, "get_span", return_value=mock_span):
            result = inst.get_span(run_id)
        self.assertEqual(result, mock_span)

    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.get_otel_logger")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.trace_api.get_tracer")
    @patch("microsoft.opentelemetry._genai._langchain._tracer_instrumentor.wrap_function_wrapper")
    def test_get_ancestors_returns_empty_when_not_instrumented(self, mock_wrap, mock_get_tracer, mock_get_logger):
        inst = LangChainInstrumentor()
        self.assertEqual(inst.get_ancestors(uuid4()), [])


class TestBaseCallbackManagerInit(TestCase):
    def test_adds_tracer_to_handlers(self):
        mock_tracer = MagicMock()
        hook = _BaseCallbackManagerInit(mock_tracer)
        mock_wrapped = MagicMock()
        mock_instance = MagicMock()
        mock_instance.inheritable_handlers = []
        hook(mock_wrapped, mock_instance, (), {})
        mock_wrapped.assert_called_once_with()
        mock_instance.add_handler.assert_called_once_with(mock_tracer, inherit=True)

    def test_does_not_add_duplicate(self):
        mock_tracer = MagicMock()
        hook = _BaseCallbackManagerInit(mock_tracer)
        mock_wrapped = MagicMock()
        mock_instance = MagicMock()
        mock_instance.inheritable_handlers = [mock_tracer]
        hook(mock_wrapped, mock_instance, (), {})
        mock_instance.add_handler.assert_not_called()
