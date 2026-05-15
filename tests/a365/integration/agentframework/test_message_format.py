# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Integration tests for AgentFramework message format mapping.

These tests use the real A365 observability pipeline provided by the
distro_exporter session fixture (conftest.py).  The distro auto-instruments
AgentFramework, so spans are captured after enrichment — matching the real
export path: auto-instrumentation → enricher → mapper → serialize → export.
"""

import json
import time
from typing import Any

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import get_tracer_provider

# AgentFramework SDK
try:
    from agent_framework._agents import RawAgent
    from agent_framework._tools import tool
    from agent_framework.openai import OpenAIChatClient
except ImportError:
    pytest.skip(
        "AgentFramework library and dependencies required for integration tests",
        allow_module_level=True,
    )

from microsoft.opentelemetry.a365.core.constants import (
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
)


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name to get weather for.

    Returns:
        A string describing the weather.
    """
    return f"The weather in {city} is sunny, 22°C."


@pytest.mark.integration
class TestAgentFrameworkMessageFormat:
    """Capture real AgentFramework span attributes after enrichment
    and verify the A365 versioned message format."""

    @pytest.fixture
    def chat_client(self, azure_openai_config: dict[str, Any]) -> OpenAIChatClient:
        """Create a real Azure OpenAI chat client."""
        return OpenAIChatClient(
            model=azure_openai_config["deployment"],
            azure_endpoint=azure_openai_config["endpoint"],
            api_key=azure_openai_config["api_key"],
        )

    def _find_chat_spans(self, distro_exporter) -> list[ReadableSpan]:
        """Find exported spans that have gen_ai.input.messages.

        Forces a flush so batched spans are exported before inspection.
        """
        get_tracer_provider().force_flush()
        time.sleep(0.5)
        return [
            s
            for s in distro_exporter.spans
            if s.attributes and GEN_AI_INPUT_MESSAGES_KEY in s.attributes
        ]

    @pytest.mark.asyncio
    async def test_simple_chat_message_mapping(
        self, distro_exporter, chat_client: OpenAIChatClient
    ) -> None:
        """Simple chat: verify exported spans contain versioned A365 messages
        after enrichment (no manual mapper call)."""
        agent = RawAgent(
            client=chat_client,
            instructions="You are a helpful assistant. Reply in one sentence.",
            tools=[],
        )

        result = await agent.run("What is the capital of France?")
        assert result is not None
        assert len(result.text) > 0

        chat_spans = self._find_chat_spans(distro_exporter)
        assert len(chat_spans) > 0, (
            f"No chat spans found. All spans: {[s.name for s in distro_exporter.spans]}"
        )

        attrs = dict(chat_spans[-1].attributes or {})

        # --- Input messages: enriched to versioned format ---
        input_data = json.loads(attrs[GEN_AI_INPUT_MESSAGES_KEY])
        # Enricher should have produced versioned wrapper for chat spans
        if isinstance(input_data, dict):
            assert input_data["version"] == "0.1.0"
            messages = input_data["messages"]
        else:
            messages = input_data

        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles
        for msg in messages:
            for part in msg["parts"]:
                assert "type" in part

        # --- Output messages: enriched to versioned format ---
        output_data = json.loads(attrs[GEN_AI_OUTPUT_MESSAGES_KEY])
        if isinstance(output_data, dict):
            assert output_data["version"] == "0.1.0"
            out_messages = output_data["messages"]
        else:
            out_messages = output_data

        assert out_messages[0]["role"] == "assistant"
        assert any(p["type"] == "text" for p in out_messages[0]["parts"])

        print(f"\n=== Enriched input ===\n{json.dumps(input_data, indent=2)}")
        print(f"\n=== Enriched output ===\n{json.dumps(output_data, indent=2)}")

    @pytest.mark.asyncio
    async def test_tool_call_message_mapping(
        self, distro_exporter, chat_client: OpenAIChatClient
    ) -> None:
        """Tool-calling chat: verify tool_call and tool_call_response parts
        survive enrichment in exported spans."""
        agent = RawAgent(
            client=chat_client,
            instructions="You are a weather assistant. Always use the get_weather function.",
            tools=[get_weather],
        )

        result = await agent.run("What's the weather in Seattle?")
        assert result is not None
        assert len(result.text) > 0

        chat_spans = self._find_chat_spans(distro_exporter)
        assert len(chat_spans) > 0

        print(f"\n=== All exported spans ({len(distro_exporter.spans)}) ===")
        for s in distro_exporter.spans:
            op = (s.attributes or {}).get(GEN_AI_OPERATION_NAME_KEY, "(none)")
            print(f"  {s.name} | op={op}")

        # Collect part types from exported (enriched) spans
        part_types: set[str] = set()
        for span in chat_spans:
            attrs = dict(span.attributes or {})
            for key in (GEN_AI_INPUT_MESSAGES_KEY, GEN_AI_OUTPUT_MESSAGES_KEY):
                raw = attrs.get(key)
                if not raw:
                    continue
                data = json.loads(raw)
                messages = data["messages"] if isinstance(data, dict) else data
                for msg in messages:
                    for part in msg.get("parts", []):
                        part_types.add(part.get("type", ""))

        assert "tool_call" in part_types, f"Expected tool_call in exported parts: {part_types}"
        assert "tool_call_response" in part_types, (
            f"Expected tool_call_response in exported parts: {part_types}"
        )
        print(f"\n  Exported part types: {part_types}")
