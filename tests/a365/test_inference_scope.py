# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
from typing import Any, cast

from microsoft.opentelemetry.a365.core import (
    AgentDetails,
    InferenceCallDetails,
    InferenceOperationType,
    InferenceScope,
    Request,
    ServiceEndpoint,
)
from microsoft.opentelemetry.a365.core.constants import SOURCE_NAME
from microsoft.opentelemetry.a365.core.opentelemetry_scope import OpenTelemetryScope
from opentelemetry.sdk.trace import TracerProvider


def _span_attributes(scope: InferenceScope) -> dict[str, object]:
    assert scope._span is not None
    span = cast(Any, scope._span)
    return dict(span.attributes)


def setup_function() -> None:
    os.environ["ENABLE_OBSERVABILITY"] = "true"
    provider = TracerProvider()
    OpenTelemetryScope._tracer = provider.get_tracer(SOURCE_NAME)
    setup_function.provider = provider  # type: ignore[attr-defined]


def teardown_function() -> None:
    provider = getattr(setup_function, "provider", None)
    if provider:
        provider.shutdown()
    OpenTelemetryScope._tracer = None
    os.environ.pop("ENABLE_OBSERVABILITY", None)


def test_inference_scope_records_model_observation_attributes() -> None:
    scope = InferenceScope.start(
        Request(),
        InferenceCallDetails(
            operationName=InferenceOperationType.CHAT,
            model="gpt-4o",
            providerName="openai",
            inputTokens=100,
            outputTokens=25,
            responseModel="gpt-4o-2024-11-20",
            cacheReadInputTokens=12,
            cacheWriteInputTokens=7,
            endpoint=ServiceEndpoint(hostname="models.example", port=8443),
        ),
        AgentDetails(agent_id="agent-1"),
    )
    try:
        attrs = _span_attributes(scope)
        assert attrs["gen_ai.operation.name"] == "chat"
        assert attrs["gen_ai.request.model"] == "gpt-4o"
        assert attrs["gen_ai.response.model"] == "gpt-4o-2024-11-20"
        assert attrs["gen_ai.provider.name"] == "openai"
        assert attrs["gen_ai.usage.input_tokens"] == 100
        assert attrs["gen_ai.usage.output_tokens"] == 25
        assert attrs["gen_ai.usage.cache_read.input_tokens"] == 12
        assert attrs["gen_ai.usage.cache_write.input_tokens"] == 7
        assert attrs["server.address"] == "models.example"
        assert attrs["server.port"] == 8443
    finally:
        scope.dispose()


def test_inference_scope_records_canonical_operation_names() -> None:
    for operation_name, expected in (
        (InferenceOperationType.CHAT, "chat"),
        (InferenceOperationType.TEXT_COMPLETION, "text_completion"),
        (InferenceOperationType.GENERATE_CONTENT, "generate_content"),
    ):
        scope = InferenceScope.start(
            Request(),
            InferenceCallDetails(
                operationName=operation_name,
                model="gpt-4o",
                providerName="openai",
            ),
            AgentDetails(agent_id="agent-1"),
        )
        try:
            assert _span_attributes(scope)["gen_ai.operation.name"] == expected
            assert scope._span is not None
            assert cast(Any, scope._span).name == f"{expected} gpt-4o"
        finally:
            scope.dispose()


def test_inference_scope_records_late_response_details() -> None:
    scope = InferenceScope.start(
        Request(),
        InferenceCallDetails(
            operationName=InferenceOperationType.CHAT,
            model="gpt-4o",
            providerName="openai",
        ),
        AgentDetails(agent_id="agent-1"),
    )
    try:
        scope.record_response_model("gpt-4o-2024-11-20")
        scope.record_cache_read_input_tokens(11)
        scope.record_cache_write_input_tokens(6)
        attrs = _span_attributes(scope)
        assert attrs["gen_ai.response.model"] == "gpt-4o-2024-11-20"
        assert attrs["gen_ai.usage.cache_read.input_tokens"] == 11
        assert attrs["gen_ai.usage.cache_write.input_tokens"] == 6
    finally:
        scope.dispose()
