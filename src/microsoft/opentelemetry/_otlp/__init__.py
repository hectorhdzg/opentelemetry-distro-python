# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -------------------------------------------------------------------------

from microsoft.opentelemetry._otlp.handler import (
    is_otlp_enabled,
    create_otlp_components,
    OtlpHandlers,
)

__all__ = [
    "is_otlp_enabled",
    "create_otlp_components",
    "OtlpHandlers",
]
