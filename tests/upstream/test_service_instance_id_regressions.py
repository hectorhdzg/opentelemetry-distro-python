import os

import pytest
import opentelemetry.sdk.resources as resources_module
from opentelemetry.resource.detector.azure.vm import AzureVMResourceDetector
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import (
    Resource,
    ServiceInstanceIdResourceDetector,
    get_aggregated_resources,
)
from opentelemetry.sdk.trace import TracerProvider


@pytest.fixture(autouse=True)
def reset_generated_service_instance_id(monkeypatch):
    monkeypatch.setattr(resources_module, "_service_instance_id", None)
    monkeypatch.setattr(resources_module, "_service_instance_id_pid", None)
    monkeypatch.delenv("OTEL_RESOURCE_ATTRIBUTES", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)


def test_generated_service_instance_id_is_stable_within_one_process():
    detector = ServiceInstanceIdResourceDetector()

    first = detector.detect().attributes["service.instance.id"]
    second = detector.detect().attributes["service.instance.id"]

    assert first == second


def test_generated_service_instance_id_changes_when_process_identity_changes(monkeypatch):
    detector = ServiceInstanceIdResourceDetector()
    parent_id = detector.detect().attributes["service.instance.id"]
    child_pid = os.getpid() + 1

    monkeypatch.setattr(resources_module.os, "getpid", lambda: child_pid)
    child_id = detector.detect().attributes["service.instance.id"]

    assert child_id != parent_id


def test_resource_create_does_not_generate_unbounded_ids_in_one_process():
    instance_ids = {Resource.create().attributes["service.instance.id"] for _ in range(100)}

    assert len(instance_ids) == 1


def test_explicit_resource_service_instance_id_overrides_generated_id():
    resource = Resource.create({"service.instance.id": "explicit-instance"})

    assert resource.attributes["service.instance.id"] == "explicit-instance"


def test_environment_service_instance_id_overrides_generated_id(monkeypatch):
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "service.instance.id=pod-123")

    resource = Resource.create()

    assert resource.attributes["service.instance.id"] == "pod-123"


def test_azure_vm_detector_does_not_override_environment_service_instance_id(monkeypatch):
    monkeypatch.setenv("OTEL_EXPERIMENTAL_RESOURCE_DETECTORS", "azure_vm")
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "service.instance.id=pod-123")
    monkeypatch.setattr(
        AzureVMResourceDetector,
        "detect",
        lambda self: Resource(
            {
                "cloud.platform": "azure_vm",
                "host.id": "vm-id",
                "service.instance.id": "vm-id",
            }
        ),
    )

    resource = Resource.create()

    assert resource.attributes["cloud.platform"] == "azure_vm"
    assert resource.attributes["host.id"] == "vm-id"
    assert resource.attributes["service.instance.id"] == "pod-123"


def test_aks_identity_is_not_replaced_by_vm_detector(monkeypatch):
    monkeypatch.setenv("AKS_ARM_NAMESPACE_ID", "aks-resource-id")
    monkeypatch.setenv("OTEL_EXPERIMENTAL_RESOURCE_DETECTORS", "azure_vm")
    monkeypatch.setenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        "k8s.pod.name=orders-7f8c9,service.instance.id=orders-7f8c9",
    )

    resource = Resource.create()

    assert resource.attributes["k8s.pod.name"] == "orders-7f8c9"
    assert resource.attributes["service.instance.id"] == "orders-7f8c9"
    assert "cloud.platform" not in resource.attributes
    assert "host.id" not in resource.attributes


@pytest.mark.xfail(
    strict=True,
    reason="opentelemetry-sdk 1.44 runs the generated service_instance detector after Azure detectors",
)
def test_azure_app_service_instance_id_overrides_generated_id(monkeypatch):
    monkeypatch.setenv("OTEL_EXPERIMENTAL_RESOURCE_DETECTORS", "azure_app_service")
    monkeypatch.setenv("WEBSITE_SITE_NAME", "orders-api")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "app-service-worker")

    resource = Resource.create()

    assert resource.attributes["service.instance.id"] == "app-service-worker"


@pytest.mark.xfail(
    strict=True,
    reason="opentelemetry-sdk 1.44 merges process-dependent detector refreshes over explicit resources",
)
def test_initial_resource_service_instance_id_has_highest_aggregation_priority():
    resource = get_aggregated_resources(
        [ServiceInstanceIdResourceDetector()],
        initial_resource=Resource({"service.instance.id": "explicit-instance"}),
    )

    assert resource.attributes["service.instance.id"] == "explicit-instance"


def _provider_resource(provider):
    if isinstance(provider, MeterProvider):
        return provider._sdk_config.resource
    return provider.resource


@pytest.mark.parametrize("provider_class", [TracerProvider, MeterProvider, LoggerProvider])
@pytest.mark.xfail(
    strict=True,
    reason="opentelemetry-sdk 1.44 fork refresh overwrites explicit service.instance.id",
)
def test_provider_fork_refresh_preserves_explicit_instance_id(monkeypatch, provider_class):
    provider = provider_class(
        resource=Resource({"service.instance.id": "explicit-instance"}),
        shutdown_on_exit=False,
    )
    child_pid = os.getpid() + 1
    monkeypatch.setattr(resources_module.os, "getpid", lambda: child_pid)

    try:
        provider._handle_fork()
        assert _provider_resource(provider).attributes["service.instance.id"] == "explicit-instance"
    finally:
        provider.shutdown()


@pytest.mark.parametrize("provider_class", [TracerProvider, MeterProvider, LoggerProvider])
def test_provider_fork_refresh_regenerates_generated_instance_id(monkeypatch, provider_class):
    provider = provider_class(shutdown_on_exit=False)
    parent_id = _provider_resource(provider).attributes["service.instance.id"]
    child_pid = os.getpid() + 1
    monkeypatch.setattr(resources_module.os, "getpid", lambda: child_pid)

    try:
        provider._handle_fork()
        child_id = _provider_resource(provider).attributes["service.instance.id"]
        assert child_id != parent_id
    finally:
        provider.shutdown()
