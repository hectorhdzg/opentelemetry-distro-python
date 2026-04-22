# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
Azure OpenAI client utilities and configuration.
"""

import logging
from os import environ

from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)


def create_azure_openai_client() -> AsyncAzureOpenAI:
    """Create Azure OpenAI client with environment configuration."""
    endpoint = environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = environ.get("AZURE_OPENAI_API_KEY")

    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    if not api_key:
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")

    return AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2025-01-01-preview",
    )


def get_deployment_name() -> str:
    """Get the deployment name from environment."""
    return environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
