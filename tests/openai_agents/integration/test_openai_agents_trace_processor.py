# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Integration tests for A365 OpenAI Agents trace processor with real OpenAI / Azure OpenAI."""

import logging
import os
import time

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import get_tracer_provider, set_tracer_provider

try:
    from agents import Agent, Runner, function_tool, set_default_openai_api, set_default_openai_client
    from openai import AsyncAzureOpenAI
except ImportError:
    pytest.skip(
        "openai-agents and openai packages required for integration tests",
        allow_module_level=True,
    )

from microsoft.opentelemetry._genai._openai_agents._trace_instrumentor import A365OpenAIAgentsInstrumentor

# A365 attribute keys used in assertions
from microsoft.opentelemetry.a365.core.constants import (
    CUSTOM_PARENT_SPAN_ID_KEY,
    EXECUTE_TOOL_OPERATION_NAME,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_PROVIDER_NAME_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    GEN_AI_TOOL_CALL_ID_KEY,
    INVOKE_AGENT_OPERATION_NAME,
)


@function_tool
def get_weather(city: str) -> str:
    """Return a mock weather forecast for a city."""
    return f"The weather in {city} is sunny, 25 °C."


@function_tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together and return the result."""
    return a + b


class _MockSpanProcessor:
    """Captures finished spans in-memory for assertions."""

    def __init__(self):
        self.captured_spans = []

    def on_start(self, span, parent_context=None):
        pass

    def _on_ending(self, span):
        pass

    def on_end(self, span):
        self.captured_spans.append(span)

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def _setup_provider_and_processor():
    """Create a TracerProvider with a MockSpanProcessor and install it."""
    processor = _MockSpanProcessor()
    current = get_tracer_provider()
    if isinstance(current, TracerProvider):
        current.add_span_processor(processor)
    else:
        tp = TracerProvider()
        tp.add_span_processor(processor)
        set_tracer_provider(tp)
    return processor


def _spans_by_name(spans):
    """Return dict of span name -> span for easy lookup."""
    return {s.name: s for s in spans}


def _spans_with_attr(spans, attr_key):
    """Return list of spans that have a given attribute."""
    return [s for s in spans if attr_key in dict(s.attributes or {})]


# ---------------------------------------------------------------------------
# Tests using OpenAI (api key based)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestOpenAIAgentsTraceProcessorOpenAI:
    """Integration tests using OpenAI API directly."""

    _processor: _MockSpanProcessor

    def setup_method(self):
        self._processor = _setup_provider_and_processor()

    def test_simple_agent_produces_spans(self, openai_config):
        """A simple agent run should produce at least agent + generation spans."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor.instrument()

        try:
            agent = Agent(
                name="Greeter",
                instructions="You are a concise assistant. Reply in one sentence.",
                model=openai_config["model"],
            )
            result = Runner.run_sync(agent, "Say hello.")
            time.sleep(1)

            assert result is not None
            assert len(result.final_output) > 0

            spans = self._processor.captured_spans
            assert len(spans) >= 2, f"Expected >=2 spans, got {len(spans)}"

            # Should have an agent (invoke_agent) span
            agent_spans = [
                s for s in spans if (s.attributes or {}).get(GEN_AI_OPERATION_NAME_KEY) == INVOKE_AGENT_OPERATION_NAME
            ]
            assert len(agent_spans) >= 1, "No invoke_agent span found"

            # All spans should have provider = openai
            for s in spans:
                attrs = dict(s.attributes or {})
                assert attrs.get(GEN_AI_PROVIDER_NAME_KEY) == "openai"

        finally:
            instrumentor.uninstrument()

    def test_agent_with_tool_call(self, openai_config):
        """An agent with a tool should produce function/execute_tool spans."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor.instrument()

        try:
            agent = Agent(
                name="Calculator",
                instructions="You are a calculator. Use the add_numbers tool to compute the answer. Be concise.",
                tools=[add_numbers],
                model=openai_config["model"],
            )
            result = Runner.run_sync(agent, "What is 15 + 27?")
            time.sleep(1)

            assert result is not None
            assert "42" in result.final_output

            spans = self._processor.captured_spans
            # Should have execute_tool spans
            tool_spans = [
                s for s in spans if (s.attributes or {}).get(GEN_AI_OPERATION_NAME_KEY) == EXECUTE_TOOL_OPERATION_NAME
            ]
            assert len(tool_spans) >= 1, "No execute_tool span found"

            # Tool span should have tool_call_id
            tool_attrs = dict(tool_spans[0].attributes or {})
            assert GEN_AI_TOOL_CALL_ID_KEY in tool_attrs, "Tool span missing tool_call_id"

            # Generation spans should have custom.parent.span.id
            gen_spans = _spans_with_attr(spans, CUSTOM_PARENT_SPAN_ID_KEY)
            assert len(gen_spans) >= 1, "No spans with custom.parent.span.id"

        finally:
            instrumentor.uninstrument()

    def test_agent_captures_messages(self, openai_config):
        """Agent span should have input/output messages from child generation spans."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor.instrument()

        try:
            agent = Agent(
                name="EchoBot",
                instructions="Repeat what the user says, word for word.",
                model=openai_config["model"],
            )
            result = Runner.run_sync(agent, "The quick brown fox")
            time.sleep(1)

            assert result is not None
            spans = self._processor.captured_spans

            # Agent span should have captured messages
            agent_spans = [
                s for s in spans if (s.attributes or {}).get(GEN_AI_OPERATION_NAME_KEY) == INVOKE_AGENT_OPERATION_NAME
            ]
            assert len(agent_spans) >= 1

            agent_attrs = dict(agent_spans[0].attributes or {})
            # Input and output messages should be present on the agent span
            assert GEN_AI_INPUT_MESSAGES_KEY in agent_attrs, "Agent span missing input messages"
            assert GEN_AI_OUTPUT_MESSAGES_KEY in agent_attrs, "Agent span missing output messages"

        finally:
            instrumentor.uninstrument()

    def test_generation_span_has_model(self, openai_config):
        """Generation (chat) spans should have gen_ai.request.model."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor.instrument()

        try:
            agent = Agent(
                name="ModelCheck",
                instructions="Reply with one word: OK",
                model=openai_config["model"],
            )
            Runner.run_sync(agent, "Ping")
            time.sleep(1)

            spans = self._processor.captured_spans
            gen_spans = _spans_with_attr(spans, GEN_AI_REQUEST_MODEL_KEY)
            assert len(gen_spans) >= 1, "No generation span with model attribute"

            model_val = dict(gen_spans[0].attributes or {})[GEN_AI_REQUEST_MODEL_KEY]
            assert isinstance(model_val, str)
            assert len(model_val) > 0

        finally:
            instrumentor.uninstrument()


# ---------------------------------------------------------------------------
# Tests using Azure OpenAI
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestOpenAIAgentsTraceProcessorAzure:
    """Integration tests using Azure OpenAI."""

    _processor: _MockSpanProcessor

    def setup_method(self):
        self._processor = _setup_provider_and_processor()

    def test_azure_agent_produces_spans(self, azure_openai_config):
        """An agent using Azure OpenAI should produce A365-format spans."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor.instrument()

        try:
            azure_client = AsyncAzureOpenAI(
                azure_endpoint=azure_openai_config["endpoint"],
                api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                api_version=azure_openai_config["api_version"],
            )
            set_default_openai_client(azure_client, use_for_tracing=False)
            set_default_openai_api("chat_completions")

            agent = Agent(
                name="AzureBot",
                instructions="You are a concise assistant. Reply in one sentence.",
                model=azure_openai_config["deployment"],
            )
            result = Runner.run_sync(agent, "What is Python?")
            time.sleep(1)

            assert result is not None
            assert len(result.final_output) > 0

            spans = self._processor.captured_spans
            assert len(spans) >= 2

            agent_spans = [
                s for s in spans if (s.attributes or {}).get(GEN_AI_OPERATION_NAME_KEY) == INVOKE_AGENT_OPERATION_NAME
            ]
            assert len(agent_spans) >= 1

        finally:
            instrumentor.uninstrument()

    def test_azure_agent_with_tool(self, azure_openai_config):
        """An Azure agent with tools should produce tool spans with A365 attributes."""
        instrumentor = A365OpenAIAgentsInstrumentor()
        instrumentor.instrument()

        try:
            azure_client = AsyncAzureOpenAI(
                azure_endpoint=azure_openai_config["endpoint"],
                api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                api_version=azure_openai_config["api_version"],
            )
            set_default_openai_client(azure_client, use_for_tracing=False)
            set_default_openai_api("chat_completions")

            agent = Agent(
                name="AzureCalc",
                instructions="Use the add_numbers tool to answer math questions. Be concise.",
                tools=[add_numbers],
                model=azure_openai_config["deployment"],
            )
            result = Runner.run_sync(agent, "What is 100 + 200?")
            time.sleep(1)

            assert result is not None
            assert "300" in result.final_output

            spans = self._processor.captured_spans
            tool_spans = [
                s for s in spans if (s.attributes or {}).get(GEN_AI_OPERATION_NAME_KEY) == EXECUTE_TOOL_OPERATION_NAME
            ]
            assert len(tool_spans) >= 1

        finally:
            instrumentor.uninstrument()


