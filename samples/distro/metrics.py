# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
import time
import random

from opentelemetry import metrics

from microsoft.opentelemetry import use_microsoft_opentelemetry

# Connection string can also be passed directly:
# azure_monitor_connection_string="InstrumentationKey=..."
use_microsoft_opentelemetry(
    azure_monitor_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
)

meter = metrics.get_meter(__name__)

# Counter — monotonically increasing value (e.g. number of requests)
request_counter = meter.create_counter(
    name="app.requests",
    description="Total number of requests",
    unit="1",
)

# Histogram — distribution of values (e.g. request duration)
duration_histogram = meter.create_histogram(
    name="app.request.duration",
    description="Request processing duration",
    unit="ms",
)

# UpDownCounter — value that can increase or decrease (e.g. active connections)
active_connections = meter.create_up_down_counter(
    name="app.active_connections",
    description="Number of active connections",
    unit="1",
)

# Simulate some activity
for i in range(10):
    # Record a request
    request_counter.add(1, {"http.method": "GET", "http.route": "/api/items"})

    # Record request duration
    duration = random.uniform(10, 500)
    duration_histogram.record(duration, {"http.method": "GET", "http.route": "/api/items"})

    # Simulate connections opening and closing
    active_connections.add(1, {"server.address": "app-server-1"})
    time.sleep(0.05)
    if i % 3 == 0:
        active_connections.add(-1, {"server.address": "app-server-1"})

print("Metrics recorded. Waiting for export (metrics export every 60s by default)...")
input()
