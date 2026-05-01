# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Utilities for the Agent365 exporter.

Vendored from microsoft-agents-a365-observability-core exporters/utils.py.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, List, Optional, TypeVar
from urllib.parse import urlparse

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanProcessor
from opentelemetry.trace import SpanKind, StatusCode

from microsoft.opentelemetry.a365.constants import (
    A365_AGENT_APP_INSTANCE_ID_ENV,
    A365_AGENTIC_USER_ID_ENV,
    A365_CLUSTER_CATEGORY_ENV,
    A365_OBSERVABILITY_DOMAIN_OVERRIDE,
    A365_SERVICE_CLIENT_ID_ENV,
    A365_SERVICE_CLIENT_SECRET_ENV,
    A365_SERVICE_TENANT_ID_ENV,
    A365_SUPPRESS_INVOKE_AGENT_INPUT_ENV,
    A365_USE_S2S_ENDPOINT_ENV,
    CHAT_OPERATION_NAME,
    ENABLE_A365_OBSERVABILITY_EXPORTER,
    EXECUTE_TOOL_OPERATION_NAME,
    GEN_AI_AGENT_ID_KEY,
    GEN_AI_OPERATION_NAME_KEY,
    INVOKE_AGENT_OPERATION_NAME,
    OUTPUT_MESSAGES_OPERATION_NAME,
    TENANT_ID_KEY,
)
from microsoft.opentelemetry.a365.core.inference_operation_type import InferenceOperationType

logger = logging.getLogger(__name__)

# Maximum allowed span size in bytes (250KB)
MAX_SPAN_SIZE_BYTES = 250 * 1024

# Operation names that identify a span as eligible for export to the Agent 365
# observability ingest service. Only spans whose gen_ai.operation.name matches
# one of these values are included; all other spans are filtered out.
GEN_AI_OPERATION_NAMES: frozenset[str] = frozenset(
    {
        INVOKE_AGENT_OPERATION_NAME,
        EXECUTE_TOOL_OPERATION_NAME,
        OUTPUT_MESSAGES_OPERATION_NAME,
        CHAT_OPERATION_NAME,
        InferenceOperationType.CHAT.value,
    }
)


# pylint: disable=broad-exception-caught, too-many-return-statements
def hex_trace_id(value: int) -> str:
    """Convert a 128-bit trace ID to a 32-character hex string."""
    return f"{value:032x}"


def hex_span_id(value: int) -> str:
    """Convert a 64-bit span ID to a 16-character hex string."""
    return f"{value:016x}"


def _as_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v)
    return s if s.strip() else None


def kind_name(kind: SpanKind) -> str:
    """Return span kind name (enum name or numeric)."""
    try:
        return kind.name
    except Exception:
        return str(kind)


def status_name(code: StatusCode) -> str:
    """Return status code name."""
    try:
        return code.name
    except Exception:
        return str(code)


def truncate_span(span_dict: dict[str, Any]) -> dict[str, Any]:
    """Truncate span attributes if the serialized span exceeds MAX_SPAN_SIZE_BYTES.

    Removes the largest attributes first until the span fits within the limit.
    """
    try:
        serialized = json.dumps(span_dict, separators=(",", ":"))
        current_size = len(serialized.encode("utf-8"))

        if current_size <= MAX_SPAN_SIZE_BYTES:
            return span_dict

        logger.warning(
            "Span size (%d bytes) exceeds limit (%d bytes). Truncating large payload attributes.",
            current_size,
            MAX_SPAN_SIZE_BYTES,
        )

        truncated_span = span_dict.copy()
        if "attributes" in truncated_span:
            truncated_span["attributes"] = truncated_span["attributes"].copy()
        attributes = truncated_span.get("attributes", {})

        truncated_keys: list[str] = []

        if attributes:
            attr_sizes: list[tuple[str, int]] = []
            for key, value in attributes.items():
                try:
                    value_size = len(json.dumps(value, separators=(",", ":")).encode("utf-8"))
                    attr_sizes.append((key, value_size))
                except Exception:
                    attr_sizes.append((key, 0))

            attr_sizes.sort(key=lambda x: x[1], reverse=True)

            for key, _ in attr_sizes:
                if key in attributes:
                    attributes[key] = "TRUNCATED"
                    truncated_keys.append(key)

                    serialized = json.dumps(truncated_span, separators=(",", ":"))
                    current_size = len(serialized.encode("utf-8"))

                    if current_size <= MAX_SPAN_SIZE_BYTES:
                        break

        if truncated_keys:
            logger.info("Truncated attributes: %s", ", ".join(truncated_keys))

        return truncated_span

    except Exception as e:
        logger.error("Error during span truncation: %s", e)
        return span_dict


