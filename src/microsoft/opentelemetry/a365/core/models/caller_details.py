# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from microsoft.opentelemetry.a365.core.models.user_details import UserDetails

if TYPE_CHECKING:
    from microsoft.opentelemetry.a365.core.agent_details import AgentDetails



@dataclass
class CallerDetails:
    """Composite caller details for agent-to-agent (A2A) scenarios.

    Groups the human caller identity and the calling agent identity together.
    """

    user_details: Optional[UserDetails] = None
    """Details about the human user in the call chain."""

    caller_agent_details: Optional["AgentDetails"] = None
    """Details about the calling agent in A2A scenarios."""
