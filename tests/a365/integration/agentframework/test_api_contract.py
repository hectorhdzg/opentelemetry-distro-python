# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from inspect import signature

import pytest

observability = pytest.importorskip("agent_framework.observability")


def test_enable_instrumentation_supports_distro_options():
    parameters = signature(observability.enable_instrumentation).parameters

    assert "enable_message_events" in parameters
    assert "force" in parameters