def filter_and_partition_by_identity(
    spans: Sequence[ReadableSpan],
) -> dict[tuple[str, str], list[ReadableSpan]]:
    """Filter export-eligible spans and partition them by (tenantId, agentId).

    Only spans whose ``gen_ai.operation.name`` is in
    ``GEN_AI_OPERATION_NAMES`` are included; non-genAI spans (e.g. HTTP, DB)
    and spans with other operation names are filtered out. Spans without
    both tenant and agent identity are also skipped.
    """
    groups: dict[tuple[str, str], list[ReadableSpan]] = {}
    non_gen_ai_count = 0
    missing_identity_count = 0
    for sp in spans:
        attrs = sp.attributes or {}
        operation_name = _as_str(attrs.get(GEN_AI_OPERATION_NAME_KEY))
        if not operation_name or operation_name not in GEN_AI_OPERATION_NAMES:
            non_gen_ai_count += 1
            continue
        tenant = _as_str(attrs.get(TENANT_ID_KEY))
        agent = _as_str(attrs.get(GEN_AI_AGENT_ID_KEY))
        if not tenant or not agent:
            missing_identity_count += 1
            continue
        key = (tenant, agent)
        groups.setdefault(key, []).append(sp)

    if non_gen_ai_count > 0:
        logger.debug(
            "[Agent365Exporter] %d spans without an eligible gen_ai.operation.name filtered out",
            non_gen_ai_count,
        )
    if missing_identity_count > 0:
        logger.debug(
            "[Agent365Exporter] %d spans skipped due to missing tenant or agent ID",
            missing_identity_count,
        )
    return groups


def get_validated_domain_override() -> str | None:
    """Get and validate the domain override from environment variable.

    Returns the validated domain override, or None if not set or invalid.
    """
    domain_override = os.getenv(A365_OBSERVABILITY_DOMAIN_OVERRIDE, "").strip()
    if not domain_override:
        return None

    try:
        parsed = urlparse(domain_override)

        if parsed.scheme and "://" in domain_override:
            if parsed.scheme not in ("http", "https"):
                logger.warning(
                    "Invalid domain override '%s': scheme must be http or https, got '%s'",
                    domain_override,
                    parsed.scheme,
                )
                return None
            if not parsed.netloc:
                logger.warning("Invalid domain override '%s': missing hostname", domain_override)
                return None
        else:
            if domain_override.startswith(("http:", "https:")) and "://" not in domain_override:
                logger.warning(
                    "Invalid domain override '%s': malformed URL - protocol requires '://'",
                    domain_override,
                )
                return None
            if "/" in domain_override:
                logger.warning(
                    "Invalid domain override '%s': domain without protocol should not contain path separators (/)",
                    domain_override,
                )
                return None
    except Exception as e:
        logger.warning("Invalid domain override '%s': %s", domain_override, e)
        return None

    if domain_override.lower().startswith("http://"):
        logger.warning(
            "Domain override uses insecure HTTP. Telemetry data (including "
            "bearer tokens) will be transmitted in cleartext."
        )

    return domain_override


def build_export_url(endpoint: str, agent_id: str, tenant_id: str, use_s2s_endpoint: bool = False) -> str:
    """Construct the full export URL from endpoint and agent ID."""
    endpoint_path = (
        f"/observabilityService/tenants/{tenant_id}/otlp/agents/{agent_id}/traces"
        if use_s2s_endpoint
        else f"/observability/tenants/{tenant_id}/otlp/agents/{agent_id}/traces"
    )

    parsed = urlparse(endpoint)
    if parsed.scheme and "://" in endpoint:
        return f"{endpoint}{endpoint_path}?api-version=1"
    return f"https://{endpoint}{endpoint_path}?api-version=1"


def parse_retry_after(headers: dict[str, str]) -> float | None:
    """Parse the ``Retry-After`` header value.

    Only numeric (seconds) values are supported. HTTP-date values are ignored.
    """
    retry_after = headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except (ValueError, TypeError):
        return None


