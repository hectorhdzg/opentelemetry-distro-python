import socket

import pytest


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    def unexpected_network_call(*args, **kwargs):
        pytest.fail("upstream compatibility tests must not perform external network calls")

    monkeypatch.delenv("OTEL_EXPERIMENTAL_RESOURCE_DETECTORS", raising=False)
    monkeypatch.setattr(socket, "create_connection", unexpected_network_call)
    monkeypatch.setattr("requests.sessions.Session.request", unexpected_network_call)
