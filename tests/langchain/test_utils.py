# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
import json
from enum import Enum
from unittest import TestCase
from unittest.mock import MagicMock

from microsoft.genai._langchain._utils import (
    DictWithLock,
    CHAT_OPERATION_NAME,
    EXECUTE_TOOL_OPERATION_NAME,
    GEN_AI_AGENT_DESCRIPTION_KEY,
    GEN_AI_AGENT_ID_KEY,
    GEN_AI_AGENT_NAME_KEY,
    GEN_AI_CONVERSATION_ID_KEY,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_PROVIDER_NAME_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    GEN_AI_SYSTEM_INSTRUCTIONS_KEY,
    GEN_AI_TOOL_ARGS_KEY,
    GEN_AI_TOOL_CALL_ID_KEY,
    GEN_AI_TOOL_CALL_RESULT_KEY,
    GEN_AI_TOOL_DESCRIPTION_KEY,
    GEN_AI_TOOL_NAME_KEY,
    GEN_AI_TOOL_TYPE_KEY,
    GEN_AI_USAGE_INPUT_TOKENS_KEY,
    GEN_AI_USAGE_OUTPUT_TOKENS_KEY,
    SESSION_ID_KEY,
    add_operation_type,
    as_utc_nano,
    build_llm_invocation,
    chain_node_messages,
    extract_agent_metadata,
    extract_session_info,
    flatten,
    function_calls,
    get_first_value,
    input_messages,
    invocation_parameters,
    invoke_agent_input_message,
    invoke_agent_output_message,
    llm_provider,
    metadata,
    model_name,
    output_messages,
    prompts,
    safe_json_dumps,
    stop_on_exception,
    token_counts,
    tools,
)


def _make_run(**kwargs):
    """Create a minimal mock Run with sensible defaults."""
    run = MagicMock()
    run.id = kwargs.get("id", "run-1")
    run.name = kwargs.get("name", "test_run")
    run.run_type = kwargs.get("run_type", "chain")
    run.inputs = kwargs.get("inputs", None)
    run.outputs = kwargs.get("outputs", None)
    run.extra = kwargs.get("extra", None)
    run.serialized = kwargs.get("serialized", None)
    run.error = kwargs.get("error", None)
    run.parent_run_id = kwargs.get("parent_run_id", None)
    run.start_time = kwargs.get("start_time", datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc))
    run.end_time = kwargs.get("end_time", datetime.datetime(2024, 1, 1, second=1, tzinfo=datetime.timezone.utc))
    return run


# ---- Core utilities ----------------------------------------------------------


class TestSafeJsonDumps(TestCase):
    def test_serializes_dict(self):
        result = safe_json_dumps({"key": "value"})
        self.assertEqual(json.loads(result), {"key": "value"})

    def test_handles_non_serializable_types(self):
        import uuid

        obj = {"id": uuid.UUID("12345678-1234-5678-1234-567812345678")}
        result = safe_json_dumps(obj)
        self.assertIn("12345678-1234-5678-1234-567812345678", result)

    def test_handles_datetime(self):
        obj = {"ts": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)}
        result = safe_json_dumps(obj)
        self.assertIn("2024", result)


class TestAsUtcNano(TestCase):
    def test_epoch_returns_zero(self):
        dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertEqual(as_utc_nano(dt), 0)

    def test_known_timestamp(self):
        dt = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        expected = int(dt.timestamp() * 1_000_000_000)
        self.assertEqual(as_utc_nano(dt), expected)


class TestGetFirstValue(TestCase):
    def test_returns_first_match(self):
        mapping = {"a": 1, "b": 2, "c": 3}
        self.assertEqual(get_first_value(mapping, ["x", "b", "c"]), 2)

    def test_returns_none_when_no_match(self):
        mapping = {"a": 1}
        self.assertIsNone(get_first_value(mapping, ["x", "y"]))

    def test_skips_none_values(self):
        mapping = {"a": None, "b": 2}
        self.assertEqual(get_first_value(mapping, ["a", "b"]), 2)

    def test_handles_non_mapping(self):
        self.assertIsNone(get_first_value("not a mapping", ["a"]))


