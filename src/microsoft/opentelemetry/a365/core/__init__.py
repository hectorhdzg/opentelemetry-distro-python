# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Core Agent365 observability primitives.

Span scopes (such as invoke-agent, execute-tool, and apply-guardrail), data
models, and exporters that make up the Agent365 OpenTelemetry tracing surface.
"""

from microsoft.opentelemetry.a365.core.agent_details import AgentDetails
from microsoft.opentelemetry.a365.core.apply_guardrail_scope import ApplyGuardrailScope
from microsoft.opentelemetry.a365.core.execute_tool_scope import ExecuteToolScope
from microsoft.opentelemetry.a365.core.guardrail_decision_type import GuardrailDecisionType
from microsoft.opentelemetry.a365.core.guardrail_details import GuardrailDetails
from microsoft.opentelemetry.a365.core.guardrail_finding import GuardrailFinding
from microsoft.opentelemetry.a365.core.guardrail_risk_severity import GuardrailRiskSeverity
from microsoft.opentelemetry.a365.core.guardrail_target_type import GuardrailTargetType
from microsoft.opentelemetry.a365.core.gen_ai_request_parameters import GenAiRequestParameters
from microsoft.opentelemetry.a365.core.gen_ai_response_parameters import GenAiResponseParameters
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
    "ApplyGuardrailScope",
    "ExecuteToolScope",
    "InvokeAgentScope",
    "InferenceScope",
    "OutputScope",
    # Guardrail data classes and constants
    "GuardrailDecisionType",
    "GuardrailDetails",
    "GuardrailFinding",
    "GuardrailRiskSeverity",
    "GuardrailTargetType",
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
    "GenAiRequestParameters",
    "GenAiResponseParameters",
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
