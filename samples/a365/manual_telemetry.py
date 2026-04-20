# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Sample: A365 Manual Telemetry APIs

Demonstrates how to use the A365 scope classes to create rich, structured
telemetry for an agent that:
  1. Receives a user request        (InvokeAgentScope)
  2. Calls an LLM for inference     (InferenceScope)
  3. Executes a tool                (ExecuteToolScope)
  4. Returns a response

Uses ``use_microsoft_opentelemetry(enable_a365=True)`` for initialization,
then the A365 scope classes and BaggageBuilder for per-request telemetry.

Environment variables:
  ENABLE_OBSERVABILITY=true                    Required to enable scope telemetry
  ENABLE_A365_OBSERVABILITY_EXPORTER=true      Enable A365 HTTP exporter
"""

import time

from microsoft.opentelemetry import use_microsoft_opentelemetry
from microsoft_agents_a365.observability.core import (
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
    # ------------------------------------------------------------------ #
    # 1. Configure telemetry through the distro
    # ------------------------------------------------------------------ #
    use_microsoft_opentelemetry(
        enable_a365=True,
        enable_azure_monitor=False,
    )
    print("Telemetry configured.\n")

    # ------------------------------------------------------------------ #
    # 2. Define agent and user identity
    # ------------------------------------------------------------------ #
    agent = AgentDetails(
        agent_id="weather-agent-001",
        agent_name="Weather Agent",
        agent_description="Answers weather-related questions",
        tenant_id="contoso-tenant",
        provider_name="openai",
    )

    user = UserDetails(
        user_id="user-42",
        user_email="alice@contoso.com",
        user_name="Alice",
    )

    caller = CallerDetails(user_details=user)

    # ------------------------------------------------------------------ #
    # 3. Build per-request baggage
    # ------------------------------------------------------------------ #
    baggage = (
        BaggageBuilder()
        .tenant_id(agent.tenant_id)
        .agent_id(agent.agent_id)
        .user_id(user.user_id)
        .user_email(user.user_email)
        .user_name(user.user_name)
        .channel_name("webchat")
        .channel_links("https://contoso.com/chat")
        .session_id("session-abc-123")
        .conversation_id("conv-789")
    )

    with baggage.build():
        # -------------------------------------------------------------- #
        # 4. InvokeAgentScope — top-level agent invocation
        # -------------------------------------------------------------- #
        user_question = "What's the weather in Seattle?"

        request = Request(
            content=user_question,
            session_id="session-abc-123",
            channel=Channel(name="webchat"),
            conversation_id="conv-789",
        )

        with InvokeAgentScope.start(
            request=request,
            scope_details=InvokeAgentScopeDetails(
                endpoint=ServiceEndpoint(hostname="weather-agent.contoso.com", port=443),
            ),
            agent_details=agent,
            caller_details=caller,
        ) as invoke_scope:

            # Record structured input messages
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

            # ---------------------------------------------------------- #
            # 5. InferenceScope — LLM call to decide on tool use
            # ---------------------------------------------------------- #
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

                # Simulate LLM latency
                time.sleep(0.05)

                # Record token usage and output
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

            # ---------------------------------------------------------- #
            # 6. ExecuteToolScope — call the weather tool
            # ---------------------------------------------------------- #
            with ExecuteToolScope.start(
                request=Request(content=user_question),
                details=ToolCallDetails(
                    tool_name="get_weather",
                    arguments={"city": "Seattle", "units": "fahrenheit"},
                    tool_call_id="call_abc123",
                    description="Fetches current weather for a city",
                    tool_type=ToolType.FUNCTION.value,
                    endpoint=ServiceEndpoint(hostname="weather-api.contoso.com"),
                ),
                agent_details=agent,
                user_details=user,
            ) as tool_scope:

                # Simulate tool execution
                time.sleep(0.02)
                tool_result = '{"temperature": 62, "condition": "Partly cloudy"}'
                tool_scope.record_response(tool_result)

            # ---------------------------------------------------------- #
            # 7. Second InferenceScope — generate the final answer
            # ---------------------------------------------------------- #
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

                time.sleep(0.05)

                final_answer = "It's currently 62°F and partly cloudy in Seattle."

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

            # ---------------------------------------------------------- #
            # 8. Record the final response on the top-level scope
            # ---------------------------------------------------------- #
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

    print("\nDone. All spans have been created and exported.")


if __name__ == "__main__":
    main()
