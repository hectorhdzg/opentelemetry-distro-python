# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json

from microsoft.opentelemetry.a365.core.message_utils import serialize_messages
from microsoft.opentelemetry.a365.core.models.messages import (
    ChatMessage,
    InputMessages,
    MessageRole,
    OutputMessage,
    OutputMessages,
    TextPart,
)


def test_serialize_messages_preserves_input_message_shape() -> None:
    payload = InputMessages(
        messages=[
            ChatMessage(
                role=MessageRole.USER,
                parts=[TextPart(content="hello")],
            )
        ]
    )

    assert json.loads(serialize_messages(payload)) == [
        {
            "role": "user",
            "parts": [{"content": "hello", "type": "text"}],
        }
    ]


def test_serialize_messages_preserves_output_message_fallback_shape() -> None:
    payload = OutputMessages(messages=[object()])  # type: ignore[list-item]

    assert json.loads(serialize_messages(payload)) == [
        {
            "role": "system",
            "parts": [{"type": "text", "content": "[serialization failed: 1 message]"}],
            "finish_reason": "error",
        }
    ]


def test_serialize_messages_preserves_input_message_fallback_shape() -> None:
    payload = InputMessages(messages=[object()])  # type: ignore[list-item]

    assert json.loads(serialize_messages(payload)) == [
        {
            "role": "system",
            "parts": [{"type": "text", "content": "[serialization failed: 1 message]"}],
        }
    ]


def test_serialize_messages_preserves_output_message_shape() -> None:
    payload = OutputMessages(
        messages=[
            OutputMessage(
                role=MessageRole.ASSISTANT,
                parts=[TextPart(content="hello back")],
            )
        ]
    )

    assert json.loads(serialize_messages(payload)) == [
        {
            "role": "assistant",
            "parts": [{"content": "hello back", "type": "text"}],
            "finish_reason": "stop",
        }
    ]
