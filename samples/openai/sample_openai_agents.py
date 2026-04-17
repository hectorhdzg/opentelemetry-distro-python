# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Sample: OpenAI Agents SDK with Microsoft OpenTelemetry Distro.

Prerequisites:
    pip install microsoft-opentelemetry openai-agents

Environment variables:
    APPLICATIONINSIGHTS_CONNECTION_STRING  – Azure Monitor connection string
    OPENAI_API_KEY                         – OpenAI API key
    AZURE_OPENAI_ENDPOINT                  – Azure OpenAI endpoint
    AZURE_OPENAI_API_KEY                   – Azure OpenAI API key
"""

import os

from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
)
from openai import AsyncAzureOpenAI

from microsoft.opentelemetry import use_microsoft_opentelemetry

os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "SPAN_AND_EVENT")
os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental")
# Connection string can also be passed directly:
# azure_monitor_connection_string="InstrumentationKey=..."
use_microsoft_opentelemetry(
    azure_monitor_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", ""),
)

@function_tool
def get_weather(city: str) -> str:
    """Return a mock weather forecast for a city."""
    return f"The weather in {city} is sunny, 25°C."

# --- OpenAI ---
agent = Agent(
    name="Travel Concierge",
    instructions="You are a concise travel assistant. Answer in one or two sentences.",
    tools=[get_weather],
)

result = Runner.run_sync(agent, "What should I pack for Barcelona this weekend?")

# --- Azure OpenAI ---
ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
API_KEY = os.environ.get("AZURE_OPENAI_API_KEY", "")
API_VER = "2024-06-01"

def _make_azure_client() -> AsyncAzureOpenAI:
    return AsyncAzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version=API_VER,
    )

# Configure the openai-agents SDK to use the Azure OpenAI client.
# use_for_tracing=False so the SDK doesn't try to upload its own traces.
# set_default_openai_api("chat_completions") because Azure uses the
# Chat Completions API (not the newer Responses API).
set_default_openai_client(_make_azure_client(), use_for_tracing=False)
set_default_openai_api("chat_completions")

azure_agent = Agent(
    name="Travel Concierge",
    instructions="You are a concise travel assistant. Answer in one or two sentences.",
    tools=[get_weather],
)

result = Runner.run_sync(azure_agent, "What should I pack for Barcelona this weekend?")
print(result.final_output)

input()
