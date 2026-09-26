from __future__ import annotations

from collections import Counter
from typing import Any

from fred.brain.memory.contracts import MemoryStatus, TraceType
from fred.brain.memory.repositories import Repositories


class MemoryObserver:
    """Read-only research view over persisted MEM-01 state and traces."""

    def __init__(self, repositories: Repositories) -> None:
        self.repositories = repositories

    async def snapshot(self, *, session_id: str | None = None) -> dict[str, Any]:
        experiences = sorted(
            await self.repositories.experiences.search(),
            key=lambda item: item.ended_at,
        )
        memories = sorted(
            await self.repositories.memories.list_all(),
            key=lambda item: item.created_at,
        )
        states = sorted(await self.repositories.state.list_all(), key=lambda item: item.key)
        traces = await self.repositories.traces.query(session_id)
        traces.sort(key=lambda item: item.occurred_at)

        trace_counts = Counter(item.trace_type.value for item in traces)
        latest_by_type: dict[str, dict[str, Any]] = {}
        for trace in traces:
            latest_by_type[trace.trace_type.value] = trace.model_dump(mode="json")

        latest_experience = experiences[-1] if experiences else None
        return {
            "session_id": session_id,
            "latest_turn": (
                {
                    "session_id": latest_experience.session_id,
                    "turn_id": latest_experience.turn_id,
                    "experience_ref": str(latest_experience.ref),
                    "input": latest_experience.input,
                    "decision": latest_experience.decision,
                    "action": latest_experience.action,
                    "outcome": latest_experience.outcome,
                    "feedback": latest_experience.feedback,
                }
                if latest_experience
                else None
            ),
            "state": [item.model_dump(mode="json") for item in states],
            "experience": [item.model_dump(mode="json") for item in experiences],
            "memory": {
                status.value: [
                    item.model_dump(mode="json")
                    for item in memories
                    if item.status is status
                ]
                for status in MemoryStatus
            },
            "retrieval": [
                item.model_dump(mode="json")
                for item in traces
                if item.trace_type is TraceType.RETRIEVAL
            ],
            "memory_proposals": [
                item.model_dump(mode="json")
                for item in traces
                if item.trace_type is TraceType.MEMORY_PROPOSAL
            ],
            "memory_validations": [
                item.model_dump(mode="json")
                for item in traces
                if item.trace_type is TraceType.MEMORY_VALIDATION
            ],
            "sleep": [
                item.model_dump(mode="json")
                for item in traces
                if item.trace_type is TraceType.SLEEP
            ],
            "errors": [
                item.model_dump(mode="json")
                for item in traces
                if item.trace_type is TraceType.ERROR
            ],
            "provenance": {
                str(item.ref): item.provenance for item in memories
            },
            "trace_summary": {
                "counts": dict(trace_counts),
                "latest_by_type": latest_by_type,
            },
        }

