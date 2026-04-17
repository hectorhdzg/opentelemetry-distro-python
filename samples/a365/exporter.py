# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Sample: A365 Exporter with LangChain

Demonstrates A365 as an exporter with auto-instrumented LangChain operations.
The distro instruments LangChain automatically — all LLM calls, tool executions,
and agent runs produce OTel spans that flow through the A365 span processors.

A365 auto-enables when ENABLE_A365_OBSERVABILITY_EXPORTER=true is set.

Environment variables:
  OPENAI_API_KEY=<key>                         OpenAI API key
  ENABLE_A365_OBSERVABILITY_EXPORTER=true      Enable A365 HTTP exporter (required)
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from microsoft.opentelemetry import use_microsoft_opentelemetry


def get_token(agent_id: str, tenant_id: str) -> str | None:
    """Example token resolver. Replace with your actual auth logic."""
    return "example-bearer-token"


use_microsoft_opentelemetry(
    enable_a365=True,
    a365_token_resolver=get_token,
    a365_tenant_id="my-tenant",
    a365_agent_id="my-agent",
    enable_azure_monitor=False,
    instrumentation_options={
        "langchain": {"enabled": True},
    },
)


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    weather = {
        "seattle": "62°F, partly cloudy",
        "paris": "58°F, light rain",
        "tokyo": "72°F, sunny",
    }
    return weather.get(city.lower(), f"No weather data for {city}.")


def main():
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # Simple LLM call — automatically traced
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="What is the capital of France?"),
    ]
    result = llm.invoke(messages)
    print("LLM output:", result.content)

    # Agent with tools — all steps automatically traced
    from langchain.agents import create_agent

    agent = create_agent(
        llm,
        tools=[get_weather],
        system_prompt="You are a weather assistant. Use the tool to answer weather questions.",
        name="Weather_Agent",
    )

    agent_result = agent.invoke({"messages": [("human", "What's the weather in Seattle?")]})
    print("Agent output:", agent_result["messages"][-1].content)


if __name__ == "__main__":
    main()