def is_agent365_exporter_enabled() -> bool:
    """Check if Agent365 exporter is enabled via environment variable."""
    enable_exporter = os.getenv(ENABLE_A365_OBSERVABILITY_EXPORTER, "").lower()
    return enable_exporter in ("true", "1", "yes", "on")


# ---------------------------------------------------------------------------
# Span size estimation and byte-level chunking
# ---------------------------------------------------------------------------

# Default upper bound on HTTP request body size in bytes. Provides ~100 KB
# headroom under the A365 1 MB server limit for estimator error and JSON/
# envelope overhead (e.g. resource attributes and scope wrappers).
DEFAULT_MAX_PAYLOAD_BYTES = 900_000

# Overhead constant for OTLP JSON span fixed fields (traceId, spanId,
# parentSpanId, kind, timestamps, status, scope wrapper, etc.). Intentionally
# generous to account for serializer variance.
_SPAN_BASE_OVERHEAD = 2000

# Overhead per attribute in OTLP JSON format. Covers key/value JSON wrapping.
_ATTR_OVERHEAD = 80

# Overhead per event in OTLP JSON.
_EVENT_OVERHEAD = 200


# Extra bytes per character to account for JSON escaping (quotes,
# backslashes, control characters, unicode escapes).  A factor of 1.1
# covers typical real-world content; the base overhead constants
# provide additional headroom.
_JSON_ESCAPE_FACTOR = 1.1


def _utf8_len(s: str) -> int:
    return len(s.encode("utf-8"))


def estimate_value_bytes(value: Any) -> int:
    """Estimate the serialized byte size of a single attribute value in OTLP/HTTP JSON."""
    if isinstance(value, str):
        return 40 + int(_utf8_len(value) * _JSON_ESCAPE_FACTOR)
    # bool is a subclass of int; check before sequence/list handling below
    if isinstance(value, bool):
        return 40
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return 60
        first = value[0]
        if isinstance(first, str):
            total = 60
            for s in value:
                total += 40 + int(_utf8_len(str(s)) * _JSON_ESCAPE_FACTOR)
            return total
        return 60 + 50 * len(value)
    return 40  # int/float/None/other


def estimate_span_bytes(span: dict[str, Any]) -> int:
    """Heuristic estimator for the serialized size of an OTLP span in HTTP JSON.

    Uses generous constants tuned to over-estimate by ~25-50%, providing
    headroom for JSON serializer variance (whitespace, enum representation,
    integer-as-string).
    """
    total = _SPAN_BASE_OVERHEAD
    name = span.get("name")
    if isinstance(name, str):
        total += _utf8_len(name)

    attributes = span.get("attributes")
    if attributes:
        for key, value in attributes.items():
            total += _ATTR_OVERHEAD
            total += _utf8_len(str(key))
            total += estimate_value_bytes(value)

    events = span.get("events")
    if events:
        for ev in events:
            total += _EVENT_OVERHEAD
            ev_name = ev.get("name") if isinstance(ev, dict) else None
            if isinstance(ev_name, str):
                total += _utf8_len(ev_name)
            ev_attrs = ev.get("attributes") if isinstance(ev, dict) else None
            if ev_attrs:
                for key, value in ev_attrs.items():
                    total += _ATTR_OVERHEAD
                    total += _utf8_len(str(key))
                    total += estimate_value_bytes(value)
    return total


T = TypeVar("T")


def chunk_by_size(
    items: Sequence[T],
    get_size: Callable[[T], int],
    max_chunk_bytes: int,
) -> list[list[T]]:
    """Split items into sub-batches whose cumulative estimated size stays under ``max_chunk_bytes``.

    Multi-item chunks are guaranteed to stay within the limit. A single item
    whose estimated size exceeds ``max_chunk_bytes`` forms its own one-item
    chunk (never silently dropped) even though that chunk exceeds the limit.

    Invariants:
    - Input order is preserved across chunks.
    - Empty input produces empty output.
    - No item is ever dropped.
    - No chunk is ever empty.

    Raises:
        ValueError: If ``max_chunk_bytes`` is not positive, or if ``get_size``
            returns a negative value for any item.
    """
    if max_chunk_bytes <= 0:
        raise ValueError(f"max_chunk_bytes must be positive, got {max_chunk_bytes}")

    chunks: list[list[T]] = []
    current: list[T] = []
    current_bytes = 0

    for item in items:
        item_bytes = get_size(item)
        if item_bytes < 0:
            raise ValueError(f"get_size returned a negative value ({item_bytes}); sizes must be non-negative")
        if current and current_bytes + item_bytes > max_chunk_bytes:
            chunks.append(current)
            current = []
            current_bytes = 0
        current.append(item)
        current_bytes += item_bytes

    if current:
        chunks.append(current)

    return chunks


