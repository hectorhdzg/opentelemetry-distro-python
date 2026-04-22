# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
Azure OpenAI service with observability integration.

Migrated from: microsoft_agents_a365.observability.core → microsoft.opentelemetry.a365.core
"""

import logging

from microsoft_agents.hosting.core import TurnContext

# ✅ NEW — distro imports
from microsoft.opentelemetry.a365.core import (
    InferenceCallDetails,
    InferenceOperationType,
    InferenceScope,
    Request,
)

from utils.azure_openai_client import create_azure_openai_client, get_deployment_name
from utils.observability_helpers import create_agent_details

logger = logging.getLogger(__name__)


async def call_azure_openai(user_message: str, context: TurnContext) -> str:
    """Make a call to Azure OpenAI with the user's message."""
    agent_details = create_agent_details(context)
    deployment_name = get_deployment_name()

    inference_details = InferenceCallDetails(
        operationName=InferenceOperationType.CHAT,
        model=deployment_name,
        providerName="Azure OpenAI",
    )

    request_details = Request(content=user_message)

    # Start inference scope for observability
    inference_scope = InferenceScope.start(
        request=request_details,
        details=inference_details,
        agent_details=agent_details,
    )

    try:
        with inference_scope:
            client = create_azure_openai_client()

            completion = await client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. Provide clear, concise responses.",
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=16384,
                temperature=0.7,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None,
                stream=False,
            )

            message_content = completion.choices[0].message.content
            inference_scope.record_output_messages([message_content])

            if hasattr(completion, "usage") and completion.usage:
                inference_scope.record_input_tokens(completion.usage.prompt_tokens)
                inference_scope.record_output_tokens(completion.usage.completion_tokens)

            if completion.choices and completion.choices[0].finish_reason:
                inference_scope.record_finish_reasons([completion.choices[0].finish_reason])

            return message_content

    except Exception as e:
        logger.error(f"Error calling Azure OpenAI: {e}")
        inference_scope.record_error(e)
        return f"Sorry, I encountered an error while processing your request: {str(e)}"
