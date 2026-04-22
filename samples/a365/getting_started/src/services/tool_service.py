# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
Tool execution service with observability integration.

Migrated from: microsoft_agents_a365.observability.core → microsoft.opentelemetry.a365.core
"""

import logging
import uuid

from microsoft_agents.hosting.core import TurnContext

# ✅ NEW — distro imports
from microsoft.opentelemetry.a365.core import (
    ExecuteToolScope,
    Request,
    ToolCallDetails,
)

from utils.observability_helpers import create_agent_details

logger = logging.getLogger(__name__)


async def execute_tool(tool_name: str, arguments: str, context: TurnContext) -> str:
    """Execute a tool with ExecuteToolScope tracing."""
    agent_details = create_agent_details(context)

    tool_call_id = str(uuid.uuid4())
    tool_details = ToolCallDetails(
        tool_name=tool_name,
        arguments={"input": arguments},
        tool_call_id=tool_call_id,
        description=f"Executing {tool_name} tool",
        tool_type="function",
    )

    # Start execute tool scope for observability
    tool_scope = ExecuteToolScope.start(
        request=Request(),
        details=tool_details,
        agent_details=agent_details,
    )

    try:
        with tool_scope:
            logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")

            # Mock tool execution — replace with actual tool calls
            if tool_name == "get_weather":
                result = f"Weather information for {arguments}: Sunny, 72°F"
            elif tool_name == "calculate":
                result = f"Calculation result for {arguments}: 42"
            else:
                result = f"Tool {tool_name} executed successfully with arguments: {arguments}"

            logger.info(f"Tool execution result: {result}")
            tool_scope.record_response({"result": result, "tool_call_id": tool_call_id})
            return result

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        tool_scope.record_error(e)
        return f"Error executing tool {tool_name}: {str(e)}"
