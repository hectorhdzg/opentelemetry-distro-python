# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# Microsoft Agent 365 Python SDK for OpenTelemetry tracing.

from microsoft.opentelemetry.a365.core.agent_details import AgentDetails
from microsoft.opentelemetry.a365.core.execute_tool_scope import ExecuteToolScope
from microsoft.opentelemetry.a365.core.inference_call_details import InferenceCallDetails
from microsoft.opentelemetry.a365.core.models.service_endpoint import ServiceEndpoint
from microsoft.opentelemetry.a365.core.inference_operation_type import InferenceOperationType
from microsoft.opentelemetry.a365.core.inference_scope import InferenceScope
from microsoft.opentelemetry.a365.core.invoke_agent_details import InvokeAgentScopeDetails
from microsoft.opentelemetry.a365.core.invoke_agent_scope import InvokeAgentScope
from microsoft.opentelemetry.a365.core.middleware.baggage_builder import BaggageBuilder
from microsoft.opentelemetry.a365.core.models.caller_details import CallerDetails
from microsoft.opentelemetry.a365.core.models.messages import (
    BlobPart,
    ChatMessage,
    FilePart,
    FinishReason,
    GenericPart,
    InputMessages,
    InputMessagesParam,
    MessagePart,
    MessageRole,
    Modality,
    OutputMessage,
    OutputMessages,
    OutputMessagesParam,
    ReasoningPart,
    ServerToolCallPart,
    ServerToolCallResponsePart,
    TextPart,
    ToolCallRequestPart,
    ToolCallResponsePart,
    UriPart,
)
from microsoft.opentelemetry.a365.core.models.response import Response
from microsoft.opentelemetry.a365.core.models.user_details import UserDetails
from microsoft.opentelemetry.a365.core.opentelemetry_scope import OpenTelemetryScope
from microsoft.opentelemetry.a365.core.request import Request
from microsoft.opentelemetry.a365.core.channel import Channel
from microsoft.opentelemetry.a365.core.span_details import SpanDetails
from microsoft.opentelemetry.a365.core.spans_scopes.output_scope import OutputScope
from microsoft.opentelemetry.a365.core.tool_call_details import ToolCallDetails
from microsoft.opentelemetry.a365.core.tool_type import ToolType

__all__ = [
    # Base scope class
    "OpenTelemetryScope",
    # Specific scope classes
    "ExecuteToolScope",
    "InvokeAgentScope",
    "InferenceScope",
    "OutputScope",
    # Middleware
    "BaggageBuilder",
    # Data classes
    "InvokeAgentScopeDetails",
    "AgentDetails",
    "CallerDetails",
    "UserDetails",
    "ToolCallDetails",
    "Channel",
    "Request",
    "Response",
    "SpanDetails",
    "InferenceCallDetails",
    "ServiceEndpoint",
    # Enums
    "InferenceOperationType",
    "ToolType",
    # OTEL gen-ai message format types
    "MessageRole",
    "FinishReason",
    "Modality",
    "TextPart",
    "ToolCallRequestPart",
    "ToolCallResponsePart",
    "ReasoningPart",
    "BlobPart",
    "FilePart",
    "UriPart",
    "ServerToolCallPart",
    "ServerToolCallResponsePart",
    "GenericPart",
    "MessagePart",
    "ChatMessage",
    "OutputMessage",
    "InputMessages",
    "OutputMessages",
    "InputMessagesParam",
    "OutputMessagesParam",
]

# This is a namespace package
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