_A365_DEFAULT_SCOPE = "api://9b975845-388f-4429-889e-eab1ef63949c/Agent365.Observability.OtelWrite"


def _create_fic_token_resolver(scope_override: Optional[str] = None) -> Callable[[str, str], Optional[str]]:
    """Create a token resolver using the FIC (Federated Identity Credential) flow.

    Uses MSAL's ``ConfidentialClientApplication`` with the ``fmi_path``
    parameter, which is the mechanism the agents SDK uses internally.

    This runs synchronously, which is safe because the batch span processor
    calls ``export`` from a worker thread, not the async event loop.

    Required environment variables:
      - ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID``
      - ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET``
      - ``CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID``
      - ``A365_AGENT_APP_INSTANCE_ID``
      - ``A365_AGENTIC_USER_ID``
    """
    import msal

    _cache: dict[str, tuple[str, float]] = {}  # key -> (token, expires_at)
    _lock = threading.Lock()

    def _resolve(agent_id: str, tenant_id: str) -> Optional[str]:
        cache_key = f"{tenant_id}:{agent_id}"

        with _lock:
            cached = _cache.get(cache_key)
            if cached is not None:
                token, expires_at = cached
                if time.time() < expires_at - 60:  # 60 s buffer
                    return token

        client_id = os.environ.get(A365_SERVICE_CLIENT_ID_ENV, "")
        client_secret = os.environ.get(A365_SERVICE_CLIENT_SECRET_ENV, "")
        cfg_tenant = os.environ.get(A365_SERVICE_TENANT_ID_ENV, tenant_id)
        instance_id = os.environ.get(A365_AGENT_APP_INSTANCE_ID_ENV, "")
        user_id = os.environ.get(A365_AGENTIC_USER_ID_ENV, "")

        if not all([client_id, client_secret, instance_id, user_id]):
            logger.debug(
                "FIC env vars incomplete — need %s, %s, %s, %s.",
                A365_SERVICE_CLIENT_ID_ENV,
                A365_SERVICE_CLIENT_SECRET_ENV,
                A365_AGENT_APP_INSTANCE_ID_ENV,
                A365_AGENTIC_USER_ID_ENV,
            )
            return None

        authority = f"https://login.microsoftonline.com/{cfg_tenant}"

        try:
            # Step 1: Agent application token via fmi_path
            # Uses the blueprint's credentials + fmi_path=instance_id
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
                scopes=[scope_override or _A365_DEFAULT_SCOPE],
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

            logger.debug("FIC token acquired for agent %s, tenant %s", agent_id, tenant_id)
            return access_token  # type: ignore[no-any-return]

        except Exception:
            logger.warning("FIC token flow failed.", exc_info=True)
            return None

    return _resolve


def _create_dac_token_resolver(scope_override: Optional[str] = None) -> Callable[[str, str], Optional[str]]:
    """Create a token resolver backed by ``DefaultAzureCredential``.

    The credential is lazily initialised on first call and cached for
    subsequent invocations (thread-safe).
    """
    _credential = None
    _lock = threading.Lock()
    scope = scope_override or _A365_DEFAULT_SCOPE

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
            token = _credential.get_token(scope)
            return token.token
        except Exception:
            logger.warning("Failed to acquire A365 token via DefaultAzureCredential.", exc_info=True)
            return None

    return _resolve


