"""SSE event types for the agent choreography."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import orjson


class EventType(str, Enum):
    AGENT_STARTED = "agent_started"
    REASONING_TICK = "reasoning_tick"
    FINDING_EMITTED = "finding_emitted"
    AGENT_COMPLETED = "agent_completed"
    VERIFICATION = "verification"
    RUN_COMPLETED = "run_completed"
    RUN_ENQUEUED = "run_enqueued"
    RUN_ERROR = "run_error"


@dataclass
class AgentEvent:
    event: EventType
    agent: str = ""
    data: dict | None = None

    def to_json(self) -> str:
        payload = {"event": self.event.value, "agent": self.agent}
        if self.data:
            payload.update(self.data)
        return orjson.dumps(payload).decode()
