# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Token cache for observability tokens per (agentId, tenantId).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import Lock

from microsoft_agents.hosting.core.app.oauth.authorization import Authorization
from microsoft_agents.hosting.core.turn_context import TurnContext

logger = logging.getLogger(__name__)


@dataclass
class AgenticTokenStruct:
    """Structure containing the token generation components."""

    authorization: Authorization
    """The user authorization object for token exchange."""

    turn_context: TurnContext
    """The turn context for the current conversation."""

    auth_handler_name: str | None = "AGENTIC"
    """The name of the authentication handler."""


class AgenticTokenCache:
    """
    Caches observability tokens per (agentId, tenantId) using the provided
    UserAuthorization and TurnContext.
    """

    @dataclass
    class _Entry:
        """Internal entry structure for cache storage."""

        agentic_token_struct: AgenticTokenStruct
        """The token generation structure."""

        scopes: list[str]
        """The observability scopes for token requests."""

    def __init__(self) -> None:
        """Initialize the token cache."""
        self._map: dict[str, AgenticTokenCache._Entry] = {}
        self._lock = Lock()

    def register_observability(
        self,
        agent_id: str,
        tenant_id: str,
        token_generator: AgenticTokenStruct,
        observability_scopes: list[str],
    ) -> None:
        """
        Register observability for the specified agent and tenant.

        Args:
            agent_id: The agent identifier.
            tenant_id: The tenant identifier.
            token_generator: The token generator structure.
            observability_scopes: The observability scopes.

        Raises:
            ValueError: If agent_id or tenant_id is empty or None.
            TypeError: If token_generator is None.
        """
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be None or whitespace")

        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id cannot be None or whitespace")

        if token_generator is None:
            raise TypeError("token_generator cannot be None")

        key = f"{agent_id}:{tenant_id}"

        # First registration wins; subsequent calls ignored (idempotent)
        with self._lock:
            if key not in self._map:
                self._map[key] = AgenticTokenCache._Entry(
                    agentic_token_struct=token_generator,
                    scopes=observability_scopes,
                )
                logger.debug("Registered observability for %s", key)
            else:
                logger.debug("Observability already registered for %s, ignoring", key)

    async def get_observability_token(self, agent_id: str, tenant_id: str) -> str | None:
        """
        Get the observability token for the specified agent and tenant.

        Args:
            agent_id: The agent identifier.
            tenant_id: The tenant identifier.

        Returns:
            The observability token if available; otherwise, None.
        """
        key = f"{agent_id}:{tenant_id}"

        logger.debug("Cache lookup for %s", key)

        with self._lock:
            entry = self._map.get(key)

        if entry is None:
            logger.debug("Cache miss for %s", key)
            return None

        logger.debug("Cache hit for %s, exchanging token", key)

        try:
            authorization = entry.agentic_token_struct.authorization
            turn_context = entry.agentic_token_struct.turn_context
            auth_handler_id = entry.agentic_token_struct.auth_handler_name

            # Exchange the turn token for an observability token
            token = await authorization.exchange_token(
                context=turn_context,
                scopes=entry.scopes,
                auth_handler_id=auth_handler_id,
            )

            logger.info("Successfully exchanged token for %s", key)
            return token  # type: ignore[no-any-return]
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Return None if token generation fails
            logger.error("Token exchange failed for %s: %s", key, type(e).__name__)
            return None
