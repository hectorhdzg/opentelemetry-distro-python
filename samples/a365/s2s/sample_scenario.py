# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Deterministic telemetry scenario for the A365 S2S sample."""

from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    ApplyGuardrailScope,
    BaggageBuilder,
    CallerDetails,
    ChatMessage,
    ExecuteToolScope,
    GuardrailDecisionType,
    GuardrailDetails,
    GuardrailFinding,
    GuardrailRiskSeverity,
    GuardrailTargetType,
    InferenceCallDetails,
    InferenceOperationType,
    InferenceScope,
    InputMessages,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    MessageRole,
    OutputScope,
    OutputMessage,
    OutputMessages,
    Request,
    Response,
    ServiceEndpoint,
    SpanDetails,
    TextPart,
    ToolCallDetails,
    ToolType,
    UserDetails,
)


def emit_sample_telemetry(
    agent_details: AgentDetails,
    user_details: UserDetails,
    request: Request,
) -> str:
    """Emit deterministic Store-validation telemetry without network calls."""
    user_question = request.content
    if not isinstance(user_question, str):
        raise ValueError("The S2S sample request content must be a string.")
    final_answer = "It's currently 62°F and partly cloudy in Seattle."
    invoke_context = None
    baggage = (
        BaggageBuilder()
        .tenant_id(agent_details.tenant_id)
        .agent_id(agent_details.agent_id)
        .agent_blueprint_id(agent_details.agent_blueprint_id)
        .agent_name(agent_details.agent_name)
        .agent_description(agent_details.agent_description)
        .agent_version(agent_details.agent_version)
        .user_id(user_details.user_id)
        .user_email(user_details.user_email)
        .user_name(user_details.user_name)
        .user_client_ip(user_details.user_client_ip)
        .channel_name(request.channel.name if request.channel else None)
        .channel_links(request.channel.link if request.channel else None)
        .session_id(request.session_id)
        .conversation_id(request.conversation_id)
        .invoke_agent_server("weather-agent.contoso.com", 8443)
    )

    with baggage.build():
        with InvokeAgentScope.start(
            request=request,
            scope_details=InvokeAgentScopeDetails(
                endpoint=ServiceEndpoint(hostname="weather-agent.contoso.com", port=8443),
            ),
            agent_details=agent_details,
            caller_details=CallerDetails(user_details=user_details),
        ) as invoke_scope:
            invoke_scope.record_input_messages(
                InputMessages(
                    messages=[
                        ChatMessage(
                            role=MessageRole.USER,
                            parts=[TextPart(content=user_question)],
                        ),
                    ]
                )
            )

            with ApplyGuardrailScope.start(
                details=GuardrailDetails(
                    target_type=GuardrailTargetType.LLM_INPUT,
                    decision_type=GuardrailDecisionType.ALLOW,
                    guardian_name="Sample Content Safety",
                    guardian_id="sample-content-safety",
                    guardian_provider_name="contoso.security",
                    guardian_version="1.0",
                    target_id="prompt-123",
                    decision_reason="No unsafe content detected",
                    decision_code="allowed",
                    policy_id="policy-123",
                    policy_name="Default Prompt Safety",
                    policy_version="1.0",
                    content_modified=False,
                ),
                agent_details=agent_details,
                request=request,
                user_details=user_details,
            ) as guardrail_scope:
                guardrail_scope.record_content_input(user_question)
                guardrail_scope.record_finding(
                    GuardrailFinding(
                        risk_category="unsafe_content",
                        risk_severity=GuardrailRiskSeverity.NONE,
                        risk_score=0.0,
                        policy_decision_type=GuardrailDecisionType.ALLOW,
                        policy_id="policy-123",
                        policy_name="Default Prompt Safety",
                        policy_version="1.0",
                    )
                )

            with InferenceScope.start(
                request=request,
                details=InferenceCallDetails(
                    operationName=InferenceOperationType.CHAT,
                    model="gpt-4o",
                    providerName="azure-openai",
                    endpoint=ServiceEndpoint(hostname="example.openai.azure.com", port=443),
                ),
                agent_details=agent_details,
                user_details=user_details,
            ) as inference_scope:
                inference_scope.record_input_messages(
                    InputMessages(
                        messages=[
                            ChatMessage(
                                role=MessageRole.SYSTEM,
                                parts=[TextPart(content="You are a helpful weather assistant.")],
                            ),
                            ChatMessage(
                                role=MessageRole.USER,
                                parts=[TextPart(content=user_question)],
                            ),
                        ]
                    )
                )
                inference_scope.record_input_tokens(45)
                inference_scope.record_output_tokens(12)
                inference_scope.record_finish_reasons(["tool_call"])
                inference_scope.record_output_messages(
                    OutputMessages(
                        messages=[
                            OutputMessage(
                                role=MessageRole.ASSISTANT,
                                parts=[TextPart(content="I'll look up the weather for Seattle.")],
                                finish_reason="tool_call",
                            ),
                        ]
                    )
                )

            with ExecuteToolScope.start(
                request=request,
                details=ToolCallDetails(
                    tool_name="get_weather",
                    arguments={"city": "Seattle", "units": "fahrenheit"},
                    tool_call_id="call-123",
                    description="Fetches current weather for a city",
                    tool_type=ToolType.FUNCTION.value,
                    endpoint=ServiceEndpoint(hostname="weather-api.contoso.com", port=443),
                ),
                agent_details=agent_details,
                user_details=user_details,
            ) as tool_scope:
                tool_scope.record_response('{"temperature":62,"condition":"Partly cloudy"}')

            invoke_scope.record_output_messages(
                OutputMessages(
                    messages=[
                        OutputMessage(
                            role=MessageRole.ASSISTANT,
                            parts=[TextPart(content=final_answer)],
                            finish_reason="stop",
                        ),
                    ]
                )
            )
            invoke_context = invoke_scope.get_context()

        assert invoke_context is not None
        with OutputScope.start(
            request=request,
            response=Response(messages=final_answer),
            agent_details=agent_details,
            user_details=user_details,
            span_details=SpanDetails(parent_context=invoke_context),
        ) as output_scope:
            if request.channel:
                output_scope.set_tag_maybe("microsoft.channel.name", request.channel.name)

    return final_answer
