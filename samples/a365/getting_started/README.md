# Getting Started with A365 Exporter (Microsoft OpenTelemetry Distro)

Port of the `getting_started_with_kairo_exporter` sample, using the new
`microsoft-opentelemetry` distro instead of the standalone
`microsoft-agents-a365-observability-*` packages.

## What it does

An aiohttp bot server that receives Teams messages, calls Azure OpenAI,
optionally runs tools (weather/calculator), and traces everything via
the A365 observability scopes:

- **InvokeAgentScope** — top-level agent invocation per message
- **InferenceScope** — each Azure OpenAI chat completion
- **ExecuteToolScope** — tool execution (triggered by "weather" or "calculate" in the message)
- **BaggageBuilder** — propagates tenant/agent/user context across spans
- **ObservabilityHostingManager** — hosting middleware (baggage + output logging)
- **AgenticTokenCache** — caches auth tokens for the A365 HTTP exporter

## Two ways to run

### Option A: Quick scope test (no infra needed)

Verifies all scope classes work with a console span exporter. No Azure OpenAI,
no Agent365 registration, no Teams.

```bash
cd <repo-root>
.venv\Scripts\python.exe samples\a365\getting_started\run_scopes_test.py
```

### Option B: Full hosted agent

#### Prerequisites

- Python >= 3.11
- Azure OpenAI deployment (endpoint + API key + deployment name)
- Agent365 app registration (client ID, client secret, tenant ID)
- Bot Framework Emulator or Teams channel to send messages

#### Step 1: Create virtual environment and install

```bash
cd samples/a365/getting_started

# Create venv
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

# Install the distro from repo root + deps
pip install -e ../../..
pip install -r requirements.txt
```

#### Step 2: Configure environment

```bash
# Windows
copy env.TEMPLATE .env

# macOS/Linux
# cp env.TEMPLATE .env
```

Edit `.env` and fill in **all** values:

```env
# Agent365 app registration
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<your-client-id>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<your-client-secret>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<your-tenant-id>

# Blueprint (use same creds if single-identity setup)
CONNECTIONS__AGENTBLUEPRINT__SETTINGS__CLIENTID=<your-client-id>
CONNECTIONS__AGENTBLUEPRINT__SETTINGS__CLIENTSECRET=<your-client-secret>
CONNECTIONS__AGENTBLUEPRINT__SETTINGS__TENANTID=<your-tenant-id>

# Azure OpenAI
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# Observability (already set in template)
ENABLE_OBSERVABILITY=true
ENABLE_A365_OBSERVABILITY_EXPORTER=true
```

#### Step 3: Run

```bash
cd src
python main.py
```

Server starts on `http://localhost:3978/api/messages`.

Send a POST to `/api/messages` with a Bot Framework Activity, or connect
via Bot Framework Emulator / Teams.

**Test messages:**
- `"Hello"` — simple LLM response
- `"What's the weather?"` — triggers ExecuteToolScope + LLM
- `"Calculate 2+2"` — triggers ExecuteToolScope + LLM

## File structure

```
getting_started/
├── README.md              ← you are here
├── env.TEMPLATE           ← copy to .env and fill in
├── pyproject.toml
├── requirements.txt
├── run_scopes_test.py     ← standalone scope test (no infra needed)
└── src/
    ├── main.py            ← entry point
    ├── agent.py           ← message handler + InvokeAgentScope + BaggageBuilder
    ├── start_server.py    ← server bootstrap + use_microsoft_opentelemetry()
    ├── services/
    │   ├── openai_service.py  ← Azure OpenAI calls + InferenceScope
    │   └── tool_service.py    ← tool execution + ExecuteToolScope
    └── utils/
        ├── azure_openai_client.py   ← AsyncAzureOpenAI client factory
        ├── observability_helpers.py ← AgentDetails/Request factory helpers
        └── token_cache.py           ← fallback token cache
```

## Key differences from old Kairo sample

| Old SDK | New Distro |
|---------|-----------|
| `pip install microsoft-agents-a365-observability-core` | `pip install microsoft-opentelemetry` |
| `from microsoft_agents_a365.observability.core import configure` | `from microsoft.opentelemetry import use_microsoft_opentelemetry` |
| `from microsoft_agents_a365.observability.core.* import ...` | `from microsoft.opentelemetry.a365.core import ...` |
| `from microsoft_agents_a365.observability.hosting.* import ...` | `from microsoft.opentelemetry.a365.hosting import ...` |
| `from microsoft_agents_a365.runtime.* import ...` | `from microsoft.opentelemetry.a365.runtime import ...` |
| `configure(service_name=..., token_resolver=...)` | `use_microsoft_opentelemetry(enable_a365=True, a365_token_resolver=...)` |
| `ENABLE_KAIRO_EXPORTER=true` | `ENABLE_A365_OBSERVABILITY_EXPORTER=true` |
| `ObservabilityHostingOptions(True, True)` | `ObservabilityHostingOptions(enable_baggage=True, enable_output_logging=True)` |

See [MIGRATION_A365.md](../../../docs/MIGRATION_A365.md) for the full migration guide.
