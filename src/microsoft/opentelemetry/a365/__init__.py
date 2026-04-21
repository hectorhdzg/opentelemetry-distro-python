# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Agent365 observability for the Microsoft OpenTelemetry Distro.

Use ``use_microsoft_opentelemetry(enable_a365=True)`` to enable A365
telemetry.  Import scope classes and data models from
``microsoft.opentelemetry.a365.core``.

The symbols below are internal — kept only for backward compatibility
with existing tests.
"""

from microsoft.opentelemetry.a365.core.exporters.utils import (  # noqa: F401
    A365Handlers,
    create_a365_components,
    is_a365_enabled,
)

# Nothing is public — all integration goes through the distro entry point.
__all__: list[str] = []
