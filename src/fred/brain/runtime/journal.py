from __future__ import annotations

from fred.brain.memory.contracts import JournalEvent
from fred.brain.memory.repositories import JournalRepository


class Journal:
    def __init__(self, repository: JournalRepository) -> None:
        self.repository = repository

    async def append(
        self,
        *,
        event_type: str,
        session_id: str,
        payload: dict[str, object],
        turn_id: str | None = None,
    ) -> JournalEvent:
        existing = await self.repository.query(session_id)
        sequence = existing[-1].sequence + 1 if existing else 1
        return await self.repository.append(
            sequence=sequence,
            event_type=event_type,
            session_id=session_id,
            turn_id=turn_id,
            payload=payload,
        )

