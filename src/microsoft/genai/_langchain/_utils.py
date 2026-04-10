# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Data extraction functions for LangChain runs → OpenTelemetry span attributes."""

import datetime
import json
import logging
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from copy import deepcopy
from enum import Enum
from threading import RLock
from typing import Any, Generic, TypeVar, cast

from langchain_core.messages import BaseMessage
from langchain_core.tracers.schemas import Run
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_AGENT_DESCRIPTION,
    GEN_AI_AGENT_ID,
    GEN_AI_AGENT_NAME,
    GEN_AI_CONVERSATION_ID,
    GEN_AI_INPUT_MESSAGES,
    GEN_AI_OPERATION_NAME,
    GEN_AI_OUTPUT_MESSAGES,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_RESPONSE_FINISH_REASONS,
    GEN_AI_RESPONSE_ID,
    GEN_AI_SYSTEM_INSTRUCTIONS,
    GEN_AI_TOOL_CALL_ARGUMENTS,
    GEN_AI_TOOL_CALL_ID,
    GEN_AI_TOOL_CALL_RESULT,
    GEN_AI_TOOL_DESCRIPTION,
    GEN_AI_TOOL_NAME,
    GEN_AI_TOOL_TYPE,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    GenAiOperationNameValues,
)
from opentelemetry.semconv.attributes.server_attributes import SERVER_ADDRESS, SERVER_PORT
from opentelemetry.util.genai.utils import gen_ai_json_dumps
from opentelemetry.util.genai.types import (
    InputMessage,
    LLMInvocation,
    OutputMessage,
    Text,
    ToolCall,
)
from opentelemetry.util.types import AttributeValue
from wrapt import ObjectProxy

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ---- Core utilities ----------------------------------------------------------


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """JSON serializer that tolerates non-serializable LangChain objects.

    Prefer ``gen_ai_json_dumps`` for OTel-compliant attribute values.
    This wrapper adds ``default=str`` for LangChain data that may contain
    UUIDs, datetime objects, or other non-JSON-native types.
    """
    return gen_ai_json_dumps(obj, default=str, **kwargs)


def as_utc_nano(dt: datetime.datetime) -> int:
    return int(dt.astimezone(datetime.timezone.utc).timestamp() * 1_000_000_000)


KeyType = TypeVar("KeyType")
ValueType = TypeVar("ValueType")

# pylint: disable=too-many-branches, abstract-method, too-many-return-statements
# pylint: disable=broad-exception-caught
def get_first_value(mapping: Mapping[KeyType, ValueType], keys: Iterable[KeyType]) -> ValueType | None:
    if not hasattr(mapping, "get"):
        return None
    return next(
        (value for key in keys if (value := mapping.get(key)) is not None),
        None,
    )


def stop_on_exception(
    wrapped: Callable[..., Iterator[tuple[str, Any]]],
) -> Callable[..., Iterator[tuple[str, Any]]]:
    def wrapper(*args: Any, **kwargs: Any) -> Iterator[tuple[str, Any]]:
        try:
            yield from wrapped(*args, **kwargs)
        except Exception:
            logger.exception("Failed to get attribute.")

    return wrapper


@stop_on_exception
def flatten(key_values: Iterable[tuple[str, Any]]) -> Iterator[tuple[str, AttributeValue]]:
    for key, value in key_values:
        if value is None:
            continue
        if isinstance(value, Mapping):
            for sub_key, sub_value in flatten(value.items()):
                yield f"{key}.{sub_key}", sub_value
        elif isinstance(value, list) and any(isinstance(item, Mapping) for item in value):
            for index, sub_value in enumerate(value):
                if sub_value is None:
                    continue
                if isinstance(sub_value, Mapping):
                    for sub_key, flattened_sub_value in flatten(sub_value.items()):
                        yield f"{key}.{index}.{sub_key}", flattened_sub_value
                else:
                    if isinstance(sub_value, Enum):
                        sub_value = sub_value.value
                    yield f"{key}.{index}", sub_value
        else:
            if isinstance(value, Enum):
                value = value.value
            yield key, value


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class DictWithLock(ObjectProxy, Generic[K, V]):  # type: ignore
    def __init__(self, wrapped: dict[str, V] | None = None) -> None:
        super().__init__(wrapped or {})
        self._self_lock = RLock()

    def get(self, key: K) -> V | None:
        with self._self_lock:
            return cast(V | None, self.__wrapped__.get(key))

    def pop(self, key: K, *args: Any) -> V | None:
        with self._self_lock:
            return cast(V | None, self.__wrapped__.pop(key, *args))

    def __getitem__(self, key: K) -> V:
        with self._self_lock:
            return cast(V, super().__getitem__(key))

    def __setitem__(self, key: K, value: V) -> None:
        with self._self_lock:
            super().__setitem__(key, value)

    def __delitem__(self, key: K) -> None:
        with self._self_lock:
            super().__delitem__(key)


