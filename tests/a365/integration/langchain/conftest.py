# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""LangChain-specific test fixtures.

The OpenAI v2 instrumentor (auto-enabled by the distro) crashes when
LangChain calls Azure OpenAI because ``model`` is not in the call kwargs
(Azure uses deployment-based routing). Work around this by temporarily
uninstrumenting OpenAI v2 for LangChain tests.
"""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _uninstrument_openai_v2():
    """Disable the OpenAI v2 instrumentor so LangChain can call Azure OpenAI."""
    try:
        from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

        instrumentor = OpenAIInstrumentor()
        if instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.uninstrument()
            yield
            instrumentor.instrument()
        else:
            yield
    except ImportError:
        yield
