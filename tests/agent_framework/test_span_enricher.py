# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for Agent Framework span enricher."""

import unittest
from unittest.mock import Mock

from microsoft.opentelemetry.a365.core.constants import (
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_TOOL_ARGS_KEY,
    GEN_AI_TOOL_CALL_RESULT_KEY,
)
from microsoft.opentelemetry._agent_framework._span_enricher import (
    AF_TOOL_CALL_ARGUMENTS_KEY,
    AF_TOOL_CALL_RESULT_KEY,
    enrich_agent_framework_span,
)


class TestAgentFrameworkSpanEnricher(unittest.TestCase):
    """Test suite for enrich_agent_framework_span function."""

    def test_invoke_agent_span_enrichment(self):
        """Test invoke_agent span extracts user input and assistant output text only."""
        span = Mock()
        span.name = "invoke_agent Agent365Assistant"
        span.attributes = {
            GEN_AI_INPUT_MESSAGES_KEY: ('[{"role": "user", "parts": [{"type": "text", "content": "Compute 15 % 4"}]}]'),
            GEN_AI_OUTPUT_MESSAGES_KEY: (
                '[{"role": "assistant", "parts": [{"type": "tool_call", "id": "c1"}]}, '
                '{"role": "tool", "parts": [{"type": "tool_call_response"}]}, '
                '{"role": "assistant", "parts": [{"type": "text", "content": "Result is 3."}]}]'
            ),
        }

        result = enrich_agent_framework_span(span)

        assert result.attributes is not None
        self.assertEqual(result.attributes[GEN_AI_INPUT_MESSAGES_KEY], '["Compute 15 % 4"]')
        self.assertEqual(result.attributes[GEN_AI_OUTPUT_MESSAGES_KEY], '["Result is 3."]')

    def test_execute_tool_span_enrichment(self):
        """Test execute_tool span maps tool arguments and result to standard keys."""
        span = Mock()
        span.name = "execute_tool calculate"
        span.attributes = {
            AF_TOOL_CALL_ARGUMENTS_KEY: '{"expression": "2 + 2"}',
            AF_TOOL_CALL_RESULT_KEY: "Result is 4",
        }

        result = enrich_agent_framework_span(span)

        assert result.attributes is not None
        self.assertEqual(result.attributes[GEN_AI_TOOL_ARGS_KEY], '{"expression": "2 + 2"}')
        self.assertEqual(result.attributes[GEN_AI_TOOL_CALL_RESULT_KEY], "Result is 4")

    def test_non_matching_span_returns_original(self):
        """Test non-matching spans return unchanged."""
        span = Mock()
        span.name = "other_op"
        span.attributes = {"key": "value"}

        self.assertEqual(enrich_agent_framework_span(span), span)

    def test_none_attributes_returns_original(self):
        """Test spans with None attributes return unchanged."""
        span = Mock()
        span.name = "invoke_agent Test"
        span.attributes = None

        self.assertEqual(enrich_agent_framework_span(span), span)

    def test_empty_attributes_returns_original(self):
        """Test spans with empty attributes return unchanged."""
        span = Mock()
        span.name = "invoke_agent Test"
        span.attributes = {}

        self.assertEqual(enrich_agent_framework_span(span), span)


if __name__ == "__main__":
    unittest.main()
