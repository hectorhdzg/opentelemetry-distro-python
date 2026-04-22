# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Span enricher for Semantic Kernel."""

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

from ._utils import extract_content_as_string_list

# Semantic Kernel specific attribute keys
SK_TOOL_CALL_ARGUMENTS_KEY = "gen_ai.tool.call.arguments"
SK_TOOL_CALL_RESULT_KEY = "gen_ai.tool.call.result"


def enrich_semantic_kernel_span(span: ReadableSpan) -> ReadableSpan:
    """Enricher function for Semantic Kernel spans.

    Transforms SK-specific attributes to standard gen_ai attributes
    before the span is exported. Enrichment is applied based on span type:
    - invoke_agent spans: Extract only content from input/output messages
    - execute_tool spans: Map tool arguments and results to standard keys
    """
    extra_attributes = {}
    attributes = span.attributes or {}

    if span.name.startswith(INVOKE_AGENT_OPERATION_NAME):
        input_messages = attributes.get(GEN_AI_INPUT_MESSAGES_KEY)
        if input_messages:
            extra_attributes[GEN_AI_INPUT_MESSAGES_KEY] = extract_content_as_string_list(str(input_messages))

        output_messages = attributes.get(GEN_AI_OUTPUT_MESSAGES_KEY)
        if output_messages:
            extra_attributes[GEN_AI_OUTPUT_MESSAGES_KEY] = extract_content_as_string_list(str(output_messages))

    elif span.name.startswith(EXECUTE_TOOL_OPERATION_NAME):
        if SK_TOOL_CALL_ARGUMENTS_KEY in attributes:
            extra_attributes[GEN_AI_TOOL_ARGS_KEY] = str(attributes[SK_TOOL_CALL_ARGUMENTS_KEY])

        if SK_TOOL_CALL_RESULT_KEY in attributes:
            extra_attributes[GEN_AI_TOOL_CALL_RESULT_KEY] = str(attributes[SK_TOOL_CALL_RESULT_KEY])

    if extra_attributes:
        return EnrichedReadableSpan(span, extra_attributes)

    return span
