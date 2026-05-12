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
def openai_config() -> dict[str, Any]:
    """OpenAI configuration for integration tests."""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        pytest.skip("Integration tests require OPENAI_API_KEY")

    return {
        "api_key": api_key,
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }
