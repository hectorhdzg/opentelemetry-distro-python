# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import time

import pytest
from opentelemetry.trace import get_tracer_provider

from microsoft.opentelemetry.a365.core.constants import (
    GEN_AI_AGENT_ID_KEY,
    GEN_AI_AGENT_NAME_KEY,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_PROVIDER_NAME_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    INVOKE_AGENT_OPERATION_NAME,
    TENANT_ID_KEY,
)
from microsoft.opentelemetry.a365.core.agent_details import AgentDetails
from microsoft.opentelemetry.a365.core.invoke_agent_details import InvokeAgentScopeDetails
from microsoft.opentelemetry.a365.core.invoke_agent_scope import InvokeAgentScope
from microsoft.opentelemetry.a365.core.request import Request

try:
    from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool
    from openai import AsyncAzureOpenAI
except ImportError:
    pytest.skip(
        "OpenAI agents library and dependencies required for integration tests",
        allow_module_level=True,
    )


@function_tool
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
class TestOpenAITraceProcessorIntegration:
    """Integration tests for OpenAI trace processor with real Azure OpenAI."""

    def test_openai_trace_processor_integration(self, distro_exporter, azure_openai_config, agent365_config):
        """Test OpenAI trace processor with real Azure OpenAI call."""

        # Create Azure OpenAI client using API key (simpler for testing)
        openai_client = AsyncAzureOpenAI(
            api_key=azure_openai_config["api_key"],
            api_version=azure_openai_config["api_version"],
            azure_endpoint=azure_openai_config["endpoint"],
        )

        # Create agent with proper model configuration
        agent = Agent(
            name="TestAgent",
            instructions="You are a helpful assistant.",
            model=OpenAIChatCompletionsModel(
                model=azure_openai_config["deployment"], openai_client=openai_client
            ),
        )

        # Execute a simple prompt using async runner
        import asyncio

        async def run_agent():
            result = await Runner.run(agent, "What can you do?")
            return result.final_output

        response = asyncio.run(run_agent())

        # Flush and wait for spans to be exported
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
        assert len(response) > 0
        print(f"Agent response: {response}")

    def test_openai_trace_processor_with_tool_calls(self, distro_exporter, azure_openai_config, agent365_config):
        """Test OpenAI trace processor with tool calls."""

        # Create Azure OpenAI client using API key
        openai_client = AsyncAzureOpenAI(
            api_key=azure_openai_config["api_key"],
            api_version=azure_openai_config["api_version"],
            azure_endpoint=azure_openai_config["endpoint"],
        )

        # Create agent with tool
        agent = Agent(
            name="MathAgent",
            instructions="You are a helpful math assistant. Use the add_numbers tool to perform calculations.",
            model=OpenAIChatCompletionsModel(
                model=azure_openai_config["deployment"], openai_client=openai_client
            ),
            tools=[add_numbers],
        )

        # Execute a prompt that requires tool usage
        import asyncio

        async def run_agent_with_tool():
            result = await Runner.run(agent, "What is 15 + 27?")
            return result.final_output

        response = asyncio.run(run_agent_with_tool())

        # Flush and wait for spans to be exported
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
        assert len(response) > 0
        assert "42" in response  # 15 + 27 = 42
        print(f"Agent response with tool: {response}")

    def test_invoke_agent_span_required_attributes(self, distro_exporter, azure_openai_config, agent365_config):
        """Test that invoke_agent span has all required attributes per schema.

        The distro sets up _EnrichingBatchSpanProcessor so that agent_details
        set on the InvokeAgentScope parent span are propagated to child spans
        created by the instrumentor.
        """
        openai_client = AsyncAzureOpenAI(
            api_key=azure_openai_config["api_key"],
            api_version=azure_openai_config["api_version"],
            azure_endpoint=azure_openai_config["endpoint"],
        )

        agent = Agent(
            name="TestAgent",
            instructions="You are a helpful assistant. Answer briefly.",
            model=OpenAIChatCompletionsModel(
                model=azure_openai_config["deployment"], openai_client=openai_client
            ),
        )

        import asyncio

        agent_details = AgentDetails(
            agent_id="test-agent-id",
            agent_name="TestAgent",
            tenant_id="test-tenant-id",
        )
        request = Request(content="Say hello", session_id="test-session")

        async def run_agent():
            with InvokeAgentScope.start(
                request=request,
                scope_details=InvokeAgentScopeDetails(),
                agent_details=agent_details,
            ):
                result = await Runner.run(agent, "Say hello")
                return result.final_output

        response = asyncio.run(run_agent())

        # Flush the enriching batch processor so spans are exported
        get_tracer_provider().force_flush()
        time.sleep(0.5)

        # There are two invoke_agent spans:
        # 1. The InvokeAgentScope span (parent) - has gen_ai.agent.id/name
        # 2. The instrumentor span (child) - has gen_ai.input/output.messages
        # Find the scope span (has gen_ai.agent.id) for attribute validation
        invoke_agent_spans = [
            s for s in distro_exporter.spans
            if s.name.startswith(INVOKE_AGENT_OPERATION_NAME)
        ]
        assert len(invoke_agent_spans) >= 1, "No invoke_agent spans found"

        # The scope span is the one with gen_ai.agent.id set
        scope_span = None
        instrumentor_span = None
        for span in invoke_agent_spans:
            attrs = dict(span.attributes or {})
            if GEN_AI_AGENT_ID_KEY in attrs:
                scope_span = span
            else:
                instrumentor_span = span

        # Validate scope span has agent identity attributes
        assert scope_span is not None, (
            f"No invoke_agent span with {GEN_AI_AGENT_ID_KEY} found. "
            f"Span attrs: {[list((s.attributes or {}).keys()) for s in invoke_agent_spans]}"
        )
        scope_attrs = dict(scope_span.attributes or {})
        print(f"Scope span attributes: {list(scope_attrs.keys())}")

        assert scope_attrs[GEN_AI_OPERATION_NAME_KEY] == INVOKE_AGENT_OPERATION_NAME
        assert scope_attrs[GEN_AI_AGENT_ID_KEY] == "test-agent-id"
        assert scope_attrs[GEN_AI_AGENT_NAME_KEY] == "TestAgent"
        print("✓ Scope span: gen_ai.agent.id and gen_ai.agent.name validated")

        # Validate instrumentor span has message attributes
        if instrumentor_span is not None:
            instr_attrs = dict(instrumentor_span.attributes or {})
            print(f"Instrumentor span attributes: {list(instr_attrs.keys())}")
            assert GEN_AI_INPUT_MESSAGES_KEY in instr_attrs, "Instrumentor span missing input messages"
            assert GEN_AI_OUTPUT_MESSAGES_KEY in instr_attrs, "Instrumentor span missing output messages"
            print("✓ Instrumentor span: gen_ai.input/output.messages validated")

        print("✓ All required invoke_agent span attributes validated")
        print(f"Agent response: {response}")

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

            if GEN_AI_AGENT_ID_KEY in attributes:
                assert attributes[GEN_AI_AGENT_ID_KEY] == agent365_config["agent_id"]

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

            if GEN_AI_AGENT_ID_KEY in attributes:
                assert attributes[GEN_AI_AGENT_ID_KEY] == agent365_config["agent_id"]

            # Check for LLM spans (generation spans)
            if (
                GEN_AI_PROVIDER_NAME_KEY in attributes
                and attributes[GEN_AI_PROVIDER_NAME_KEY] == "openai"
            ):
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
            if "execute_tool" in span.name.lower() or "calculator_tool" in span.name.lower():
                tool_spans_found += 1
                print(f"✓ Found tool execution span: {span.name}")

        # Ensure we found the expected span types
        assert len(distro_exporter.spans) > 0, "No spans were captured"
        print(f"✓ Captured {len(distro_exporter.spans)} spans total")
        print(
            f"✓ Found {llm_spans_found} LLM spans, {agent_spans_found} agent spans, and {tool_spans_found} tool spans"
        )