class TestStopOnException(TestCase):
    def test_yields_normally(self):
        @stop_on_exception
        def gen():
            yield ("k", "v")

        self.assertEqual(list(gen()), [("k", "v")])

    def test_catches_exception(self):
        @stop_on_exception
        def gen():
            raise ValueError("boom")
            yield ("k", "v")  # noqa: unreachable # pylint: disable=unreachable

        self.assertEqual(list(gen()), [])


class TestFlatten(TestCase):
    def test_simple_key_value(self):
        result = list(flatten([("key", "value")]))
        self.assertEqual(result, [("key", "value")])

    def test_nested_dict(self):
        result = list(flatten([("parent", {"child": "value"})]))
        self.assertEqual(result, [("parent.child", "value")])

    def test_skips_none(self):
        result = list(flatten([("key", None)]))
        self.assertEqual(result, [])

    def test_enum_value(self):
        class Color(Enum):
            RED = "red"

        result = list(flatten([("color", Color.RED)]))
        self.assertEqual(result, [("color", "red")])

    def test_list_of_dicts(self):
        data = [("items", [{"a": 1}, {"b": 2}])]
        result = list(flatten(data))
        self.assertEqual(result, [("items.0.a", 1), ("items.1.b", 2)])


class TestDictWithLock(TestCase):
    def test_get_set(self):
        d = DictWithLock()
        d["key"] = "value"
        self.assertEqual(d.get("key"), "value")

    def test_get_missing(self):
        d = DictWithLock()
        self.assertIsNone(d.get("missing"))

    def test_pop(self):
        d = DictWithLock({"key": "value"})
        self.assertEqual(d.pop("key"), "value")
        self.assertIsNone(d.get("key"))

    def test_del(self):
        d = DictWithLock({"key": "value"})
        del d["key"]
        self.assertIsNone(d.get("key"))


# ---- Data extractors ---------------------------------------------------------


class TestPrompts(TestCase):
    def test_extracts_prompts(self):
        inputs = {"prompts": ["System prompt here"]}
        result = list(prompts(inputs))
        self.assertEqual(result, [(GEN_AI_SYSTEM_INSTRUCTIONS_KEY, ["System prompt here"])])

    def test_returns_empty_on_none(self):
        self.assertEqual(list(prompts(None)), [])

    def test_returns_empty_on_no_prompts(self):
        self.assertEqual(list(prompts({"other": "data"})), [])


class TestInputMessages(TestCase):
    def test_extracts_from_basemessage(self):
        msg = MagicMock(spec=["content"])
        msg.content = "Hello"
        # Ensure isinstance(msg, BaseMessage) doesn't match for mock
        # Use dict-style messages instead for reliable testing
        inputs = {"messages": [[{"content": "Hello"}]]}
        result = list(input_messages(inputs))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], GEN_AI_INPUT_MESSAGES_KEY)

    def test_returns_empty_on_none(self):
        self.assertEqual(list(input_messages(None)), [])

    def test_returns_empty_on_no_messages(self):
        self.assertEqual(list(input_messages({"other": "data"})), [])

    def test_extracts_from_dict_messages(self):
        inputs = {"messages": [[{"content": "Hi"}, {"content": "There"}]]}
        result = list(input_messages(inputs))
        self.assertEqual(len(result), 1)
        parsed = json.loads(result[0][1])
        self.assertEqual(parsed, ["Hi", "There"])


