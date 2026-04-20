# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Token resolver utilities for Agent365 exporter integration.

This module provides distro-specific helpers for creating authentication
token resolvers used by the A365 span exporter
(:class:`microsoft_agents_a365.observability.core.exporters.agent365_exporter._Agent365Exporter`).

The A365 exporter accepts a generic ``token_resolver`` callable with the
signature ``(agent_id: str, tenant_id: str) -> str | None``.  This module
supplies two concrete implementations:

* **FIC (Federated Identity Credential)** — a 3-step MSAL flow used in
  Azure-hosted agent environments.  Requires several hosting-platform
  environment variables (see :func:`_create_fic_token_resolver`).
* **DefaultAzureCredential** — a fallback for local development and
  non-FIC deployments.  Requires the ``azure-identity`` package
  (see :func:`_create_dac_token_resolver`).

Callers should normally use :func:`_create_default_token_resolver`, which
auto-detects the available credentials and returns the appropriate resolver.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from typing import Optional

logger = logging.getLogger(__name__)

_A365_DEFAULT_SCOPE = "api://9b975845-388f-4429-889e-eab1ef63949c/.default"

# --- Environment variable names for FIC token flow ---
_A365_SERVICE_CLIENT_ID_ENV = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID"
_A365_SERVICE_CLIENT_SECRET_ENV = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET"
_A365_SERVICE_TENANT_ID_ENV = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID"
_A365_AGENT_APP_INSTANCE_ID_ENV = "A365_AGENT_APP_INSTANCE_ID"
_A365_AGENTIC_USER_ID_ENV = "A365_AGENTIC_USER_ID"


def _execute_fic_flow(
    client_id: str,
    client_secret: str,
    cfg_tenant: str,
    instance_id: str,
    user_id: str,
    agent_id: str,
    _cache: dict,
    _lock: threading.Lock,
) -> Optional[str]:
    """Execute the 3-step MSAL FIC token exchange.

    Separated from the resolver closure to keep the return-statement
    count manageable.

    :param client_id: Service principal client ID.
    :param client_secret: Service principal client secret.
    :param cfg_tenant: AAD tenant ID.
    :param instance_id: Agent application instance ID.
    :param user_id: Agentic user ID for the FIC grant.
    :param agent_id: Agent ID (used for cache key and logging).
    :param _cache: Shared token cache dict.
    :param _lock: Lock protecting the cache.
    :returns: Bearer token string or ``None`` on failure.
    :rtype: Optional[str]
    """
    import msal  # pylint: disable=import-outside-toplevel

    authority = f"https://login.microsoftonline.com/{cfg_tenant}"
    cache_key = f"{cfg_tenant}:{agent_id}"

    try:
        # Step 1: Agent application token via fmi_path
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )
        result = app.acquire_token_for_client(
            scopes=["api://AzureAdTokenExchange/.default"],
            fmi_path=instance_id,
        )
        if "access_token" not in result:
            logger.warning("FIC step 1 (app token) failed: %s", result.get("error_description", result))
            return None
        agent_token = result["access_token"]

        # Step 2: Instance token (client_assertion = agent_token)
        instance_app = msal.ConfidentialClientApplication(
            client_id=instance_id,
            client_credential={"client_assertion": agent_token},
            authority=authority,
        )
        result = instance_app.acquire_token_for_client(
            scopes=["api://AzureAdTokenExchange/.default"],
        )
        if "access_token" not in result:
            logger.warning("FIC step 2 (instance token) failed: %s", result.get("error_description", result))
            return None
        instance_token = result["access_token"]

        # Step 3: User FIC token for A365 observability scope
        result = instance_app.acquire_token_for_client(
            scopes=[_A365_DEFAULT_SCOPE],
            data={
                "user_id": user_id,
                "user_federated_identity_credential": instance_token,
                "grant_type": "user_fic",
            },
        )
        if "access_token" not in result:
            logger.warning("FIC step 3 (user FIC token) failed: %s", result.get("error_description", result))
            return None

        access_token = result["access_token"]
        expires_in = result.get("expires_in", 3600)

        with _lock:
            _cache[cache_key] = (access_token, time.time() + expires_in)

        logger.debug("FIC token acquired for agent %s, tenant %s", agent_id, cfg_tenant)
        return access_token  # type: ignore[no-any-return]

    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning("FIC token flow failed.", exc_info=True)
        return None


