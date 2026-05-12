# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from microsoft_agents.activity import (
    Activity,
    ActivityEventNames,
    ActivityTypes,
    ChannelAccount,
    ChannelId,
    ConversationAccount,
)
from microsoft_agents.hosting.core import TurnContext
from microsoft.opentelemetry.a365.core.constants import (
    CHANNEL_LINK_KEY,
    TENANT_ID_KEY,
    USER_ID_KEY,
)
from microsoft.opentelemetry.a365.hosting.middleware.baggage_middleware import (
    BaggageMiddleware,
)
from opentelemetry import baggage


def _make_turn_context(
    activity_type: str = "message",
    activity_name: str | None = None,
    text: str = "Hello",
) -> TurnContext:
    """Create a TurnContext with a test activity."""
    kwargs: dict = {
        "type": activity_type,
        "text": text,
        "from_property": ChannelAccount(
            aad_object_id="caller-id",
            name="Caller",
            agentic_user_id="caller-upn",
            tenant_id="tenant-id",
        ),
        "recipient": ChannelAccount(
            tenant_id="tenant-123",
            role="user",
            name="Agent",
        ),
        "conversation": ConversationAccount(id="conv-id"),
        "service_url": "https://example.com",
        "channel_id": "test-channel",
    }
    if activity_name is not None:
        kwargs["name"] = activity_name
    activity = Activity(**kwargs)
    adapter = MagicMock()
    return TurnContext(adapter, activity)


@pytest.mark.asyncio
async def test_baggage_middleware_propagates_baggage():
    """BaggageMiddleware should set baggage context for the downstream logic."""
    middleware = BaggageMiddleware()
    ctx = _make_turn_context()

    captured_caller_id = None
    captured_tenant_id = None

    async def logic():
        nonlocal captured_caller_id, captured_tenant_id
        captured_caller_id = baggage.get_baggage(USER_ID_KEY)
        captured_tenant_id = baggage.get_baggage(TENANT_ID_KEY)

    await middleware.on_turn(ctx, logic)

    assert captured_caller_id == "caller-id"
    assert captured_tenant_id == "tenant-123"


@pytest.mark.asyncio
async def test_baggage_middleware_skips_async_reply():
    """BaggageMiddleware should skip baggage setup for ContinueConversation events."""
    middleware = BaggageMiddleware()
    ctx = _make_turn_context(
        activity_type=ActivityTypes.event,
        activity_name=ActivityEventNames.continue_conversation,
    )

    logic_called = False
    captured_caller_id = None

    async def logic():
        nonlocal logic_called, captured_caller_id
        logic_called = True
        captured_caller_id = baggage.get_baggage(USER_ID_KEY)

    await middleware.on_turn(ctx, logic)

    assert logic_called is True
    # Baggage should NOT be set because the middleware skipped it
    assert captured_caller_id is None


def _make_channel_data_turn_context(
    channel_id: str | ChannelId = "test-channel",
    channel_data: Any = None,
) -> TurnContext:
    """Create a TurnContext with channel_data for productContext tests."""
    activity = Activity(
        type="message",
        text="Hello",
        from_property=ChannelAccount(
            aad_object_id="caller-id",
            name="Caller",
            agentic_user_id="caller-upn",
            tenant_id="tenant-id",
        ),
        recipient=ChannelAccount(
            tenant_id="tenant-123",
            role="user",
            name="Agent",
        ),
        conversation=ConversationAccount(id="conv-id"),
        service_url="https://example.com",
        channel_id=channel_id,
        channel_data=channel_data,
    )
    adapter = MagicMock()
    return TurnContext(adapter, activity)


@pytest.mark.asyncio
async def test_baggage_middleware_extracts_product_context_from_dict_channel_data():
    """BaggageMiddleware should extract productContext from dict channel_data as sub_channel."""
    middleware = BaggageMiddleware()
    ctx = _make_channel_data_turn_context(
        channel_data={"productContext": "word"},
    )

    captured_channel_link = None

    async def logic():
        nonlocal captured_channel_link
        captured_channel_link = baggage.get_baggage(CHANNEL_LINK_KEY)

    await middleware.on_turn(ctx, logic)

    assert captured_channel_link == "word"


@pytest.mark.asyncio
async def test_baggage_middleware_sub_channel_takes_precedence_over_product_context():
    """When ChannelId has sub_channel set, it should take precedence over productContext."""
    middleware = BaggageMiddleware()
    ctx = _make_channel_data_turn_context(
        channel_id=ChannelId(channel="teams", sub_channel="from-channel-id"),
        channel_data={"productContext": "from-product-context"},
    )

    captured_channel_link = None

    async def logic():
        nonlocal captured_channel_link
        captured_channel_link = baggage.get_baggage(CHANNEL_LINK_KEY)

    await middleware.on_turn(ctx, logic)

    assert captured_channel_link == "from-channel-id"


@pytest.mark.asyncio
async def test_baggage_middleware_extracts_product_context_from_json_string():
    """BaggageMiddleware should extract productContext from JSON string channel_data."""
    middleware = BaggageMiddleware()
    ctx = _make_channel_data_turn_context(
        channel_data=json.dumps({"productContext": "excel"}),
    )

    captured_channel_link = None

    async def logic():
        nonlocal captured_channel_link
        captured_channel_link = baggage.get_baggage(CHANNEL_LINK_KEY)

    await middleware.on_turn(ctx, logic)

    assert captured_channel_link == "excel"


@pytest.mark.asyncio
async def test_baggage_middleware_handles_invalid_json_channel_data_gracefully():
    """BaggageMiddleware should not raise on invalid JSON in channel_data."""
    middleware = BaggageMiddleware()
    ctx = _make_channel_data_turn_context(
        channel_data="not-valid-json{{{",
    )

    captured_channel_link = None

    async def logic():
        nonlocal captured_channel_link
        captured_channel_link = baggage.get_baggage(CHANNEL_LINK_KEY)

    await middleware.on_turn(ctx, logic)

    assert captured_channel_link is None
