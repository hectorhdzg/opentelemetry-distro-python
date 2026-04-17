# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Agent365 exporter integration for the Microsoft OpenTelemetry Distro."""

from microsoft.opentelemetry.a365.core.exporters.utils import (  # noqa: F401
    A365Handlers,
    create_a365_components,
    is_a365_enabled,
)

__all__ = [
    "A365Handlers",
    "create_a365_components",
    "is_a365_enabled",
]
