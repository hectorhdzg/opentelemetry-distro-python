# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Integration tests for OpenAI message format mapping.

These tests use the real A365 observability pipeline via the shared
distro_exporter fixture from conftest. The message mapping is applied
directly in trace_processor before spans are ended, converting raw OpenAI
messages to the A365 versioned format (v0.1.0) with typed parts.
"""

import json
import time
from typing import Any

import pytest
from opentelemetry.sdk.trace import ReadableSpan

try:
    from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool
    from openai import AsyncAzureOpenAI
except ImportError:
    pytest.skip(
        "OpenAI agents library and dependencies required for integration tests",
        allow_module_level=True,
    )

from opentelemetry.trace import get_tracer_provider

from microsoft.opentelemetry.a365.core.constants import (
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
)


@function_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: The city name to get weather for.

    Returns:
        A string describing the weather.
    """
    return f"The weather in {city} is sunny, 22°C."


def _span_to_json(span: ReadableSpan) -> dict[str, object]:
    """Convert a ReadableSpan (or EnrichedReadableSpan) to a JSON-serializable dict."""
    try:
        ctx = span.get_span_context()
        context_dict: dict[str, object] = {
            "trace_id": f"0x{ctx.trace_id:032x}",
            "span_id": f"0x{ctx.span_id:016x}",
        }
    except (AttributeError, TypeError):
        context_dict = {"note": "context not available on enriched span"}

    try:
        parent = span.parent
        parent_id = f"0x{parent.span_id:016x}" if parent else None
    except (AttributeError, TypeError):
        parent_id = None

    events_list: list[dict[str, object]] = []
    for e in getattr(span, "events", None) or []:
        events_list.append({
            "name": e.name,
            "attributes": dict(e.attributes) if e.attributes else {},
        })

    links_list: list[dict[str, object]] = []
    for lnk in getattr(span, "links", None) or []:
        links_list.append({
            "attributes": dict(lnk.attributes) if lnk.attributes else {},
        })

    result: dict[str, object] = {
        "name": span.name,
        "context": context_dict,
        "kind": str(getattr(span, "kind", None)),
        "parent_id": parent_id,
        "status": str(getattr(span, "status", None)),
        "attributes": dict(span.attributes) if span.attributes else {},
        "events": events_list,
        "links": links_list,
    }

    resource = getattr(span, "resource", None)
    if resource:
        result["resource"] = dict(resource.attributes) if resource.attributes else {}

    scope = getattr(span, "instrumentation_scope", None)
    if scope:
        result["instrumentation_scope"] = {"name": scope.name, "version": scope.version}

    return result