def _create_default_token_resolver(
    scope_override: Optional[str] = None,
) -> Callable[[str, str], Optional[str]]:
    """Create the default token resolver.

    Tries FIC first (if the required env vars are set), otherwise
    falls back to ``DefaultAzureCredential``.
    """
    fic_available = all(
        [
            os.environ.get(A365_SERVICE_CLIENT_ID_ENV),
            os.environ.get(A365_SERVICE_CLIENT_SECRET_ENV),
            os.environ.get(A365_AGENT_APP_INSTANCE_ID_ENV),
            os.environ.get(A365_AGENTIC_USER_ID_ENV),
        ]
    )

    if fic_available:
        logger.info("FIC env vars detected \u2014 using FIC token resolver for A365.")
        return _create_fic_token_resolver(scope_override=scope_override)
    logger.info("FIC env vars not set \u2014 falling back to DefaultAzureCredential for A365.")
    return _create_dac_token_resolver(scope_override=scope_override)


@dataclass
class A365Handlers:
    """Processors created for Agent365 export, mirroring ``OtlpHandlers``."""

    span_processors: List[SpanProcessor] = field(default_factory=list)


def is_a365_enabled(enable_a365: bool = False) -> bool:
    """Determine whether Agent365 export should be enabled."""
    return bool(enable_a365)


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean from an environment variable."""
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val in ("true", "1", "yes", "on")


def create_a365_components(
    token_resolver: Callable[[str, str], Optional[str]] | None = None,
) -> A365Handlers:
    """Create Agent365 span processors ready to be added to a TracerProvider.

    :param token_resolver: Optional callable ``(agent_id, tenant_id) -> str | None``.
        When provided, it is used instead of the default ``DefaultAzureCredential``
        resolver.  This allows callers to supply FIC-based or other custom tokens.

    All other configuration is read from environment variables:
      - ``ENABLE_A365_OBSERVABILITY_EXPORTER`` -- must be true for the HTTP exporter
      - ``A365_CLUSTER_CATEGORY`` -- defaults to ``"prod"``
      - ``A365_USE_S2S_ENDPOINT`` -- defaults to False
      - ``A365_SUPPRESS_INVOKE_AGENT_INPUT`` -- defaults to False
    """
    # pylint: disable=import-outside-toplevel,cyclic-import
    from microsoft.opentelemetry.a365.core.exporters.enriching_span_processor import _EnrichingBatchSpanProcessor
    from microsoft.opentelemetry.a365.core.exporters.agent365_exporter import _Agent365Exporter
    from microsoft.opentelemetry.a365.core.exporters.agent365_exporter_options import Agent365ExporterOptions
    from microsoft.opentelemetry.a365.core.exporters.span_processor import A365SpanProcessor

    if token_resolver is None:
        token_resolver = _create_default_token_resolver()
    cluster_category = os.environ.get(A365_CLUSTER_CATEGORY_ENV, "prod")
    use_s2s_endpoint = _env_bool(A365_USE_S2S_ENDPOINT_ENV)
    suppress_invoke_agent_input = _env_bool(A365_SUPPRESS_INVOKE_AGENT_INPUT_ENV)

    options = Agent365ExporterOptions(
        cluster_category=cluster_category,
        token_resolver=token_resolver,
        use_s2s_endpoint=use_s2s_endpoint,
    )

    # Create the exporter (Agent365 HTTP or console fallback)
    if is_agent365_exporter_enabled() and options.token_resolver is not None:
        exporter = _Agent365Exporter(
            token_resolver=options.token_resolver,
            cluster_category=options.cluster_category,
            use_s2s_endpoint=options.use_s2s_endpoint,
            max_payload_bytes=options.max_payload_bytes,
        )
    else:
        logger.warning(
            "ENABLE_A365_OBSERVABILITY_EXPORTER not set or token_resolver not provided. "
            "A365 exporter will not be active."
        )
        return A365Handlers()

    # Enriching batch processor wrapping the exporter
    batch_processor = _EnrichingBatchSpanProcessor(
        exporter,
        suppress_invoke_agent_input=suppress_invoke_agent_input,
        max_queue_size=options.max_queue_size,
        schedule_delay_millis=options.scheduled_delay_ms,
        export_timeout_millis=options.exporter_timeout_ms,
        max_export_batch_size=options.max_export_batch_size,
    )

    # Baggage-to-span attribute propagation processor. Tenant/agent IDs
    # are supplied per-request via BaggageMiddleware / BaggageBuilder.
    baggage_processor = A365SpanProcessor()

    return A365Handlers(span_processors=[batch_processor, baggage_processor])
