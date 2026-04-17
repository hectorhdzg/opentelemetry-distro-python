# OpenAI Samples

These samples demonstrate how to use OpenAI and Azure OpenAI with OpenTelemetry tracing exported to Azure Monitor (Application Insights).

## Prerequisites

- Python 3.10+
- An OpenAI API key or an Azure OpenAI resource
- An Application Insights resource (for the connection string)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

| Environment Variable                    | Description                                              |
| --------------------------------------- | -------------------------------------------------------- |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Azure Monitor connection string                          |
| `OPENAI_API_KEY`                        | OpenAI API key                                           |
| `AZURE_OPENAI_ENDPOINT`                 | Azure OpenAI endpoint (e.g. `https://<resource>.openai.azure.com/`) |
| `AZURE_OPENAI_API_KEY`                  | Azure OpenAI API key                                     |
| `AZURE_OPENAI_DEPLOYMENT`               | Azure OpenAI deployment/model name                       |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Set to capture GenAI message content (prompts and completions). The options are `SPAN_ONLY`, `EVENT_ONLY` and `SPAN_AND_EVENT` |
| `OTEL_SEMCONV_STABILITY_OPT_IN`        | Set to `gen_ai_latest_experimental` to enable experimental attributes. (must be set if the above is set) |

## Samples

### 1. `sample_openai_chat.py`

Demonstrates chat completions using both the OpenAI and Azure OpenAI clients.

**Run:**
```bash
python sample_openai_chat.py
```

### 2. `sample_openai_agents.py`

Demonstrates the OpenAI Agents SDK with tool calling and tracing.

**Run:**
```bash
python sample_openai_agents.py
```
