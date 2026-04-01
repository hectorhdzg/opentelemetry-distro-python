
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.langchain import LangChainInstrumentor
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# This sample demonstrates the current state of the opentelemetry-instrumentation-langchain package (unreleased) and how it can be integrated with the opentelemetry distro
# If  using Azure OpenAI endpoint and API KEY
endpoint = "<AZURE_OPENAI_ENDPOINT>"
model_name = "gpt-4.1"
api_key = "<AZURE_OPENAI_API_KEY>"

# Otherwise, set the env variable OPENAI_API_KEY

configure_azure_monitor() # TODO: This will be replaced with the opentelemetry distro
"""
configure_microsoft_opentelemetry(
    connection_string="InstrumentationKey=...",
    enable_genai_langchain=True,
)
"""
LangChainInstrumentor().instrument()

# Two models with different configs — each call produces its own span
creative_llm = ChatOpenAI(
    model=model_name,
    temperature=0.9,
    max_tokens=200,
    top_p=0.95,
    api_key=api_key, # Do not include if using the OPENAI_API_KEY environment variable
    base_url=endpoint, # Do not include if using the OPENAI_API_KEY environment variable
)

precise_llm = ChatOpenAI(
    model=model_name,
    temperature=0.0,
    max_tokens=100,
    top_p=0.1,
    frequency_penalty=0.5,
    presence_penalty=0.5,
    seed=42,
    api_key=api_key, # Do not include if using the OPENAI_API_KEY environment variable
    base_url=endpoint,
)


# --------------- Scenarios ---------------

def multi_turn_conversation():
    """Multi-turn chat — each invoke() is a separate instrumented span."""
    print("=== Multi-turn Conversation ===")
    history = [
        SystemMessage(content="You are a travel guide. Be concise."),
        HumanMessage(content="I'm planning a trip to Japan. Where should I start?"),
    ]

    response1 = creative_llm.invoke(history)
    print(f"Turn 1: {response1.content}\n")

    history.append(AIMessage(content=response1.content))
    history.append(HumanMessage(content="What food should I try there?"))

    response2 = creative_llm.invoke(history)
    print(f"Turn 2: {response2.content}\n")


def compare_temperatures():
    """Same prompt, different models — compare creative vs precise in telemetry."""
    print("=== Temperature Comparison ===")
    messages = [
        SystemMessage(content="You are a poet."),
        HumanMessage(content="Write a haiku about observability."),
    ]

    creative_result = creative_llm.invoke(messages)
    print(f"Creative (temp=0.9): {creative_result.content}\n")

    precise_result = precise_llm.invoke(messages)
    print(f"Precise  (temp=0.0): {precise_result.content}\n")


if __name__ == "__main__":
    multi_turn_conversation()
    compare_temperatures()

    LangChainInstrumentor().uninstrument()