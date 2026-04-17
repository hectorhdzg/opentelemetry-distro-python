# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
import time

from opentelemetry import trace

from microsoft.opentelemetry import use_microsoft_opentelemetry

# Connection string can also be passed directly:
# azure_monitor_connection_string="InstrumentationKey=..."
use_microsoft_opentelemetry(
    azure_monitor_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
)

tracer = trace.get_tracer(__name__)

# Basic span
with tracer.start_as_current_span("hello-span") as span:
    span.set_attribute("user.id", "user-123")
    span.set_attribute("operation", "greeting")
    print("Inside hello-span")

# Nested spans (parent-child relationship)
with tracer.start_as_current_span("parent-operation") as parent:
    parent.set_attribute("step", "start")
    time.sleep(0.1)

    with tracer.start_as_current_span("child-db-query") as child:
        child.set_attribute("db.system", "postgresql")
        child.set_attribute("db.statement", "SELECT * FROM users WHERE id = ?")
        time.sleep(0.05)

    with tracer.start_as_current_span("child-http-call") as child:
        child.set_attribute("http.method", "GET")
        child.set_attribute("http.url", "https://example.com/api/data")
        child.set_attribute("http.status_code", 200)
        time.sleep(0.05)

# Span with events and status
with tracer.start_as_current_span("process-order") as span:
    span.add_event("order.received", {"order.id": "ORD-456"})
    try:
        # Simulate processing
        time.sleep(0.1)
        span.add_event("order.processed")
    except Exception as ex:  # pylint: disable=broad-exception-caught
        span.set_status(trace.StatusCode.ERROR, str(ex))
        span.record_exception(ex)

print("Traces sent. Waiting for export...")
input()
