# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import unittest
from unittest.mock import MagicMock, patch

from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import SpanKind, StatusCode

from microsoft.opentelemetry.a365.core.exporters.agent365_exporter import (
    _Agent365Exporter,
)


def _make_span(
    tenant_id="t1",
    agent_id="a1",
    name="test_span",
    trace_id=0x1234,
    span_id=0x5678,
):
    span = MagicMock()
    span.name = name
    span.attributes = {
        "microsoft.tenant.id": tenant_id,
        "gen_ai.agent.id": agent_id,
    }

    ctx = MagicMock()
    ctx.trace_id = trace_id
    ctx.span_id = span_id
    span.context = ctx

    span.parent = None
    span.kind = SpanKind.INTERNAL
    span.start_time = 1000000000
    span.end_time = 2000000000

    status = MagicMock()
    status.status_code = StatusCode.OK
    status.description = ""
    span.status = status

    span.events = []
    span.links = []

    scope = MagicMock()
    scope.name = "test_scope"
    scope.version = "1.0"
    span.instrumentation_scope = scope

    resource = MagicMock()
    resource.attributes = {"service.name": "test-service"}
    span.resource = resource

    return span


class TestAgent365ExporterInit(unittest.TestCase):
    def test_raises_on_none_resolver(self):
        with self.assertRaises(ValueError):
            _Agent365Exporter(token_resolver=None)

    def test_raises_on_zero_max_payload_bytes(self):
        with self.assertRaises(ValueError):
            _Agent365Exporter(token_resolver=lambda a, t: "token", max_payload_bytes=0)

    def test_raises_on_negative_max_payload_bytes(self):
        with self.assertRaises(ValueError):
            _Agent365Exporter(token_resolver=lambda a, t: "token", max_payload_bytes=-1)

    def test_creates_with_valid_resolver(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        self.assertIsNotNone(exporter)
        exporter.shutdown()


class TestAgent365ExporterExport(unittest.TestCase):
    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {}, clear=True)
    def test_export_success(self, mock_post):
        mock_post.return_value = True
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        span = _make_span()
        result = exporter.export([span])
        self.assertEqual(result, SpanExportResult.SUCCESS)
        mock_post.assert_called_once()
        exporter.shutdown()

    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {}, clear=True)
    def test_export_failure(self, mock_post):
        mock_post.return_value = False
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        span = _make_span()
        result = exporter.export([span])
        self.assertEqual(result, SpanExportResult.FAILURE)
        exporter.shutdown()

    @patch.dict(os.environ, {}, clear=True)
    def test_export_no_identity_spans(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        span = MagicMock()
        span.attributes = {}
        result = exporter.export([span])
        self.assertEqual(result, SpanExportResult.SUCCESS)
        exporter.shutdown()

    @patch.dict(os.environ, {}, clear=True)
    def test_export_after_shutdown(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        exporter.shutdown()
        span = _make_span()
        result = exporter.export([span])
        self.assertEqual(result, SpanExportResult.FAILURE)

    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {}, clear=True)
    def test_export_partitions_by_identity(self, mock_post):
        mock_post.return_value = True
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        s1 = _make_span(tenant_id="t1", agent_id="a1")
        s2 = _make_span(tenant_id="t2", agent_id="a2")
        result = exporter.export([s1, s2])
        self.assertEqual(result, SpanExportResult.SUCCESS)
        self.assertEqual(mock_post.call_count, 2)
        exporter.shutdown()

    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {}, clear=True)
    def test_token_resolver_called_with_agent_tenant(self, mock_post):
        mock_post.return_value = True
        resolver = MagicMock(return_value="token123")
        exporter = _Agent365Exporter(token_resolver=resolver)
        span = _make_span(tenant_id="my_tenant", agent_id="my_agent")
        exporter.export([span])
        resolver.assert_called_once_with("my_agent", "my_tenant")
        exporter.shutdown()

    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {}, clear=True)
    def test_token_resolution_failure_continues(self, mock_post):
        resolver = MagicMock(side_effect=Exception("auth error"))
        exporter = _Agent365Exporter(token_resolver=resolver)
        span = _make_span()
        result = exporter.export([span])
        self.assertEqual(result, SpanExportResult.FAILURE)
        mock_post.assert_not_called()
        exporter.shutdown()

    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {"A365_OBSERVABILITY_DOMAIN_OVERRIDE": "https://custom.host.com"})
    def test_domain_override(self, mock_post):
        mock_post.return_value = True
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        span = _make_span()
        exporter.export([span])
        url_arg = mock_post.call_args[0][0]
        self.assertIn("custom.host.com", url_arg)
        exporter.shutdown()


class TestAgent365ExporterBuildRequest(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_build_export_request_structure(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        span = _make_span()
        mapped_spans = exporter._map_and_truncate_spans([span])
        resource_attrs = exporter._get_resource_attributes([span])
        payload = exporter._build_envelope(mapped_spans, resource_attrs)
        self.assertIn("resourceSpans", payload)
        resource_spans = payload["resourceSpans"]
        self.assertEqual(len(resource_spans), 1)
        self.assertIn("scopeSpans", resource_spans[0])
        self.assertIn("resource", resource_spans[0])
        exporter.shutdown()

    @patch.dict(os.environ, {}, clear=True)
    def test_map_span_basic_fields(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        span = _make_span(name="my_span")
        mapped = exporter._map_span(span)
        self.assertEqual(mapped["name"], "my_span")
        self.assertIn("traceId", mapped)
        self.assertIn("spanId", mapped)
        self.assertIn("status", mapped)
        self.assertIn("startTimeUnixNano", mapped)
        self.assertIn("endTimeUnixNano", mapped)
        exporter.shutdown()


class TestAgent365ExporterForceFlush(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_force_flush_returns_true(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        self.assertTrue(exporter.force_flush())
        exporter.shutdown()


class TestAgent365ExporterShutdown(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_double_shutdown_safe(self):
        exporter = _Agent365Exporter(token_resolver=lambda a, t: "token")
        exporter.shutdown()
        exporter.shutdown()  # should not raise


class TestAgent365ExporterS2S(unittest.TestCase):
    @patch("microsoft.opentelemetry.a365.core.exporters.agent365_exporter._Agent365Exporter._post_with_retries")
    @patch.dict(os.environ, {}, clear=True)
    def test_s2s_endpoint_url(self, mock_post):
        mock_post.return_value = True
        exporter = _Agent365Exporter(
            token_resolver=lambda a, t: "token",
            use_s2s_endpoint=True,
        )
        span = _make_span()
        exporter.export([span])
        url_arg = mock_post.call_args[0][0]
        self.assertIn("/observabilityService/", url_arg)
        exporter.shutdown()


if __name__ == "__main__":
    unittest.main()
