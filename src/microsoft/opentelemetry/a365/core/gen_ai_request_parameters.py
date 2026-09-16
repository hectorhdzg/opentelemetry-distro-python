# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""GenAI request parameters for InvokeAgent telemetry."""

from dataclasses import dataclass
from typing import Sequence

from microsoft.opentelemetry.a365.core.models.messages import TextPart


@dataclass
class GenAiRequestParameters:
    """Optional GenAI request parameters recorded on InvokeAgent spans."""

    model: str | None = None
    seed: int | None = None
    choice_count: int | None = None
    frequency_penalty: float | None = None
    max_tokens: int | None = None
    presence_penalty: float | None = None
    stop_sequences: Sequence[str] | None = None
    temperature: float | None = None
    top_p: float | None = None
    data_source_id: str | None = None
    output_type: str | None = None
    system_instructions: Sequence[TextPart] | None = None
