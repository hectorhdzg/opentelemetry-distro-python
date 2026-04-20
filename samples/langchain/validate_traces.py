#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
E2E validation: verifies the LangChain tracer produces spans that comply
with the OTel GenAI semantic conventions.

Uses FakeListLLM (no API key needed).
"""

import os
import sys

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import set_tracer_provider, SpanKind


class MemoryExporter(SpanExporter):
    def __init__(self):
        self._spans = []

    def export(self, spans):
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self):
        return list(self._spans)

    def shutdown(self):
        pass


def main(): # pylint: disable=too-many-statements
    # Enable content capture for validation (must be set before instrumentation)
    os.environ["OTEL_SEMCONV_STABILITY_OPT_IN"] = "gen_ai_latest_experimental"
    os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "SPAN_ONLY"

    mem = MemoryExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "e2e-validation"}))
    provider.add_span_processor(SimpleSpanProcessor(mem))
    set_tracer_provider(provider)

    from microsoft.opentelemetry._genai._langchain._tracer_instrumentor import LangChainInstrumentor

    inst = LangChainInstrumentor()
    inst.instrument(
        tracer_provider=provider,
        agent_name="TestAgent",
        agent_id="agent-123",
        agent_description="E2E test agent",
        agent_version="1.0.0",
        server_address="test.example.com",
        server_port=443,
    )

    # ── Sample 1: Simple LLM call ───────────────────────────────────────
    from langchain_community.llms.fake import FakeListLLM

    llm = FakeListLLM(responses=["Paris is the capital of France."])
    llm.invoke("What is the capital of France?")

    # ── Sample 2: Chain (prompt → LLM → parser) ────────────────────────
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm2 = FakeListLLM(responses=["42 is the answer."])
    chain = ChatPromptTemplate.from_messages([
        ("system", "You are helpful."),
        ("human", "{q}"),
    ]) | llm2 | StrOutputParser()
    chain.invoke({"q": "What is 6*7?"})

    # ── Sample 3: Tool invocation ───────────────────────────────────────
    from langchain_core.tools import tool

    @tool
    def get_weather(location: str) -> str:
        """Get the weather for a location."""
        return f"Sunny, 72°F in {location}"

    get_weather.invoke({"location": "San Francisco"})

    # ── Flush and analyse ───────────────────────────────────────────────
    provider.force_flush()
    spans = mem.get_finished_spans()

    llm_spans = [s for s in spans if s.attributes.get("gen_ai.operation.name") == "chat"]
    tool_spans = [s for s in spans if s.attributes.get("gen_ai.operation.name") == "execute_tool"]

    ok = True

    def check(label, condition, detail=""):
        nonlocal ok
        status = "✅" if condition else "❌"
        if not condition:
            ok = False
        print(f"  {status} {label}" + (f" — {detail}" if detail else ""))

    # ── LLM span checks ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"LLM SPANS ({len(llm_spans)} found)")
    print(f"{'='*60}")

    for span in llm_spans:
        attrs = span.attributes
        print(f"\n  Span: {span.name}")
        check("gen_ai.operation.name present", "gen_ai.operation.name" in attrs)
        check("gen_ai.operation.name == 'chat'", attrs.get("gen_ai.operation.name") == "chat")
        check("gen_ai.provider.name present", "gen_ai.provider.name" in attrs)
        check("SpanKind is CLIENT", span.kind == SpanKind.CLIENT,
              f"actual: {span.kind.name}")
        check("Span name is not 'chat None'", "None" not in span.name,
              f"actual: '{span.name}'")
        check("gen_ai.response.finish_reasons present",
              "gen_ai.response.finish_reasons" in attrs)

    # ── Tool span checks ───────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"TOOL SPANS ({len(tool_spans)} found)")
    print(f"{'='*60}")

    for span in tool_spans:
        attrs = span.attributes
        print(f"\n  Span: {span.name}")
        check("gen_ai.operation.name present", "gen_ai.operation.name" in attrs)
        check("gen_ai.operation.name == 'execute_tool'",
              attrs.get("gen_ai.operation.name") == "execute_tool")
        check("gen_ai.tool.name present", "gen_ai.tool.name" in attrs)
        check("gen_ai.tool.type == 'function'",
              attrs.get("gen_ai.tool.type") == "function",
              f"actual: {attrs.get('gen_ai.tool.type')}")
        check("gen_ai.tool.description present", "gen_ai.tool.description" in attrs)
        check("SpanKind is INTERNAL", span.kind == SpanKind.INTERNAL,
              f"actual: {span.kind.name}")
        check("Span name format 'execute_tool <name>'",
              span.name.startswith("execute_tool "))
        # Content capture enabled — args/results should be present
        check("gen_ai.tool.call.arguments present (content on)",
              "gen_ai.tool.call.arguments" in attrs)
        check("gen_ai.tool.call.result present (content on)",
              "gen_ai.tool.call.result" in attrs)

    # ── All-span attribute dump ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print("ALL SPANS ATTRIBUTE DUMP")
    print(f"{'='*60}")
    for span in spans:
        print(f"\n  [{span.kind.name}] {span.name}")
        for k, v in sorted(span.attributes.items()):
            val = repr(v) if len(repr(v)) < 120 else repr(v)[:120] + "..."
            print(f"    {k} = {val}")

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if ok:
        print("✅ ALL CHECKS PASSED")
    else:
        print("❌ SOME CHECKS FAILED")
    print(f"{'='*60}")

    inst.uninstrument()
    provider.shutdown()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
