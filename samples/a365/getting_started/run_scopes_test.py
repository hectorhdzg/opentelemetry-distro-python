# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Quick test: exercise all A365 scope classes with console span output.

Usage:
    python samples/a365/getting_started/run_scopes_test.py

No Agent365 infrastructure required — uses ConsoleSpanExporter to print spans.
"""

import os
import time

# Ensure observability is enabled
os.environ["ENABLE_OBSERVABILITY"] = "true"

from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    BaggageBuilder,
    CallerDetails,
    Channel,
    ChatMessage,
    ExecuteToolScope,
    InferenceCallDetails,
    InferenceOperationType,
    InferenceScope,
    InputMessages,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    MessageRole,
    OutputMessage,
    OutputMessages,
    Request,
    ServiceEndpoint,
    TextPart,
    ToolCallDetails,
    ToolType,
    UserDetails,
)


def main():
    # 1. Configure distro with console exporter (no A365 backend needed)
    use_microsoft_opentelemetry(
        enable_a365=False,
        enable_azure_monitor=False,
        span_processors=[SimpleSpanProcessor(ConsoleSpanExporter())],
    )
    print("=== Telemetry configured (console exporter) ===\n")

    # 2. Define agent + user
    agent = AgentDetails(
        agent_id="test-agent-001",
        agent_name="Test Agent",
        agent_description="Sample agent for scope testing",
        tenant_id="test-tenant",
        provider_name="openai",
    )

    user = UserDetails(
        user_id="user-42",
        user_email="alice@contoso.com",
        user_name="Alice",
    )

    caller = CallerDetails(user_details=user)

    # 3. Build baggage
    baggage = (
        BaggageBuilder()
        .tenant_id(agent.tenant_id)
        .agent_id(agent.agent_id)
        .user_id(user.user_id)
        .user_email(user.user_email)
        .session_id("session-test-001")
        .conversation_id("conv-test-001")
        .channel_name("test")
    )

    with baggage.build():
        # 4. InvokeAgentScope
        user_question = "What's the weather in Seattle?"

        request = Request(
            content=user_question,
            session_id="session-test-001",
            channel=Channel(name="test"),
            conversation_id="conv-test-001",
        )

        with InvokeAgentScope.start(
            request=request,
            scope_details=InvokeAgentScopeDetails(
                endpoint=ServiceEndpoint(hostname="test-agent.contoso.com", port=443),
            ),
            agent_details=agent,
            caller_details=caller,
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
            print("[OK] InvokeAgentScope started")

            # 5. InferenceScope
            with InferenceScope.start(
                request=Request(content=user_question),
                details=InferenceCallDetails(
                    operationName=InferenceOperationType.CHAT,
                    model="gpt-4o",
                    providerName="openai",
                    endpoint=ServiceEndpoint(hostname="api.openai.com", port=443),
                ),
                agent_details=agent,
                user_details=user,
            ) as inference_scope:

                inference_scope.record_input_messages(
                    InputMessages(
                        messages=[
                            ChatMessage(role=MessageRole.SYSTEM, parts=[TextPart(content="You are a weather assistant.")]),
                            ChatMessage(role=MessageRole.USER, parts=[TextPart(content=user_question)]),
                        ]
                    )
                )

                time.sleep(0.01)

                inference_scope.record_input_tokens(45)
                inference_scope.record_output_tokens(12)
                inference_scope.record_finish_reasons(["tool_call"])
                inference_scope.record_output_messages(
                    OutputMessages(
                        messages=[
                            OutputMessage(
                                role=MessageRole.ASSISTANT,
                                parts=[TextPart(content="I'll check the weather.")],
                                finish_reason="tool_call",
                            ),
                        ]
                    )
                )
                print("[OK] InferenceScope (1st LLM call) completed")

            # 6. ExecuteToolScope
            with ExecuteToolScope.start(
                request=Request(content=user_question),
                details=ToolCallDetails(
                    tool_name="get_weather",
                    arguments={"city": "Seattle"},
                    tool_call_id="call_001",
                    description="Get current weather",
                    tool_type=ToolType.FUNCTION.value,
                    endpoint=ServiceEndpoint(hostname="weather-api.contoso.com"),
                ),
                agent_details=agent,
                user_details=user,
            ) as tool_scope:

                time.sleep(0.01)
                tool_result = '{"temp": 62, "condition": "Partly cloudy"}'
                tool_scope.record_response(tool_result)
                print("[OK] ExecuteToolScope completed")

            # 7. Second InferenceScope
            with InferenceScope.start(
                request=Request(content=user_question),
                details=InferenceCallDetails(
                    operationName=InferenceOperationType.CHAT,
                    model="gpt-4o",
                    providerName="openai",
                    inputTokens=80,
                    outputTokens=25,
                    finishReasons=["stop"],
                    endpoint=ServiceEndpoint(hostname="api.openai.com", port=443),
                ),
                agent_details=agent,
                user_details=user,
            ) as inference_scope_2:

                time.sleep(0.01)
                final_answer = "It's 62°F and partly cloudy in Seattle."
                inference_scope_2.record_output_messages(
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
                print("[OK] InferenceScope (2nd LLM call) completed")

            # 8. Record final response
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

    print("\n=== All scopes completed successfully ===")


if __name__ == "__main__":
    main()
