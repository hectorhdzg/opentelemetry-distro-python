# A365 S2S Exporter Sample

This sample exports [Agent 365](https://learn.microsoft.com/en-us/microsoft-agent-365/)
telemetry through the service-to-service (S2S) endpoint and demonstrates every
public manual observability scope.

The service authenticates on its own behalf. The token resolver uses the
Blueprint application credentials to obtain an agent-instance token and then an
application token for the A365 observability scope. It deliberately omits the
agentic-user FIC step and does not emit `microsoft.agent.user.id` or
`microsoft.agent.user.email`.

## Sample organization

| File | Responsibility |
| --- | --- |
| `s2s_exporter.py` | Executable entry point that loads configuration, enables S2S export, and runs the scenario |
| `sample_config.py` | Environment validation and deterministic agent, caller, and request inputs |
| `token_resolver.py` | Blueprint-to-agent token exchange, observability token acquisition, and token caching |
| `sample_scenario.py` | Deterministic manual-scope telemetry used for Store validation |

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- A Blueprint app registration granted the
  `Agent365.Observability.OtelWrite` **application** permission with admin
  consent. See [`MIGRATION_A365.md`](../../../MIGRATION_A365.md) under
  "Troubleshooting - Permissions and Setup".
- Real tenant, Blueprint app client ID, agent app instance client ID, and human caller
  values from the deployment being validated. Angle-bracket placeholders are
  rejected at startup.

## Configure and run

PowerShell:

```powershell
$env:ENABLE_OBSERVABILITY = "true"
$env:ENABLE_A365_OBSERVABILITY_EXPORTER = "true"
$env:CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID = "<blueprint-app-client-id>"
$env:CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET = "<blueprint-app-secret>"
$env:CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID = "<tenant-guid>"
$env:A365_AGENT_APP_INSTANCE_ID = "<agent-app-instance-id>"
$env:A365_CALLER_USER_ID = "<caller-user-id>"
$env:A365_CALLER_USER_EMAIL = "<caller-user-email>"
$env:A365_CALLER_CLIENT_IP = "<caller-client-ip>"

uv run --with msal python samples\a365\s2s\s2s_exporter.py
```

Bash:

```bash
export ENABLE_OBSERVABILITY=true
export ENABLE_A365_OBSERVABILITY_EXPORTER=true
export CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID="<blueprint-app-client-id>"
export CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET="<blueprint-app-secret>"
export CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID="<tenant-guid>"
export A365_AGENT_APP_INSTANCE_ID="<agent-app-instance-id>"
export A365_CALLER_USER_ID="<caller-user-id>"
export A365_CALLER_USER_EMAIL="<caller-user-email>"
export A365_CALLER_CLIENT_IP="<caller-client-ip>"

uv run --with msal python samples/a365/s2s/s2s_exporter.py
```

`a365_use_s2s_endpoint=True` routes exports to the S2S ingest endpoint. The
tenant and agent ID in each export request must match the configured tenant and
agent app instance client ID; the resolver rejects mismatches before token
acquisition. `gen_ai.agent.id` and the `{agentId}` export URL segment therefore
use `A365_AGENT_APP_INSTANCE_ID`, not the Blueprint client ID.
The Blueprint telemetry attribute uses the same
`CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` value used to authenticate
the Blueprint application.

## Scope and Store-validation coverage

| Scope | Sample behavior | Store validation |
| --- | --- | --- |
| `InvokeAgentScope` | Root request, agent/Blueprint/caller identity, endpoint, input, and final output | Required |
| `InferenceScope` | Model/provider, messages, token usage, and finish reason | Required |
| `ExecuteToolScope` | Tool identity, arguments, and result | Required |
| `OutputScope` | Child span representing asynchronous/final output | Validate before publishing |
| `ApplyGuardrailScope` | Input-safety decision and finding event | Additional security telemetry |

The sample populates the publishing attributes documented in
[Validate for Store publishing](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/observability?tabs=python#validate-for-store-publishing),
including the tenant, agent, Blueprint, human caller, client address, channel,
conversation, operation, message, endpoint, model, and tool fields applicable
to each span. Human caller identity uses the standard `user.id` and
`user.email` attributes. S2S agentic-user attributes
`microsoft.agent.user.id` and `microsoft.agent.user.email` are intentionally
absent.

## Verify export

The sample enables DEBUG logging for the A365 exporter. A successful run reports
the HTTP status and correlation ID on stderr:

```text
DEBUG ...agent365_exporter: HTTP 200 success on attempt 1. Correlation ID: <id>. Response: ...
```

HTTP 401 usually indicates an invalid token audience or tenant. HTTP 403
usually indicates missing `Agent365.Observability.OtelWrite` application
permission, missing admin consent, or an agent/Blueprint identity that is not
onboarded for the tenant. Use the logged correlation ID when investigating
either response.
