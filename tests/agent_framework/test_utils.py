# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for Agent Framework utils."""

import unittest

from microsoft.opentelemetry._agent_framework._utils import (
    extract_content_as_string_list,
    extract_input_content,
    extract_output_content,
)


class TestAgentFrameworkUtils(unittest.TestCase):
    """Test suite for Agent Framework utility functions."""

    def test_extract_content_filters_text_by_role(self):
        """Test text extraction with role filtering, ignoring tool calls."""
        msgs = (
            '[{"role": "user", "parts": [{"type": "text", "content": "Hi"}]}, '
            '{"role": "assistant", "parts": [{"type": "tool_call"}, {"type": "text", "content": "Hello"}]}]'
        )
        self.assertEqual(extract_content_as_string_list(msgs), '["Hi", "Hello"]')
        self.assertEqual(extract_content_as_string_list(msgs, role_filter="user"), '["Hi"]')
        self.assertEqual(extract_input_content(msgs), '["Hi"]')
        self.assertEqual(extract_output_content(msgs), '["Hello"]')

    def test_handles_invalid_json(self):
        """Test invalid JSON returns original string."""
        self.assertEqual(extract_content_as_string_list("invalid"), "invalid")

    def test_handles_non_list_json(self):
        """Test non-list JSON returns original string."""
        self.assertEqual(extract_content_as_string_list('{"not": "list"}'), '{"not": "list"}')

    def test_handles_empty_list(self):
        """Test empty list returns empty array."""
        self.assertEqual(extract_content_as_string_list("[]"), "[]")

    def test_handles_messages_without_parts(self):
        """Test messages without parts yield no content."""
        self.assertEqual(extract_content_as_string_list('[{"role": "user"}]'), "[]")

    def test_handles_parts_without_text_type(self):
        """Test that non-text parts are ignored."""
        msgs = '[{"role": "user", "parts": [{"type": "tool_call", "id": "c1"}]}]'
        self.assertEqual(extract_content_as_string_list(msgs), "[]")


if __name__ == "__main__":
    unittest.main()
