"""Travel planner with nested agents — coordinator delegates to specialist agents."""

import random
from uuid import uuid4

from azure.monitor.opentelemetry import configure_azure_monitor
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer

try:
    from langchain.agents import create_agent as create_react_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent

# If using Azure OpenAI endpoint and API KEY
ENDPOINT = "<AZURE_OPENAI_ENDPOINT>"
API_KEY = "<AZURE_OPENAI_API_KEY>"
MODEL_NAME = "gpt-4.1"

# Otherwise, set the env variable OPENAI_API_KEY

configure_azure_monitor(  # Replace with the opentelemetry distro
    connection_string="InstrumentationKey=...",
)

tracer = AzureAIOpenTelemetryTracer(name="travel_planner", provider_name="openai")


# --- Tools ---
@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for flights between two cities on a given date."""
    airline = random.choice(["SkyLine", "AeroJet", "CloudNine"])
    fare = random.randint(700, 1250)
    return f"{airline} non-stop {origin} -> {destination}, {date} 09:05, fare ${fare}"


@tool
def search_hotels(destination: str, check_in: str, check_out: str) -> str:
    """Search for hotels in a city for given dates."""
    hotel = random.choice(["Maison Azure", "Le Jardin", "Vista Royale"])
    rate = random.randint(220, 380)
    return f"{hotel} in {destination}, ${rate}/night, {check_in} to {check_out}"


@tool
def search_activities(destination: str) -> str:
    """Find popular activities in a destination city."""
    activities = {
        "Paris": [
            "Eiffel Tower at sunset",
            "Seine dinner cruise",
            "Day trip to Versailles",
        ],
        "Tokyo": ["Sushi masterclass", "Ghibli Museum", "Hakone hot springs"],
        "Rome": ["Colosseum tour", "Pasta masterclass", "Trastevere walk"],
    }
    items = activities.get(destination, ["Sightseeing", "Local cuisine", "Museum visit"])
    return "\n".join(f"- {a}" for a in items)


# --- Specialist Agents ---
def _make_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=MODEL_NAME,
        api_key=API_KEY,
        base_url=ENDPOINT,  # Do not include api_key and base_url if using the OPENAI_API_KEY environment variable
        temperature=temperature,
    )


flight_agent = create_react_agent(_make_llm(0.3), tools=[search_flights])
hotel_agent = create_react_agent(_make_llm(0.3), tools=[search_hotels])
activity_agent = create_react_agent(_make_llm(0.5), tools=[search_activities])


# --- Coordinator tools that invoke sub-agents ---
@tool
def find_flights(origin: str, destination: str, date: str) -> str:
    """Delegate to the flight specialist agent to find flights."""
    result = flight_agent.invoke(
        {"messages": [HumanMessage(content=f"Find flights from {origin} to {destination} on {date}.")]},
        config={"callbacks": [tracer]},
    )
    return result["messages"][-1].content


@tool
def find_hotels(destination: str, check_in: str, check_out: str) -> str:
    """Delegate to the hotel specialist agent to find hotels."""
    result = hotel_agent.invoke(
        {"messages": [HumanMessage(content=f"Find a boutique hotel in {destination} from {check_in} to {check_out}.")]},
        config={"callbacks": [tracer]},
    )
    return result["messages"][-1].content


@tool
def find_activities(destination: str) -> str:
    """Delegate to the activity specialist agent to find things to do."""
    result = activity_agent.invoke(
        {"messages": [HumanMessage(content=f"Find fun activities in {destination}.")]},
        config={"callbacks": [tracer]},
    )
    return result["messages"][-1].content


# --- Coordinator Agent ---
coordinator = create_react_agent(
    _make_llm(0.2),
    tools=[find_flights, find_hotels, find_activities],
)


def main():
    session_id = str(uuid4())
    user_request = (
        "Plan a weekend trip to Paris from Seattle next month. " + "Find flights, a boutique hotel, and fun activities."
    )

    print("Travel Planner (Nested Agents)")
    print("=" * 40)
    print(f"Request: {user_request}\n")

    result = coordinator.invoke(
        {"messages": [HumanMessage(content=user_request)]},
        config={
            "metadata": {"session_id": session_id, "thread_id": session_id},
            "callbacks": [tracer],
        },
    )

    final = result["messages"][-1].content
    print("Plan:\n" + "-" * 40)
    print(final)


if __name__ == "__main__":
    main()
