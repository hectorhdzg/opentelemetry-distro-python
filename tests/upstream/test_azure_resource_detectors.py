import json
import os
from importlib.metadata import entry_points
from urllib.error import URLError

import pytest
from opentelemetry.resource.detector.azure.app_service import AzureAppServiceResourceDetector
from opentelemetry.resource.detector.azure.functions import AzureFunctionsResourceDetector
from opentelemetry.resource.detector.azure.vm import AzureVMResourceDetector
from opentelemetry.sdk.environment_variables import OTEL_EXPERIMENTAL_RESOURCE_DETECTORS
from opentelemetry.sdk.resources import Resource, ResourceDetector, get_aggregated_resources

from microsoft.opentelemetry._azure_monitor._constants import RESOURCE_ARG
from microsoft.opentelemetry._azure_monitor._utils.configurations import _default_resource

_AZURE_ENVIRONMENT_VARIABLES = (
    "AKS_ARM_NAMESPACE_ID",
    "FUNCTIONS_WORKER_RUNTIME",
    "REGION_NAME",
    "WEBSITE_HOME_STAMPNAME",
    "WEBSITE_HOSTNAME",
    "WEBSITE_INSTANCE_ID",
    "WEBSITE_MEMORY_LIMIT_MB",
    "WEBSITE_OWNER_NAME",
    "WEBSITE_RESOURCE_GROUP",
    "WEBSITE_SITE_NAME",
    "WEBSITE_SLOT_NAME",
)


@pytest.fixture(autouse=True)
def clear_azure_environment(monkeypatch):
    for name in _AZURE_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv(OTEL_EXPERIMENTAL_RESOURCE_DETECTORS, raising=False)


def test_azure_resource_detector_entry_points_remain_loadable():
    detector_entry_points = {
        entry_point.name: entry_point
        for entry_point in entry_points(group="opentelemetry_resource_detector")
        if entry_point.name.startswith("azure_")
    }

    required_detectors = {"azure_app_service", "azure_functions", "azure_vm"}
    assert required_detectors <= detector_entry_points.keys()
    for name in required_detectors:
        entry_point = detector_entry_points[name]
        detector_class = entry_point.load()
        assert issubclass(detector_class, ResourceDetector)
        assert isinstance(detector_class(), ResourceDetector)


def test_app_service_detector_maps_azure_environment_to_resource(monkeypatch):
    monkeypatch.setenv("WEBSITE_SITE_NAME", "orders-api")
    monkeypatch.setenv("REGION_NAME", "westus2")
    monkeypatch.setenv("WEBSITE_SLOT_NAME", "staging")
    monkeypatch.setenv("WEBSITE_HOSTNAME", "orders-api.azurewebsites.net")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "instance-123")
    monkeypatch.setenv("WEBSITE_HOME_STAMPNAME", "waws-prod-bay-001")
    monkeypatch.setenv("WEBSITE_OWNER_NAME", "subscription-id+resource-owner")
    monkeypatch.setenv("WEBSITE_RESOURCE_GROUP", "observability-rg")

    attributes = AzureAppServiceResourceDetector().detect().attributes

    assert attributes == {
        "azure.app.service.stamp": "waws-prod-bay-001",
        "cloud.platform": "azure_app_service",
        "cloud.provider": "azure",
        "cloud.region": "westus2",
        "cloud.resource_id": (
            "/subscriptions/subscription-id/resourceGroups/observability-rg/" "providers/Microsoft.Web/sites/orders-api"
        ),
        "deployment.environment": "staging",
        "host.id": "orders-api.azurewebsites.net",
        "service.instance.id": "instance-123",
        "service.name": "orders-api",
    }


def test_app_service_detector_returns_empty_resource_outside_app_service():
    assert not AzureAppServiceResourceDetector().detect().attributes


def test_app_service_detector_defers_service_identity_to_functions(monkeypatch):
    monkeypatch.setenv("FUNCTIONS_WORKER_RUNTIME", "python")
    monkeypatch.setenv("WEBSITE_SITE_NAME", "function-app")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "function-instance")

    attributes = AzureAppServiceResourceDetector().detect().attributes

    assert attributes["cloud.provider"] == "azure"
    assert attributes["service.instance.id"] == "function-instance"
    assert "cloud.platform" not in attributes
    assert "service.name" not in attributes


def test_functions_detector_maps_azure_environment_to_resource(monkeypatch):
    monkeypatch.setenv("FUNCTIONS_WORKER_RUNTIME", "python")
    monkeypatch.setenv("WEBSITE_SITE_NAME", "queue-processor")
    monkeypatch.setenv("REGION_NAME", "eastus")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "function-instance")
    monkeypatch.setenv("WEBSITE_MEMORY_LIMIT_MB", "1536")
    monkeypatch.setenv("WEBSITE_OWNER_NAME", "subscription-id")
    monkeypatch.setenv("WEBSITE_RESOURCE_GROUP", "functions-rg")

    attributes = AzureFunctionsResourceDetector().detect().attributes

    assert attributes["cloud.platform"] == "azure_functions"
    assert attributes["cloud.provider"] == "azure"
    assert attributes["cloud.region"] == "eastus"
    assert attributes["cloud.resource_id"] == (
        "/subscriptions/subscription-id/resourceGroups/functions-rg/" "providers/Microsoft.Web/sites/queue-processor"
    )
    assert attributes["faas.instance"] == "function-instance"
    assert attributes["faas.max_memory"] == 1536
    process_pid = attributes["process.pid"]
    assert isinstance(process_pid, int)
    assert process_pid > 0
    assert attributes["service.name"] == "queue-processor"


