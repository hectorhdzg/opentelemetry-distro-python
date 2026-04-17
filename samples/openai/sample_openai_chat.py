# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Sample: OpenAI and Azure OpenAI Chat Completions with Microsoft OpenTelemetry Distro.

Prerequisites:
    pip install microsoft-opentelemetry openai

Environment variables:
    APPLICATIONINSIGHTS_CONNECTION_STRING  – Azure Monitor connection string
    OPENAI_API_KEY                         – OpenAI API key
    AZURE_OPENAI_ENDPOINT                  – Azure OpenAI endpoint (e.g. https://<resource>.openai.azure.com/)
    AZURE_OPENAI_API_KEY                   – Azure OpenAI API key
    AZURE_OPENAI_DEPLOYMENT                – Azure OpenAI deployment/model name
"""

import os

from openai import OpenAI, AzureOpenAI
from microsoft.opentelemetry import use_microsoft_opentelemetry

# Connection string can also be passed directly:
# azure_monitor_connection_string="InstrumentationKey=..."
use_microsoft_opentelemetry(
    azure_monitor_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
)

# --- OpenAI ---
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", ""),
)

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": "You are a concise assistant. Answer in one or two sentences."},
        {"role": "user", "content": "What is OpenTelemetry?"},
    ],
)

print("OpenAI response:", response.choices[0].message.content)

# --- Azure OpenAI ---
azure_client = AzureOpenAI(
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
    api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
    api_version="2024-06-01",
)

azure_response = azure_client.chat.completions.create(
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    messages=[
        {"role": "system", "content": "You are a concise assistant. Answer in one or two sentences."},
        {"role": "user", "content": "What is OpenTelemetry?"},
    ],
)

print("Azure OpenAI response:", azure_response.choices[0].message.content)

input()