@pytest.mark.integration
class TestOpenAIMessageFormat:
    """Capture real OpenAI Agents SDK span attributes after enrichment
    and verify the A365 versioned message format."""

    @pytest.fixture
    def openai_client(self, azure_openai_config: dict[str, Any]) -> AsyncAzureOpenAI:
        """Create a real Azure OpenAI client."""
        return AsyncAzureOpenAI(
            api_key=azure_openai_config["api_key"],
            api_version=azure_openai_config["api_version"],
            azure_endpoint=azure_openai_config["endpoint"],
        )

    def _find_message_spans(self, distro_exporter) -> list[ReadableSpan]:
        """Find exported spans that have gen_ai.input.messages."""
        get_tracer_provider().force_flush()
        time.sleep(0.5)
        return [
            s
            for s in distro_exporter.spans
            if s.attributes and GEN_AI_INPUT_MESSAGES_KEY in s.attributes
        ]

    @pytest.mark.asyncio
    async def test_simple_chat_message_mapping(
        self,
        distro_exporter,
        openai_client: AsyncAzureOpenAI,
        azure_openai_config: dict[str, Any],
    ) -> None:
        """Simple chat: verify exported spans contain versioned A365 messages."""
        agent = Agent(
            name="TestAgent",
            instructions="You are a helpful assistant. Reply in one sentence.",
            model=OpenAIChatCompletionsModel(
                model=azure_openai_config["deployment"],
                openai_client=openai_client,
            ),
        )

        result = await Runner.run(agent, "What is the capital of France?")
        assert result is not None
        assert len(result.final_output) > 0

        # Print ALL spans as full JSON
        get_tracer_provider().force_flush()
        time.sleep(0.5)
        print(f"\n=== All exported spans ({len(distro_exporter.spans)}) ===")
        for i, s in enumerate(distro_exporter.spans):
            span_json = _span_to_json(s)
            print(f"\n--- SPAN {i} ---")
            print(json.dumps(span_json, indent=2, default=str))

        message_spans = self._find_message_spans(distro_exporter)
        assert len(message_spans) > 0, (
            f"No message spans found. All spans: {[s.name for s in distro_exporter.spans]}"
        )

        # Verify at least one span has versioned A365 format
        found_versioned = False
        for span in message_spans:
            attrs = dict(span.attributes or {})
            raw_input = attrs.get(GEN_AI_INPUT_MESSAGES_KEY)
            if raw_input:
                input_data = json.loads(raw_input)
                if isinstance(input_data, dict) and input_data.get("version") == "0.1.0":
                    found_versioned = True
                    messages = input_data["messages"]
                    roles = [m["role"] for m in messages]
                    assert "user" in roles
                    for msg in messages:
                        for part in msg["parts"]:
                            assert "type" in part

            raw_output = attrs.get(GEN_AI_OUTPUT_MESSAGES_KEY)
            if raw_output:
                output_data = json.loads(raw_output)
                if isinstance(output_data, dict) and output_data.get("version") == "0.1.0":
                    out_messages = output_data["messages"]
                    assert out_messages[0]["role"] == "assistant"
                    assert any(p["type"] == "text" for p in out_messages[0]["parts"])

        assert found_versioned, "Expected at least one span with versioned A365 message format"

    @pytest.mark.asyncio
    async def test_tool_call_message_mapping(
        self,
        distro_exporter,
        openai_client: AsyncAzureOpenAI,
        azure_openai_config: dict[str, Any],
    ) -> None:
        """Tool-calling chat: verify tool_call and tool_call_response parts."""
        agent = Agent(
            name="WeatherAgent",
            instructions="You are a weather assistant. Always use the get_weather function.",
            model=OpenAIChatCompletionsModel(
                model=azure_openai_config["deployment"],
                openai_client=openai_client,
            ),
            tools=[get_weather],
        )

        result = await Runner.run(agent, "What's the weather in Seattle?")
        assert result is not None
        assert len(result.final_output) > 0

        # Print ALL spans as full JSON
        get_tracer_provider().force_flush()
        time.sleep(0.5)
        print(f"\n=== All exported spans ({len(distro_exporter.spans)}) ===")
        for i, s in enumerate(distro_exporter.spans):
            span_json = _span_to_json(s)
            print(f"\n--- SPAN {i} ---")
            print(json.dumps(span_json, indent=2, default=str))

        message_spans = self._find_message_spans(distro_exporter)
        assert len(message_spans) > 0

        # Collect part types from exported (enriched) spans
        part_types: set[str] = set()
        for span in message_spans:
            attrs = dict(span.attributes or {})
            for key in (GEN_AI_INPUT_MESSAGES_KEY, GEN_AI_OUTPUT_MESSAGES_KEY):
                raw = attrs.get(key)
                if not raw:
                    continue
                data = json.loads(raw)
                if isinstance(data, dict) and "messages" in data:
                    messages = data["messages"]
                    for msg in messages:
                        for part in msg.get("parts", []):
                            part_types.add(part.get("type", ""))

        print(f"\n  Exported part types: {part_types}")
        assert "text" in part_types, f"Expected text in exported parts: {part_types}"