def test_functions_detector_returns_empty_resource_outside_functions():
    assert not AzureFunctionsResourceDetector().detect().attributes


def test_functions_detector_ignores_invalid_memory_limit(monkeypatch):
    monkeypatch.setenv("FUNCTIONS_WORKER_RUNTIME", "python")
    monkeypatch.setenv("WEBSITE_MEMORY_LIMIT_MB", "not-an-integer")

    attributes = AzureFunctionsResourceDetector().detect().attributes

    assert attributes["cloud.platform"] == "azure_functions"
    assert "faas.max_memory" not in attributes


class _MetadataResponse:
    def __init__(self, metadata):
        self._payload = json.dumps(metadata).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self._payload


def test_vm_detector_maps_metadata_service_response_to_resource(monkeypatch):
    metadata = {
        "location": "centralus",
        "name": "worker-01",
        "osType": "Linux",
        "resourceId": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/worker-01",
        "sku": "2022-datacenter",
        "version": "22.04",
        "vmId": "vm-id-123",
        "vmScaleSetName": "worker-pool",
        "vmSize": "Standard_D4s_v5",
    }

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("api-version=2021-12-13&format=json")
        assert request.get_header("Metadata") == "True"
        assert timeout == 0.2
        return _MetadataResponse(metadata)

    monkeypatch.setattr("opentelemetry.resource.detector.azure.vm.urlopen", fake_urlopen)

    attributes = AzureVMResourceDetector().detect().attributes

    assert attributes == {
        "azure.vm.scaleset.name": "worker-pool",
        "azure.vm.sku": "2022-datacenter",
        "cloud.platform": "azure_vm",
        "cloud.provider": "azure",
        "cloud.region": "centralus",
        "cloud.resource_id": metadata["resourceId"],
        "host.id": "vm-id-123",
        "host.name": "worker-01",
        "host.type": "Standard_D4s_v5",
        "os.type": "Linux",
        "os.version": "22.04",
        "service.instance.id": "vm-id-123",
    }


def test_vm_detector_handles_non_azure_hosts_without_failing(monkeypatch):
    def unavailable_metadata_service(request, timeout):
        raise URLError("metadata service unavailable")

    monkeypatch.setattr("opentelemetry.resource.detector.azure.vm.urlopen", unavailable_metadata_service)

    assert AzureVMResourceDetector().detect().attributes == Resource.get_empty().attributes


@pytest.mark.parametrize(
    ("environment_variable", "value"),
    [
        ("AKS_ARM_NAMESPACE_ID", "cluster-resource-id"),
        ("FUNCTIONS_WORKER_RUNTIME", "python"),
        ("WEBSITE_SITE_NAME", "app-service"),
    ],
)
def test_vm_detector_skips_metadata_request_on_other_azure_platforms(monkeypatch, environment_variable, value):
    monkeypatch.setenv(environment_variable, value)

    def unexpected_request(request, timeout):
        pytest.fail("VM metadata must not be queried on another Azure platform")

    monkeypatch.setattr("opentelemetry.resource.detector.azure.vm.urlopen", unexpected_request)

    assert not AzureVMResourceDetector().detect().attributes


def test_resource_aggregation_ignores_failing_detector():
    class FailingDetector(ResourceDetector):
        def detect(self):
            raise RuntimeError("detector failure")

    class WorkingDetector(ResourceDetector):
        def detect(self):
            return Resource({"service.name": "working-detector"})

    resource = get_aggregated_resources(
        [FailingDetector(), WorkingDetector()],
        initial_resource=Resource({"deployment.environment": "test"}),
    )

    assert resource.attributes["deployment.environment"] == "test"
    assert resource.attributes["service.name"] == "working-detector"


def test_distro_default_resource_runs_registered_azure_detectors(monkeypatch):
    monkeypatch.setenv("WEBSITE_SITE_NAME", "inventory-api")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "inventory-instance")
    configurations = {}

    _default_resource(configurations)

    assert configurations[RESOURCE_ARG].attributes["service.name"] == "inventory-api"
    assert configurations[RESOURCE_ARG].attributes["service.instance.id"]
    assert configurations[RESOURCE_ARG].attributes["cloud.platform"] == "azure_app_service"
    assert configurations[RESOURCE_ARG].attributes["cloud.provider"] == "azure"
    assert os.environ[OTEL_EXPERIMENTAL_RESOURCE_DETECTORS] == "azure_app_service,azure_vm"