class TestMetadata(TestCase):
    def test_extracts_session_id(self):
        run = _make_run(extra={"metadata": {"session_id": "sess-123"}})
        result = list(metadata(run))
        self.assertEqual(result, [(SESSION_ID_KEY, "sess-123")])

    def test_extracts_conversation_id(self):
        run = _make_run(extra={"metadata": {"conversation_id": "conv-456"}})
        result = list(metadata(run))
        self.assertEqual(result, [(SESSION_ID_KEY, "conv-456")])

    def test_extracts_thread_id(self):
        run = _make_run(extra={"metadata": {"thread_id": "thread-789"}})
        result = list(metadata(run))
        self.assertEqual(result, [(SESSION_ID_KEY, "thread-789")])

    def test_returns_empty_on_no_extra(self):
        run = _make_run(extra=None)
        self.assertEqual(list(metadata(run)), [])


class TestOutputMessages(TestCase):
    def test_extracts_from_generations(self):
        outputs = {
            "generations": [[{"message": {"content": "Response", "role": "assistant"}}]],
        }
        result = list(output_messages(outputs))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], GEN_AI_OUTPUT_MESSAGES_KEY)

    def test_returns_empty_on_none(self):
        self.assertEqual(list(output_messages(None)), [])

    def test_extracts_response_id(self):
        outputs = {
            "type": "LLMResult",
            "llm_output": {"id": "resp-123"},
            "generations": [[{"message": {"content": "Hi"}}]],
        }
        result = dict(output_messages(outputs))
        self.assertIn("resp-123", str(result))


class TestLlmProvider(TestCase):
    def test_extracts_provider(self):
        extra = {"metadata": {"ls_provider": "OpenAI"}}
        result = list(llm_provider(extra))
        self.assertEqual(result, [(GEN_AI_PROVIDER_NAME_KEY, "openai")])

    def test_returns_empty_on_none(self):
        self.assertEqual(list(llm_provider(None)), [])


class TestModelName(TestCase):
    def test_from_llm_output(self):
        outputs = {"llm_output": {"model_name": "gpt-4"}}
        result = list(model_name(outputs, None))
        self.assertEqual(result, [(GEN_AI_REQUEST_MODEL_KEY, "gpt-4")])

    def test_from_metadata(self):
        extra = {"metadata": {"ls_model_name": "gpt-3.5-turbo"}}
        result = list(model_name(None, extra))
        self.assertEqual(result, [(GEN_AI_REQUEST_MODEL_KEY, "gpt-3.5-turbo")])

    def test_from_invocation_params(self):
        extra = {"invocation_params": {"model_name": "claude-3"}}
        result = list(model_name(None, extra))
        self.assertEqual(result, [(GEN_AI_REQUEST_MODEL_KEY, "claude-3")])

    def test_returns_empty_on_none(self):
        self.assertEqual(list(model_name(None, None)), [])


class TestTokenCounts(TestCase):
    def test_extracts_token_counts(self):
        outputs = {
            "llm_output": {
                "token_usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                }
            }
        }
        result = dict(token_counts(outputs))
        self.assertEqual(result[GEN_AI_USAGE_INPUT_TOKENS_KEY], 10)
        self.assertEqual(result[GEN_AI_USAGE_OUTPUT_TOKENS_KEY], 20)

    def test_returns_empty_on_none(self):
        self.assertEqual(list(token_counts(None)), [])


class TestInvocationParameters(TestCase):
    def test_extracts_tools(self):
        run = _make_run(
            run_type="llm",
            extra={"invocation_params": {"tools": [{"name": "get_weather"}]}},
        )
        result = list(invocation_parameters(run))
        self.assertEqual(len(result), 1)
        self.assertIn("get_weather", result[0][1])

    def test_skips_non_llm(self):
        run = _make_run(run_type="chain", extra={"invocation_params": {"tools": []}})
        self.assertEqual(list(invocation_parameters(run)), [])


class TestFunctionCalls(TestCase):
    def test_extracts_function_call(self):
        outputs = {
            "generations": [
                [
                    {
                        "message": {
                            "kwargs": {
                                "additional_kwargs": {
                                    "function_call": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "NYC"}',
                                    }
                                }
                            }
                        }
                    }
                ]
            ]
        }
        result = dict(function_calls(outputs))
        self.assertEqual(result[GEN_AI_TOOL_NAME_KEY], "get_weather")
        self.assertEqual(result[GEN_AI_TOOL_TYPE_KEY], "function")

    def test_returns_empty_on_none(self):
        self.assertEqual(list(function_calls(None)), [])


