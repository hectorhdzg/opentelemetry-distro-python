# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import asyncio
import time

import pytest
from opentelemetry.trace import get_tracer_provider

from microsoft.opentelemetry.a365.core.constants import (
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_PROVIDER_NAME_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    TENANT_ID_KEY,
)

# AgentFramework SDK
try:
    from agent_framework._agents import RawAgent
    from agent_framework._tools import tool as ai_function
    from agent_framework.openai import OpenAIChatClient
except ImportError as _e:
    pytest.skip(
        f"AgentFramework library and dependencies required for integration tests: {_e}",
        allow_module_level=True,
    )


@ai_function
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together.
    Args:
        a: First number
        b: Second number
    Returns:
        The sum of a and b
    """
    return a + b


@pytest.mark.integration
class TestAgentFrameworkTraceProcessorIntegration:
    """Integration tests for AgentFramework trace processor with real Azure OpenAI."""

    def test_agentframework_trace_processor_integration(
        self, distro_exporter, azure_openai_config, agent365_config
    ):
        """Test AgentFramework trace processor with real Azure OpenAI call."""

        # Create Azure OpenAI ChatClient
        chat_client = OpenAIChatClient(
            model=azure_openai_config["deployment"],
            azure_endpoint=azure_openai_config["endpoint"],
            api_key=azure_openai_config["api_key"],
        )

        # Create agent framework agent
        agent = RawAgent(
            client=chat_client,
            instructions="You are a helpful assistant.",
            tools=[],
        )

        # Execute a simple prompt using async runner
        async def run_agent():
            result = await agent.run("What can you do with agent framework?")
            return result

        response = asyncio.run(run_agent())
        print(f"Agent response: {response}")

        # Flush spans
        get_tracer_provider().force_flush()
        time.sleep(0.5)

        # Verify that spans were captured
        assert len(distro_exporter.spans) > 0, "No spans were captured"

        # Verify we have the expected span types
        span_names = [span.name for span in distro_exporter.spans]
        print(f"Captured spans: {span_names}")

        # Validate attributes on spans
        self._validate_span_attributes(distro_exporter, agent365_config)

        # Verify the response content
        assert response is not None
        assert len(response.text) > 0
        print(f"Agent response: {response.text}")

    def test_agentframework_trace_processor_with_tool_calls(
        self, distro_exporter, azure_openai_config, agent365_config
    ):
        """Test AgentFramework trace processor with tool calls."""

        # Create Azure OpenAI ChatClient
        chat_client = OpenAIChatClient(
            model=azure_openai_config["deployment"],
            azure_endpoint=azure_openai_config["endpoint"],
            api_key=azure_openai_config["api_key"],
        )

        # Create agent framework agent
        agent = RawAgent(
            client=chat_client,
            instructions="You are a helpful agent framework assistant.",
            tools=[add_numbers],
        )

        # Execute a prompt that requires tool usage
        async def run_agent_with_tool():
            result = await agent.run("What is 15 + 27?")
            return result

        response = asyncio.run(run_agent_with_tool())

        # Flush spans
        get_tracer_provider().force_flush()
        time.sleep(0.5)

        # Verify that spans were captured
        assert len(distro_exporter.spans) > 0, "No spans were captured"

        # Verify we have the expected span types
        span_names = [span.name for span in distro_exporter.spans]
        print(f"Captured spans with tools: {span_names}")

        # Validate attributes on spans including tool calls
        self._validate_tool_span_attributes(distro_exporter, agent365_config)

        # Verify the response content includes the calculation result
        assert response is not None
        assert len(response.text) > 0
        assert "42" in response.text  # 15 + 27 = 42
        print(f"Agent response with tool: {response.text}")

    def _validate_span_attributes(self, distro_exporter, agent365_config):
        """Validate that spans have the expected attributes."""
        llm_spans_found = 0
        agent_spans_found = 0

        for span in distro_exporter.spans:
            attributes = dict(span.attributes or {})
            print(f"Span '{span.name}' attributes: {list(attributes.keys())}")

            # Check common attributes
            if TENANT_ID_KEY in attributes:
                assert attributes[TENANT_ID_KEY] == agent365_config["tenant_id"]

            # Check for LLM spans (generation spans)
            if (
                GEN_AI_PROVIDER_NAME_KEY in attributes
                and attributes[GEN_AI_PROVIDER_NAME_KEY] == "openai"
            ):
                if GEN_AI_REQUEST_MODEL_KEY in attributes:
                    llm_spans_found += 1
                    # Validate LLM span attributes
                    assert GEN_AI_REQUEST_MODEL_KEY in attributes
                    assert attributes[GEN_AI_REQUEST_MODEL_KEY] is not None
                    print(f"✓ Found LLM span with model: {attributes[GEN_AI_REQUEST_MODEL_KEY]}")

                    # Check for input/output messages
                    if GEN_AI_INPUT_MESSAGES_KEY in attributes:
                        input_messages = attributes[GEN_AI_INPUT_MESSAGES_KEY]
                        assert input_messages is not None
                        print(f"✓ Input messages found: {input_messages[:100]}...")

                    if GEN_AI_OUTPUT_MESSAGES_KEY in attributes:
                        output_messages = attributes[GEN_AI_OUTPUT_MESSAGES_KEY]
                        assert output_messages is not None
                        print(f"✓ Output messages found: {output_messages[:100]}...")

            # Check for agent spans
            if "agent" in span.name.lower():
                agent_spans_found += 1
                print(f"✓ Found agent span: {span.name}")

        # Ensure we found at least some spans with telemetry data
        assert len(distro_exporter.spans) > 0, "No spans were captured"
        print(f"✓ Captured {len(distro_exporter.spans)} spans total")
        print(f"✓ Found {llm_spans_found} LLM spans and {agent_spans_found} agent spans")

    def _validate_tool_span_attributes(self, distro_exporter, agent365_config):
        """Validate that spans have the expected attributes including tool calls."""
        llm_spans_found = 0
        agent_spans_found = 0
        tool_spans_found = 0

        for span in distro_exporter.spans:
            attributes = dict(span.attributes or {})
            print(f"Span '{span.name}' attributes: {list(attributes.keys())}")

            # Check common attributes
            if TENANT_ID_KEY in attributes:
                assert attributes[TENANT_ID_KEY] == agent365_config["tenant_id"]

            # Check for LLM spans
            if "chat" in span.name.lower():
                if GEN_AI_REQUEST_MODEL_KEY in attributes:
                    llm_spans_found += 1
                    print(f"✓ Found LLM span with model: {attributes[GEN_AI_REQUEST_MODEL_KEY]}")

                    # Check for tool calls in messages
                    if GEN_AI_OUTPUT_MESSAGES_KEY in attributes:
                        output_messages = attributes[GEN_AI_OUTPUT_MESSAGES_KEY]
                        if "tool_calls" in output_messages:
                            print("✓ Found tool calls in LLM output messages")

            # Check for agent spans
            if "agent" in span.name.lower():
                agent_spans_found += 1
                print(f"✓ Found agent span: {span.name}")

            # Check for tool execution spans
            if "execute_tool" in span.name.lower() or "add_numbers" in span.name.lower():
                tool_spans_found += 1
                print(f"✓ Found tool execution span: {span.name}")

        # Ensure we found the expected span types
        assert len(distro_exporter.spans) > 0, "No spans were captured"
        print(f"✓ Captured {len(distro_exporter.spans)} spans total")
        print(
            f"✓ Found {llm_spans_found} LLM spans, {agent_spans_found} agent spans, and {tool_spans_found} tool spans"
        )
