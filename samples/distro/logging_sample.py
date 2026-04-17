# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
from logging import getLogger, DEBUG

from microsoft.opentelemetry import use_microsoft_opentelemetry

# Connection string can also be passed directly:
# azure_monitor_connection_string="InstrumentationKey=..."
use_microsoft_opentelemetry(
    azure_monitor_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
    logger_name="my_app",
)

logger = getLogger("my_app")
logger.setLevel(DEBUG)

# Basic log levels — all of these will be exported as trace telemetry
logger.debug("Debug-level detail for troubleshooting")
logger.info("Application started successfully")
logger.warning("Cache miss for key 'user-session-42'")
logger.error("Failed to connect to database after 3 retries")

# Structured logging with extra attributes
logger.info(
    "User login",
    extra={
        "user.id": "user-789",
        "auth.method": "oauth2",
    },
)

# Logging an exception — the traceback is captured automatically
try:
    result = 1 / 0
except ZeroDivisionError:
    logger.exception("Math error during calculation")

# Custom event via the microsoft.custom_event.name attribute
logger.info(
    "Order placed",
    extra={
        "microsoft.custom_event.name": "OrderPlaced",
        "order.id": "ORD-001",
        "order.total": 99.99,
    },
)

print("Log records sent. Waiting for export...")
input()
