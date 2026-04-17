# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""OTel-standard BaseInstrumentor for LangChain.

Works with ``configure_azure_monitor`` auto-discovery via entry points
or can be used standalone:

    LangChainInstrumentor().instrument(tracer_provider=provider)
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Collection
from typing import Any
from uuid import UUID

import langchain_core
import langchain_core.callbacks
import langchain_core.runnables.config
import opentelemetry.trace as trace_api
from langchain_core.callbacks import BaseCallbackManager
from opentelemetry._logs import get_logger as get_otel_logger
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor  # type: ignore[attr-defined]
from opentelemetry.trace import Span
from wrapt import wrap_function_wrapper

from microsoft.opentelemetry._genai._langchain._tracer import LangChainTracer

logger = logging.getLogger(__name__)

_INSTRUMENTS: str = "langchain-core >= 0.2.0"


class LangChainInstrumentor(BaseInstrumentor):
    """Attaches a LangChainTracer to every new BaseCallbackManager."""

    def __init__(self) -> None:
        super().__init__()
        self._tracer: LangChainTracer | None = None
        self._original_cb_init: Callable[..., None] | None = None

    # ---- BaseInstrumentor API -------------------------------------------------

    def instrumentation_dependencies(self) -> Collection[str]:
        return (_INSTRUMENTS,)

    def _instrument(self, **kwargs: Any) -> None:
        tracer_provider = kwargs.get("tracer_provider")
        tracer = trace_api.get_tracer(
            __name__,
            tracer_provider=tracer_provider,
        )

        logger_provider = kwargs.get("logger_provider")
        event_logger = get_otel_logger(
            __name__,
            logger_provider=logger_provider,
        )

        agent_config = {
            "agent_name": kwargs.get("agent_name"),
            "agent_id": kwargs.get("agent_id"),
            "agent_description": kwargs.get("agent_description"),
            "server_address": kwargs.get("server_address"),
            "server_port": kwargs.get("server_port"),
        }

        self._tracer = LangChainTracer(
            tracer,
            bool(kwargs.get("separate_trace_from_runtime_context")),
            agent_config=agent_config,
            event_logger=event_logger,
        )

        self._original_cb_init = langchain_core.callbacks.BaseCallbackManager.__init__
        wrap_function_wrapper(
            module="langchain_core.callbacks",
            name="BaseCallbackManager.__init__",
            wrapper=_BaseCallbackManagerInit(self._tracer),
        )

    def _uninstrument(self, **kwargs: Any) -> None:
        if self._original_cb_init is not None:
            langchain_core.callbacks.BaseCallbackManager.__init__ = self._original_cb_init  # type: ignore[assignment]
        self._original_cb_init = None
        self._tracer = None

    # ---- Helpers --------------------------------------------------------------

    def get_span(self, run_id: UUID) -> Span | None:
        if not self._tracer:
            return None
        return self._tracer.get_span(run_id)

    def get_ancestors(self, run_id: UUID) -> list[Span]:
        if not self._tracer:
            return []
        run_map = getattr(self._tracer, "run_map", {}) or {}
        ancestors: list[Span] = []

        run = run_map.get(str(run_id))
        if not run:
            return ancestors

        ancestor_id = getattr(run, "parent_run_id", None)
        while ancestor_id:
            span = self.get_span(ancestor_id)
            if span:
                ancestors.append(span)
            run = run_map.get(str(ancestor_id))
            ancestor_id = getattr(run, "parent_run_id", None) if run else None

        return ancestors


class _BaseCallbackManagerInit:
    """Post-constructor hook that adds the tracer once (inheritable)."""

    __slots__ = ("_processor",)

    def __init__(self, processor: LangChainTracer):
        self._processor = processor

    def __call__(
        self,
        wrapped: Callable[..., None],
        instance: BaseCallbackManager,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        wrapped(*args, **kwargs)
        if not any(isinstance(h, type(self._processor)) for h in instance.inheritable_handlers):
            instance.add_handler(self._processor, inherit=True)


# ------------------------------ Convenience APIs ------------------------------


def _current_parent_run_id() -> UUID | None:
    try:
        config = langchain_core.runnables.config.var_child_runnable_config.get()
    except LookupError:
        return None
    if not isinstance(config, dict):
        return None
    for v in config.values():
        if isinstance(v, langchain_core.callbacks.BaseCallbackManager):
            if v.parent_run_id:
                return UUID(str(v.parent_run_id))
    return None


def get_current_span() -> Span | None:
    run_id = _current_parent_run_id()
    if not run_id:
        return None
    return LangChainInstrumentor().get_span(run_id)


def get_ancestor_spans() -> list[Span]:
    run_id = _current_parent_run_id()
    if not run_id:
        return []
    return LangChainInstrumentor().get_ancestors(run_id)
