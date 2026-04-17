# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# This is a temporary internal LangChain instrumentation. It will be replaced
# by the upstream OpenTelemetry contrib LangChain instrumentation once that
# package is published to PyPI, conforms to the latest GenAI semantic
# conventions, and is functionally mature. See PLANNING.md for migration criteria.

from microsoft.opentelemetry._genai._langchain._tracer_instrumentor import LangChainInstrumentor

__all__ = ["LangChainInstrumentor"]
