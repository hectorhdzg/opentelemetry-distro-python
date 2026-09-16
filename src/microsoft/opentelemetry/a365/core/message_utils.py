# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Conversion and serialization helpers for OTEL gen-ai message format.

Provides normalization from plain ``list[str]`` (backward compat) to the
structured array format, and a non-throwing ``serialize_messages`` function.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from enum import Enum
from typing import Any, Sequence, Union

from microsoft.opentelemetry.a365.core.models.messages import (
    ChatMessage,
    InputMessages,
    InputMessagesParam,
    MessageRole,
    OutputMessage,
    OutputMessages,
    OutputMessagesParam,
    TextPart,
)

logger = logging.getLogger(__name__)


# pylint: disable=broad-exception-caught
def is_string_list(
    param: Union[InputMessagesParam, OutputMessagesParam],
) -> bool:
    """Return ``True`` when *param* is a plain ``list[str]``."""
    return isinstance(param, list) and all(isinstance(item, str) for item in param)


def is_wrapped_messages(
    param: Union[InputMessagesParam, OutputMessagesParam],
) -> bool:
    """Return ``True`` when *param* is a structured message container."""
    return isinstance(param, (InputMessages, OutputMessages))


# ---------------------------------------------------------------------------
# Plain-string -> structured conversion
# ---------------------------------------------------------------------------


def to_input_messages(messages: list[str]) -> list[ChatMessage]:
    """Convert plain input strings into OTEL ``ChatMessage`` objects."""
    return [ChatMessage(role=MessageRole.USER, parts=[TextPart(content=content)]) for content in messages]


def to_output_messages(messages: list[str]) -> list[OutputMessage]:
    """Convert plain output strings into OTEL ``OutputMessage`` objects."""
    return [OutputMessage(role=MessageRole.ASSISTANT, parts=[TextPart(content=content)]) for content in messages]


# ---------------------------------------------------------------------------
# Normalization (union -> structured container)
# ---------------------------------------------------------------------------


def normalize_input_messages(param: InputMessagesParam) -> InputMessages:
    """Normalize an ``InputMessagesParam`` to an ``InputMessages`` container.

    - ``str`` -> wrapped in a single-element list, then converted.
    - ``list[str]`` -> converted to ``ChatMessage`` list and wrapped.
    - ``InputMessages`` -> returned as-is.
    """
    if isinstance(param, str):
        return InputMessages(messages=to_input_messages([param]))
    if is_string_list(param):
        return InputMessages(messages=to_input_messages(param))  # type: ignore[arg-type]
    return param  # type: ignore[return-value]


def normalize_output_messages(param: OutputMessagesParam) -> OutputMessages:
    """Normalize an ``OutputMessagesParam`` to an ``OutputMessages`` container.

    - ``str`` -> wrapped in a single-element list, then converted.
    - ``list[str]`` -> converted to ``OutputMessage`` list and wrapped.
    - ``OutputMessages`` -> returned as-is.
    """
    if isinstance(param, str):
        return OutputMessages(messages=to_output_messages([param]))
    if is_string_list(param):
        return OutputMessages(messages=to_output_messages(param))  # type: ignore[arg-type]
    return param  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _message_dict_factory(items: list[tuple[str, object]]) -> dict[str, object]:
    """Custom dict factory for ``dataclasses.asdict``.

    Drops ``None`` values and converts enum members to their string value.
    """
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in items if v is not None}


def _serialize_dataclasses(items: Sequence[Any]) -> str:
    """Serialize dataclass instances as a JSON array."""
    return json.dumps(
        [asdict(item, dict_factory=_message_dict_factory) for item in items],
        default=str,
        ensure_ascii=False,
    )


def serialize_messages(
    wrapper: Union[InputMessages, OutputMessages],
) -> str:
    """Serialize a message container to a JSON array.

    The output is a plain JSON array of message objects per OTel spec:
    ``[{"role":"user","parts":[...]}]``.

    The try/except ensures telemetry recording is non-throwing even when
    message parts contain non-JSON-serializable values.
    """
    try:
        return _serialize_dataclasses(wrapper.messages)
    except Exception:
        logger.warning("Failed to serialize messages; using fallback.", exc_info=True)
        messages = getattr(wrapper, "messages", [])
        count = len(messages) if isinstance(messages, list) else 0
        noun = "message" if count == 1 else "messages"
        fallback_msg: dict[str, object] = {
            "role": MessageRole.SYSTEM.value,
            "parts": [
                {
                    "type": "text",
                    "content": f"[serialization failed: {count} {noun}]",
                }
            ],
        }
        if isinstance(wrapper, OutputMessages):
            fallback_msg["finish_reason"] = "error"
        return json.dumps([fallback_msg], ensure_ascii=False)


def serialize_system_instructions(parts: Sequence[TextPart]) -> str:
    """Serialize OTel system-instruction parts as a JSON array."""
    try:
        return _serialize_dataclasses(parts)
    except Exception:
        logger.warning("Failed to serialize system instructions; using fallback.", exc_info=True)
        count = len(parts)
        noun = "instruction part" if count == 1 else "instruction parts"
        return _serialize_dataclasses([TextPart(content=f"[serialization failed: {count} {noun}]")])
