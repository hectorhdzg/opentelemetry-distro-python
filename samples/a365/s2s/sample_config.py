# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Validated configuration and deterministic inputs for the A365 S2S sample."""

import os
from dataclasses import dataclass, field

from microsoft.opentelemetry.a365.core import AgentDetails, Channel, Request, UserDetails

A365_SERVICE_CLIENT_ID_ENV = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID"
A365_SERVICE_CLIENT_SECRET_ENV = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET"
A365_SERVICE_TENANT_ID_ENV = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID"
A365_AGENT_APP_INSTANCE_ID_ENV = "A365_AGENT_APP_INSTANCE_ID"
A365_CALLER_USER_ID_ENV = "A365_CALLER_USER_ID"
A365_CALLER_USER_EMAIL_ENV = "A365_CALLER_USER_EMAIL"
A365_CALLER_CLIENT_IP_ENV = "A365_CALLER_CLIENT_IP"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or (value.startswith("<") and value.endswith(">")):
        raise SystemExit(
            f"Environment variable {name} is not set. Set the required shell variables "
            "and run the sample as described in samples/a365/s2s/README.md."
        )
    return value


@dataclass(frozen=True)
class SampleConfig:
    """Validated environment settings for the A365 S2S sample."""

    client_id: str
    client_secret: str = field(repr=False)
    tenant_id: str
    agent_instance_id: str
    caller_user_id: str
    caller_user_email: str
    caller_client_ip: str

    @classmethod
    def load(cls) -> "SampleConfig":
        """Load all required settings from the environment."""
        return cls(
            client_id=_require_env(A365_SERVICE_CLIENT_ID_ENV),
            client_secret=_require_env(A365_SERVICE_CLIENT_SECRET_ENV),
            tenant_id=_require_env(A365_SERVICE_TENANT_ID_ENV),
            agent_instance_id=_require_env(A365_AGENT_APP_INSTANCE_ID_ENV),
            caller_user_id=_require_env(A365_CALLER_USER_ID_ENV),
            caller_user_email=_require_env(A365_CALLER_USER_EMAIL_ENV),
            caller_client_ip=_require_env(A365_CALLER_CLIENT_IP_ENV),
        )

    def create_agent_details(self) -> AgentDetails:
        """Create the deterministic agent identity used by the sample."""
        return AgentDetails(
            agent_id=self.agent_instance_id,
            agent_name="Weather Agent",
            agent_description="Answers weather-related questions",
            agent_blueprint_id=self.client_id,
            tenant_id=self.tenant_id,
            provider_name="azure-openai",
            agent_version="1.0.0",
        )

    def create_user_details(self) -> UserDetails:
        """Create the deterministic human caller used by the sample."""
        return UserDetails(
            user_id=self.caller_user_id,
            user_email=self.caller_user_email,
            user_name="Sample Caller",
            user_client_ip=self.caller_client_ip,
        )

    def create_request(self) -> Request:
        """Create the deterministic request used by the sample."""
        return Request(
            content="What's the weather in Seattle?",
            session_id="session-s2s-123",
            channel=Channel(name="service", link="https://contoso.example/a365-s2s"),
            conversation_id="conv-s2s-789",
        )
