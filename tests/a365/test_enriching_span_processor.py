# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.trace import ReadableSpan

from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import (
    _EnrichingBatchSpanProcessor,
    get_span_enricher,
    register_span_enricher,
    unregister_span_enricher,
)


class TestSpanEnricherRegistration(unittest.TestCase):
    def setUp(self):
        unregister_span_enricher()

    def tearDown(self):
        unregister_span_enricher()

    def test_register_enricher(self):
        def my_enricher(span: ReadableSpan) -> ReadableSpan:
            return span

        register_span_enricher(my_enricher)
        self.assertIs(get_span_enricher(), my_enricher)

    def test_unregister_enricher(self):
        def my_enricher(span: ReadableSpan) -> ReadableSpan:
            return span

        register_span_enricher(my_enricher)
        unregister_span_enricher()
        self.assertIsNone(get_span_enricher())

    def test_double_register_raises(self):
        def enricher1(span: ReadableSpan) -> ReadableSpan:
            return span

        def enricher2(span: ReadableSpan) -> ReadableSpan:
            return span

        register_span_enricher(enricher1)
        with self.assertRaises(RuntimeError):
            register_span_enricher(enricher2)

    def test_no_enricher_by_default(self):
        self.assertIsNone(get_span_enricher())

    def test_unregister_when_none(self):
        unregister_span_enricher()  # should not raise


class TestEnrichingBatchSpanProcessor(unittest.TestCase):
    def setUp(self):
        unregister_span_enricher()

    def tearDown(self):
        unregister_span_enricher()

    @patch.object(_EnrichingBatchSpanProcessor, "__init__", lambda self, *a, **kw: None)
    def test_on_end_calls_enricher(self):
        enriched = MagicMock(spec=ReadableSpan)
        enriched.name = "test"
        enriched.attributes = {}

        def my_enricher(span):
            return enriched

        register_span_enricher(my_enricher)

        processor = _EnrichingBatchSpanProcessor.__new__(_EnrichingBatchSpanProcessor)
        processor._suppress_invoke_agent_input = False

        original_span = MagicMock(spec=ReadableSpan)
        original_span.name = "original"
        original_span.attributes = {}

        with patch.object(_EnrichingBatchSpanProcessor.__bases__[0], "on_end") as mock_super_on_end:
            processor.on_end(original_span)
            mock_super_on_end.assert_called_once_with(enriched)

    @patch.object(_EnrichingBatchSpanProcessor, "__init__", lambda self, *a, **kw: None)
    def test_on_end_falls_back_on_enricher_error(self):
        def bad_enricher(span):
            raise ValueError("enricher error")

        register_span_enricher(bad_enricher)

        processor = _EnrichingBatchSpanProcessor.__new__(_EnrichingBatchSpanProcessor)
        processor._suppress_invoke_agent_input = False

        original_span = MagicMock(spec=ReadableSpan)
        original_span.name = "original"
        original_span.attributes = {}

        with patch.object(_EnrichingBatchSpanProcessor.__bases__[0], "on_end") as mock_super_on_end:
            processor.on_end(original_span)
            mock_super_on_end.assert_called_once_with(original_span)

    @patch.object(_EnrichingBatchSpanProcessor, "__init__", lambda self, *a, **kw: None)
    def test_suppress_invoke_agent_input(self):
        processor = _EnrichingBatchSpanProcessor.__new__(_EnrichingBatchSpanProcessor)
        processor._suppress_invoke_agent_input = True

        span = MagicMock(spec=ReadableSpan)
        span.name = "invoke_agent Travel_Assistant"
        span.attributes = {
            "gen_ai.operation.name": "invoke_agent",
            "gen_ai.input.messages": "[{...}]",
        }

        with patch.object(_EnrichingBatchSpanProcessor.__bases__[0], "on_end") as mock_super_on_end:
            processor.on_end(span)
            passed_span = mock_super_on_end.call_args[0][0]
            self.assertNotIn("gen_ai.input.messages", dict(passed_span.attributes))

    @patch.object(_EnrichingBatchSpanProcessor, "__init__", lambda self, *a, **kw: None)
    def test_no_suppress_for_non_invoke_agent(self):
        processor = _EnrichingBatchSpanProcessor.__new__(_EnrichingBatchSpanProcessor)
        processor._suppress_invoke_agent_input = True

        span = MagicMock(spec=ReadableSpan)
        span.name = "chat gpt-4"
        span.attributes = {
            "gen_ai.operation.name": "chat",
            "gen_ai.input.messages": "[{...}]",
        }

        with patch.object(_EnrichingBatchSpanProcessor.__bases__[0], "on_end") as mock_super_on_end:
            processor.on_end(span)
            mock_super_on_end.assert_called_once_with(span)


if __name__ == "__main__":
    unittest.main()