class TestTools(TestCase):
    def test_extracts_tool_info(self):
        run = _make_run(
            run_type="tool",
            serialized={"name": "calculator", "description": "Does math"},
            inputs={"input": "2+2"},
            outputs={"output": "4"},
            extra={"tool_call_id": "tc-1"},
        )
        result = dict(tools(run))
        self.assertEqual(result[GEN_AI_TOOL_NAME_KEY], "calculator")
        self.assertEqual(result[GEN_AI_TOOL_DESCRIPTION_KEY], "Does math")
        self.assertEqual(result[GEN_AI_TOOL_TYPE_KEY], "extension")
        self.assertEqual(result[GEN_AI_TOOL_ARGS_KEY], "2+2")
        self.assertEqual(result[GEN_AI_TOOL_CALL_RESULT_KEY], "4")
        self.assertEqual(result[GEN_AI_TOOL_CALL_ID_KEY], "tc-1")

    def test_skips_non_tool(self):
        run = _make_run(run_type="llm", serialized={"name": "calc"})
        self.assertEqual(list(tools(run)), [])


class TestChainNodeMessages(TestCase):
    def test_extracts_messages_from_dict(self):
        data = {"messages": [{"content": "Hello", "role": "human"}]}
        result = list(chain_node_messages(data, GEN_AI_INPUT_MESSAGES_KEY))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], GEN_AI_INPUT_MESSAGES_KEY)
        self.assertIn("human: Hello", result[0][1])

    def test_returns_empty_on_none(self):
        self.assertEqual(list(chain_node_messages(None, GEN_AI_INPUT_MESSAGES_KEY)), [])

    def test_returns_empty_on_no_messages(self):
        self.assertEqual(list(chain_node_messages({"other": 1}, GEN_AI_INPUT_MESSAGES_KEY)), [])


class TestAddOperationType(TestCase):
    def test_llm_type(self):
        run = _make_run(run_type="llm")
        result = dict(add_operation_type(run))
        self.assertEqual(result[GEN_AI_OPERATION_NAME_KEY], CHAT_OPERATION_NAME)

    def test_chat_model_type(self):
        run = _make_run(run_type="chat_model")
        result = dict(add_operation_type(run))
        self.assertEqual(result[GEN_AI_OPERATION_NAME_KEY], CHAT_OPERATION_NAME)

    def test_tool_type(self):
        run = _make_run(run_type="tool")
        result = dict(add_operation_type(run))
        self.assertEqual(result[GEN_AI_OPERATION_NAME_KEY], EXECUTE_TOOL_OPERATION_NAME)

    def test_chain_type_returns_empty(self):
        run = _make_run(run_type="chain")
        self.assertEqual(list(add_operation_type(run)), [])


# ---- Agent I/O extractors ---------------------------------------------------


class TestInvokeAgentInputMessage(TestCase):
    def test_extracts_human_message(self):
        inputs = {"messages": [{"role": "human", "content": "What is 2+2?"}]}
        result = list(invoke_agent_input_message(inputs))
        self.assertEqual(result, [(GEN_AI_INPUT_MESSAGES_KEY, "What is 2+2?")])

    def test_extracts_from_nested_list(self):
        inputs = {"messages": [[{"role": "human", "content": "Hello"}]]}
        result = list(invoke_agent_input_message(inputs))
        self.assertEqual(result, [(GEN_AI_INPUT_MESSAGES_KEY, "Hello")])

    def test_returns_empty_on_none(self):
        self.assertEqual(list(invoke_agent_input_message(None)), [])


