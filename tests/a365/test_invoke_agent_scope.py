# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from typing import Any, cast

from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    GenAiRequestParameters,
    GenAiResponseParameters,
    InvokeAgentScope,
    InvokeAgentScopeDetails,
    Request,
    TextPart,
)
from microsoft.opentelemetry.a365.core.constants import SOURCE_NAME
from microsoft.opentelemetry.a365.core.opentelemetry_scope import OpenTelemetryScope
from opentelemetry.sdk.trace import TracerProvider


def _start_invoke_agent_scope(scope_details: InvokeAgentScopeDetails) -> InvokeAgentScope:
    return InvokeAgentScope.start(
        request=Request(),
        scope_details=scope_details,
        agent_details=AgentDetails(agent_id="agent-1"),
    )


def _span_attributes(scope: InvokeAgentScope) -> dict[str, object]:
    assert scope._span is not None
    span = cast(Any, scope._span)
    return dict(span.attributes)


def _string_attribute(attrs: dict[str, object], key: str) -> str:
    value = attrs[key]
    assert isinstance(value, str)
    return value


LEGACY_CACHE_CREATION_INPUT_TOKENS_KEY = ".".join(("gen_ai", "usage", "cache_creation", "input_tokens"))


def setup_function() -> None:
    import os

    os.environ["ENABLE_OBSERVABILITY"] = "true"
    provider = TracerProvider()
    OpenTelemetryScope._tracer = provider.get_tracer(SOURCE_NAME)
    setup_function.provider = provider  # type: ignore[attr-defined]


def teardown_function() -> None:
    import os

    provider = getattr(setup_function, "provider", None)
    if provider:
        provider.shutdown()
    OpenTelemetryScope._tracer = None
    os.environ.pop("ENABLE_OBSERVABILITY", None)


def test_invoke_agent_details_accepts_semantic_parameters() -> None:
    request = GenAiRequestParameters(model="gpt-4o", max_tokens=128)
    response = GenAiResponseParameters(input_tokens=10, output_tokens=4)
    details = InvokeAgentScopeDetails(
        request_parameters=request,
        response_parameters=response,
    )
    assert details.request_parameters is request
    assert details.response_parameters is response


def test_invoke_agent_scope_records_request_parameters() -> None:
    parameters = GenAiRequestParameters(
        model="gpt-4o",
        seed=42,
        choice_count=2,
        frequency_penalty=0.5,
        max_tokens=128,
        presence_penalty=0.25,
        stop_sequences=["stop", "halt"],
        temperature=0.7,
        top_p=0.9,
        data_source_id="data-source-1",
        output_type="json",
        system_instructions=[
            TextPart(content="Be concise."),
            TextPart(content="Return JSON."),
        ],
    )
    scope = _start_invoke_agent_scope(InvokeAgentScopeDetails(request_parameters=parameters))
    try:
        attrs = _span_attributes(scope)
        assert attrs["gen_ai.request.model"] == "gpt-4o"
        assert attrs["gen_ai.request.seed"] == 42
        assert attrs["gen_ai.request.choice.count"] == 2
        assert attrs["gen_ai.request.frequency_penalty"] == 0.5
        assert attrs["gen_ai.request.max_tokens"] == 128
        assert attrs["gen_ai.request.presence_penalty"] == 0.25
        assert attrs["gen_ai.request.stop_sequences"] == ("stop", "halt")
        assert attrs["gen_ai.request.temperature"] == 0.7
        assert attrs["gen_ai.request.top_p"] == 0.9
        assert attrs["gen_ai.data_source.id"] == "data-source-1"
        assert attrs["gen_ai.output.type"] == "json"
        assert json.loads(_string_attribute(attrs, "gen_ai.system_instructions")) == [
            {"content": "Be concise.", "type": "text"},
            {"content": "Return JSON.", "type": "text"},
        ]
    finally:
        scope.dispose()


def test_invoke_agent_scope_records_response_parameters_after_completion() -> None:
    scope = _start_invoke_agent_scope(InvokeAgentScopeDetails())
    try:
        scope.record_response_parameters(
            GenAiResponseParameters(
                finish_reasons=["stop"],
                input_tokens=10,
                output_tokens=4,
                cache_write_input_tokens=2,
                cache_read_input_tokens=1,
            )
        )
        attrs = _span_attributes(scope)
        assert attrs["gen_ai.response.finish_reasons"] == ("stop",)
        assert attrs["gen_ai.usage.input_tokens"] == 10
        assert attrs["gen_ai.usage.output_tokens"] == 4
        assert attrs["gen_ai.usage.cache_write.input_tokens"] == 2
        assert LEGACY_CACHE_CREATION_INPUT_TOKENS_KEY not in attrs
        assert attrs["gen_ai.usage.cache_read.input_tokens"] == 1
    finally:
        scope.dispose()


def test_invoke_agent_scope_omits_none_semantic_parameters() -> None:
    scope = _start_invoke_agent_scope(
        InvokeAgentScopeDetails(
            request_parameters=GenAiRequestParameters(model="gpt-4o"),
            response_parameters=GenAiResponseParameters(input_tokens=10),
        )
    )
    try:
        attrs = _span_attributes(scope)
        assert attrs["gen_ai.request.model"] == "gpt-4o"
        assert attrs["gen_ai.usage.input_tokens"] == 10
        assert "gen_ai.request.seed" not in attrs
        assert "gen_ai.request.stop_sequences" not in attrs
        assert "gen_ai.response.finish_reasons" not in attrs
        assert "gen_ai.usage.output_tokens" not in attrs
        assert "gen_ai.usage.cache_write.input_tokens" not in attrs
        assert LEGACY_CACHE_CREATION_INPUT_TOKENS_KEY not in attrs
        assert "gen_ai.usage.cache_read.input_tokens" not in attrs
        assert "gen_ai.system_instructions" not in attrs
    finally:
        scope.dispose()


def test_invoke_agent_scope_system_instructions_serialization_is_non_throwing() -> None:
    parameters = GenAiRequestParameters(
        system_instructions=[object()],  # type: ignore[list-item]
    )

    scope = _start_invoke_agent_scope(InvokeAgentScopeDetails(request_parameters=parameters))
    try:
        attrs = _span_attributes(scope)
        assert json.loads(_string_attribute(attrs, "gen_ai.system_instructions")) == [
            {
                "content": "[serialization failed: 1 instruction part]",
                "type": "text",
            }
        ]
    finally:
        scope.dispose()
