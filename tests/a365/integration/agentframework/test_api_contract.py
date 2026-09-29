# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from inspect import signature

from agent_framework.observability import enable_instrumentation


def test_enable_instrumentation_supports_distro_options():
    parameters = signature(enable_instrumentation).parameters

    assert "enable_message_events" in parameters
    assert "force" in parameters
