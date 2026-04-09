# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -------------------------------------------------------------------------

"""Microsoft OpenTelemetry Distro for Python.

Provides a single entry-point — :func:`use_microsoft_opentelemetry` —
that initialises OpenTelemetry global providers (tracing, metrics, logging)
and optionally configures Azure Monitor as an exporter.
"""

from microsoft.opentelemetry._distro import use_microsoft_opentelemetry

from ._version import VERSION

__all__ = [
    "use_microsoft_opentelemetry",
]
__version__ = VERSION
