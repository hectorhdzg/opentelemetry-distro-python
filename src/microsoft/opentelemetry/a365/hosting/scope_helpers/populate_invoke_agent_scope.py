# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING

from microsoft.opentelemetry.a365.core.invoke_agent_scope import InvokeAgentScope

from microsoft.opentelemetry.a365.hosting.scope_helpers.utils import (
    get_caller_pairs,
    get_channel_pairs,
    get_conversation_pairs,
    get_target_agent_pairs,
    get_tenant_id_pair,
)

if TYPE_CHECKING:
    from microsoft_agents.hosting.core.turn_context import TurnContext

# mypy: disable-error-code="arg-type"


def populate(scope: InvokeAgentScope, turn_context: TurnContext) -> InvokeAgentScope:
    """
    Populate all supported InvokeAgentScope tags from the provided TurnContext.
    :param scope: The InvokeAgentScope instance to populate.
    :param turn_context: The TurnContext containing activity information.
    :return: The updated InvokeAgentScope instance.
    """
    if not turn_context:
        raise ValueError("turn_context is required")

    if not turn_context.activity:
        return scope

    activity = turn_context.activity

    scope.record_attributes(get_caller_pairs(activity))
    scope.record_attributes(get_target_agent_pairs(activity))
    scope.record_attributes(get_tenant_id_pair(activity))
    scope.record_attributes(get_channel_pairs(activity))
    scope.record_attributes(get_conversation_pairs(activity))

    if activity.text:
        scope.record_input_messages([activity.text])

    return scope
