# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
Observability helper utilities for creating observability objects.

Migrated from: microsoft_agents_a365.observability.core → microsoft.opentelemetry.a365.core
"""

import logging
from os import environ

from microsoft_agents.hosting.core import TurnContext

# ✅ NEW — distro imports
from microsoft.opentelemetry.a365.core import AgentDetails, Request

logger = logging.getLogger(__name__)


def create_agent_details(context: TurnContext) -> AgentDetails:
    """Create agent details for observability."""
    tenant_id = None
    if context.activity.recipient and hasattr(context.activity.recipient, "tenant_id"):
        tenant_id = context.activity.recipient.tenant_id
    if not tenant_id:
        tenant_id = environ.get("TENANT_ID", "default-tenant")

    return AgentDetails(
        agent_id=context.activity.recipient.agentic_app_id,
        agent_name=environ.get("AGENT_NAME", "Azure OpenAI Agent"),
        agent_description="An AI agent powered by Azure OpenAI",
        agent_blueprint_id="4a380e3b-7092-4d73-bb9d-b6a54702684af",
        tenant_id=tenant_id,
    )


def create_request_details(user_message: str, session_id: str = None) -> Request:
    """Create request details for observability."""
    return Request(
        content=user_message,
        session_id=session_id,
    )
