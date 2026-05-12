# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the OpenAI Agents A365 trace processor."""

from collections import OrderedDict
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("agents")

from agents.tracing.span_data import (  # noqa: E402  # pylint: disable=wrong-import-position
    AgentSpanData,
    FunctionSpanData,
    HandoffSpanData,
)

from microsoft.opentelemetry._genai._openai_agents._trace_processor import (  # noqa: E402  # pylint: disable=wrong-import-position
    OpenAIAgentsTraceProcessor,
)
from microsoft.opentelemetry.a365.core.constants import (  # noqa: E402  # pylint: disable=wrong-import-position
    CUSTOM_PARENT_SPAN_ID_KEY,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_PROVIDER_NAME_KEY,
    GEN_AI_TOOL_CALL_ID_KEY,
    GEN_AI_TOOL_TYPE_KEY,
    INVOKE_AGENT_OPERATION_NAME,
)
from microsoft.opentelemetry._genai._openai_agents._constants import (  # noqa: E402  # pylint: disable=wrong-import-position
    GEN_AI_GRAPH_NODE_PARENT_ID,
)

_NOW = "2024-06-01T12:00:00+00:00"
_NOW_END = "2024-06-01T12:00:01+00:00"


def _make_span(
    span_data,
    span_id="span-1",
    parent_id=None,
    trace_id="trace-1",
    started_at=_NOW,
    ended_at=_NOW_END,
    error=None,
):
    span = MagicMock()
    span.span_id = span_id
    span.parent_id = parent_id
    span.trace_id = trace_id
    span.started_at = started_at
    span.ended_at = ended_at
    span.span_data = span_data
    span.error = error
    return span


def _make_trace(trace_id="trace-1"):
    trace = MagicMock()
    trace.trace_id = trace_id
    return trace


def _make_otel_span():
    otel_span = MagicMock()
    otel_span.attributes = {}

    def set_attribute(k, v):
        otel_span.attributes[k] = v

    otel_span.set_attribute = set_attribute
    ctx = MagicMock()
    ctx.span_id = 12345
    otel_span.get_span_context.return_value = ctx
    return otel_span