# ---------------------------------------------------------------------------
# Manual runner
# ---------------------------------------------------------------------------


def _run_manual_tests():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("=== Starting OpenAI Agents A365 Integration Tests ===")

    processor = _setup_provider_and_processor()

    instrumentor = A365OpenAIAgentsInstrumentor()
    instrumentor.instrument()

    try:
        logger.info("--- test: simple agent ---")
        agent = Agent(
            name="Greeter",
            instructions="You are a concise assistant. Reply in one sentence.",
        )
        result = Runner.run_sync(agent, "Say hello.")
        time.sleep(1)

        logger.info("  Result: %s", result.final_output[:100] if result else "None")
        logger.info("  Captured spans: %d", len(processor.captured_spans))
        for s in processor.captured_spans:
            attrs = dict(s.attributes or {})
            logger.info("    [%s] %s", attrs.get(GEN_AI_OPERATION_NAME_KEY, "?"), s.name)

        processor.captured_spans.clear()

        logger.info("--- test: agent with tool ---")
        calc_agent = Agent(
            name="Calculator",
            instructions="Use add_numbers to compute. Be concise.",
            tools=[add_numbers],
        )
        result = Runner.run_sync(calc_agent, "What is 7 + 8?")
        time.sleep(1)

        logger.info("  Result: %s", result.final_output[:100] if result else "None")
        logger.info("  Captured spans: %d", len(processor.captured_spans))
        for s in processor.captured_spans:
            attrs = dict(s.attributes or {})
            logger.info(
                "    [%s] %s  tool_call_id=%s",
                attrs.get(GEN_AI_OPERATION_NAME_KEY, "?"),
                s.name,
                attrs.get(GEN_AI_TOOL_CALL_ID_KEY, "n/a"),
            )

    finally:
        instrumentor.uninstrument()

    logger.info("=== Done ===")


if __name__ == "__main__":
    _run_manual_tests()
