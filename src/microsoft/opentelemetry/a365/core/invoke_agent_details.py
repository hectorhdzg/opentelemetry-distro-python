# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# Data class for invoke agent scope details.

from dataclasses import dataclass

from microsoft.opentelemetry.a365.core.gen_ai_request_parameters import GenAiRequestParameters
from microsoft.opentelemetry.a365.core.gen_ai_response_parameters import GenAiResponseParameters
from microsoft.opentelemetry.a365.core.models.service_endpoint import ServiceEndpoint


@dataclass
class InvokeAgentScopeDetails:
    """Scope-level configuration for agent invocation tracing."""

    endpoint: ServiceEndpoint | None = None
    request_parameters: GenAiRequestParameters | None = None
    response_parameters: GenAiResponseParameters | None = None