class TestOpenAIAgentsTraceProcessor(TestCase):
    """Unit tests for OpenAIAgentsTraceProcessor."""

    def setUp(self):
        self.mock_tracer = MagicMock()
        self.mock_otel_span = _make_otel_span()
        self.mock_tracer.start_span.return_value = self.mock_otel_span
        self.processor = OpenAIAgentsTraceProcessor(self.mock_tracer)

    def test_on_trace_end_ends_root_span(self):
        """Root span should be ended with OK status when trace ends."""
        root = _make_otel_span()
        self.processor._root_spans["trace-1"] = root

        trace = _make_trace("trace-1")
        self.processor.on_trace_end(trace)

        root.set_status.assert_called_once()
        root.end.assert_called_once()
        self.assertNotIn("trace-1", self.processor._root_spans)

    def test_on_trace_end_noop_without_root(self):
        """on_trace_end should not raise if no root span exists."""
        trace = _make_trace("trace-nonexistent")
        self.processor.on_trace_end(trace)  # should not raise

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.attach")
    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.set_span_in_context")
    def test_on_span_start_creates_otel_span(self, mock_set_ctx, mock_attach):
        """on_span_start should create an OTel span with correct attributes."""
        agent_data = AgentSpanData(name="TestAgent")
        span = _make_span(agent_data)

        self.processor.on_span_start(span)

        self.mock_tracer.start_span.assert_called_once()
        call_kwargs = self.mock_tracer.start_span.call_args
        attrs = call_kwargs.kwargs.get("attributes") or call_kwargs[1].get("attributes")
        self.assertEqual(attrs[GEN_AI_PROVIDER_NAME_KEY], "openai")
        self.assertIn("span-1", self.processor._otel_spans)

    def test_on_span_start_skips_without_started_at(self):
        """on_span_start should skip if started_at is None."""
        span = _make_span(AgentSpanData(name="Agent"), started_at=None)
        self.processor.on_span_start(span)
        self.mock_tracer.start_span.assert_not_called()

    def test_on_span_start_tracks_agent_span_ids(self):
        """Agent spans should be tracked for ancestor lookup."""
        span = _make_span(AgentSpanData(name="Agent"), span_id="agent-1")
        with patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.attach"):
            self.processor.on_span_start(span)
        self.assertIn("agent-1", self.processor._agent_span_ids)

    def test_on_span_start_tracks_parent_child(self):
        """Parent-child relationships should be tracked."""
        span = _make_span(AgentSpanData(name="Agent"), span_id="child-1", parent_id="parent-1")
        with patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.attach"):
            self.processor.on_span_start(span)
        self.assertEqual(self.processor._span_parents["child-1"], "parent-1")

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_on_span_end_agent_span_sets_name(self, mock_detach):
        """Agent span should update name to 'invoke_agent <name>'."""
        agent_data = AgentSpanData(name="MyAgent")
        span = _make_span(agent_data, span_id="agent-1")

        # Pre-populate the otel span
        otel_span = _make_otel_span()
        self.processor._otel_spans["agent-1"] = otel_span
        self.processor._tokens["agent-1"] = MagicMock()

        self.processor.on_span_end(span)

        otel_span.update_name.assert_called()
        # Last call should be the invoke_agent name
        last_name = otel_span.update_name.call_args_list[-1][0][0]
        self.assertTrue(last_name.startswith(INVOKE_AGENT_OPERATION_NAME))
        self.assertIn("MyAgent", last_name)

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_on_span_end_function_span_sets_tool_attrs(self, mock_detach):
        """Function span should set tool name, type, and update name."""
        func_data = FunctionSpanData(name="add_numbers", input='{"a":1}', output="2")
        span = _make_span(func_data, span_id="func-1")

        otel_span = _make_otel_span()
        self.processor._otel_spans["func-1"] = otel_span
        self.processor._tokens["func-1"] = MagicMock()

        self.processor.on_span_end(span)

        self.assertEqual(otel_span.attributes[GEN_AI_TOOL_TYPE_KEY], "function")
        otel_span.update_name.assert_called()
        last_name = otel_span.update_name.call_args_list[-1][0][0]
        self.assertIn("add_numbers", last_name)

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_on_span_end_function_span_sets_tool_call_id(self, mock_detach):
        """Function span should set tool_call_id from pending_tool_calls."""
        func_data = FunctionSpanData(name="add", input='{"a":1}', output="2")
        span = _make_span(func_data, span_id="func-1")

        otel_span = _make_otel_span()
        self.processor._otel_spans["func-1"] = otel_span
        self.processor._tokens["func-1"] = MagicMock()
        # Pre-populate pending tool calls (keyed with trace_id)
        self.processor._pending_tool_calls['trace-1:add:{"a":1}'] = "call_abc"

        self.processor.on_span_end(span)

        self.assertEqual(otel_span.attributes.get(GEN_AI_TOOL_CALL_ID_KEY), "call_abc")

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_handoff_sets_graph_node_parent_id(self, mock_detach):
        """Handoff → AgentSpan should set graph_node_parent_id."""
        # 1) Process HandoffSpan: from AgentA to AgentB
        handoff_data = HandoffSpanData(from_agent="AgentA", to_agent="AgentB")
        handoff_span = _make_span(handoff_data, span_id="handoff-1", trace_id="t1")
        otel_handoff = _make_otel_span()
        self.processor._otel_spans["handoff-1"] = otel_handoff
        self.processor._tokens["handoff-1"] = MagicMock()
        self.processor.on_span_end(handoff_span)

        # 2) Now process AgentB's AgentSpan
        agent_data = AgentSpanData(name="AgentB")
        agent_span = _make_span(agent_data, span_id="agent-b", trace_id="t1")
        otel_agent = _make_otel_span()
        self.processor._otel_spans["agent-b"] = otel_agent
        self.processor._tokens["agent-b"] = MagicMock()
        self.processor.on_span_end(agent_span)

        self.assertEqual(otel_agent.attributes.get(GEN_AI_GRAPH_NODE_PARENT_ID), "AgentA")

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_agent_span_gets_input_output_from_child_generation(self, mock_detach):
        """Agent span should receive input/output messages captured from child GenerationSpan."""
        # Set up agent span in tracking
        self.processor._agent_span_ids["agent-1"] = None

        # Pre-populate captured messages
        self.processor._agent_inputs["agent-1"] = "Hello user input"
        self.processor._agent_outputs["agent-1"] = "Hello output"

        agent_data = AgentSpanData(name="TestAgent")
        span = _make_span(agent_data, span_id="agent-1")

        otel_span = _make_otel_span()
        self.processor._otel_spans["agent-1"] = otel_span
        self.processor._tokens["agent-1"] = MagicMock()

        self.processor.on_span_end(span)

        self.assertEqual(otel_span.attributes.get(GEN_AI_INPUT_MESSAGES_KEY), "Hello user input")
        self.assertEqual(otel_span.attributes.get(GEN_AI_OUTPUT_MESSAGES_KEY), "Hello output")

    def test_stamp_custom_parent_sets_attribute(self):
        """_stamp_custom_parent should set custom.parent.span.id from root span."""
        root = _make_otel_span()
        self.processor._root_spans["trace-1"] = root

        otel_span = _make_otel_span()
        self.processor._stamp_custom_parent(otel_span, "trace-1")

        self.assertIn(CUSTOM_PARENT_SPAN_ID_KEY, otel_span.attributes)

    def test_stamp_custom_parent_noop_without_root(self):
        """_stamp_custom_parent should not set attribute when no root span."""
        otel_span = _make_otel_span()
        self.processor._stamp_custom_parent(otel_span, "nonexistent")
        self.assertNotIn(CUSTOM_PARENT_SPAN_ID_KEY, otel_span.attributes)

    def test_cap_ordered_dict(self):
        """_cap_ordered_dict should evict oldest entries."""
        d = OrderedDict()
        for i in range(15):
            d[f"key-{i}"] = i
        OpenAIAgentsTraceProcessor._cap_ordered_dict(d, 10)
        self.assertEqual(len(d), 10)
        # Oldest keys should be removed
        self.assertNotIn("key-0", d)
        self.assertIn("key-14", d)

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_on_span_end_noop_without_otel_span(self, mock_detach):
        """on_span_end should not raise if OTel span was not created."""
        span = _make_span(AgentSpanData(name="Agent"), span_id="missing")
        self.processor.on_span_end(span)  # should not raise

    @patch("microsoft.opentelemetry._genai._openai_agents._trace_processor.detach")
    def test_on_span_end_sets_error_status(self, mock_detach):
        """Spans with errors should get ERROR status."""
        agent_data = AgentSpanData(name="Agent")
        span = _make_span(
            agent_data,
            span_id="err-1",
            error={"message": "bad", "data": "detail"},
        )
        otel_span = _make_otel_span()
        self.processor._otel_spans["err-1"] = otel_span
        self.processor._tokens["err-1"] = MagicMock()

        self.processor.on_span_end(span)

        status_call = otel_span.set_status.call_args
        status = status_call.kwargs.get("status") or status_call[0][0]
        from opentelemetry.trace import StatusCode

        self.assertEqual(status.status_code, StatusCode.ERROR)

    def test_force_flush_and_shutdown(self):
        """force_flush and shutdown should not raise."""
        self.processor.force_flush()
        self.processor.shutdown()
