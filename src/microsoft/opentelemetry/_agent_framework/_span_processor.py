# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from opentelemetry.sdk.trace.export import SpanProcessor


class AgentFrameworkSpanProcessor(SpanProcessor):
    """SpanProcessor for Agent Framework.

    Kept for interface compatibility. Both ``on_start`` and ``on_end``
    are intentional no-ops.
    """

    TOOL_CALL_RESULT_TAG = "gen_ai.tool.call.result"

    def __init__(self, service_name: str | None = None):
        self.service_name = service_name
        super().__init__()

    def on_start(self, span, parent_context=None):  # type: ignore[no-untyped-def, override]
        pass

    def on_end(self, span):  # type: ignore[no-untyped-def, override]
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
