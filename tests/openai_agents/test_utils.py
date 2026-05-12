# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for OpenAI Agents A365 utility functions."""

from collections import OrderedDict
from unittest import TestCase
from unittest.mock import MagicMock

import pytest

pytest.importorskip("agents")

from agents.tracing.span_data import (  # noqa: E402  # pylint: disable=wrong-import-position
    AgentSpanData,
    FunctionSpanData,
    GenerationSpanData,
    HandoffSpanData,
)

from microsoft.opentelemetry._genai._openai_agents._utils import (  # noqa: E402  # pylint: disable=wrong-import-position
    capture_input_message,
    capture_output_message,
    capture_tool_call_ids,
    find_ancestor_agent_span_id,
    get_attributes_from_function_span_data,
    get_span_kind,
    get_span_name,
    get_span_status,
    get_tool_call_id,
)
from microsoft.opentelemetry._genai._openai_agents._constants import (  # noqa: E402  # pylint: disable=wrong-import-position
    GEN_AI_SPAN_KIND_AGENT_KEY,
    GEN_AI_SPAN_KIND_LLM_KEY,
    GEN_AI_SPAN_KIND_TOOL_KEY,
)
from microsoft.opentelemetry.a365.core.constants import (  # noqa: E402  # pylint: disable=wrong-import-position
    GEN_AI_TOOL_ARGS_KEY,
    GEN_AI_TOOL_CALL_RESULT_KEY,
    GEN_AI_TOOL_NAME_KEY,
)


class TestGetSpanName(TestCase):
    def test_agent_span_data_name(self):
        span = MagicMock()
        span.span_data = AgentSpanData(name="MyAgent")
        self.assertEqual(get_span_name(span), "MyAgent")

    def test_function_span_data_name(self):
        span = MagicMock()
        span.span_data = FunctionSpanData(name="my_tool", input="", output="")
        self.assertEqual(get_span_name(span), "my_tool")

    def test_handoff_span_data_name(self):
        span = MagicMock()
        span.span_data = HandoffSpanData(from_agent="A", to_agent="B")
        self.assertEqual(get_span_name(span), "handoff to B")

    def test_handoff_span_data_no_to_agent_uses_type(self):
        span = MagicMock()
        data = HandoffSpanData(from_agent="A", to_agent="")
        span.span_data = data
        # Falls through to type
        result = get_span_name(span)
        self.assertIsNotNone(result)


class TestGetSpanKind(TestCase):
    def test_agent_span(self):
        self.assertEqual(get_span_kind(AgentSpanData(name="A")), GEN_AI_SPAN_KIND_AGENT_KEY)

    def test_function_span(self):
        self.assertEqual(
            get_span_kind(FunctionSpanData(name="f", input="", output="")),
            GEN_AI_SPAN_KIND_TOOL_KEY,
        )

    def test_generation_span(self):
        data = GenerationSpanData(model="gpt-4", model_config={}, input=[], output=[], usage={})
        self.assertEqual(get_span_kind(data), GEN_AI_SPAN_KIND_LLM_KEY)

    def test_handoff_span(self):
        data = HandoffSpanData(from_agent="A", to_agent="B")
        self.assertEqual(get_span_kind(data), GEN_AI_SPAN_KIND_TOOL_KEY)


class TestGetSpanStatus(TestCase):
    def test_ok_status_without_error(self):
        span = MagicMock()
        span.error = None
        status = get_span_status(span)
        from opentelemetry.trace import StatusCode

        self.assertEqual(status.status_code, StatusCode.OK)

    def test_error_status_with_error(self):
        span = MagicMock()
        span.error = {"message": "something failed", "data": "details"}
        status = get_span_status(span)
        from opentelemetry.trace import StatusCode

        self.assertEqual(status.status_code, StatusCode.ERROR)
        self.assertIn("something failed", status.description)


class TestGetAttributesFromFunctionSpanData(TestCase):
    def test_basic_function_span(self):
        data = FunctionSpanData(name="add", input='{"a":1}', output="2")
        attrs = dict(get_attributes_from_function_span_data(data))
        self.assertEqual(attrs[GEN_AI_TOOL_NAME_KEY], "add")
        self.assertEqual(attrs[GEN_AI_TOOL_ARGS_KEY], '{"a":1}')
        self.assertEqual(attrs[GEN_AI_TOOL_CALL_RESULT_KEY], "2")

    def test_function_span_no_input(self):
        data = FunctionSpanData(name="noop", input="", output=None)
        attrs = dict(get_attributes_from_function_span_data(data))
        self.assertEqual(attrs[GEN_AI_TOOL_NAME_KEY], "noop")
        self.assertNotIn(GEN_AI_TOOL_ARGS_KEY, attrs)


