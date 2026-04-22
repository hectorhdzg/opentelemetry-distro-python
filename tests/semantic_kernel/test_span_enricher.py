# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for Semantic Kernel span enricher."""

import unittest
from unittest.mock import Mock

from microsoft.opentelemetry.a365.core.constants import (
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_TOOL_ARGS_KEY,
    GEN_AI_TOOL_CALL_RESULT_KEY,
)
from microsoft.opentelemetry._semantic_kernel._span_enricher import (
    SK_TOOL_CALL_ARGUMENTS_KEY,
    SK_TOOL_CALL_RESULT_KEY,
    enrich_semantic_kernel_span,
)


class TestSemanticKernelSpanEnricher(unittest.TestCase):
    """Test suite for enrich_semantic_kernel_span function."""

    def test_invoke_agent_span_extracts_content_from_messages(self):
        """Test that invoke_agent spans have content extracted from input/output messages."""
        mock_span = Mock()
        mock_span.name = "invoke_agent test-agent"
        mock_span.attributes = {
            GEN_AI_INPUT_MESSAGES_KEY: '[{"role": "user", "content": "Hello"}]',
            GEN_AI_OUTPUT_MESSAGES_KEY: '[{"role": "assistant", "content": "Hi there!"}]',
        }

        enriched = enrich_semantic_kernel_span(mock_span)

        self.assertNotEqual(enriched, mock_span)
        attributes = enriched.attributes
        assert attributes is not None
        self.assertEqual(attributes[GEN_AI_INPUT_MESSAGES_KEY], '["Hello"]')
        self.assertEqual(attributes[GEN_AI_OUTPUT_MESSAGES_KEY], '["Hi there!"]')

    def test_execute_tool_span_maps_tool_attributes(self):
        """Test that execute_tool spans map tool arguments and results."""
        mock_span = Mock()
        mock_span.name = "execute_tool calculate"
        mock_span.attributes = {
            SK_TOOL_CALL_ARGUMENTS_KEY: '{"expression": "2+2"}',
            SK_TOOL_CALL_RESULT_KEY: "4",
        }

        enriched = enrich_semantic_kernel_span(mock_span)

        self.assertNotEqual(enriched, mock_span)
        attributes = enriched.attributes
        assert attributes is not None
        self.assertEqual(attributes[GEN_AI_TOOL_ARGS_KEY], '{"expression": "2+2"}')
        self.assertEqual(attributes[GEN_AI_TOOL_CALL_RESULT_KEY], "4")

    def test_non_matching_span_returns_original(self):
        """Test that spans not matching invoke_agent or execute_tool are returned unchanged."""
        mock_span = Mock()
        mock_span.name = "some_other_operation"
        mock_span.attributes = {"some_key": "some_value"}

        result = enrich_semantic_kernel_span(mock_span)

        self.assertEqual(result, mock_span)

    def test_empty_attributes_returns_original(self):
        """Test that spans with no relevant attributes return unchanged."""
        mock_span = Mock()
        mock_span.name = "invoke_agent test"
        mock_span.attributes = {}

        result = enrich_semantic_kernel_span(mock_span)

        self.assertEqual(result, mock_span)

    def test_none_attributes_returns_original(self):
        """Test that spans with None attributes return unchanged."""
        mock_span = Mock()
        mock_span.name = "invoke_agent test"
        mock_span.attributes = None

        result = enrich_semantic_kernel_span(mock_span)

        self.assertEqual(result, mock_span)


if __name__ == "__main__":
    unittest.main()
