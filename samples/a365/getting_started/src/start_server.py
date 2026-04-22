# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
Server bootstrap with the Microsoft OpenTelemetry Distro.

Migrated from:
  configure()                        → use_microsoft_opentelemetry(enable_a365=True)
  ObservabilityHostingManager        → same class, new import path
  ENABLE_KAIRO_EXPORTER              → ENABLE_A365_OBSERVABILITY_EXPORTER
"""

import logging
from os import environ

from aiohttp.web import Application, Request, Response, run_app
from microsoft_agents.hosting.aiohttp import (
    CloudAdapter,
    start_agent_process,
)
from microsoft_agents.hosting.core import AgentApplication, AgentAuthConfiguration

# ✅ NEW — distro entry point replaces configure()
from microsoft.opentelemetry import use_microsoft_opentelemetry

# ✅ NEW — hosting middleware from distro (same classes, new import path)
from microsoft.opentelemetry.a365.hosting import (
    ObservabilityHostingManager,
    ObservabilityHostingOptions,
)
from microsoft.opentelemetry.a365.hosting.token_cache_helpers import AgenticTokenCache

from utils.token_cache import get_cached_agentic_token

logger = logging.getLogger(__name__)


def create_token_resolver(token_cache: AgenticTokenCache):
    """
    Factory function that creates a token resolver with injected dependencies.

    Args:
        token_cache: The AgenticTokenCache instance to use for token resolution.

    Returns:
        A token resolver function suitable for the A365 exporter.
    """

    def token_resolver(agent_id: str, tenant_id: str) -> str | None:
        """
        Token resolver for the A365 exporter.

        Uses the AgenticTokenCache to retrieve observability tokens.
        The cache was registered in the agent's on_message handler with the
        authorization, turn context, and auth handler name.
        """
        try:
            logger.info(f"Token resolver called for agent_id: {agent_id}, tenant_id: {tenant_id}")

            import asyncio

            token = asyncio.run(token_cache.get_observability_token(agent_id, tenant_id))

            if token:
                logger.info("Successfully retrieved token from AgenticTokenCache")
                return token.token

            # Fallback: use cached agentic token (old approach for reference)
            cached_token = get_cached_agentic_token(tenant_id, agent_id)
            if cached_token:
                logger.info("Using cached agentic token (fallback)")
                return cached_token
            else:
                logger.warning(
                    f"No cached token found for agent_id: {agent_id}, tenant_id: {tenant_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Error resolving token for agent {agent_id}, tenant {tenant_id}: {e}")
            return None

    return token_resolver


def start_server(agent_application: AgentApplication, auth_configuration: AgentAuthConfiguration):
    async def entry_point(req: Request) -> Response:
        agent: AgentApplication = req.app["agent_app"]
        adapter: CloudAdapter = req.app["adapter"]
        return await start_agent_process(req, agent, adapter)

    app = Application()
    app.router.add_post("/api/messages", entry_point)
    app["agent_configuration"] = auth_configuration
    app["agent_app"] = agent_application
    app["adapter"] = agent_application.adapter

    # Create token cache instance and store in app context
    token_cache = AgenticTokenCache()
    app["token_cache"] = token_cache

    # Make token cache available to agent handlers via application storage
    agent_application.adapter.app_context = {"token_cache": token_cache}

    # Create token resolver with injected token cache dependency
    token_resolver_func = create_token_resolver(token_cache)

    # ✅ NEW — single distro call replaces configure() + ENABLE_KAIRO_EXPORTER
    use_microsoft_opentelemetry(
        enable_a365=True,
        a365_token_resolver=token_resolver_func,
        enable_azure_monitor=False,
    )

    # Register observability hosting middleware (baggage + output logging)
    ObservabilityHostingManager.configure(
        agent_application.adapter.middleware_set,
        ObservabilityHostingOptions(
            enable_baggage=True,
            enable_output_logging=True,
        ),
    )

    try:
        run_app(app, host="localhost", port=environ.get("PORT", 3978))
    except Exception as error:
        raise error
