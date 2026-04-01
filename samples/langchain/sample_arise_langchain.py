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

configure_azure_monitor(connection_string="InstrumentationKey=...") # TODO: This will be replaced with the opentelemetry distro

LangChainInstrumentor().instrument()

# If using Azure OpenAI endpoint and API KEY
endpoint = "<AZURE_OPENAI_ENDPOINT>"
model_name = "gpt-4.1"
api_key = "<AZURE_OPENAI_API_KEY>"

# Otherwise, set the env variable OPENAI_API_KEY

image_url = "<IMAGE_URL>"

model = ChatOpenAI(model=model_name, api_key=api_key, base_url=endpoint) # Do not include api_key and base_url if using the OPENAI_API_KEY environment variable
image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")

message = HumanMessage(
    content=[
        {"type": "text", "text": "describe this image"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}", "detail": "low"},
        },
    ],
)

if __name__ == "__main__":
    response = model.invoke([message])
    print(response.content)