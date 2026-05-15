# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""End-to-end pipeline integration tests for AgentFramework observability.

These tests verify the full A365 observability pipeline:
  InvokeAgentScope → InferenceScope (auto-instrumented) → ExecuteToolScope (auto-instrumented)

All three scope types must appear in a single trace with correct parent-child
relationships and A365 message format attributes.

Uses the ``distro_exporter`` session fixture from conftest.py which configures
the distro and captures spans after enrichment.
"""

import json
import time

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.trace import get_tracer_provider

try:
    from agent_framework._agents import RawAgent
    from agent_framework._tools import tool as ai_function
    from agent_framework.openai import OpenAIChatClient
except ImportError:
    pytest.skip(
        "AgentFramework library and dependencies required for integration tests",
        allow_module_level=True,
    )

from microsoft.opentelemetry.a365.core.agent_details import AgentDetails
from microsoft.opentelemetry.a365.core.constants import (
    EXECUTE_TOOL_OPERATION_NAME,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    GEN_AI_TOOL_NAME_KEY,
    INVOKE_AGENT_OPERATION_NAME,
    TENANT_ID_KEY,
)
from microsoft.opentelemetry.a365.core.invoke_agent_details import InvokeAgentScopeDetails
from microsoft.opentelemetry.a365.core.invoke_agent_scope import InvokeAgentScope
from microsoft.opentelemetry.a365.core.request import Request


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


def _get_span_attr(span: ReadableSpan, key: str) -> str | None:
    """Safely get an attribute from a span."""
    attrs = span.attributes or {}
    val = attrs.get(key)
    return str(val) if val is not None else None


def _find_spans_by_operation(spans: list[ReadableSpan], operation_name: str) -> list[ReadableSpan]:
    """Find spans matching a given gen_ai.operation.name."""
    return [s for s in spans if _get_span_attr(s, GEN_AI_OPERATION_NAME_KEY) == operation_name]


def _find_spans_by_name_prefix(spans: list[ReadableSpan], prefix: str) -> list[ReadableSpan]:
    """Find spans whose name starts with a given prefix."""
    return [s for s in spans if s.name.startswith(prefix)]


@pytest.mark.integration
class TestAgentFrameworkObservabilityPipeline:
    """End-to-end pipeline tests: InvokeAgent → Inference → ToolExecution.

    Verifies that wrapping an AgentFramework call inside InvokeAgentScope
    produces a single trace with correct parent-child span hierarchy,
    operation names, and A365 message format attributes.
    """

    @pytest.fixture
    def chat_client(self, azure_openai_config: dict) -> OpenAIChatClient:
        """Create a real Azure OpenAI chat client."""
        return OpenAIChatClient(
            model=azure_openai_config["deployment"],
            azure_endpoint=azure_openai_config["endpoint"],
            api_key=azure_openai_config["api_key"],
        )

    @pytest.fixture
    def agent_details(self, agent365_config: dict) -> AgentDetails:
        """Create AgentDetails for the test agent."""
        return AgentDetails(
            agent_id=agent365_config["agent_id"],
            agent_name="pipeline-test-agent",
            agent_description="Integration test agent for pipeline verification",
            tenant_id=agent365_config["tenant_id"],
        )

    def _flush_and_collect(self, distro_exporter) -> list[ReadableSpan]:
        """Force flush and return all captured spans."""
        get_tracer_provider().force_flush()
        time.sleep(0.5)
        return list(distro_exporter.spans)

    # ------------------------------------------------------------------
    # Test: Full pipeline with tool call
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_invoke_agent_with_tool_call(  # pylint: disable=too-many-statements
        self,
        distro_exporter,
        chat_client: OpenAIChatClient,
        agent_details: AgentDetails,
        agent365_config: dict,
    ) -> None:
        """Full pipeline: InvokeAgentScope wraps AgentFramework with tool.

        Verifies:
        1. All spans share the same trace_id
        2. invoke_agent span is the root (no parent)
        3. Inference (chat) spans are descendants of invoke_agent
        4. Tool execution spans are descendants of invoke_agent
        5. A365 message format on chat spans (versioned JSON)
        6. Correct operation names and key attributes
        """
        request = Request(content="What is 15 + 27?", session_id="test-session-pipeline")

        agent = RawAgent(
            client=chat_client,
            instructions=(
                "You are a math assistant. You MUST use the add_numbers function "
                "for any arithmetic. Never compute in your head."
            ),
            tools=[add_numbers],
        )

        with InvokeAgentScope.start(
            request=request,
            scope_details=InvokeAgentScopeDetails(),
            agent_details=agent_details,
        ):
            result = await agent.run("What is 15 + 27?")

        assert result is not None
        assert len(result.text) > 0
        assert "42" in result.text, f"Expected '42' in response: {result.text}"

        spans = self._flush_and_collect(distro_exporter)
        assert len(spans) > 0, "No spans were captured"

        # --- Print span tree for debugging ---
        print(f"\n=== Captured {len(spans)} spans ===")
        for s in spans:
            op = _get_span_attr(s, GEN_AI_OPERATION_NAME_KEY) or "(none)"
            parent_id = f"{s.parent.span_id:016x}" if s.parent else "None"
            print(
                f"  {s.name} | op={op} | trace={s.context.trace_id:032x} "
                f"| span={s.context.span_id:016x} | parent={parent_id}"
            )

        # --- 1. All spans share the same trace_id ---
        invoke_spans = _find_spans_by_name_prefix(spans, "invoke_agent")
        assert len(invoke_spans) >= 1, (
            f"Expected at least 1 invoke_agent span, got: {[s.name for s in spans]}"
        )
        invoke_span = invoke_spans[0]
        trace_id = invoke_span.context.trace_id

        for s in spans:
            assert s.context.trace_id == trace_id, (
                f"Span '{s.name}' has different trace_id: "
                f"{s.context.trace_id:032x} vs {trace_id:032x}"
            )

        # --- 2. invoke_agent span is the root (no parent) ---
        assert invoke_span.parent is None, (
            f"invoke_agent span should be root but has parent: {invoke_span.parent.span_id:016x}"
        )

        # --- 3. invoke_agent has correct operation name ---
        assert _get_span_attr(invoke_span, GEN_AI_OPERATION_NAME_KEY) == INVOKE_AGENT_OPERATION_NAME

        # --- 4. Tenant ID is set ---
        assert _get_span_attr(invoke_span, TENANT_ID_KEY) == agent365_config["tenant_id"]

        # --- 5. Chat (inference) spans are descendants of invoke_agent ---
        chat_spans = [
            s
            for s in spans
            if _get_span_attr(s, GEN_AI_OPERATION_NAME_KEY) == "chat"
            or (s.name.startswith("chat") and _get_span_attr(s, GEN_AI_REQUEST_MODEL_KEY))
        ]
        assert len(chat_spans) >= 1, (
            f"Expected at least 1 chat span, got: {[s.name for s in spans]}"
        )

        invoke_span_id = invoke_span.context.span_id
        for chat_span in chat_spans:
            assert chat_span.parent is not None, (
                f"Chat span '{chat_span.name}' should have a parent"
            )
            # Chat span should be a child of invoke_agent (directly or transitively)
            self._assert_ancestor(
                chat_span,
                invoke_span_id,
                spans,
                f"Chat span '{chat_span.name}' is not a descendant of invoke_agent",
            )

        # --- 6. Tool execution spans are descendants of invoke_agent ---
        tool_spans = _find_spans_by_name_prefix(spans, "execute_tool")
        if not tool_spans:
            # Also check by operation name
            tool_spans = _find_spans_by_operation(spans, EXECUTE_TOOL_OPERATION_NAME)

        assert len(tool_spans) >= 1, (
            f"Expected at least 1 execute_tool span. All spans: {[s.name for s in spans]}"
        )
        for tool_span in tool_spans:
            assert tool_span.parent is not None, (
                f"Tool span '{tool_span.name}' should have a parent"
            )
            self._assert_ancestor(
                tool_span,
                invoke_span_id,
                spans,
                f"Tool span '{tool_span.name}' is not a descendant of invoke_agent",
            )

        # --- 7. A365 message format on chat spans ---
        for chat_span in chat_spans:
            attrs = dict(chat_span.attributes or {})
            if GEN_AI_INPUT_MESSAGES_KEY in attrs:
                input_data = json.loads(attrs[GEN_AI_INPUT_MESSAGES_KEY])
                if isinstance(input_data, dict) and "version" in input_data:
                    assert input_data["version"] == "0.1.0"
                    for msg in input_data["messages"]:
                        assert "role" in msg
                        assert "parts" in msg

            if GEN_AI_OUTPUT_MESSAGES_KEY in attrs:
                output_data = json.loads(str(attrs[GEN_AI_OUTPUT_MESSAGES_KEY]))
                if isinstance(output_data, dict) and "version" in output_data:
                    assert output_data["version"] == "0.1.0"
                    for msg in output_data["messages"]:
                        assert "role" in msg
                        assert "parts" in msg

        # --- 8. Tool spans have tool-specific attributes ---
        for tool_span in tool_spans:
            attrs = dict(tool_span.attributes or {})
            op = str(attrs.get(GEN_AI_OPERATION_NAME_KEY, ""))
            if op == EXECUTE_TOOL_OPERATION_NAME or tool_span.name.startswith("execute_tool"):
                assert GEN_AI_TOOL_NAME_KEY in attrs or "add_numbers" in tool_span.name, (
                    f"Tool span missing tool name attribute: {list(attrs.keys())}"
                )

        print("\n✓ All pipeline assertions passed")

    # ------------------------------------------------------------------
    # Test: Pipeline without tools (simple inference only)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_invoke_agent_simple_inference(
        self,
        distro_exporter,
        chat_client: OpenAIChatClient,
        agent_details: AgentDetails,
        agent365_config: dict,
    ) -> None:
        """Pipeline with InvokeAgentScope + simple inference (no tools).

        Verifies invoke_agent → chat span hierarchy without tool calls.
        """
        request = Request(content="Say hello", session_id="test-session-simple")

        agent = RawAgent(
            client=chat_client,
            instructions="You are a helpful assistant. Reply in one sentence.",
            tools=[],
        )

        with InvokeAgentScope.start(
            request=request,
            scope_details=InvokeAgentScopeDetails(),
            agent_details=agent_details,
        ):
            result = await agent.run("Say hello in exactly 5 words.")

        assert result is not None
        assert len(result.text) > 0

        spans = self._flush_and_collect(distro_exporter)
        assert len(spans) > 0, "No spans were captured"

        # All spans share the same trace_id
        invoke_spans = _find_spans_by_name_prefix(spans, "invoke_agent")
        assert len(invoke_spans) >= 1
        invoke_span = invoke_spans[0]
        trace_id = invoke_span.context.trace_id

        for s in spans:
            assert s.context.trace_id == trace_id

        # invoke_agent is root
        assert invoke_span.parent is None

        # Chat spans are descendants
        chat_spans = [
            s
            for s in spans
            if _get_span_attr(s, GEN_AI_OPERATION_NAME_KEY) == "chat"
            or (s.name.startswith("chat") and _get_span_attr(s, GEN_AI_REQUEST_MODEL_KEY))
        ]
        assert len(chat_spans) >= 1

        invoke_span_id = invoke_span.context.span_id
        for chat_span in chat_spans:
            self._assert_ancestor(
                chat_span,
                invoke_span_id,
                spans,
                f"Chat span '{chat_span.name}' not a descendant of invoke_agent",
            )

        print(f"\n✓ Simple pipeline: {len(spans)} spans, hierarchy verified")

    # ------------------------------------------------------------------
    # Helper: assert ancestor relationship
    # ------------------------------------------------------------------

    def _assert_ancestor(
        self,
        span: ReadableSpan,
        ancestor_span_id: int,
        all_spans: list[ReadableSpan],
        message: str,
    ) -> None:
        """Walk up the parent chain and assert that ancestor_span_id is found."""
        span_map = {s.context.span_id: s for s in all_spans}
        current = span
        visited: set[int] = set()
        while current.parent is not None:
            parent_id = current.parent.span_id
            if parent_id == ancestor_span_id:
                return
            if parent_id in visited:
                break
            visited.add(parent_id)
            next_span = span_map.get(parent_id)
            if next_span is None:
                break
            current = next_span
        raise AssertionError(message)
