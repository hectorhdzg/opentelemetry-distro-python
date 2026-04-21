# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import unittest
from unittest.mock import patch

from microsoft.opentelemetry.a365 import (
    A365Handlers,
    create_a365_components,
    is_a365_enabled,
)


class TestIsA365Enabled(unittest.TestCase):
    def test_disabled_by_default(self):
        self.assertFalse(is_a365_enabled())

    def test_enabled_when_true(self):
        self.assertTrue(is_a365_enabled(enable_a365=True))

    def test_disabled_when_false(self):
        self.assertFalse(is_a365_enabled(enable_a365=False))


class TestCreateA365Components(unittest.TestCase):
    @patch.dict(os.environ, {"ENABLE_A365_OBSERVABILITY_EXPORTER": "true"})
    def test_creates_handlers_with_processors(self):
        handlers = create_a365_components()
        self.assertIsInstance(handlers, A365Handlers)
        self.assertEqual(len(handlers.span_processors), 2)

    @patch.dict(os.environ, {"ENABLE_A365_OBSERVABILITY_EXPORTER": "false"})
    def test_returns_empty_when_exporter_disabled(self):
        handlers = create_a365_components()
        self.assertIsInstance(handlers, A365Handlers)
        self.assertEqual(len(handlers.span_processors), 0)

    @patch.dict(
        os.environ,
        {
            "ENABLE_A365_OBSERVABILITY_EXPORTER": "true",
            "A365_CLUSTER_CATEGORY": "staging",
            "A365_USE_S2S_ENDPOINT": "true",
            "A365_SUPPRESS_INVOKE_AGENT_INPUT": "true",
        },
    )
    def test_reads_options_from_env_vars(self):
        handlers = create_a365_components()
        self.assertEqual(len(handlers.span_processors), 2)

    @patch.dict(
        os.environ,
        {
            "ENABLE_A365_OBSERVABILITY_EXPORTER": "true",
            "A365_TENANT_ID": "t1",
            "A365_AGENT_ID": "a1",
        },
    )
    def test_passes_identity_from_env_to_span_processor(self):
        handlers = create_a365_components()
        from microsoft.opentelemetry.a365.core.exporters.span_processor import A365SpanProcessor

        span_proc = handlers.span_processors[1]
        self.assertIsInstance(span_proc, A365SpanProcessor)
        self.assertEqual(span_proc._tenant_id, "t1")
        self.assertEqual(span_proc._agent_id, "a1")

    @patch.dict(os.environ, {"ENABLE_A365_OBSERVABILITY_EXPORTER": "true"}, clear=False)
    def test_identity_defaults_to_none_when_env_not_set(self):
        # Remove env vars if present
        env = os.environ.copy()
        env.pop("A365_TENANT_ID", None)
        env.pop("A365_AGENT_ID", None)
        with patch.dict(os.environ, env, clear=True):
            os.environ["ENABLE_A365_OBSERVABILITY_EXPORTER"] = "true"
            handlers = create_a365_components()

            span_proc = handlers.span_processors[1]
            self.assertIsNone(span_proc._tenant_id)
            self.assertIsNone(span_proc._agent_id)

    @patch.dict(os.environ, {"ENABLE_A365_OBSERVABILITY_EXPORTER": "true"})
    def test_baggage_processor_is_a365_span_processor(self):
        handlers = create_a365_components()
        from microsoft.opentelemetry.a365.core.exporters.span_processor import A365SpanProcessor

        span_proc = handlers.span_processors[1]
        self.assertIsInstance(span_proc, A365SpanProcessor)


class TestA365HandlersDefault(unittest.TestCase):
    def test_default_empty(self):
        handlers = A365Handlers()
        self.assertEqual(handlers.span_processors, [])


if __name__ == "__main__":
    unittest.main()
