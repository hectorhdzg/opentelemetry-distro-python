# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""LangChain BaseTracer that emits OpenTelemetry spans."""

import logging
import re
from collections import OrderedDict
from collections.abc import Iterator
from itertools import chain
from threading import RLock
from typing import (
    TYPE_CHECKING,
    Any,
    cast,
)
from uuid import UUID

from langchain_core.tracers import BaseTracer
from langchain_core.tracers.schemas import Run
from opentelemetry import context as context_api
from opentelemetry import trace as trace_api
from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    get_value,
)
from opentelemetry.trace import Span
from opentelemetry.util.genai.span_utils import (
    _apply_error_attributes,
    _apply_llm_finish_attributes,
    _maybe_emit_llm_event,
)
from opentelemetry.util.genai.types import Error, LLMInvocation
from opentelemetry.util.types import AttributeValue

from microsoft.genai._langchain._utils import (
    DictWithLock,
    as_utc_nano,
    build_llm_invocation,
    flatten,
    safe_json_dumps,
    IGNORED_EXCEPTION_PATTERNS,
    INVOKE_AGENT_OPERATION_NAME,
    EXECUTE_TOOL_OPERATION_NAME,
    GEN_AI_AGENT_DESCRIPTION_KEY,
    GEN_AI_AGENT_ID_KEY,
    GEN_AI_AGENT_NAME_KEY,
    GEN_AI_INPUT_MESSAGES_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    GEN_AI_OUTPUT_MESSAGES_KEY,
    GEN_AI_REQUEST_MODEL_KEY,
    SERVER_ADDRESS_KEY,
    SERVER_PORT_KEY,
    add_operation_type,
    chain_node_messages,
    extract_agent_metadata,
    extract_session_info,
    function_calls,
    input_messages,
    invocation_parameters,
    invoke_agent_input_message,
    invoke_agent_output_message,
    metadata,
    model_name,
    output_messages,
    prompts,
    tools,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


CONTEXT_ATTRIBUTES = (
    "session.id",
    "user.id",
    "metadata",
    "tag.tags",
    "llm.prompt_template.template",
    "llm.prompt_template.variables",
    "llm.prompt_template.version",
)


# pylint: disable=broad-exception-caught
class LangChainTracer(BaseTracer):  # pylint: disable=too-many-ancestors, too-many-instance-attributes
    _MAX_TRACKED_RUNS = 10000

    __slots__ = (
        "_tracer",
        "_separate_trace_from_runtime_context",
        "_agent_config",
        "_agent_run_ids",
        "_agent_content",
        "_agent_wrapper_spans",
        "_spans_by_run",
        "_event_logger",
    )

    def __init__(
        self,
        tracer: trace_api.Tracer,
        separate_trace_from_runtime_context: bool,
        *args: Any,
        agent_config: dict[str, Any] | None = None,
        event_logger: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if TYPE_CHECKING:
            assert self.run_map  # type: ignore[has-type]
        self.run_map = DictWithLock[str, Run](self.run_map)  # type: ignore[has-type,misc]
        self._tracer = tracer
        self._separate_trace_from_runtime_context = separate_trace_from_runtime_context
        self._agent_config: dict[str, Any] = agent_config or {}
        self._agent_run_ids: set[UUID] = set()
        self._agent_content: dict[UUID, dict[str, Any]] = {}
        self._agent_wrapper_spans: dict[UUID, Span] = {}
        self._spans_by_run: OrderedDict[UUID, Span] = OrderedDict()
        self._event_logger = event_logger
        self._lock = RLock()  # type: ignore[misc]

    def get_span(self, run_id: UUID) -> Span | None:
        with self._lock:
            return self._spans_by_run.get(run_id)

    @staticmethod
    def _cap_ordered_dict(d: OrderedDict, max_size: int) -> None:
        while len(d) > max_size:
            d.popitem(last=False)

    def _start_trace(self, run: Run) -> None:
        self.run_map[str(run.id)] = run
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return
        with self._lock:
            parent_context = (
                trace_api.set_span_in_context(parent)
                if (parent_run_id := run.parent_run_id) and (parent := self._spans_by_run.get(parent_run_id))
                else (context_api.Context() if self._separate_trace_from_runtime_context else None)
            )
        start_time_utc_nano = as_utc_nano(run.start_time)

        is_agent = self._is_agent_run(run)

        # Determine span name based on run type
        if is_agent:
            agent_name = self._resolve_agent_name(run)
            span_name = (
                f"{INVOKE_AGENT_OPERATION_NAME} {agent_name}"
                if agent_name
                else f"{INVOKE_AGENT_OPERATION_NAME} {run.name}"
            )
        elif run.run_type.lower() == "tool":
            span_name = f"{EXECUTE_TOOL_OPERATION_NAME} {run.name}"
        else:
            span_name = run.name

        # For agent runs, always create a wrapper span.
        # The wrapper gets the agent name (from config or metadata).
        # The inner span shows the framework name (e.g. "invoke_agent LangGraph").
        wrapper_span: Span | None = None
        if is_agent:
            agent_name = self._resolve_agent_name(run)
            wrapper_label = agent_name or run.name
            wrapper_span = self._tracer.start_span(
                name=f"{INVOKE_AGENT_OPERATION_NAME} {wrapper_label}",
                context=parent_context,
                start_time=start_time_utc_nano,
            )
            parent_context = trace_api.set_span_in_context(wrapper_span)
            # Resolve framework name for the inner span (e.g. "LangGraph")
            framework_name = self._resolve_framework_name(run)
            span_name = f"{INVOKE_AGENT_OPERATION_NAME} {framework_name}"

        span = self._tracer.start_span(
            name=span_name,
            context=parent_context,
            start_time=start_time_utc_nano,
        )

        # For agent spans, set immediate attributes and init content aggregation
        if is_agent:
            # Use wrapper span (if present) as the agent span for attributes
            agent_span = wrapper_span or span
            with self._lock:
                self._agent_run_ids.add(run.id)
                self._agent_content[run.id] = {
                    "input_messages": [],
                    "output_messages": [],
                    "model": None,
                }
                if wrapper_span is not None:
                    self._agent_wrapper_spans[run.id] = wrapper_span
            agent_span.set_attribute(GEN_AI_OPERATION_NAME_KEY, INVOKE_AGENT_OPERATION_NAME)
            if agent_name:
                agent_span.set_attribute(GEN_AI_AGENT_NAME_KEY, agent_name)
            agent_id = self._agent_config.get("agent_id")
            if agent_id:
                agent_span.set_attribute(GEN_AI_AGENT_ID_KEY, agent_id)
            agent_desc = self._agent_config.get("agent_description")
            if agent_desc:
                agent_span.set_attribute(GEN_AI_AGENT_DESCRIPTION_KEY, agent_desc)
            agent_span.set_attributes(dict(flatten(extract_agent_metadata(run))))
            server_addr = self._agent_config.get("server_address")
            if server_addr:
                agent_span.set_attribute(SERVER_ADDRESS_KEY, server_addr)
            server_port = self._agent_config.get("server_port")
            if server_port:
                agent_span.set_attribute(SERVER_PORT_KEY, server_port)
            agent_span.set_attributes(dict(flatten(extract_session_info(run))))

        with self._lock:
            self._spans_by_run[run.id] = span
            self._cap_ordered_dict(self._spans_by_run, self._MAX_TRACKED_RUNS)

    def _end_trace(self, run: Run) -> None:
        self.run_map.pop(str(run.id), None)
        if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
            return

        is_agent = run.id in self._agent_run_ids

        # Aggregate child content into parent agent span
        if not is_agent and run.parent_run_id:
            self._aggregate_into_parent(run)

        with self._lock:
            span = self._spans_by_run.pop(run.id, None)
            wrapper_span = self._agent_wrapper_spans.pop(run.id, None) if is_agent else None

        end_time_utc_nano = as_utc_nano(run.end_time) if run.end_time else None

        if span:
            invocation: LLMInvocation | None = None
            try:
                if is_agent and wrapper_span:
                    # Two-span agent: update inner span as chain, finalize wrapper as agent
                    _update_span(span, run)
                elif is_agent:
                    # Single-span agent: finalize directly
                    self._finalize_agent_span(span, run)
                else:
                    invocation = _update_span(span, run)
            except Exception:
                logger.exception("Failed to update span with run data.")
            # Emit OTel GenAI event for LLM spans (respects env-var config)
            if invocation is not None and self._event_logger is not None:
                try:
                    _maybe_emit_llm_event(self._event_logger, span, invocation)
                except Exception:
                    logger.debug("Failed to emit LLM event.", exc_info=True)
            span.end(end_time=end_time_utc_nano)

        # Finalize and end wrapper span after the inner span
        if wrapper_span:
            try:
                self._finalize_agent_span(wrapper_span, run)
            except Exception:
                logger.exception("Failed to finalize agent wrapper span.")
            wrapper_span.end(end_time=end_time_utc_nano)

        # Clean up agent tracking
        if is_agent:
            with self._lock:
                self._agent_run_ids.discard(run.id)
                self._agent_content.pop(run.id, None)

    def _persist_run(self, run: Run) -> None:
        pass

    def on_llm_error(self, error: BaseException, *args: Any, run_id: UUID, **kwargs: Any) -> Run:
        with self._lock:
            span = self._spans_by_run.get(run_id)
        if span:
            span.record_exception(error)
            _apply_error_attributes(span, Error(message=str(error), type=type(error)))
        return super().on_llm_error(error, *args, run_id=run_id, **kwargs)

    def on_chain_error(self, error: BaseException, *args: Any, run_id: UUID, **kwargs: Any) -> Run:
        with self._lock:
            span = self._spans_by_run.get(run_id)
        if span:
            span.record_exception(error)
            _apply_error_attributes(span, Error(message=str(error), type=type(error)))
        return super().on_chain_error(error, *args, run_id=run_id, **kwargs)

    def on_retriever_error(self, error: BaseException, *args: Any, run_id: UUID, **kwargs: Any) -> Run:
        with self._lock:
            span = self._spans_by_run.get(run_id)
        if span:
            span.record_exception(error)
            _apply_error_attributes(span, Error(message=str(error), type=type(error)))
        return super().on_retriever_error(error, *args, run_id=run_id, **kwargs)

    def on_tool_error(self, error: BaseException, *args: Any, run_id: UUID, **kwargs: Any) -> Run:
        with self._lock:
            span = self._spans_by_run.get(run_id)
        if span:
            span.record_exception(error)
            _apply_error_attributes(span, Error(message=str(error), type=type(error)))
        return super().on_tool_error(error, *args, run_id=run_id, **kwargs)

    # ---- Agent detection & aggregation ----------------------------------------

    @staticmethod
    def _is_agent_like_chain(run: Run) -> bool:
        """Check whether a chain matches agent-like criteria (LangGraph, etc.)."""
        if run.run_type != "chain":
            return False
        if run.name == "LangGraph":
            return True
        serialized = run.serialized or {}
        graph_type = serialized.get("graph", {}).get("type") if isinstance(serialized.get("graph"), dict) else None
        if graph_type in ("CompiledGraph", "StateGraph"):
            return True
        if "agent" in run.name.lower():
            return True
        # LangChain create_agent sets lc_agent_name in metadata
        if run.extra and isinstance(run.extra, dict):
            meta = run.extra.get("metadata")
            if isinstance(meta, dict) and meta.get("lc_agent_name"):
                return True
        return False

    def _is_agent_run(self, run: Run) -> bool:
        """Detect whether a LangChain run should be the top-level agent span."""
        if not self._is_agent_like_chain(run):
            return False
        # Don't nest agents — if a parent is already an agent, this is internal
        if run.parent_run_id and run.parent_run_id in self._agent_run_ids:
            return False
        return True

    def _resolve_agent_name(self, run: Run) -> str | None:
        """Resolve agent name from config override, run metadata, or run name."""
        # 1. Explicit config override
        if name := self._agent_config.get("agent_name"):
            return str(name)
        # 2. From run metadata (agent_name or lc_agent_name)
        if run.extra and isinstance(run.extra, dict):
            meta = run.extra.get("metadata")
            if isinstance(meta, dict):
                if name := meta.get("agent_name"):
                    return str(name)
                if name := meta.get("lc_agent_name"):
                    return str(name)
        # 3. From serialized graph name
        if run.serialized and isinstance(run.serialized, dict):
            if name := run.serialized.get("name"):
                if name != "LangGraph":  # avoid generic name
                    return str(name)
        # 4. Run name itself if it's not just "LangGraph"
        if run.name and run.name != "LangGraph":
            return str(run.name)
        return None

    @staticmethod
    def _resolve_framework_name(run: Run) -> str:
        """Resolve the framework/graph type name for the inner agent span."""
        serialized = run.serialized or {}
        graph = serialized.get("graph")
        if isinstance(graph, dict):
            graph_type = graph.get("type")
            if graph_type in ("CompiledGraph", "StateGraph"):
                return "LangGraph"
        if serialized.get("name") and serialized["name"] != run.name:
            return str(serialized["name"])
        return "LangGraph"

    def _aggregate_into_parent(self, run: Run) -> None:  # pylint: disable=too-many-branches
        """Aggregate child run content into the parent agent span's content."""
        parent_id = run.parent_run_id
        if not parent_id:
            return
        # Walk up to find the nearest agent ancestor
        agent_id = self._find_agent_ancestor(run)
        if not agent_id:
            return

        run_type = run.run_type.lower()

        with self._lock:
            content = self._agent_content.get(agent_id)
            if not content:
                return

            # Capture model name from LLM runs
            if run_type in ("llm", "chat_model") and not content.get("model"):
                for _, m in model_name(run.outputs, run.extra):
                    content["model"] = m
                    break

            # Capture input messages from LLM runs (first LLM child wins)
            if run_type in ("llm", "chat_model") and not content["input_messages"]:
                if run.inputs:
                    for _, val in input_messages(run.inputs):
                        content["input_messages"].append(val)
                        break
                    if not content["input_messages"]:
                        for _, val in prompts(run.inputs):
                            if isinstance(val, list) and val:
                                content["input_messages"].append(str(val[0]))
                            elif isinstance(val, str):
                                content["input_messages"].append(val)
                            break

            # Capture output messages from LLM runs (last LLM child wins)
            if run_type in ("llm", "chat_model") and run.outputs:
                for _, val in output_messages(run.outputs):
                    content["output_messages"] = [val]  # overwrite with latest
                    break

            # Capture tool results
            if run_type == "tool" and run.outputs:
                if output := run.outputs.get("output"):
                    result_str = output if isinstance(output, str) else safe_json_dumps(output)
                    content["output_messages"].append(result_str)

    def _find_agent_ancestor(self, run: Run) -> UUID | None:
        """Walk up the run tree to find the nearest agent ancestor run_id."""
        run_map = self.run_map
        current_id: UUID | None = run.parent_run_id
        while current_id:
            if current_id in self._agent_run_ids:
                return current_id
            parent_run = run_map.get(str(current_id))
            current_id = parent_run.parent_run_id if parent_run else None
        return None

    def _finalize_agent_span(self, span: Span, run: Run) -> None:
        """Apply aggregated content and status to an invoke_agent span."""
        # Set status
        if run.error is None or any(re.match(pattern, run.error) for pattern in IGNORED_EXCEPTION_PATTERNS):
            span.set_status(trace_api.StatusCode.OK)
        else:
            _apply_error_attributes(span, Error(message=run.error, type=Exception))

        span.set_attributes(dict(get_attributes_from_context()))

        with self._lock:
            content = self._agent_content.get(run.id) or {}

        # Set aggregated model
        if model := content.get("model"):
            span.set_attribute(GEN_AI_REQUEST_MODEL_KEY, model)

        # Set aggregated input messages
        if msgs := content.get("input_messages"):
            span.set_attribute(GEN_AI_INPUT_MESSAGES_KEY, safe_json_dumps(msgs))
        else:
            # Fall back to run's own inputs
            for _, val in invoke_agent_input_message(run.inputs):
                span.set_attribute(GEN_AI_INPUT_MESSAGES_KEY, val)
                break

        # Set aggregated output messages
        if msgs := content.get("output_messages"):
            span.set_attribute(GEN_AI_OUTPUT_MESSAGES_KEY, safe_json_dumps(msgs))
        else:
            # Fall back to run's own outputs
            for _, val in invoke_agent_output_message(run.outputs):
                span.set_attribute(GEN_AI_OUTPUT_MESSAGES_KEY, val)
                break

        # Set metadata (session_id, etc.)
        span.set_attributes(dict(flatten(metadata(run))))


def get_attributes_from_context() -> Iterator[tuple[str, AttributeValue]]:
    for ctx_attr in CONTEXT_ATTRIBUTES:
        if (val := get_value(ctx_attr)) is not None:
            yield ctx_attr, cast(AttributeValue, val)


def _update_span(span: Span, run: Run) -> LLMInvocation | None:
    """Update a non-agent span with run data.

    Returns the ``LLMInvocation`` for LLM runs (used for event emission
    and future metrics), or ``None`` for other run types.
    """
    # If there is no error or if there is an agent control exception, set the span to OK
    if run.error is None or any(re.match(pattern, run.error) for pattern in IGNORED_EXCEPTION_PATTERNS):
        span.set_status(trace_api.StatusCode.OK)
    else:
        _apply_error_attributes(span, Error(message=run.error, type=Exception))

    span.set_attributes(dict(get_attributes_from_context()))

    run_type = run.run_type.lower()

    # --- LLM runs: use LLMInvocation + _apply_llm_finish_attributes ---
    if run_type in ("llm", "chat_model"):
        invocation = build_llm_invocation(run)
        _apply_llm_finish_attributes(span, invocation)
        # Extras not covered by LLMInvocation
        span.set_attributes(
            dict(
                flatten(
                    chain(
                        invocation_parameters(run),
                        function_calls(run.outputs),
                        metadata(run),
                    )
                )
            )
        )
        return invocation

    # --- Tool / chain / other runs ---
    span.set_attributes(
        dict(
            flatten(
                chain(
                    add_operation_type(run),
                    chain_node_messages(run.inputs, GEN_AI_INPUT_MESSAGES_KEY),
                    chain_node_messages(run.outputs, GEN_AI_OUTPUT_MESSAGES_KEY),
                    tools(run),
                    metadata(run),
                )
            )
        )
    )
    return None
