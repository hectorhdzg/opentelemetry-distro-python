# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# Invoke agent scope for tracing agent invocation.

import logging

from opentelemetry.trace import SpanKind

from microsoft.opentelemetry.a365.core.agent_details import AgentDetails
from microsoft.opentelemetry.a365.core.constants import (
    CHANNEL_LINK_KEY,
    CHANNEL_NAME_KEY,
    GEN_AI_CALLER_AGENT_APPLICATION_ID_KEY,
    GEN_AI_CALLER_AGENT_EMAIL_KEY,
    GEN_AI_CALLER_AGENT_ID_KEY,
    GEN_AI_CALLER_AGENT_NAME_KEY,
    GEN_AI_CALLER_AGENT_PLATFORM_ID_KEY,
    GEN_AI_CALLER_AGENT_USER_ID_KEY,
    GEN_AI_CALLER_AGENT_VERSION_KEY,
    GEN_AI_CALLER_CLIENT_IP_KEY,
    GEN_AI_CONVERSATION_ID_KEY,
    GEN_AI_DATA_SOURCE_ID_KEY,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_TYPE_KEY,
    GEN_AI_REQUEST_CHOICE_COUNT_KEY,
    GEN_AI_REQUEST_FREQUENCY_PENALTY_KEY,
    GEN_AI_REQUEST_MAX_TOKENS_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    GEN_AI_REQUEST_PRESENCE_PENALTY_KEY,
    GEN_AI_REQUEST_SEED_KEY,
    GEN_AI_REQUEST_STOP_SEQUENCES_KEY,
    GEN_AI_REQUEST_TEMPERATURE_KEY,
    GEN_AI_REQUEST_TOP_P_KEY,
    GEN_AI_RESPONSE_FINISH_REASONS_KEY,
    GEN_AI_SYSTEM_INSTRUCTIONS_KEY,
    GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS_KEY,
    GEN_AI_USAGE_CACHE_WRITE_INPUT_TOKENS_KEY,
    GEN_AI_USAGE_INPUT_TOKENS_KEY,
    GEN_AI_USAGE_OUTPUT_TOKENS_KEY,
    INVOKE_AGENT_OPERATION_NAME,
    SERVER_ADDRESS_KEY,
    SERVER_PORT_KEY,
    SESSION_ID_KEY,
    USER_EMAIL_KEY,
    USER_ID_KEY,
    USER_NAME_KEY,
)
from microsoft.opentelemetry.a365.core.gen_ai_request_parameters import GenAiRequestParameters
from microsoft.opentelemetry.a365.core.gen_ai_response_parameters import GenAiResponseParameters
from microsoft.opentelemetry.a365.core.invoke_agent_details import InvokeAgentScopeDetails
from microsoft.opentelemetry.a365.core.message_utils import (
    normalize_input_messages,
    normalize_output_messages,
    serialize_messages,
    serialize_system_instructions,
)
from microsoft.opentelemetry.a365.core.models.caller_details import CallerDetails
from microsoft.opentelemetry.a365.core.models.messages import InputMessagesParam, OutputMessagesParam
from microsoft.opentelemetry.a365.core.opentelemetry_scope import OpenTelemetryScope
from microsoft.opentelemetry.a365.core.request import Request
from microsoft.opentelemetry.a365.core.span_details import SpanDetails
from microsoft.opentelemetry.a365.core.utils import validate_and_normalize_ip

logger = logging.getLogger(__name__)