class TestInvokeAgentOutputMessage(TestCase):
    def test_extracts_ai_message(self):
        outputs = {"messages": [{"role": "ai", "content": "The answer is 4"}]}
        result = list(invoke_agent_output_message(outputs))
        self.assertEqual(result, [(GEN_AI_OUTPUT_MESSAGES_KEY, "The answer is 4")])

    def test_returns_empty_on_none(self):
        self.assertEqual(list(invoke_agent_output_message(None)), [])

    def test_extracts_last_ai_message(self):
        outputs = {
            "messages": [
                {"role": "ai", "content": "First"},
                {"role": "human", "content": "Again"},
                {"role": "ai", "content": "Second"},
            ]
        }
        result = list(invoke_agent_output_message(outputs))
        self.assertEqual(result, [(GEN_AI_OUTPUT_MESSAGES_KEY, "Second")])


# ---- Agent metadata extractors -----------------------------------------------


class TestExtractAgentMetadata(TestCase):
    def test_extracts_from_metadata(self):
        run = _make_run(
            extra={"metadata": {"agent_name": "TravelBot", "agent_id": "a-1", "agent_description": "Helps travel"}},
        )
        result = dict(extract_agent_metadata(run))
        self.assertEqual(result[GEN_AI_AGENT_NAME_KEY], "TravelBot")
        self.assertEqual(result[GEN_AI_AGENT_ID_KEY], "a-1")
        self.assertEqual(result[GEN_AI_AGENT_DESCRIPTION_KEY], "Helps travel")

    def test_extracts_from_serialized(self):
        run = _make_run(
            extra=None,
            serialized={"name": "MyAgent"},
        )
        result = dict(extract_agent_metadata(run))
        self.assertEqual(result[GEN_AI_AGENT_NAME_KEY], "MyAgent")

    def test_skips_langgraph_name(self):
        run = _make_run(extra=None, serialized={"name": "LangGraph"})
        result = dict(extract_agent_metadata(run))
        self.assertNotIn(GEN_AI_AGENT_NAME_KEY, result)


class TestExtractSessionInfo(TestCase):
    def test_extracts_session_id(self):
        run = _make_run(extra={"metadata": {"session_id": "s-1"}})
        result = dict(extract_session_info(run))
        self.assertEqual(result[SESSION_ID_KEY], "s-1")

    def test_extracts_conversation_id(self):
        run = _make_run(extra={"metadata": {"conversation_id": "c-1"}})
        result = dict(extract_session_info(run))
        self.assertIn(GEN_AI_CONVERSATION_ID_KEY, result)
        self.assertEqual(result[GEN_AI_CONVERSATION_ID_KEY], "c-1")

    def test_returns_empty_on_no_metadata(self):
        run = _make_run(extra=None)
        self.assertEqual(list(extract_session_info(run)), [])


# ---- build_llm_invocation ---------------------------------------------------


class TestBuildLlmInvocation(TestCase):
    def test_builds_invocation_with_model(self):
        run = _make_run(
            run_type="llm",
            outputs={"llm_output": {"model_name": "gpt-4"}},
            extra={"metadata": {"ls_provider": "OpenAI"}},
            inputs=None,
        )
        inv = build_llm_invocation(run)
        self.assertEqual(inv.request_model, "gpt-4")
        self.assertEqual(inv.provider, "openai")
        self.assertEqual(inv.operation_name, CHAT_OPERATION_NAME)

    def test_builds_invocation_with_tokens(self):
        run = _make_run(
            run_type="llm",
            outputs={
                "llm_output": {"token_usage": {"prompt_tokens": 10, "completion_tokens": 20}},
                "generations": [],
            },
            extra=None,
            inputs=None,
        )
        inv = build_llm_invocation(run)
        self.assertEqual(inv.input_tokens, 10)
        self.assertEqual(inv.output_tokens, 20)

    def test_builds_invocation_minimal(self):
        run = _make_run(run_type="llm", outputs=None, extra=None, inputs=None)
        inv = build_llm_invocation(run)
        self.assertEqual(inv.operation_name, CHAT_OPERATION_NAME)
        self.assertIsNone(inv.request_model)