# ---- Semantic convention aliases (kept for readability) ----------------------

INVOKE_AGENT_OPERATION_NAME = GenAiOperationNameValues.INVOKE_AGENT.value
EXECUTE_TOOL_OPERATION_NAME = GenAiOperationNameValues.EXECUTE_TOOL.value
CHAT_OPERATION_NAME = GenAiOperationNameValues.CHAT.value

# Re-export canonical constants under short names for use by tracer.py
GEN_AI_OPERATION_NAME_KEY = GEN_AI_OPERATION_NAME
GEN_AI_REQUEST_MODEL_KEY = GEN_AI_REQUEST_MODEL
GEN_AI_RESPONSE_FINISH_REASONS_KEY = GEN_AI_RESPONSE_FINISH_REASONS
GEN_AI_RESPONSE_ID_KEY = GEN_AI_RESPONSE_ID
GEN_AI_USAGE_INPUT_TOKENS_KEY = GEN_AI_USAGE_INPUT_TOKENS
GEN_AI_USAGE_OUTPUT_TOKENS_KEY = GEN_AI_USAGE_OUTPUT_TOKENS
GEN_AI_PROVIDER_NAME_KEY = GEN_AI_PROVIDER_NAME
GEN_AI_SYSTEM_INSTRUCTIONS_KEY = GEN_AI_SYSTEM_INSTRUCTIONS
GEN_AI_INPUT_MESSAGES_KEY = GEN_AI_INPUT_MESSAGES
GEN_AI_OUTPUT_MESSAGES_KEY = GEN_AI_OUTPUT_MESSAGES
GEN_AI_AGENT_NAME_KEY = GEN_AI_AGENT_NAME
GEN_AI_AGENT_ID_KEY = GEN_AI_AGENT_ID
GEN_AI_AGENT_DESCRIPTION_KEY = GEN_AI_AGENT_DESCRIPTION
GEN_AI_CONVERSATION_ID_KEY = GEN_AI_CONVERSATION_ID
SERVER_ADDRESS_KEY = SERVER_ADDRESS
SERVER_PORT_KEY = SERVER_PORT

# Tool execution constants
GEN_AI_TOOL_CALL_ID_KEY = GEN_AI_TOOL_CALL_ID
GEN_AI_TOOL_NAME_KEY = GEN_AI_TOOL_NAME
GEN_AI_TOOL_DESCRIPTION_KEY = GEN_AI_TOOL_DESCRIPTION
GEN_AI_TOOL_ARGS_KEY = GEN_AI_TOOL_CALL_ARGUMENTS
GEN_AI_TOOL_CALL_RESULT_KEY = GEN_AI_TOOL_CALL_RESULT
GEN_AI_TOOL_TYPE_KEY = GEN_AI_TOOL_TYPE

SESSION_ID_KEY = "microsoft.session.id"


# ---- Internal helpers --------------------------------------------------------

IGNORED_EXCEPTION_PATTERNS = [
    r"^Command\(",
    r"^ParentCommand\(",
]

LANGCHAIN_SESSION_ID = "session_id"
LANGCHAIN_CONVERSATION_ID = "conversation_id"
LANGCHAIN_THREAD_ID = "thread_id"


@stop_on_exception
def prompts(inputs: Mapping[str, Any] | None) -> Iterator[tuple[str, list[str]]]:
    if not inputs:
        return
    if not isinstance(inputs, Mapping):
        return
    if p := inputs.get("prompts"):
        yield GEN_AI_SYSTEM_INSTRUCTIONS_KEY, p


