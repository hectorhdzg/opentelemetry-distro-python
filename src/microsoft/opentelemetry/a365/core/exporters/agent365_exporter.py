# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""Agent365 span exporter.

Vendored from microsoft-agents-a365-observability-core exporters/agent365_exporter.py.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any, final

import requests
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

from microsoft.opentelemetry.a365.core.exporters.utils import (
    build_export_url,
    get_validated_domain_override,
    hex_span_id,
    hex_trace_id,
    kind_name,
    parse_retry_after,
    partition_by_identity,
    status_name,
    truncate_span,
)

# mypy: disable-error-code="import-untyped, union-attr"

# Hardcoded constants - not configurable
DEFAULT_HTTP_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_ENDPOINT_URL = "https://agent365.svc.cloud.microsoft"

logger = logging.getLogger(__name__)


@final
# pylint: disable=broad-exception-caught
class _Agent365Exporter(SpanExporter):
    """Agent365 span exporter.

    * Partitions spans by (tenantId, agentId)
    * Builds OTLP-like JSON: resourceSpans -> scopeSpans -> spans
    * POSTs per group to the Agent365 observability endpoint
    * Adds Bearer token via token_resolver(agentId, tenantId)
    """

    def __init__(
        self,
        token_resolver: Callable[[str, str], str | None],
        cluster_category: str = "prod",
        use_s2s_endpoint: bool = False,
    ):
        if token_resolver is None:
            raise ValueError("token_resolver must be provided.")
        self._session = requests.Session()
        self._closed = False
        self._lock = threading.Lock()
        self._token_resolver = token_resolver
        self._cluster_category = cluster_category
        self._use_s2s_endpoint = use_s2s_endpoint
        self._domain_override = get_validated_domain_override()

    # ------------- SpanExporter API -----------------

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if self._closed:
            return SpanExportResult.FAILURE

        try:
            groups = partition_by_identity(spans)
            if not groups:
                logger.info("No spans with tenant/agent identity found; nothing exported.")
                return SpanExportResult.SUCCESS

            total_spans = sum(len(activities) for activities in groups.values())
            logger.debug(
                "Found %d identity groups with %d total spans to export",
                len(groups),
                total_spans,
            )

            any_failure = False
            for (tenant_id, agent_id), activities in groups.items():
                payload = self._build_export_request(activities)
                body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

                endpoint = self._domain_override or DEFAULT_ENDPOINT_URL
                url = build_export_url(endpoint, agent_id, tenant_id, self._use_s2s_endpoint)

                logger.debug(
                    "Exporting %d spans to endpoint: %s (tenant: %s, agent: %s)",
                    len(activities),
                    url,
                    tenant_id,
                    agent_id,
                )

                headers: dict[str, str] = {"content-type": "application/json"}
                try:
                    token = self._token_resolver(agent_id, tenant_id)
                    if token:
                        if not url.lower().startswith("https://"):
                            logger.warning(
                                "Bearer token is being sent over a non-HTTPS connection. "
                                "This may expose credentials in transit."
                            )
                        headers["authorization"] = f"Bearer {token}"
                        logger.debug("Token resolved successfully for agent %s", agent_id)
                    else:
                        logger.debug("No token returned for agent %s", agent_id)
                except Exception as e:
                    logger.error(
                        "Token resolution failed for agent %s, tenant %s: %s",
                        agent_id,
                        tenant_id,
                        e,
                    )
                    any_failure = True
                    continue

                ok = self._post_with_retries(url, body, headers)
                if not ok:
                    any_failure = True

            return SpanExportResult.FAILURE if any_failure else SpanExportResult.SUCCESS

        except Exception as e:
            logger.error("Export failed with exception: %s", e)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._session.close()
            except Exception:
                pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    # ------------- HTTP helper ----------------------

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def _post_with_retries(self, url: str, body: str, headers: dict[str, str]) -> bool:
        for attempt in range(DEFAULT_MAX_RETRIES + 1):
            try:
                resp = self._session.post(
                    url,
                    data=body.encode("utf-8"),
                    headers=headers,
                    timeout=DEFAULT_HTTP_TIMEOUT_SECONDS,
                )

                correlation_id = resp.headers.get("x-ms-correlation-id") or resp.headers.get("request-id") or "N/A"

                if 200 <= resp.status_code < 300:
                    logger.debug(
                        "HTTP %d success on attempt %d. Correlation ID: %s. Response: %s",
                        resp.status_code,
                        attempt + 1,
                        correlation_id,
                        self._truncate_text(resp.text, 200),
                    )
                    return True

                response_text = self._truncate_text(resp.text, 500)

                if resp.status_code in (408, 429) or 500 <= resp.status_code < 600:
                    retry_after = parse_retry_after(resp.headers)
                    if attempt < DEFAULT_MAX_RETRIES:
                        if retry_after is not None:
                            time.sleep(min(retry_after, 60.0))
                        else:
                            time.sleep(0.5 * (2**attempt))
                        continue
                    logger.error(
                        "HTTP %d final failure after %d attempts. Correlation ID: %s. Response: %s",
                        resp.status_code,
                        DEFAULT_MAX_RETRIES + 1,
                        correlation_id,
                        response_text,
                    )
                else:
                    logger.error(
                        "HTTP %d non-retryable error. Correlation ID: %s. Response: %s. "
                        "WWW-Authenticate: %s. Response headers: %s",
                        resp.status_code,
                        correlation_id,
                        response_text,
                        resp.headers.get("www-authenticate", "N/A"),
                        dict(resp.headers),
                    )
                return False

            except requests.RequestException as e:
                if attempt < DEFAULT_MAX_RETRIES:
                    time.sleep(0.5 * (2**attempt))
                    continue
                logger.error("Request failed after %d attempts: %s", DEFAULT_MAX_RETRIES + 1, e)
                return False
        return False

    # ------------- Payload mapping ------------------

    def _build_export_request(self, spans: Sequence[ReadableSpan]) -> dict[str, Any]:
        scope_map: dict[tuple[str, str | None], list[dict[str, Any]]] = {}

        for sp in spans:
            scope = sp.instrumentation_scope
            scope_key = (scope.name, scope.version)
            scope_map.setdefault(scope_key, []).append(self._map_span(sp))

        scope_spans: list[dict[str, Any]] = []
        for (name, version), mapped_spans in scope_map.items():
            scope_spans.append(
                {
                    "scope": {"name": name, "version": version},
                    "spans": mapped_spans,
                }
            )

        resource_attrs: dict[str, Any] = {}
        if spans:
            resource_attrs = dict(getattr(spans[0].resource, "attributes", {}) or {})

        return {
            "resourceSpans": [
                {
                    "resource": {"attributes": resource_attrs or None},
                    "scopeSpans": scope_spans,
                }
            ]
        }

    def _map_span(self, sp: ReadableSpan) -> dict[str, Any]:
        ctx = sp.context

        parent_span_id = None
        if sp.parent is not None and sp.parent.span_id != 0:
            parent_span_id = hex_span_id(sp.parent.span_id)

        attrs = dict(sp.attributes or {})

        events: list[dict[str, Any]] | None = None
        if sp.events:
            events = []
            for ev in sp.events:
                ev_attrs = dict(ev.attributes or {}) if ev.attributes else None
                events.append(
                    {
                        "timeUnixNano": ev.timestamp,
                        "name": ev.name,
                        "attributes": ev_attrs,
                    }
                )

        links: list[dict[str, Any]] | None = None
        if sp.links:
            links = []
            for ln in sp.links:
                ln_attrs = dict(ln.attributes or {}) if ln.attributes else None
                links.append(
                    {
                        "traceId": hex_trace_id(ln.context.trace_id),
                        "spanId": hex_span_id(ln.context.span_id),
                        "attributes": ln_attrs,
                    }
                )

        status_code = sp.status.status_code if sp.status else StatusCode.UNSET
        status = {
            "code": status_name(status_code),
            "message": getattr(sp.status, "description", "") or "",
        }

        span_dict: dict[str, Any] = {
            "traceId": hex_trace_id(ctx.trace_id),
            "spanId": hex_span_id(ctx.span_id),
            "parentSpanId": parent_span_id,
            "name": sp.name,
            "kind": kind_name(sp.kind),
            "startTimeUnixNano": sp.start_time,
            "endTimeUnixNano": sp.end_time,
            "attributes": attrs or None,
            "events": events,
            "links": links,
            "status": status,
        }

        return truncate_span(span_dict)
