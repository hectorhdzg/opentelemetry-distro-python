# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
from pathlib import Path
from typing import Any

import pytest

try:
    from dotenv import load_dotenv

    tests_dir = Path(__file__).parent.parent.parent.parent
    env_file = tests_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


@pytest.fixture(scope="session")
def azure_openai_config() -> dict[str, Any]:
    """Azure OpenAI configuration for integration tests."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    if not endpoint:
        pytest.skip("Integration tests require AZURE_OPENAI_ENDPOINT")

    return {
        "endpoint": endpoint,
        "deployment": deployment,
        "api_version": api_version,
    }


@pytest.fixture(scope="session")
def agent365_config() -> dict[str, Any]:
    """Microsoft Agent 365 configuration for integration tests."""
    tenant_id = os.getenv("AGENT365_TEST_TENANT_ID")
    agent_id = os.getenv("AGENT365_TEST_AGENT_ID")

    if not tenant_id:
        pytest.skip("Integration tests require AGENT365_TEST_TENANT_ID")

    return {"tenant_id": tenant_id, "agent_id": agent_id}
