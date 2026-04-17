# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
from collections import OrderedDict
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from microsoft.opentelemetry._genai._langchain._tracer import (
    LangChainTracer,
    _update_span,
    get_attributes_from_context,
)
from microsoft.opentelemetry._genai._langchain._utils import (
    EXECUTE_TOOL_OPERATION_NAME,
    INVOKE_AGENT_OPERATION_NAME,
)

_NOW = datetime.datetime(2024, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
_NOW_END = datetime.datetime(2024, 6, 1, 12, 0, 1, tzinfo=datetime.timezone.utc)


# pylint: disable=unused-variable, broad-exception-caught
def _make_run(**kwargs):
    """Create a minimal mock Run."""
    run = MagicMock()
    run.id = kwargs.get("id", uuid4())
    run.name = kwargs.get("name", "test_run")
    run.run_type = kwargs.get("run_type", "chain")
    run.inputs = kwargs.get("inputs", None)
    run.outputs = kwargs.get("outputs", None)
    run.extra = kwargs.get("extra", None)
    run.serialized = kwargs.get("serialized", None)
    run.error = kwargs.get("error", None)
    run.parent_run_id = kwargs.get("parent_run_id", None)
    run.start_time = kwargs.get("start_time", _NOW)
    run.end_time = kwargs.get("end_time", _NOW_END)
    return run


def _make_tracer(**kwargs):
    """Create a LangChainTracer with mocked OTel tracer."""
    otel_tracer = MagicMock()
    mock_span = MagicMock()
    otel_tracer.start_span.return_value = mock_span
    tracer = LangChainTracer(
        otel_tracer,
        kwargs.get("separate_trace", False),
        agent_config=kwargs.get("agent_config", {}),
        event_logger=kwargs.get("event_logger", None),
    )
    return tracer, otel_tracer, mock_span


# ---- Static helpers ----------------------------------------------------------


class TestCapOrderedDict(TestCase):
    def test_caps_size(self):
        d = OrderedDict()
        for i in range(10):
            d[i] = f"val-{i}"
        LangChainTracer._cap_ordered_dict(d, 5)
        self.assertEqual(len(d), 5)
        # Oldest entries removed
        self.assertNotIn(0, d)
        self.assertIn(9, d)


# ---- Agent detection ---------------------------------------------------------


class TestIsAgentLikeChain(TestCase):
    def test_langgraph_name(self):
        run = _make_run(run_type="chain", name="LangGraph")
        self.assertTrue(LangChainTracer._is_agent_like_chain(run))

    def test_compiled_graph(self):
        run = _make_run(
            run_type="chain",
            name="MyGraph",
            serialized={"graph": {"type": "CompiledGraph"}},
        )
        self.assertTrue(LangChainTracer._is_agent_like_chain(run))

    def test_state_graph(self):
        run = _make_run(
            run_type="chain",
            name="MyGraph",
            serialized={"graph": {"type": "StateGraph"}},
        )
        self.assertTrue(LangChainTracer._is_agent_like_chain(run))

    def test_agent_in_name(self):
        run = _make_run(run_type="chain", name="MyAgent")
        self.assertTrue(LangChainTracer._is_agent_like_chain(run))

    def test_lc_agent_name_in_metadata(self):
        run = _make_run(
            run_type="chain",
            name="Travel_Assistant",
            extra={"metadata": {"lc_agent_name": "Travel_Assistant"}},
        )
        self.assertTrue(LangChainTracer._is_agent_like_chain(run))

    def test_non_chain_returns_false(self):
        run = _make_run(run_type="llm", name="LangGraph")
        self.assertFalse(LangChainTracer._is_agent_like_chain(run))

    def test_plain_chain_returns_false(self):
        run = _make_run(run_type="chain", name="RunnableSequence")
        self.assertFalse(LangChainTracer._is_agent_like_chain(run))


class TestIsAgentRun(TestCase):
    def test_top_level_agent(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(run_type="chain", name="LangGraph", parent_run_id=None)
        self.assertTrue(tracer._is_agent_run(run))

    def test_nested_agent_returns_false(self):
        tracer, _, _ = _make_tracer()
        parent_id = uuid4()
        tracer._agent_run_ids.add(parent_id)
        run = _make_run(run_type="chain", name="LangGraph", parent_run_id=parent_id)
        self.assertFalse(tracer._is_agent_run(run))

    def test_non_agent_returns_false(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(run_type="chain", name="RunnableSequence")
        self.assertFalse(tracer._is_agent_run(run))


# ---- Agent name resolution ---------------------------------------------------


class TestResolveAgentName(TestCase):
    def test_config_override(self):
        tracer, _, _ = _make_tracer(agent_config={"agent_name": "ConfigBot"})
        run = _make_run(run_type="chain", name="LangGraph")
        self.assertEqual(tracer._resolve_agent_name(run), "ConfigBot")

    def test_metadata_agent_name(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(
            run_type="chain",
            name="LangGraph",
            extra={"metadata": {"agent_name": "MetaBot"}},
        )
        self.assertEqual(tracer._resolve_agent_name(run), "MetaBot")

    def test_metadata_lc_agent_name(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(
            run_type="chain",
            name="Travel_Assistant",
            extra={"metadata": {"lc_agent_name": "Travel_Assistant"}},
        )
        self.assertEqual(tracer._resolve_agent_name(run), "Travel_Assistant")

    def test_serialized_name(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(
            run_type="chain",
            name="LangGraph",
            serialized={"name": "CustomGraph"},
        )
        self.assertEqual(tracer._resolve_agent_name(run), "CustomGraph")

    def test_run_name_fallback(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(run_type="chain", name="MyAgent")
        self.assertEqual(tracer._resolve_agent_name(run), "MyAgent")

    def test_langgraph_name_returns_none(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(run_type="chain", name="LangGraph")
        self.assertIsNone(tracer._resolve_agent_name(run))


# ---- Framework name resolution -----------------------------------------------


class TestResolveFrameworkName(TestCase):
    def test_compiled_graph_returns_langgraph(self):
        run = _make_run(serialized={"graph": {"type": "CompiledGraph"}})
        self.assertEqual(LangChainTracer._resolve_framework_name(run), "LangGraph")

    def test_state_graph_returns_langgraph(self):
        run = _make_run(serialized={"graph": {"type": "StateGraph"}})
        self.assertEqual(LangChainTracer._resolve_framework_name(run), "LangGraph")

    def test_serialized_name_different_from_run(self):
        run = _make_run(name="Travel_Assistant", serialized={"name": "CustomFramework"})
        self.assertEqual(LangChainTracer._resolve_framework_name(run), "CustomFramework")

    def test_defaults_to_langgraph(self):
        run = _make_run(name="Travel_Assistant", serialized=None)
        self.assertEqual(LangChainTracer._resolve_framework_name(run), "LangGraph")

    def test_same_serialized_and_run_name_defaults(self):
        run = _make_run(name="Travel_Assistant", serialized={"name": "Travel_Assistant"})
        self.assertEqual(LangChainTracer._resolve_framework_name(run), "LangGraph")


# ---- _start_trace / _end_trace -----------------------------------------------


class TestStartTrace(TestCase):
    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_creates_span_for_chain(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        run = _make_run(run_type="chain", name="RunnableSequence")
        tracer._start_trace(run)
        otel_tracer.start_span.assert_called_once()
        args = otel_tracer.start_span.call_args
        self.assertEqual(args.kwargs["name"], "RunnableSequence")

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_creates_span_for_tool(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        run = _make_run(run_type="tool", name="get_weather")
        tracer._start_trace(run)
        otel_tracer.start_span.assert_called_once()
        args = otel_tracer.start_span.call_args
        self.assertIn(EXECUTE_TOOL_OPERATION_NAME, args.kwargs["name"])
        self.assertIn("get_weather", args.kwargs["name"])

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_creates_wrapper_for_agent(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, mock_span = _make_tracer()
        run = _make_run(
            run_type="chain",
            name="Travel_Assistant",
            extra={"metadata": {"lc_agent_name": "Travel_Assistant"}},
        )
        tracer._start_trace(run)
        # Two spans: wrapper + inner
        self.assertEqual(otel_tracer.start_span.call_count, 2)
        calls = otel_tracer.start_span.call_args_list
        wrapper_name = calls[0].kwargs["name"]
        inner_name = calls[1].kwargs["name"]
        self.assertIn("Travel_Assistant", wrapper_name)
        self.assertIn(INVOKE_AGENT_OPERATION_NAME, wrapper_name)
        self.assertIn("LangGraph", inner_name)

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_suppressed_instrumentation_skips(self, mock_ctx):
        mock_ctx.get_value.return_value = True
        tracer, otel_tracer, _ = _make_tracer()
        run = _make_run(run_type="chain", name="test")
        tracer._start_trace(run)
        otel_tracer.start_span.assert_not_called()


class TestEndTrace(TestCase):
    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_ends_span(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, mock_span = _make_tracer()
        run = _make_run(run_type="chain", name="test")
        tracer._start_trace(run)
        tracer._end_trace(run)
        mock_span.end.assert_called()

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_ends_both_spans_for_agent(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        wrapper_span = MagicMock()
        inner_span = MagicMock()
        otel_tracer.start_span.side_effect = [wrapper_span, inner_span]
        run = _make_run(
            run_type="chain",
            name="Travel_Assistant",
            extra={"metadata": {"lc_agent_name": "Travel_Assistant"}},
        )
        tracer._start_trace(run)
        tracer._end_trace(run)
        inner_span.end.assert_called_once()
        wrapper_span.end.assert_called_once()

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_cleans_up_agent_tracking(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        wrapper_span = MagicMock()
        inner_span = MagicMock()
        otel_tracer.start_span.side_effect = [wrapper_span, inner_span]
        run = _make_run(
            run_type="chain",
            name="LangGraph",
        )
        tracer._start_trace(run)
        self.assertIn(run.id, tracer._agent_run_ids)
        tracer._end_trace(run)
        self.assertNotIn(run.id, tracer._agent_run_ids)
        self.assertNotIn(run.id, tracer._agent_content)


# ---- Error handlers ----------------------------------------------------------


class TestErrorHandlers(TestCase):
    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_on_llm_error_records_exception(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, mock_span = _make_tracer()
        run = _make_run(run_type="llm", name="gpt-4")
        tracer._start_trace(run)
        error = ValueError("test error")
        with patch.object(tracer, "_persist_run"):
            try:
                tracer.on_llm_error(error, run_id=run.id)
            except Exception:
                pass
        mock_span.record_exception.assert_called_with(error)

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_on_chain_error_records_exception(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, mock_span = _make_tracer()
        run = _make_run(run_type="chain", name="test")
        tracer._start_trace(run)
        error = RuntimeError("chain failed")
        with patch.object(tracer, "_persist_run"):
            try:
                tracer.on_chain_error(error, run_id=run.id)
            except Exception:
                pass
        mock_span.record_exception.assert_called_with(error)

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_on_tool_error_records_exception(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, mock_span = _make_tracer()
        run = _make_run(run_type="tool", name="calc")
        tracer._start_trace(run)
        error = RuntimeError("tool failed")
        with patch.object(tracer, "_persist_run"):
            try:
                tracer.on_tool_error(error, run_id=run.id)
            except Exception:
                pass
        mock_span.record_exception.assert_called_with(error)


# ---- _update_span ------------------------------------------------------------


class TestUpdateSpan(TestCase):
    def test_sets_ok_status_on_no_error(self):
        span = MagicMock()
        run = _make_run(run_type="chain", name="test", error=None)
        _update_span(span, run)
        span.set_status.assert_called()

    def test_llm_run_returns_invocation(self):
        span = MagicMock()
        run = _make_run(
            run_type="llm",
            name="gpt-4",
            outputs={"llm_output": {"model_name": "gpt-4"}, "generations": []},
            extra=None,
            inputs=None,
        )
        result = _update_span(span, run)
        self.assertIsNotNone(result)

    def test_chain_run_returns_none(self):
        span = MagicMock()
        run = _make_run(run_type="chain", name="test")
        result = _update_span(span, run)
        self.assertIsNone(result)

    def test_tool_run_sets_tool_attributes(self):
        span = MagicMock()
        run = _make_run(
            run_type="tool",
            name="calculator",
            serialized={"name": "calculator", "description": "Math tool"},
            inputs={"input": "2+2"},
            outputs={"output": "4"},
        )
        _update_span(span, run)
        span.set_attributes.assert_called()


# ---- Aggregation -------------------------------------------------------------


class TestAggregateIntoParent(TestCase):
    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_aggregates_llm_model(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        wrapper = MagicMock()
        inner = MagicMock()
        otel_tracer.start_span.side_effect = [wrapper, inner]

        agent_run = _make_run(run_type="chain", name="LangGraph")
        tracer._start_trace(agent_run)

        llm_run = _make_run(
            run_type="llm",
            name="gpt-4",
            parent_run_id=agent_run.id,
            outputs={"llm_output": {"model_name": "gpt-4"}, "generations": []},
            extra=None,
            inputs={"messages": [[{"content": "Hello"}]]},
        )
        tracer.run_map[str(llm_run.id)] = llm_run
        tracer._aggregate_into_parent(llm_run)

        content = tracer._agent_content[agent_run.id]
        self.assertEqual(content["model"], "gpt-4")

    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_aggregates_tool_output(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        wrapper = MagicMock()
        inner = MagicMock()
        otel_tracer.start_span.side_effect = [wrapper, inner]

        agent_run = _make_run(run_type="chain", name="LangGraph")
        tracer._start_trace(agent_run)

        tool_run = _make_run(
            run_type="tool",
            name="calculator",
            parent_run_id=agent_run.id,
            outputs={"output": "42"},
        )
        tracer.run_map[str(tool_run.id)] = tool_run
        tracer._aggregate_into_parent(tool_run)

        content = tracer._agent_content[agent_run.id]
        self.assertIn("42", content["output_messages"])


class TestFindAgentAncestor(TestCase):
    @patch("microsoft.opentelemetry._genai._langchain._tracer.context_api")
    def test_finds_direct_parent(self, mock_ctx):
        mock_ctx.get_value.return_value = None
        tracer, otel_tracer, _ = _make_tracer()
        wrapper = MagicMock()
        inner = MagicMock()
        otel_tracer.start_span.side_effect = [wrapper, inner]

        agent_run = _make_run(run_type="chain", name="LangGraph")
        tracer._start_trace(agent_run)

        child_run = _make_run(run_type="llm", name="gpt-4", parent_run_id=agent_run.id)
        tracer.run_map[str(child_run.id)] = child_run
        result = tracer._find_agent_ancestor(child_run)
        self.assertEqual(result, agent_run.id)

    def test_returns_none_without_parent(self):
        tracer, _, _ = _make_tracer()
        run = _make_run(parent_run_id=None)
        self.assertIsNone(tracer._find_agent_ancestor(run))


# ---- get_attributes_from_context ---------------------------------------------


class TestGetAttributesFromContext(TestCase):
    @patch("microsoft.opentelemetry._genai._langchain._tracer.get_value")
    def test_yields_context_attributes(self, mock_get_value):
        mock_get_value.side_effect = lambda key: "test_val" if key == "session.id" else None
        result = dict(get_attributes_from_context())
        self.assertEqual(result.get("session.id"), "test_val")

    @patch("microsoft.opentelemetry._genai._langchain._tracer.get_value", return_value=None)
    def test_yields_nothing_when_empty(self, mock_get_value):
        result = list(get_attributes_from_context())
        self.assertEqual(result, [])
