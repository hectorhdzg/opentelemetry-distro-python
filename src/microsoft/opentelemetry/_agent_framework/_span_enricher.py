# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Span enricher for Agent Framework."""

from microsoft.opentelemetry.a365.core.constants import (
    EXECUTE_TOOL_OPERATION_NAME,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_TOOL_ARGS_KEY,
    GEN_AI_TOOL_CALL_RESULT_KEY,
    INVOKE_AGENT_OPERATION_NAME,
)
from microsoft.opentelemetry.a365.core.exporters.enriched_span import EnrichedReadableSpan
from opentelemetry.sdk.trace import ReadableSpan

from ._utils import extract_input_content, extract_output_content

# Agent Framework specific attribute keys
AF_TOOL_CALL_ARGUMENTS_KEY = "gen_ai.tool.call.arguments"
AF_TOOL_CALL_RESULT_KEY = "gen_ai.tool.call.result"


def enrich_agent_framework_span(span: ReadableSpan) -> ReadableSpan:
    """Enricher function for Agent Framework spans.

    Transforms AF-specific attributes to standard gen_ai attributes
    before the span is exported. For invoke_agent spans, filters
    input to user messages and output to assistant messages.
    """
    extra_attributes = {}
    attributes = span.attributes or {}

    if span.name.startswith(INVOKE_AGENT_OPERATION_NAME):
        input_messages = attributes.get(GEN_AI_INPUT_MESSAGES_KEY)
        if input_messages:
            extra_attributes[GEN_AI_INPUT_MESSAGES_KEY] = extract_input_content(str(input_messages))

        output_messages = attributes.get(GEN_AI_OUTPUT_MESSAGES_KEY)
        if output_messages:
            extra_attributes[GEN_AI_OUTPUT_MESSAGES_KEY] = extract_output_content(str(output_messages))

    elif span.name.startswith(EXECUTE_TOOL_OPERATION_NAME):
        if AF_TOOL_CALL_ARGUMENTS_KEY in attributes:
            extra_attributes[GEN_AI_TOOL_ARGS_KEY] = str(attributes[AF_TOOL_CALL_ARGUMENTS_KEY])

        if AF_TOOL_CALL_RESULT_KEY in attributes:
            extra_attributes[GEN_AI_TOOL_CALL_RESULT_KEY] = str(attributes[AF_TOOL_CALL_RESULT_KEY])

    if extra_attributes:
        return EnrichedReadableSpan(span, extra_attributes)

    return span