def _create_fic_token_resolver() -> Callable[[str, str], Optional[str]]:
    """Create a token resolver using the FIC (Federated Identity Credential) flow.

    The returned callable performs a synchronous 3-step MSAL token exchange:

    1. **App token** — Acquire a client-credentials token for the agent
       application using ``fmi_path`` (Federated Managed Identity path).
    2. **Instance token** — Exchange the app token for an instance-level
       token via ``client_assertion``.
    3. **User FIC token** — Exchange the instance token for a
       user-scoped token targeting the A365 observability API scope.

    Tokens are cached per ``(tenant_id, agent_id)`` pair and refreshed
    60 seconds before expiry.

    This runs synchronously, which is safe because the batch span
    processor calls ``export`` from a background worker thread — not
    the async event loop.

    :returns:
        A callable with signature
        ``(agent_id: str, tenant_id: str) -> str | None``.
        Returns ``None`` when required environment variables are missing
        or any step of the token exchange fails.
    :rtype: Callable[[str, str], Optional[str]]

    .. rubric:: Required environment variables

    ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID``
        Service principal client ID.
    ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET``
        Service principal client secret.
    ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID``
        AAD tenant ID.  Overrides the *tenant_id* argument passed to
        the resolver at call time.
    ``A365_AGENT_APP_INSTANCE_ID``
        Agent application instance ID (used as ``fmi_path`` in step 1
        and as ``client_id`` in step 2).
    ``A365_AGENTIC_USER_ID``
        Agentic user ID for the user FIC grant in step 3.
    """
    _cache: dict[str, tuple[str, float]] = {}  # key -> (token, expires_at)
    _lock = threading.Lock()

    def _resolve(agent_id: str, tenant_id: str) -> Optional[str]:
        client_id = os.environ.get(_A365_SERVICE_CLIENT_ID_ENV, "")
        client_secret = os.environ.get(_A365_SERVICE_CLIENT_SECRET_ENV, "")
        cfg_tenant = os.environ.get(_A365_SERVICE_TENANT_ID_ENV, tenant_id)
        instance_id = os.environ.get(_A365_AGENT_APP_INSTANCE_ID_ENV, "")
        user_id = os.environ.get(_A365_AGENTIC_USER_ID_ENV, "")

        # Build cache key from effective tenant (after env override)
        cache_key = f"{cfg_tenant}:{agent_id}"

        with _lock:
            cached = _cache.get(cache_key)
            if cached is not None:
                token, expires_at = cached
                if time.time() < expires_at - 60:  # 60 s buffer
                    return token

        if not all([client_id, client_secret, instance_id, user_id]):
            logger.debug(
                "FIC env vars incomplete — need %s, %s, %s, %s.",
                _A365_SERVICE_CLIENT_ID_ENV,
                _A365_SERVICE_CLIENT_SECRET_ENV,
                _A365_AGENT_APP_INSTANCE_ID_ENV,
                _A365_AGENTIC_USER_ID_ENV,
            )
            return None

        return _execute_fic_flow(client_id, client_secret, cfg_tenant, instance_id, user_id, agent_id, _cache, _lock)

    return _resolve


def _create_dac_token_resolver() -> Callable[[str, str], Optional[str]]:
    """Create a token resolver backed by ``DefaultAzureCredential``.

    The ``azure.identity.DefaultAzureCredential`` instance is lazily
    created on the first call and reused for all subsequent invocations
    (thread-safe).  The *agent_id* and *tenant_id* arguments passed
    to the resolver are ignored — the credential's ambient identity
    determines the token.

    :returns:
        A callable with signature
        ``(agent_id: str, tenant_id: str) -> str | None``.
        Returns ``None`` when ``azure-identity`` is not installed or
        token acquisition fails.
    :rtype: Callable[[str, str], Optional[str]]

    .. note::

       Requires the ``azure-identity`` package.  If it is not installed,
       the resolver logs a warning and returns ``None`` on every call.
    """
    _credential = None
    _lock = threading.Lock()

    def _resolve(_agent_id: str, _tenant_id: str) -> Optional[str]:
        nonlocal _credential
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "azure-identity is not installed. "
                "Install it or provide a365_token_resolver to authenticate with the A365 endpoint."
            )
            return None

        with _lock:
            if _credential is None:
                _credential = DefaultAzureCredential()

        try:
            token = _credential.get_token(_A365_DEFAULT_SCOPE)
            return token.token
        except Exception:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to acquire A365 token via DefaultAzureCredential.", exc_info=True)
            return None

    return _resolve


def _create_default_token_resolver() -> Callable[[str, str], Optional[str]]:
    """Create the default token resolver for A365 exporter authentication.

    Selection logic:

    * If the FIC environment variables
      (``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID``,
      ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET``,
      ``A365_AGENT_APP_INSTANCE_ID``, ``A365_AGENTIC_USER_ID``) are all
      set, returns a FIC token resolver
      (see :func:`_create_fic_token_resolver`).
    * Otherwise, returns a ``DefaultAzureCredential`` resolver
      (see :func:`_create_dac_token_resolver`).

    :returns:
        A callable with signature
        ``(agent_id: str, tenant_id: str) -> str | None``.
    :rtype: Callable[[str, str], Optional[str]]
    """
    fic_available = all(
        [
            os.environ.get(_A365_SERVICE_CLIENT_ID_ENV),
            os.environ.get(_A365_SERVICE_CLIENT_SECRET_ENV),
            os.environ.get(_A365_AGENT_APP_INSTANCE_ID_ENV),
            os.environ.get(_A365_AGENTIC_USER_ID_ENV),
        ]
    )

    if fic_available:
        logger.info("FIC env vars detected — using FIC token resolver for A365.")
        return _create_fic_token_resolver()
    logger.info("FIC env vars not set — falling back to DefaultAzureCredential for A365.")
    return _create_dac_token_resolver()
