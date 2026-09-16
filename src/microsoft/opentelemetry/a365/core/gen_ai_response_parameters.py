# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""GenAI response parameters for InvokeAgent telemetry."""

from dataclasses import dataclass
from typing import Sequence


@dataclass
class GenAiResponseParameters:
    """Optional GenAI response parameters recorded on InvokeAgent spans."""

    finish_reasons: Sequence[str] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_write_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
