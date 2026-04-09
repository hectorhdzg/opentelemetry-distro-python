# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License in the project root for
# license information.
# -------------------------------------------------------------------------

# Extend path so the exporter subpackage (azure-monitor-opentelemetry-exporter)
# is discoverable when this package is installed in editable/development mode.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from microsoft.opentelemetry._azure_monitor._configure import configure_azure_monitor

from ._version import VERSION

__all__ = [
    "configure_azure_monitor",
]
__version__ = VERSION
