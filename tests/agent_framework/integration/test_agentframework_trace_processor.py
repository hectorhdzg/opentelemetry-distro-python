# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Integration tests for Agent Framework trace processor with real Azure OpenAI."""

import logging
import os
import time

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import get_tracer_provider, set_tracer_provider

try:
    from agent_framework import RawAgent, tool
    from agent_framework.openai import OpenAIChatClient
    from agent_framework.observability import enable_instrumentation
    from azure.identity import AzureCliCredential
except ImportError:
    pytest.skip(
        "agent_framework library and dependencies required for integration tests",
        allow_module_level=True,
    )

from microsoft.opentelemetry._agent_framework._trace_instrumentor import AgentFrameworkInstrumentor

_azure_openai_config = {
    "endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
}
_agent365_config = {
    "tenant_id": os.environ.get("AGENT365_TEST_TENANT_ID", ""),
    "agent_id": os.environ.get("AGENT365_TEST_AGENT_ID", ""),
}


@tool
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


class _MockSpanProcessor:
    """Mock span processor that captures spans instead of sending them."""

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


@pytest.mark.integration
class TestAgentFrameworkTraceProcessorIntegration:
    """Integration tests for AgentFramework trace processor with real Azure OpenAI."""

    _mock_processor: _MockSpanProcessor

    def setup_method(self):
        self._mock_processor = _MockSpanProcessor()

    def test_agentframework_trace_processor_integration(self, azure_openai_config, agent365_config):
        """Test AgentFramework trace processor with real Azure OpenAI call."""

        current = get_tracer_provider()
        if isinstance(current, TracerProvider):
            current.add_span_processor(self._mock_processor)
        else:
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(self._mock_processor)
            set_tracer_provider(tracer_provider)

        enable_instrumentation()
        instrumentor = AgentFrameworkInstrumentor()
        instrumentor.instrument()

        try:
            chat_client = OpenAIChatClient(
                azure_endpoint=azure_openai_config["endpoint"],
                credential=AzureCliCredential(),
                model=azure_openai_config["deployment"],
            )
            agent = RawAgent(
                client=chat_client,
                instructions="You are a helpful assistant.",
                tools=[],
            )

            import asyncio

            async def run_agent():
                return await agent.run("What can you do with agent framework?")

            response = asyncio.run(run_agent())
            time.sleep(1)

            assert len(self._mock_processor.captured_spans) > 0
            assert response is not None
            assert len(response.text) > 0

        finally:
            instrumentor.uninstrument()

    def test_agentframework_trace_processor_with_tool_calls(self, azure_openai_config, agent365_config):
        """Test AgentFramework trace processor with tool calls."""
        current = get_tracer_provider()
        if isinstance(current, TracerProvider):
            current.add_span_processor(self._mock_processor)
        else:
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(self._mock_processor)
            set_tracer_provider(tracer_provider)

        enable_instrumentation()
        instrumentor = AgentFrameworkInstrumentor()
        instrumentor.instrument()

        try:
            chat_client = OpenAIChatClient(
                azure_endpoint=azure_openai_config["endpoint"],
                credential=AzureCliCredential(),
                model=azure_openai_config["deployment"],
            )
            agent = RawAgent(
                client=chat_client,
                instructions="You are a helpful agent framework assistant.",
                tools=[add_numbers],
            )

            import asyncio

            async def run_agent_with_tool():
                return await agent.run("What is 15 + 27?")

            response = asyncio.run(run_agent_with_tool())
            time.sleep(1)

            assert len(self._mock_processor.captured_spans) > 0
            assert response is not None
            assert len(response.text) > 0
            assert "42" in response.text

        finally:
            instrumentor.uninstrument()


def _run_manual_tests():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("=== Starting Agent Framework Integration Test ===")

    logger.info("Azure OpenAI endpoint: %s", _azure_openai_config["endpoint"])
    logger.info("Azure OpenAI deployment: %s", _azure_openai_config["deployment"])
    logger.info("Agent365 tenant: %s", _agent365_config["tenant_id"])
    logger.info("Agent365 agent: %s", _agent365_config["agent_id"])

    shared_processor = _MockSpanProcessor()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(shared_processor)
    set_tracer_provider(tracer_provider)

    test_instance = TestAgentFrameworkTraceProcessorIntegration()
    test_instance._mock_processor = shared_processor

    logger.info("--- Running test: trace processor integration ---")
    try:
        test_instance.test_agentframework_trace_processor_integration(_azure_openai_config, _agent365_config)
        logger.info("PASSED: trace processor integration")
        logger.info("  Captured spans: %d", len(shared_processor.captured_spans))
    except (AssertionError, RuntimeError, OSError) as e:
        logger.error("FAILED: trace processor integration - %s", e, exc_info=True)

    # Clear captured spans for second test, reuse same provider/processor
    shared_processor.captured_spans.clear()

    logger.info("--- Running test: trace processor with tool calls ---")
    try:
        test_instance.test_agentframework_trace_processor_with_tool_calls(_azure_openai_config, _agent365_config)
        logger.info("PASSED: trace processor with tool calls")
        logger.info("  Captured spans: %d", len(shared_processor.captured_spans))
    except (AssertionError, RuntimeError, OSError) as e:
        logger.error("FAILED: trace processor with tool calls - %s", e, exc_info=True)

    logger.info("=== Done ===")


if __name__ == "__main__":
    _run_manual_tests()
