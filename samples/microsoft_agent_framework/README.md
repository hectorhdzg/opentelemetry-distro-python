# Microsoft Agent Framework Sample

This sample demonstrates how to use [Agent Framework](https://aka.ms/agent-framework) to create a simple agent using Foundry model services and export OpenTelemetry traces using the Microsoft OpenTelemetry SDK to Azure Monitor (Application Insights) or a local OpenTelemetry Collector.

Learn more about the Microsoft Agent Framework in our [GitHub repository](https://github.com/microsoft/agent-framework).

## Prerequisites

- Python 3.10+
- A [Foundry project](https://learn.microsoft.com/en-us/azure/foundry/tutorials/quickstart-create-foundry-resources?tabs=portal) endpoint and model
- (Optional) An [Application Insights](https://learn.microsoft.com/en-us/azure/azure-monitor/app/create-workspace-resource?tabs=portal) resource (for the connection string)
- (Optional) An [Aspire Dashboard](https://aspire.dev/dashboard/overview/#standalone-mode) to visualize traces (if you want to use a local OpenTelemetry Collector)

## Environment setup

1. Create and activate a virtual environment using [uv](https://docs.astral.sh/uv/) (recommended):

   ```bash
   uv venv .venv
   ```

   ```bash
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1

   # Windows (Command Prompt)
   .venv\Scripts\activate.bat

   # macOS/Linux
   source .venv/bin/activate
   ```

   > **Note:** `python -m venv .venv` also works, but can hang indefinitely on Windows with Microsoft Store Python due to a known `ensurepip` issue. Use `uv venv .venv` to avoid this.

2. Install dependencies:

   ```bash
   uv pip install -r requirements.txt
   ```

3. Create a `.env` file with your Foundry configuration following the `env.example` file in the sample.

4. Make sure you are logged in with the Azure CLI:

   ```bash
   az login
   ```

## Azure Monitor

Create an Application Insights resource in the Azure portal and copy the connection string to your `.env` file. If you don't have an Application Insights resource, you can skip this step, but you won't be able to see traces in Azure Monitor.

## OTel Exporter

You can also configure the OTLP exporter endpoint to send traces to a local OpenTelemetry Collector by setting the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable in your `.env` file.

## Run the sample

Microsoft Agent Framework is natively instrumented with OpenTelemetry, so you can run the sample directly:

```bash
python sample_maf_agent.py
```
