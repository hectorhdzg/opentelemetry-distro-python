# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import base64
import httpx

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from azure.monitor.opentelemetry import configure_azure_monitor

from openinference.instrumentation.langchain import LangChainInstrumentor

configure_azure_monitor(  # Replace with the opentelemetry distro
    connection_string="InstrumentationKey=..."
)

LangChainInstrumentor().instrument()

# If using Azure OpenAI endpoint and API KEY
ENDPOINT = "<AZURE_OPENAI_ENDPOINT>"
MODEL_NAME = "gpt-4.1"
API_KEY = "<AZURE_OPENAI_API_KEY>"

# Otherwise, set the env variable OPENAI_API_KEY

IMAGE_URL = "<IMAGE_URL>"

model = ChatOpenAI(
    model=MODEL_NAME,
    api_key=API_KEY,
    base_url=ENDPOINT,  # Do not include api_key and base_url if using the OPENAI_API_KEY environment variable
)
image_data = base64.b64encode(httpx.get(IMAGE_URL).content).decode("utf-8")

message = HumanMessage(
    content=[
        {"type": "text", "text": "describe this image"},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_data}",
                "detail": "low",
            },
        },
    ],
)

if __name__ == "__main__":
    response = model.invoke([message])
    print(response.content)
