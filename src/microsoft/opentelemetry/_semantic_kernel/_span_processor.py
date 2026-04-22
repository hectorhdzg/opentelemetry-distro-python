# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from microsoft.opentelemetry.a365.core.constants import GEN_AI_OPERATION_NAME_KEY
from microsoft.opentelemetry.a365.core.inference_operation_type import InferenceOperationType
from microsoft.opentelemetry.a365.core.utils import extract_model_name
from opentelemetry import context as context_api
from opentelemetry.sdk.trace import ReadableSpan, Span
from opentelemetry.sdk.trace.export import SpanProcessor


class SemanticKernelSpanProcessor(SpanProcessor):
    """SpanProcessor for Semantic Kernel.

    Intercepts ``chat.*`` spans on start, renames them to
    ``"chat <model_name>"`` and sets ``gen_ai.operation.name``.
    """

    def __init__(self, service_name: str | None = None):
        self.service_name = service_name

    def on_start(self, span: Span, parent_context: context_api.Context | None = None) -> None:
        if span.name.startswith("chat."):
            operation_name = InferenceOperationType.CHAT.value.lower()
            span.set_attribute(GEN_AI_OPERATION_NAME_KEY, operation_name)
            model_name = extract_model_name(span.name)
            if model_name:
                span.update_name(f"{operation_name} {model_name}")
            else:
                span.update_name(operation_name)

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