class InvokeAgentScope(OpenTelemetryScope):
    """Provides OpenTelemetry tracing scope for AI agent invocation operations."""

    @staticmethod
    def start(
        request: Request,
        scope_details: InvokeAgentScopeDetails,
        agent_details: AgentDetails,
        caller_details: CallerDetails | None = None,
        span_details: SpanDetails | None = None,
    ) -> "InvokeAgentScope":
        """Create and start a new scope for agent invocation tracing.

        Args:
            request: Request details for the invocation
            scope_details: Scope-level configuration (endpoint)
            agent_details: The details of the agent being invoked
            caller_details: Optional composite caller details (human user and/or
                calling agent for A2A scenarios)
            span_details: Optional span configuration (parent context, timing, kind)

        Returns:
            A new InvokeAgentScope instance
        """
        return InvokeAgentScope(
            request,
            scope_details,
            agent_details,
            caller_details,
            span_details,
        )

    def __init__(
        self,
        request: Request,
        scope_details: InvokeAgentScopeDetails,
        agent_details: AgentDetails,
        caller_details: CallerDetails | None = None,
        span_details: SpanDetails | None = None,
    ):
        """Initialize the agent invocation scope.

        Args:
            request: Request details for the invocation
            scope_details: Scope-level configuration (endpoint)
            agent_details: The details of the agent being invoked
            caller_details: Optional composite caller details (human user and/or
                calling agent for A2A scenarios)
            span_details: Optional span configuration (parent context, timing, kind)
        """
        activity_name = INVOKE_AGENT_OPERATION_NAME
        if agent_details.agent_name:
            activity_name = f"{INVOKE_AGENT_OPERATION_NAME} {agent_details.agent_name}"

        # spanKind defaults to CLIENT; allow override via span_details
        resolved_span_details = (
            SpanDetails(
                span_kind=span_details.span_kind if span_details and span_details.span_kind else SpanKind.CLIENT,
                parent_context=span_details.parent_context if span_details else None,
                start_time=span_details.start_time if span_details else None,
                end_time=span_details.end_time if span_details else None,
                span_links=span_details.span_links if span_details else None,
            )
            if span_details
            else SpanDetails(span_kind=SpanKind.CLIENT)
        )

        super().__init__(
            operation_name=INVOKE_AGENT_OPERATION_NAME,
            activity_name=activity_name,
            agent_details=agent_details,
            span_details=resolved_span_details,
        )

        self.set_tag_maybe(SESSION_ID_KEY, request.session_id)
        self.set_tag_maybe(GEN_AI_CONVERSATION_ID_KEY, request.conversation_id)

        endpoint = scope_details.endpoint
        if endpoint:
            self.set_tag_maybe(SERVER_ADDRESS_KEY, endpoint.hostname)
            if endpoint.port and endpoint.port != 443:
                self.set_tag_maybe(SERVER_PORT_KEY, endpoint.port)

        if scope_details.request_parameters:
            self._record_request_parameters(scope_details.request_parameters)
        if scope_details.response_parameters:
            self._record_response_parameters(scope_details.response_parameters)

        # Set request metadata
        if request.channel:
            self.set_tag_maybe(CHANNEL_NAME_KEY, request.channel.name)
            self.set_tag_maybe(CHANNEL_LINK_KEY, request.channel.link)
        if request.content is not None:
            self.record_input_messages(request.content)

        # Set caller details tags
        if caller_details:
            user_details = caller_details.user_details
            if user_details:
                self.set_tag_maybe(USER_ID_KEY, user_details.user_id)
                self.set_tag_maybe(USER_EMAIL_KEY, user_details.user_email)
                self.set_tag_maybe(USER_NAME_KEY, user_details.user_name)
                self.set_tag_maybe(
                    GEN_AI_CALLER_CLIENT_IP_KEY,
                    validate_and_normalize_ip(user_details.user_client_ip),
                )

            # Set caller agent details tags
            caller_agent_details = caller_details.caller_agent_details
            if caller_agent_details:
                self.set_tag_maybe(GEN_AI_CALLER_AGENT_NAME_KEY, caller_agent_details.agent_name)
                self.set_tag_maybe(GEN_AI_CALLER_AGENT_ID_KEY, caller_agent_details.agent_id)
                self.set_tag_maybe(
                    GEN_AI_CALLER_AGENT_APPLICATION_ID_KEY,
                    caller_agent_details.agent_blueprint_id,
                )
                self.set_tag_maybe(
                    GEN_AI_CALLER_AGENT_USER_ID_KEY,
                    caller_agent_details.agentic_user_id,
                )
                self.set_tag_maybe(
                    GEN_AI_CALLER_AGENT_EMAIL_KEY,
                    caller_agent_details.agentic_user_email,
                )
                self.set_tag_maybe(
                    GEN_AI_CALLER_AGENT_PLATFORM_ID_KEY,
                    caller_agent_details.agent_platform_id,
                )
                self.set_tag_maybe(
                    GEN_AI_CALLER_AGENT_VERSION_KEY,
                    caller_agent_details.agent_version,
                )

    def record_response(self, response: str) -> None:
        """Record response information for telemetry tracking.

        Args:
            response: The response string to record
        """
        self.record_output_messages([response])

    def record_response_parameters(self, parameters: GenAiResponseParameters) -> None:
        """Record GenAI response parameters that are only known after completion."""
        self._record_response_parameters(parameters)

    def record_input_messages(self, messages: InputMessagesParam) -> None:
        """Record the input messages for telemetry tracking.

        Accepts plain strings (auto-wrapped as OTEL ChatMessage with role ``user``)
        or a structured ``InputMessages`` container.

        Args:
            messages: List of input message strings or an InputMessages container
        """
        wrapper = normalize_input_messages(messages)
        self.set_tag_maybe(GEN_AI_INPUT_MESSAGES_KEY, serialize_messages(wrapper))

    def record_output_messages(self, messages: OutputMessagesParam) -> None:
        """Record the output messages for telemetry tracking.

        Accepts plain strings (auto-wrapped as OTEL OutputMessage with role ``assistant``)
        or a structured ``OutputMessages`` container.

        Args:
            messages: List of output message strings or an OutputMessages container
        """
        wrapper = normalize_output_messages(messages)
        self.set_tag_maybe(GEN_AI_OUTPUT_MESSAGES_KEY, serialize_messages(wrapper))

    def _record_request_parameters(self, parameters: GenAiRequestParameters) -> None:
        self.set_tag_maybe(GEN_AI_REQUEST_MODEL_KEY, parameters.model)
        self.set_tag_maybe(GEN_AI_REQUEST_SEED_KEY, parameters.seed)
        self.set_tag_maybe(GEN_AI_REQUEST_CHOICE_COUNT_KEY, parameters.choice_count)
        self.set_tag_maybe(GEN_AI_REQUEST_FREQUENCY_PENALTY_KEY, parameters.frequency_penalty)
        self.set_tag_maybe(GEN_AI_REQUEST_MAX_TOKENS_KEY, parameters.max_tokens)
        self.set_tag_maybe(GEN_AI_REQUEST_PRESENCE_PENALTY_KEY, parameters.presence_penalty)
        self.set_tag_maybe(
            GEN_AI_REQUEST_STOP_SEQUENCES_KEY,
            tuple(parameters.stop_sequences) if parameters.stop_sequences is not None else None,
        )
        self.set_tag_maybe(GEN_AI_REQUEST_TEMPERATURE_KEY, parameters.temperature)
        self.set_tag_maybe(GEN_AI_REQUEST_TOP_P_KEY, parameters.top_p)
        self.set_tag_maybe(GEN_AI_DATA_SOURCE_ID_KEY, parameters.data_source_id)
        self.set_tag_maybe(GEN_AI_OUTPUT_TYPE_KEY, parameters.output_type)
        if parameters.system_instructions is not None:
            self.set_tag_maybe(
                GEN_AI_SYSTEM_INSTRUCTIONS_KEY,
                serialize_system_instructions(parameters.system_instructions),
            )

    def _record_response_parameters(self, parameters: GenAiResponseParameters) -> None:
        self.set_tag_maybe(
            GEN_AI_RESPONSE_FINISH_REASONS_KEY,
            tuple(parameters.finish_reasons) if parameters.finish_reasons is not None else None,
        )
        self.set_tag_maybe(GEN_AI_USAGE_INPUT_TOKENS_KEY, parameters.input_tokens)
        self.set_tag_maybe(GEN_AI_USAGE_OUTPUT_TOKENS_KEY, parameters.output_tokens)
        self.set_tag_maybe(
            GEN_AI_USAGE_CACHE_WRITE_INPUT_TOKENS_KEY,
            parameters.cache_write_input_tokens,
        )
        self.set_tag_maybe(
            GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS_KEY,
            parameters.cache_read_input_tokens,
        )
