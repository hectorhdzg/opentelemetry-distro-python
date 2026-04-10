# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from logging import getLogger, INFO

from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
    azure_monitor_connection_string="InstrumentationKey=YOUR_INSTRUMENTATION_KEY",
    logger_name=__name__,
)

logger = getLogger(__name__)
logger.setLevel(INFO)

# You can send `customEvent` telemetry using a special `microsoft` attribute key through logging
# The name of the `customEvent` will correspond to the value of the attribute`
logger.info(
    "Hello World!",
    extra={
        "microsoft.custom_event.name": "test-custom-event-1",
        "additional_attrs": "genai",
    },
)

# You can also populate fields like client_Ip with attribute `client.address`
logger.info(
    "This entry will have a custom client_Ip",
    extra={
        "microsoft.custom_event.name": "test-custom-event-2",
        "client.address": "197.168.1.1",
    },
)

input()
