# Send OpenTelemetry data to Microsoft Fabric

This guide walks you through sending traces, metrics, and logs from a Python application to [Microsoft Fabric Real-Time Intelligence](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/overview) (or Azure Data Explorer).

## How it works

Your Python app doesn't connect to Fabric directly. Instead, it sends telemetry to an **OpenTelemetry Collector** running alongside it — either locally or in a cluster. The collector then forwards the data into your Fabric/ADX database.

```
┌──────────────┐     OTLP/HTTP     ┌──────────────────┐     Kusto Ingest    ┌─────────────────────────┐
│  Python App  │ ───────────────►  │  OTel Collector  │ ──────────────────► │  Fabric / Azure Data    │
│  (microsoft- │                   │                  │                     │                         │
│opentelemetry)│    :4318          │  (ADX exporter)  │                     │  Explorer               │
└──────────────┘                   └──────────────────┘                     └─────────────────────────┘
```

**What each component does:**

- **Your Python app** — uses `microsoft-opentelemetry` to automatically capture HTTP requests, logs, and metrics, then exports them via OTLP (a standard telemetry protocol) on port 4318.
- **OTel Collector** — a lightweight process that receives OTLP data and forwards it to one or more destinations. We use the [Azure Data Explorer exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/azuredataexplorerexporter) plugin to write into Kusto tables.
- **Fabric / ADX** — stores the telemetry in three KQL tables (traces, metrics, logs) that you can query with KQL.

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- An Azure Data Explorer cluster **or** a [Fabric KQL database](https://learn.microsoft.com/en-us/fabric/real-time-analytics/create-database) — a [free ADX cluster](https://dataexplorer.azure.com/freecluster) works for testing
- Azure CLI installed and logged in (`az login`) — used for authentication
- The `microsoft-opentelemetry` package (installed in Step 3)

> **Tip:** Before connecting to Fabric, you can verify your app emits telemetry correctly using the [OTLP sample](../samples/otlp/) with the debug exporter — a quick way to confirm traces, metrics, and logs are being exported. Once validated, continue with the steps below.

## Step 1: Create target tables

The collector writes telemetry into three pre-created tables. Open the [Azure Data Explorer web UI](https://dataexplorer.azure.com/) (or [Fabric KQL queryset](https://learn.microsoft.com/en-us/fabric/real-time-analytics/kusto-query-set)), select your database, and run each command below:

```kql
// Table for log records
.create-merge table OTELLogs (Timestamp:datetime, ObservedTimestamp:datetime, TraceID:string, SpanID:string, SeverityText:string, SeverityNumber:int, Body:string, ResourceAttributes:dynamic, LogsAttributes:dynamic)

// Table for metric data points
.create-merge table OTELMetrics (Timestamp:datetime, MetricName:string, MetricType:string, MetricUnit:string, MetricDescription:string, MetricValue:real, Host:string, ResourceAttributes:dynamic, MetricAttributes:dynamic)

// Table for distributed traces (spans)
.create-merge table OTELTraces (TraceID:string, SpanID:string, ParentID:string, SpanName:string, SpanStatus:string, SpanKind:string, StartTime:datetime, EndTime:datetime, ResourceAttributes:dynamic, TraceAttributes:dynamic, Events:dynamic, Links:dynamic)
```

> **Tip:** `.create-merge` is safe to run multiple times — it creates the table if it doesn't exist, or merges new columns into an existing table.

## Step 2: Grant permissions

The collector needs permission to write data into your database. Run one of these commands in the same query window:

**For local development** (uses your Azure CLI identity):

```kql
.add database <yourdbname> ingestors ('aaduser=you@yourdomain.com') 'Dev testing'
```

**For production** (uses a service principal):

```kql
.add database <yourdbname> ingestors ('aadapp=<ApplicationID>') 'OTel Collector'
```

> Replace `<yourdbname>` with your actual database name, and `<ApplicationID>` with the client ID from your [Entra app registration](https://learn.microsoft.com/en-us/azure/data-explorer/provision-entra-id-app?tabs=portal).

## Step 3: Create a Python app with `microsoft-opentelemetry`

Create a new directory and install `microsoft-opentelemetry`:

```bash
mkdir fabric-demo && cd fabric-demo
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install microsoft-opentelemetry
```

Create `app.py`:

```python
import logging
import time

from opentelemetry import trace, metrics
from microsoft.opentelemetry import use_microsoft_opentelemetry

LOGGER_NAME = "fabric-demo"

use_microsoft_opentelemetry(logger_name=LOGGER_NAME)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(LOGGER_NAME)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter(
    "app.requests",
    description="Number of requests processed",
)

logger.info("App started — sending telemetry to OTLP collector")

for i in range(5):
    with tracer.start_as_current_span("process-request") as span:
        span.set_attribute("request.id", i)
        request_counter.add(1, {"request.type": "demo"})
        logger.info("Processing request %d", i)
        time.sleep(0.5)

logger.info("Done. Waiting for export flush...")
time.sleep(5)
```

That's it for the app. `use_microsoft_opentelemetry()` automatically instruments HTTP clients, collects metrics, and captures log records via the OpenTelemetry logging pipeline. An explicit `logger_name` selects that logger and its propagating children; an omitted or empty name selects the root logger. Use `disable_logging=True` to disable log collection. The OTLP exporter is auto-enabled when the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable is set.

By default, the SDK uses OTLP/HTTP (port 4318). To point at the collector:

```bash
# Windows
set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Linux / macOS
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

To change the endpoint (e.g., a remote collector or one using TLS):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://<collector-host>:4318
```

## Step 4: Download the OpenTelemetry Collector

The collector is a standalone process that receives OTLP data from your app and forwards it to Fabric/ADX. You need the **contrib** distribution (which includes the Azure Data Explorer exporter).

### Option A: Binary (recommended for getting started)

Download the latest **otelcol-contrib** binary for your OS from [OTel Collector Contrib releases](https://github.com/open-telemetry/opentelemetry-collector-releases/releases) (look for `otelcol-contrib_*` assets).

### Option B: Docker

```bash
docker pull otel/opentelemetry-collector-contrib:0.121.0
```

### Option C: Kubernetes

For production deployments, see the [Azure Data Explorer exporter docs](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/azuredataexplorerexporter) for Kubernetes examples using Workload Identity.

## Step 5: Configure the collector

Create a file called `collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    send_batch_size: 512
    timeout: 5s

exporters:
  azuredataexplorer:
    cluster_uri: "https://<your-cluster>.kusto.windows.net"
    # Authentication — pick one:
    #   Option 1: DefaultAzureCredential (Azure CLI, Managed Identity, Workload Identity)
    use_azure_auth: true
    #   Option 2: Service principal with client secret
    # application_id: "<client-id>"
    # application_key: "<client-secret>"
    # tenant_id: "<tenant-id>"

    db_name: "<yourdbname>"
    metrics_table_name: "OTELMetrics"
    logs_table_name: "OTELLogs"
    traces_table_name: "OTELTraces"
    ingestion_type: "queued"   # or "managed" for streaming

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [azuredataexplorer]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [azuredataexplorer]
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [azuredataexplorer]
```

**Update these placeholders:**

| Placeholder | Replace with | Example |
|---|---|---|
| `<your-cluster>` | Your cluster name and region (without `https://` or `.kusto.windows.net`) | `mycluster.westus2` |
| `<yourdbname>` | The database name where you created the tables | `oteldb` |

### Authentication options

| Method | Config | When to use |
|---|---|---|
| **DefaultAzureCredential** | `use_azure_auth: true` | Local dev (`az login`), Managed Identity, Workload Identity (AKS) |
| **Service principal** | `application_id` + `application_key` + `tenant_id` | CI/CD, headless environments |

> **Note:** When using `use_azure_auth: true`, the collector authenticates via the [DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential) chain. For local development, `az login` is the simplest option. In production (AKS), use [Workload Identity federation](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview) with a federated credential on your Entra app registration — no client secrets needed.

## Step 6: Start the collector

Make sure you're logged into Azure CLI (for `use_azure_auth: true`):

```bash
az login
```

Then start the collector:

```bash
# Binary (Windows)
otelcol-contrib.exe --config collector-config.yaml

# Binary (Linux / macOS)
./otelcol-contrib --config collector-config.yaml

# Docker
docker run --rm -p 4317:4317 -p 4318:4318 \
  -v ${PWD}/collector-config.yaml:/etc/otelcol-contrib/config.yaml \
  otel/opentelemetry-collector-contrib:0.121.0
```

> **Docker + `use_azure_auth`:** Azure CLI credentials aren't available inside the Docker container. Use `application_id` + `application_key` + `tenant_id` in the config instead, or run the binary directly.

You should see `Everything is ready. Begin running and processing data.` — the collector is now listening on ports 4317 (gRPC) and 4318 (HTTP).

## Step 7: Run the app and verify

With the collector running in one terminal, open a second terminal and run the app:

```bash
# Windows
set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
python app.py

# Linux / macOS
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 python app.py
```

After the collector batch interval (5s default), query your tables in the ADX web UI:

```kql
// Check for traces (each span creates a row)
OTELTraces | take 10

// Check for logs
OTELLogs | take 10

// Check for metrics (request counts)
OTELMetrics | take 10
```

> **Don't see data?** Check the collector terminal for errors. Common issues: wrong `cluster_uri`, missing permissions (re-run Step 2), or `az login` session expired.

## Combining with Azure Monitor

You can send to both Azure Monitor **and** Fabric simultaneously. The app exports via OTLP (collector → Fabric) and directly to Azure Monitor — no extra collector needed for Azure Monitor:

```python
use_microsoft_opentelemetry(
    enable_azure_monitor=True,
    azure_monitor_connection_string="InstrumentationKey=...;IngestionEndpoint=...",
)
```

With `OTEL_EXPORTER_OTLP_ENDPOINT` set, both exporters are active — Azure Monitor receives telemetry directly and the collector forwards to Fabric.

## References

- [Ingest data from OpenTelemetry to Azure Data Explorer](https://learn.microsoft.com/en-us/azure/data-explorer/open-telemetry-connector?tabs=command-line) — Full ADX + OTel Collector setup guide
- [Create a Microsoft Entra app registration](https://learn.microsoft.com/en-us/azure/data-explorer/provision-entra-id-app?tabs=portal) — Service principal setup for ADX authentication
- [Azure Data Explorer exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/azuredataexplorerexporter) — Collector plugin source code and configuration reference
- [Fabric Real-Time Intelligence overview](https://learn.microsoft.com/en-us/fabric/real-time-intelligence/overview) — Microsoft Fabric's real-time analytics capability
- [Example: Fabric demo](../samples/fabric/) — Working sample app with collector config
