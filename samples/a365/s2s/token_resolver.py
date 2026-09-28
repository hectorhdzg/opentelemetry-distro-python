# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""S2S token resolution for the A365 exporter sample."""

import threading
import time
from collections.abc import Callable
from typing import Optional

from sample_config import SampleConfig

# Azure AD requires the resource's ``/.default`` scope rather than a specific
# delegated scope like ``Agent365.Observability.OtelWrite`` (which is only valid
# in the FIC ``user_fic`` grant used by the AI-teammate flow).
A365_OBSERVABILITY_SCOPE = "api://9b975845-388f-4429-889e-eab1ef63949c/.default"


def build_s2s_token_resolver(config: SampleConfig) -> Callable[[str, str], Optional[str]]:
    """Build the app-only S2S token resolver for the configured agent.

    Returns a ``(agent_id, tenant_id) -> token | None`` callable.
    """
    try:
        import msal
    except ImportError as exc:
        raise SystemExit(
            "msal is required for the S2S sample. Run `uv run --with msal python "
            "samples/a365/s2s/s2s_exporter.py` from the repository root as described "
            "in samples/a365/s2s/README.md."
        ) from exc

    cache: dict[str, tuple[str, float]] = {}
    lock = threading.Lock()

    def resolve(agent_id: str, request_tenant_id: str) -> Optional[str]:  # pylint: disable=too-many-return-statements
        cache_key = f"{request_tenant_id}:{agent_id}"

        if request_tenant_id != config.tenant_id:
            print(
                f"S2S token acquisition failed: request tenant {request_tenant_id!r} "
                f"does not match configured tenant {config.tenant_id!r}."
            )
            return None
        if agent_id != config.agent_instance_id:
            print(
                f"S2S token acquisition failed: request agent {agent_id!r} "
                f"does not match configured agent instance {config.agent_instance_id!r}."
            )
            return None
        authority = f"https://login.microsoftonline.com/{request_tenant_id}"

        with lock:
            cached = cache.get(cache_key)
            if cached is not None:
                token, expires_at = cached
                if time.time() < expires_at - 60:
                    return token

        try:
            # Step 1: Agent application token via fmi_path.
            app = msal.ConfidentialClientApplication(
                client_id=config.client_id,
                client_credential=config.client_secret,
                authority=authority,
            )
            result = app.acquire_token_for_client(
                scopes=["api://AzureAdTokenExchange/.default"],
                fmi_path=config.agent_instance_id,
            )
            if "access_token" not in result:
                print(f"S2S step 1 (app token) failed: {result.get('error_description', result)}")
                return None
            agent_token = result["access_token"]

            # Step 2: Instance app authenticated with the agent token as a
            # client assertion. (No agentic-user / user_fic step in S2S.)
            # Pass the assertion as a no-arg callable (MSAL's recommended form)
            # so it can be re-read on demand instead of as a static string.
            instance_app = msal.ConfidentialClientApplication(
                client_id=config.agent_instance_id,
                client_credential={"client_assertion": lambda: agent_token},
                authority=authority,
            )

            # Step 3: Application token for the A365 observability scope.
            result = instance_app.acquire_token_for_client(
                scopes=[A365_OBSERVABILITY_SCOPE],
            )
            if "access_token" not in result:
                print("S2S step 3 (observability token) failed: " f"{result.get('error_description', result)}")
                return None

            access_token = result["access_token"]
            expires_in = result.get("expires_in", 3600)

            with lock:
                cache[cache_key] = (access_token, time.time() + expires_in)
            return access_token

        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"S2S token acquisition failed: {exc}")
            return None

    return resolve