@stop_on_exception
def input_messages(
    inputs: Mapping[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    if not inputs:
        return
    if not isinstance(inputs, Mapping):
        return
    if not (multiple_messages := inputs.get("messages")):
        return
    if not isinstance(multiple_messages, Iterable):
        return
    if not (first_messages := next(iter(multiple_messages), None)):
        return
    contents: list[str] = []
    if isinstance(first_messages, list):
        for message_data in first_messages:
            if isinstance(message_data, BaseMessage):
                if hasattr(message_data, "content") and message_data.content:
                    contents.append(str(message_data.content))
            elif hasattr(message_data, "get"):
                if content := message_data.get("content"):
                    contents.append(str(content))
                elif kwargs := message_data.get("kwargs"):
                    if hasattr(kwargs, "get") and (content := kwargs.get("content")):
                        contents.append(str(content))
    elif isinstance(first_messages, BaseMessage):
        if hasattr(first_messages, "content") and first_messages.content:
            contents.append(str(first_messages.content))
    elif hasattr(first_messages, "get"):
        if content := first_messages.get("content"):
            contents.append(str(content))
    elif isinstance(first_messages, Sequence) and len(first_messages) == 2:
        _role, content = first_messages
        contents.append(str(content))
    if contents:
        yield GEN_AI_INPUT_MESSAGES_KEY, safe_json_dumps(contents)


@stop_on_exception
def metadata(run: Run) -> Iterator[tuple[str, str]]:
    if not run.extra or not (meta := run.extra.get("metadata")):
        return
    if not isinstance(meta, Mapping):
        return
    if session_id := (
        meta.get(LANGCHAIN_SESSION_ID) or meta.get(LANGCHAIN_CONVERSATION_ID) or meta.get(LANGCHAIN_THREAD_ID)
    ):
        yield SESSION_ID_KEY, session_id


@stop_on_exception
def output_messages(
    outputs: Mapping[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    if not outputs:
        return
    if not isinstance(outputs, Mapping):
        return
    output_type = outputs.get("type")
    if output_type and output_type.lower() == "llmresult":
        llm_output = outputs.get("llm_output")
        if llm_output and hasattr(llm_output, "get"):
            response_id = llm_output.get("id")
            if response_id:
                yield GEN_AI_RESPONSE_ID_KEY, response_id
    if not (multiple_generations := outputs.get("generations")):
        return
    if not isinstance(multiple_generations, Iterable):
        return
    if not (first_generations := next(iter(multiple_generations), None)):
        return
    if not isinstance(first_generations, Iterable):
        return
    contents: list[str] = []
    for generation in first_generations:
        if not isinstance(generation, Mapping):
            continue
        if message_data := generation.get("message"):
            if isinstance(message_data, BaseMessage):
                if hasattr(message_data, "content") and message_data.content:
                    contents.append(str(message_data.content))
            elif hasattr(message_data, "get"):
                if content := message_data.get("content"):
                    contents.append(str(content))
                elif kwargs := message_data.get("kwargs"):
                    if hasattr(kwargs, "get") and (content := kwargs.get("content")):
                        contents.append(str(content))
    if contents:
        yield GEN_AI_OUTPUT_MESSAGES_KEY, safe_json_dumps(contents)


@stop_on_exception
def invocation_parameters(run: Run) -> Iterator[tuple[str, str]]:
    if run.run_type.lower() != "llm":
        return
    if not (extra := run.extra):
        return
    if not isinstance(extra, Mapping):
        return
    if inv_params := extra.get("invocation_params"):
        if not isinstance(inv_params, Mapping):
            return
        tool_list = inv_params.get("tools", [])
        for idx, tool in enumerate(tool_list):
            yield f"{GEN_AI_TOOL_ARGS_KEY}.{idx}", safe_json_dumps(tool)


@stop_on_exception
def llm_provider(extra: Mapping[str, Any] | None) -> Iterator[tuple[str, str]]:
    if not extra:
        return
    if (meta := extra.get("metadata")) and (ls_provider := meta.get("ls_provider")):
        yield GEN_AI_PROVIDER_NAME_KEY, ls_provider.lower()


@stop_on_exception
def model_name(
    outputs: Mapping[str, Any] | None,
    extra: Mapping[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    if outputs and hasattr(outputs, "get") and (llm_output := outputs.get("llm_output")) and hasattr(llm_output, "get"):
        for key in ("model_name", "model"):
            if name := str(llm_output.get(key) or "").strip():
                yield GEN_AI_REQUEST_MODEL_KEY, name
                return
    if not extra:
        return
    if not isinstance(extra, Mapping):
        return
    if (
        (meta := extra.get("metadata"))
        and hasattr(meta, "get")
        and (ls_model_name := str(meta.get("ls_model_name") or "").strip())
    ):
        yield GEN_AI_REQUEST_MODEL_KEY, ls_model_name
        return
    if not (inv_params := extra.get("invocation_params")):
        return
    for key in ("model_name", "model"):
        if name := inv_params.get(key):
            yield GEN_AI_REQUEST_MODEL_KEY, name
            return


@stop_on_exception
def token_counts(outputs: Mapping[str, Any] | None) -> Iterator[tuple[str, int]]:
    if not (token_usage := _parse_token_usage(outputs)):
        return
    for attribute_name, keys in [
        (GEN_AI_USAGE_INPUT_TOKENS_KEY, ("prompt_tokens", "input_tokens", "prompt_token_count")),
        (GEN_AI_USAGE_OUTPUT_TOKENS_KEY, ("completion_tokens", "output_tokens", "candidates_token_count")),
    ]:
        if (token_count := get_first_value(token_usage, keys)) is not None:
            yield attribute_name, token_count
    # OpenAI completion_tokens_details
    if (details := token_usage.get("completion_tokens_details")) is not None:
        if (token_count := get_first_value(details, ("reasoning_tokens",))) is not None:
            yield GEN_AI_RESPONSE_FINISH_REASONS_KEY, token_count
    # langchain_core UsageMetadata
    for attribute_name, details_key, keys in [  # type: ignore[assignment]
        (GEN_AI_USAGE_INPUT_TOKENS_KEY, None, ("input_tokens",)),
        (GEN_AI_USAGE_OUTPUT_TOKENS_KEY, None, ("output_tokens",)),
        (GEN_AI_RESPONSE_FINISH_REASONS_KEY, "output_token_details", ("reasoning",)),
    ]:
        details = token_usage.get(details_key) if details_key else token_usage
        if details is not None:
            if (token_count := get_first_value(details, keys)) is not None:
                yield attribute_name, token_count


def _parse_token_usage(outputs: Mapping[str, Any] | None) -> Any:
    if (
        outputs
        and hasattr(outputs, "get")
        and (llm_output := outputs.get("llm_output"))
        and hasattr(llm_output, "get")
        and (token_usage := get_first_value(llm_output, ("token_usage", "usage")))
    ):
        return token_usage
    return None


@stop_on_exception
def function_calls(outputs: Mapping[str, Any] | None) -> Iterator[tuple[str, str]]:
    if not outputs:
        return
    if not isinstance(outputs, Mapping):
        return
    try:
        fc = deepcopy(outputs["generations"][0][0]["message"]["kwargs"]["additional_kwargs"]["function_call"])
    except Exception:
        return
    if not isinstance(fc, dict):
        return
    yield GEN_AI_OPERATION_NAME_KEY, EXECUTE_TOOL_OPERATION_NAME
    yield GEN_AI_TOOL_TYPE_KEY, "function"
    name = fc.get("name")
    if isinstance(name, str):
        yield GEN_AI_TOOL_NAME_KEY, name
    desc = fc.get("description")
    if isinstance(desc, str):
        yield GEN_AI_TOOL_DESCRIPTION_KEY, desc
    call_id = fc.get("id")
    if isinstance(call_id, str):
        yield GEN_AI_TOOL_CALL_ID_KEY, call_id
    args = fc.get("arguments")
    if args is not None:
        if isinstance(args, str):
            try:
                args_json = safe_json_dumps(json.loads(args))
            except Exception:
                args_json = safe_json_dumps(args)
        else:
            args_json = safe_json_dumps(args)
        yield GEN_AI_TOOL_ARGS_KEY, args_json
    result = fc.get("result")
    if result is not None:
        yield GEN_AI_TOOL_CALL_RESULT_KEY, safe_json_dumps(result)


@stop_on_exception
def tools(run: Run) -> Iterator[tuple[str, str]]:
    if run.run_type.lower() != "tool":
        return
    if not (serialized := run.serialized):
        return
    if not isinstance(serialized, Mapping):
        return
    yield GEN_AI_TOOL_TYPE_KEY, "extension"
    if name := serialized.get("name"):
        yield GEN_AI_TOOL_NAME_KEY, name
    if description := serialized.get("description"):
        yield GEN_AI_TOOL_DESCRIPTION_KEY, description
    if run.extra and hasattr(run.extra, "get"):
        if tool_call_id := run.extra.get("tool_call_id"):
            yield GEN_AI_TOOL_CALL_ID_KEY, tool_call_id
    if run.inputs and hasattr(run.inputs, "get"):
        if input_val := run.inputs.get("input"):
            if isinstance(input_val, str):
                yield GEN_AI_TOOL_ARGS_KEY, input_val
            else:
                yield GEN_AI_TOOL_ARGS_KEY, safe_json_dumps(input_val)
    if run.outputs and hasattr(run.outputs, "get"):
        if result := run.outputs.get("output"):
            if isinstance(result, BaseMessage):
                result_content: str = str(result.content) if hasattr(result, "content") else str(result)
            elif hasattr(result, "content"):
                result_content = str(result.content)
            elif isinstance(result, str):
                result_content = result
            else:
                result_content = safe_json_dumps(result)
            yield GEN_AI_TOOL_CALL_RESULT_KEY, result_content


def chain_node_messages(
    data: Mapping[str, Any] | None,
    attr_key: str,
) -> Iterator[tuple[str, str]]:
    """Extract messages from a LangGraph chain node's inputs or outputs.

    Chain nodes typically store messages as ``{"messages": [BaseMessage, ...]}``.
    """
    if not data or not isinstance(data, Mapping):
        return
    messages = data.get("messages")
    if not messages or not isinstance(messages, list):
        return
    contents: list[str] = []
    for msg in messages:
        c = _langchain_content(msg)
        if c:
            role = _langchain_role(msg)
            contents.append(f"{role}: {c}")
    if contents:
        yield attr_key, safe_json_dumps(contents)


def add_operation_type(run: Run) -> Iterator[tuple[str, str]]:
    run_type = run.run_type.lower()
    if run_type in ("llm", "chat_model"):
        yield GEN_AI_OPERATION_NAME_KEY, CHAT_OPERATION_NAME
    elif run_type == "tool":
        yield GEN_AI_OPERATION_NAME_KEY, EXECUTE_TOOL_OPERATION_NAME


def build_llm_invocation(run: Run) -> LLMInvocation:
    """Build an ``LLMInvocation`` from a LangChain ``Run`` for LLM-type spans.

    This bridges LangChain's run data model to the canonical OTel GenAI
    data model so that ``_apply_llm_finish_attributes`` can be used.
    """
    inv = LLMInvocation(operation_name=CHAT_OPERATION_NAME)

    # --- Model name ---
    for _, val in model_name(run.outputs, run.extra):
        inv.request_model = val
        break

    # --- Provider ---
    for _, val in llm_provider(run.extra):
        inv.provider = val
        break

    # --- Token counts ---
    for key, val in token_counts(run.outputs):
        if key == GEN_AI_USAGE_INPUT_TOKENS_KEY:
            inv.input_tokens = val
        elif key == GEN_AI_USAGE_OUTPUT_TOKENS_KEY:
            inv.output_tokens = val

    # --- Response ID ---
    if run.outputs and isinstance(run.outputs, Mapping):
        llm_output = run.outputs.get("llm_output")
        if llm_output and hasattr(llm_output, "get"):
            if resp_id := llm_output.get("id"):
                inv.response_id = resp_id

    # --- Structured messages ---
    inv.system_instruction = _extract_system_instruction(run.inputs)  # type: ignore[assignment]
    inv.input_messages = _extract_structured_input_messages(run.inputs)
    inv.output_messages = _extract_structured_output_messages(run.outputs)

    return inv


def _langchain_role(message: Any) -> str:
    """Extract role from a LangChain message (BaseMessage or dict)."""
    if isinstance(message, BaseMessage):
        return str(getattr(message, "type", "unknown"))
    if hasattr(message, "get"):
        if role := message.get("role"):
            return str(role)
        if msg_type := message.get("type"):
            return str(msg_type)
        # Fallback: parse role from serialized id field (e.g. ["langchain", "schema", "HumanMessage"])
        if id_field := message.get("id"):
            if isinstance(id_field, list) and len(id_field) > 0:
                type_name = id_field[-1]
                if "Human" in type_name:
                    return "human"
                if "AI" in type_name or "Assistant" in type_name:
                    return "ai"
                if "System" in type_name:
                    return "system"
    return "unknown"


def _langchain_content(message: Any) -> str | None:
    """Extract text content from a LangChain message."""
    if isinstance(message, BaseMessage):
        c = getattr(message, "content", None)
        return str(c) if c else None
    if hasattr(message, "get"):
        if c := message.get("content"):
            return str(c)
        if kwargs := message.get("kwargs"):
            if hasattr(kwargs, "get") and (c := kwargs.get("content")):
                return str(c)
    return None


def _langchain_tool_calls(message: Any) -> list[ToolCall]:
    """Extract tool calls from a LangChain message into OTel ToolCall parts."""
    calls: list[ToolCall] = []
    raw_calls = None
    if isinstance(message, BaseMessage):
        raw_calls = getattr(message, "tool_calls", None)
        if not raw_calls:
            raw_calls = getattr(message, "additional_kwargs", {}).get("tool_calls")
    elif hasattr(message, "get"):
        raw_calls = message.get("tool_calls")
        if not raw_calls:
            kwargs = message.get("kwargs") or {}
            raw_calls = kwargs.get("tool_calls")
            if not raw_calls:
                additional = kwargs.get("additional_kwargs") or {}
                raw_calls = additional.get("tool_calls")
    if not raw_calls or not isinstance(raw_calls, list):
        return calls
    for tc in raw_calls:
        if not isinstance(tc, Mapping):
            continue
        name = tc.get("name") or ""
        fn = tc.get("function")
        if isinstance(fn, Mapping):
            name = fn.get("name") or name
            args = fn.get("arguments")
        else:
            args = tc.get("args")
        if args is not None and not isinstance(args, str):
            args = safe_json_dumps(args)
        calls.append(ToolCall(arguments=args or "", name=name, id=tc.get("id")))
    return calls


def _extract_system_instruction(inputs: Mapping[str, Any] | None) -> list[Text]:
    """Extract system instruction / prompts as structured Text parts."""
    if not inputs or not isinstance(inputs, Mapping):
        return []
    if p := inputs.get("prompts"):
        if isinstance(p, list):
            return [Text(content=str(item)) for item in p if item]
        if isinstance(p, str):
            return [Text(content=p)]
    return []


def _extract_structured_input_messages(
    inputs: Mapping[str, Any] | None,
) -> list[InputMessage]:
    """Convert LangChain input messages to OTel ``InputMessage`` list."""
    if not inputs or not isinstance(inputs, Mapping):
        return []
    multiple_messages = inputs.get("messages")
    if not multiple_messages or not isinstance(multiple_messages, Iterable):
        return []
    first_messages = next(iter(multiple_messages), None)
    if first_messages is None:
        return []
    # Normalise to a list
    if not isinstance(first_messages, list):
        first_messages = [first_messages]
    results: list[InputMessage] = []
    for msg in first_messages:
        role = _langchain_role(msg)
        parts: list[Any] = []
        content = _langchain_content(msg)
        if content:
            parts.append(Text(content=content))
        parts.extend(_langchain_tool_calls(msg))
        if parts:
            results.append(InputMessage(role=role, parts=parts))
    return results


def _extract_structured_output_messages(
    outputs: Mapping[str, Any] | None,
) -> list[OutputMessage]:
    """Convert LangChain output generations to OTel ``OutputMessage`` list."""
    if not outputs or not isinstance(outputs, Mapping):
        return []
    multiple_generations = outputs.get("generations")
    if not multiple_generations or not isinstance(multiple_generations, Iterable):
        return []
    first_generations = next(iter(multiple_generations), None)
    if not first_generations or not isinstance(first_generations, Iterable):
        return []
    results: list[OutputMessage] = []
    for generation in first_generations:
        if not isinstance(generation, Mapping):
            continue
        message_data = generation.get("message")
        if message_data is None:
            # Fallback: generation may have text directly
            if text := generation.get("text"):
                results.append(OutputMessage(role="assistant", parts=[Text(content=str(text))], finish_reason="stop"))
            continue
        role = _langchain_role(message_data)
        parts: list[Any] = []
        content = _langchain_content(message_data)
        if content:
            parts.append(Text(content=content))
        parts.extend(_langchain_tool_calls(message_data))
        # Try to get finish_reason from generation_info
        finish_reason = "stop"
        gen_info = generation.get("generation_info")
        if isinstance(gen_info, Mapping):
            finish_reason = gen_info.get("finish_reason") or "stop"
        if parts:
            results.append(OutputMessage(role=role, parts=parts, finish_reason=finish_reason))
    return results


@stop_on_exception
def invoke_agent_input_message(
    inputs: Mapping[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    if not inputs:
        return
    if not isinstance(inputs, Mapping):
        return
    messages = inputs.get("messages")
    if not messages:
        return
    if isinstance(messages, list) and len(messages) > 0:
        first_item = messages[0]
        if isinstance(first_item, list):
            messages = first_item
    if isinstance(messages, list):
        for message in messages:
            role = _langchain_role(message)
            if role and role.lower() in ("human", "user"):
                content = _langchain_content(message)
                if content:
                    yield GEN_AI_INPUT_MESSAGES_KEY, content
                    return
        if len(messages) > 0:
            content = _langchain_content(messages[0])
            if content:
                yield GEN_AI_INPUT_MESSAGES_KEY, content


@stop_on_exception
def invoke_agent_output_message(
    outputs: Mapping[str, Any] | None,
) -> Iterator[tuple[str, str]]:
    if not outputs:
        return
    if not isinstance(outputs, Mapping):
        return
    messages = outputs.get("messages")
    if not messages:
        return
    if isinstance(messages, list) and len(messages) > 0:
        first_item = messages[0]
        if isinstance(first_item, list):
            messages = first_item
    if isinstance(messages, list):
        for message in reversed(messages):
            role = _langchain_role(message)
            if role and role.lower() in ("ai", "assistant"):
                content = _langchain_content(message)
                if content and isinstance(content, str) and content.strip():
                    yield GEN_AI_OUTPUT_MESSAGES_KEY, content
                    return


@stop_on_exception
def extract_agent_metadata(run: Run) -> Iterator[tuple[str, str]]:
    """Extract agent name and description from run metadata or serialized data."""
    # From run metadata
    if run.extra and isinstance(run.extra, dict):
        meta = run.extra.get("metadata")
        if isinstance(meta, dict):
            if name := meta.get("agent_name"):
                yield GEN_AI_AGENT_NAME_KEY, name
            if agent_id := meta.get("agent_id"):
                yield GEN_AI_AGENT_ID_KEY, agent_id
            if desc := meta.get("agent_description"):
                yield GEN_AI_AGENT_DESCRIPTION_KEY, desc
            return
    # From serialized graph
    if run.serialized and isinstance(run.serialized, dict):
        if name := run.serialized.get("name"):
            if name != "LangGraph":
                yield GEN_AI_AGENT_NAME_KEY, name


@stop_on_exception
def extract_session_info(run: Run) -> Iterator[tuple[str, str]]:
    """Extract session_id and conversation_id from run metadata."""
    if not run.extra or not isinstance(run.extra, dict):
        return
    meta = run.extra.get("metadata")
    if not isinstance(meta, dict):
        return
    for key in (LANGCHAIN_SESSION_ID, LANGCHAIN_CONVERSATION_ID, LANGCHAIN_THREAD_ID):
        if sid := meta.get(key):
            yield SESSION_ID_KEY, sid
            break
    if conv_id := meta.get(LANGCHAIN_CONVERSATION_ID):
        yield GEN_AI_CONVERSATION_ID_KEY, conv_id
