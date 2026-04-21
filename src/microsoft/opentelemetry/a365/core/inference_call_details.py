# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from dataclasses import dataclass

from microsoft.opentelemetry.a365.core.inference_operation_type import InferenceOperationType
from microsoft.opentelemetry.a365.core.models.service_endpoint import ServiceEndpoint


@dataclass
# pylint: disable=too-many-instance-attributes
class InferenceCallDetails:
    """Details of an inference call for generative AI operations."""

    operationName: InferenceOperationType
    model: str
    providerName: str
    inputTokens: int | None = None
    outputTokens: int | None = None
    finishReasons: list[str] | None = None
    thoughtProcess: str | None = None
    endpoint: ServiceEndpoint | None = None
