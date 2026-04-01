# LangChain Samples

These samples demonstrate how to use LangChain with OpenTelemetry tracing exported to Azure Monitor (Application Insights).

## Prerequisites

- Python 3.10+
- An Azure OpenAI resource (or an OpenAI API key)
- An Application Insights resource (for the connection string)

## Configuration

All samples require you to fill in placeholder values before running.

### Option A: Azure OpenAI

Replace these placeholders in each sample file:

| Placeholder | Description |
|---|---|
| `<AZURE_OPENAI_ENDPOINT>` | Your Azure OpenAI endpoint URL (e.g., `https://<resource-name>.openai.azure.com/openai/deployments/<deployment-name>/v1`) |
| `<AZURE_OPENAI_API_KEY>` | Your Azure OpenAI API key |

### Option B: OpenAI API Key

Set the environment variable `OPENAI_API_KEY` and remove the `api_key` and `base_url` parameters from the `ChatOpenAI(...)` calls in the sample files.

### Azure Monitor Connection String

Replace `"InstrumentationKey=..."` with your full Application Insights connection string. You can find this in the Azure portal under your Application Insights resource > **Overview** > **Connection String**. Or you can
set it using the `APPLICATIONINISGHTS_CONNECTION_STRING` environment variable.

## Samples

### 1. `sample_opentelemetry.py`

Demonstrates the `opentelemetry-instrumentation-langchain` package with two differently configured LLMs (creative vs. precise).

**Placeholders to fill:**

| Placeholder | Value |
|---|---|
| `<AZURE_OPENAI_ENDPOINT>` | Azure OpenAI endpoint URL |
| `<AZURE_OPENAI_API_KEY>` | Azure OpenAI API key |

**What it does:**
- Creates two `ChatOpenAI` instances with different temperature/sampling settings
- Runs a multi-turn conversation (travel guide)
- Compares creative vs. precise outputs for the same prompt (haiku about observability)
- Each `invoke()` call produces its own OpenTelemetry span

**Run:**
```bash
python sample_opentelemetry.py
```

### 2. `sample_arise_langchain.py`

Demonstrates image description using a vision-capable model, with tracing via the `openinference-instrumentation-langchain` instrumentor.

**Placeholders to fill:**

| Placeholder | Value |
|---|---|
| `<AZURE_OPENAI_ENDPOINT>` | Azure OpenAI endpoint URL |
| `<AZURE_OPENAI_API_KEY>` | Azure OpenAI API key |
| `<IMAGE_URL>` | A publicly accessible URL to an image (e.g., `https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg`) |

**What it does:**
- Downloads and base64-encodes the image at the provided URL
- Sends a multimodal message (text + image) to the model
- Asks the model to describe the image

**Run:**
```bash
python sample_arise_langchain.py
```

### 3. `sample_langchain_azure.py`

Demonstrates a multi-agent travel planner using nested LangChain agents with the `AzureAIOpenTelemetryTracer`.

**Placeholders to fill:**

| Placeholder | Value |
|---|---|
| `<AZURE_OPENAI_ENDPOINT>` | Azure OpenAI endpoint URL |
| `<AZURE_OPENAI_API_KEY>` | Azure OpenAI API key |
| `"InstrumentationKey=..."` | Application Insights connection string |

**What it does:**
- Creates specialist agents for flights, hotels, and activities (with mock tool data)
- A coordinator agent delegates to the specialists to plan a weekend trip to Paris
- All agent calls are traced via the `AzureAIOpenTelemetryTracer` callback

**Run:**
```bash
python sample_langchain_azure.py
```

## Required Packages

```bash
pip install langchain-openai langchain-core azure-monitor-opentelemetry httpx
# For sample_opentelemetry.py:
pip install opentelemetry-instrumentation-langchain

# For sample_arise_langchain.py:
pip install openinference-instrumentation-langchain

# For sample_langchain_azure.py:
pip install langchain-azure-ai langgraph
```