class TestCaptureToolCallIds(TestCase):
    def test_captures_tool_call_ids(self):
        output = [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "function": {"name": "add", "arguments": '{"a":1}'},
                    }
                ],
            }
        ]
        pending = OrderedDict()
        capture_tool_call_ids(output, pending, trace_id="trace-1")
        self.assertEqual(pending['trace-1:add:{"a":1}'], "call_123")

    def test_caps_size(self):
        pending = OrderedDict()
        for i in range(15):
            output = [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": f"call_{i}",
                            "function": {"name": f"fn_{i}", "arguments": "{}"},
                        }
                    ],
                }
            ]
            capture_tool_call_ids(output, pending, max_size=10, trace_id="trace-1")
        self.assertLessEqual(len(pending), 10)

    def test_empty_output(self):
        pending = OrderedDict()
        capture_tool_call_ids(None, pending)
        capture_tool_call_ids([], pending)
        self.assertEqual(len(pending), 0)


class TestGetToolCallId(TestCase):
    def test_pops_matching_entry(self):
        pending = OrderedDict()
        pending['trace-1:add:{"a":1}'] = "call_abc"
        result = get_tool_call_id("add", '{"a":1}', pending, trace_id="trace-1")
        self.assertEqual(result, "call_abc")
        self.assertNotIn('trace-1:add:{"a":1}', pending)

    def test_returns_none_for_missing(self):
        result = get_tool_call_id("unknown", "", OrderedDict())
        self.assertIsNone(result)


class TestCaptureInputMessage(TestCase):
    def test_captures_first_user_message(self):
        inputs = OrderedDict()
        data = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        capture_input_message("span-1", data, inputs)
        self.assertEqual(inputs["span-1"], "Hello")

    def test_does_not_overwrite_existing(self):
        inputs = OrderedDict()
        inputs["span-1"] = "First"
        data = [{"role": "user", "content": "Second"}]
        capture_input_message("span-1", data, inputs)
        self.assertEqual(inputs["span-1"], "First")

    def test_empty_input(self):
        inputs = OrderedDict()
        capture_input_message("span-1", None, inputs)
        capture_input_message("span-1", [], inputs)
        self.assertNotIn("span-1", inputs)


class TestCaptureOutputMessage(TestCase):
    def test_captures_last_assistant_content(self):
        outputs = OrderedDict()
        data = [
            {"role": "assistant", "content": None, "tool_calls": [{"id": "c1"}]},
            {"role": "assistant", "content": "Final answer"},
        ]
        capture_output_message("span-1", data, outputs)
        self.assertEqual(outputs["span-1"], "Final answer")

    def test_skips_tool_call_messages(self):
        outputs = OrderedDict()
        data = [
            {"role": "assistant", "content": "call tools", "tool_calls": [{"id": "c1"}]},
        ]
        capture_output_message("span-1", data, outputs)
        self.assertNotIn("span-1", outputs)

    def test_empty_output(self):
        outputs = OrderedDict()
        capture_output_message("span-1", None, outputs)
        self.assertNotIn("span-1", outputs)


class TestFindAncestorAgentSpanId(TestCase):
    def test_finds_direct_parent(self):
        agent_ids = {"agent-1": None}
        parents = {"child-1": "agent-1"}
        result = find_ancestor_agent_span_id("child-1", agent_ids, parents)
        self.assertEqual(result, "agent-1")

    def test_finds_grandparent(self):
        agent_ids = {"agent-1": None}
        parents = {"child-1": "mid-1", "mid-1": "agent-1"}
        result = find_ancestor_agent_span_id("child-1", agent_ids, parents)
        self.assertEqual(result, "agent-1")

    def test_returns_none_when_no_agent(self):
        result = find_ancestor_agent_span_id("child-1", {}, {"child-1": "parent-1"})
        self.assertIsNone(result)

    def test_handles_cycles(self):
        parents = {"a": "b", "b": "a"}
        result = find_ancestor_agent_span_id("a", {}, parents)
        self.assertIsNone(result)

    def test_returns_none_for_none_input(self):
        result = find_ancestor_agent_span_id(None, {"agent-1": None}, {})
        self.assertIsNone(result)
