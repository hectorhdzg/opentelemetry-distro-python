# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Utility functions for Agent Framework observability extensions."""

from __future__ import annotations

import json


def extract_content_as_string_list(  # pylint: disable=too-many-nested-blocks
    messages_json: str, role_filter: str | None = None
) -> str:
    """Extract content values from messages JSON and return as JSON string list.

    Handles Agent Framework message format with ``"parts"`` arrays.
    Only extracts text content, ignoring tool_call and tool_call_response parts.

    Args:
        messages_json: JSON string of messages.
        role_filter: If provided, only extract content from messages with this role.

    Returns:
        JSON string containing only the text content values as an array,
        or the original string if parsing fails.
    """
    try:
        messages = json.loads(messages_json)
        if isinstance(messages, list):
            contents = []
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("role", "")

                    if role_filter and role != role_filter:
                        continue

                    parts = msg.get("parts")
                    if parts and isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict):
                                part_type = part.get("type", "")
                                if part_type == "text" and "content" in part:
                                    contents.append(part["content"])
            return json.dumps(contents)
        return messages_json
    except (json.JSONDecodeError, TypeError):
        return messages_json


def extract_input_content(messages_json: str) -> str:
    """Extract text content from user messages only."""
    return extract_content_as_string_list(messages_json, role_filter="user")


def extract_output_content(messages_json: str) -> str:
    """Extract only assistant text content from output messages."""
    return extract_content_as_string_list(messages_json, role_filter="assistant")
