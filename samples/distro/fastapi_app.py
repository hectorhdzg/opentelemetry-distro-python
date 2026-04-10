# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import uvicorn
from logging import getLogger, INFO
from microsoft.opentelemetry import use_microsoft_opentelemetry

use_microsoft_opentelemetry(
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


@app.get("/items/{item_id}")
async def get_item(item_id: int):
    logger.info("Fetching item", extra={"item.id": item_id})
    return {"item_id": item_id, "name": f"Item {item_id}"}


@app.get("/error")
async def error_endpoint():
    logger.error("Intentional error triggered")
    raise ValueError("Something went wrong!")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
