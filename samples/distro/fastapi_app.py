# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
import uvicorn
from logging import getLogger, INFO
from microsoft.opentelemetry import use_microsoft_opentelemetry

# Connection string can also be passed directly:
# azure_monitor_connection_string="InstrumentationKey=..."
use_microsoft_opentelemetry(
    azure_monitor_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
    logger_name=__name__,
)

logger = getLogger(__name__)
logger.setLevel(INFO)

from fastapi import FastAPI  # pylint: disable=wrong-import-position

app = FastAPI()


@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello World"}


# Exceptions that are raised within the request are automatically captured
@app.get("/exception")
async def exception():
    raise Exception("Hit an exception")  # pylint: disable=broad-exception-raised


# Set the OTEL_PYTHON_EXCLUDED_URLS environment variable to "http://127.0.0.1:8000/exclude"
# Telemetry from this endpoint will not be captured due to excluded_urls config above
@app.get("/exclude")
async def exclude():
    return {"message": "Telemetry was not captured"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
