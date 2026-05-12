# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from collections.abc import Iterator
from typing import Any

from microsoft_agents.activity import Activity
from microsoft.opentelemetry.a365.constants import (
    CHANNEL_LINK_KEY,
    CHANNEL_NAME_KEY,
    GEN_AI_AGENT_AUID_KEY,
    GEN_AI_AGENT_DESCRIPTION_KEY,
    GEN_AI_AGENT_EMAIL_KEY,
    GEN_AI_AGENT_ID_KEY,
    GEN_AI_AGENT_NAME_KEY,
    GEN_AI_CONVERSATION_ID_KEY,
    GEN_AI_CONVERSATION_ITEM_LINK_KEY,
    TENANT_ID_KEY,
    USER_EMAIL_KEY,
    USER_ID_KEY,
    USER_NAME_KEY,
)

AGENT_ROLE = "agenticUser"


def resolve_sub_channel(activity: Activity) -> str | None:
    """Resolve sub_channel from ChannelId, falling back to productContext in channel_data."""
    channel_id = activity.channel_id
    sub_channel = None

    if channel_id is not None and hasattr(channel_id, "channel"):
        sub_channel = channel_id.sub_channel

    if not sub_channel and activity.channel_data:
        try:
            channel_data = activity.channel_data
            if isinstance(channel_data, str):
                channel_data = json.loads(channel_data)
            elif hasattr(channel_data, "__dict__"):
                channel_data = channel_data.__dict__

            product_context = channel_data.get("productContext") if isinstance(channel_data, dict) else None
            if product_context:
                sub_channel = product_context
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

    return sub_channel


def _is_agentic(entity: Any) -> bool:
    if not entity:
        return False
    return bool(
        entity.agentic_user_id
        or ((role := entity.role) and isinstance(role, str) and role.lower() == AGENT_ROLE.lower())
    )


def get_caller_pairs(activity: Activity) -> Iterator[tuple[str, Any]]:
    frm = activity.from_property
    if not frm:
        return
    yield USER_ID_KEY, frm.aad_object_id or frm.agentic_user_id or frm.id
    yield USER_NAME_KEY, frm.name
    yield USER_EMAIL_KEY, frm.agentic_user_id


def get_target_agent_pairs(activity: Activity) -> Iterator[tuple[str, Any]]:
    rec = activity.recipient
    if not rec:
        return
    yield GEN_AI_AGENT_ID_KEY, activity.get_agentic_instance_id()
    yield GEN_AI_AGENT_NAME_KEY, rec.name
    yield GEN_AI_AGENT_AUID_KEY, rec.aad_object_id
    yield GEN_AI_AGENT_EMAIL_KEY, activity.get_agentic_user()
    yield (
        GEN_AI_AGENT_DESCRIPTION_KEY,
        rec.role,
    )


def get_tenant_id_pair(activity: Activity) -> Iterator[tuple[str, Any]]:
    yield TENANT_ID_KEY, activity.recipient.tenant_id


def get_channel_pairs(activity: Activity) -> Iterator[tuple[str, Any]]:
    """
    Generate channel pairs from activity, handling both string and ChannelId object cases.

    :param activity: The activity object (Activity instance or dict)
    :return: Iterator of (key, value) tuples for channel information
    """
    # Handle channel_id (can be string or ChannelId object)
    channel_id = activity.channel_id

    # Extract channel name from either string or ChannelId object
    channel_name = None

    if channel_id is not None:
        if hasattr(channel_id, "channel"):
            # ChannelId object
            channel_name = channel_id.channel
        elif isinstance(channel_id, str):
            # Direct string value
            channel_name = channel_id

    sub_channel = resolve_sub_channel(activity)

    # Yield channel name as source name
    yield CHANNEL_NAME_KEY, channel_name
    yield CHANNEL_LINK_KEY, sub_channel


def get_conversation_pairs(activity: Activity) -> Iterator[tuple[str, Any]]:
    conv = activity.conversation
    conversation_id = conv.id if conv else None

    item_link = activity.service_url

    yield GEN_AI_CONVERSATION_ID_KEY, conversation_id
    yield GEN_AI_CONVERSATION_ITEM_LINK_KEY, item_link
