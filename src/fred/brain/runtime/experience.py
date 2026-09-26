from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fred.brain.memory.contracts import ExperienceRecord, RecordRef, RecordTable, RelationKind
from fred.brain.memory.repositories import Repositories
from fred.brain.runtime.journal import Journal
from fred.models.base import EmbeddingModel


def build_search_text(
    *,
    input: dict[str, Any],
    context: dict[str, Any],
    perception: dict[str, Any],
    decision: dict[str, Any],
    action: dict[str, Any],
    outcome: dict[str, Any],
    feedback: dict[str, Any] | None,
) -> str:
    parts = {
        "input": input,
        "context": context,
        "perception": perception,
        "decision": decision,
        "action": action,
        "outcome": outcome,
        "feedback": feedback,
    }
    return " ".join(
        f"{key}={json.dumps(value, sort_keys=True, separators=(',', ':'), default=str)}"
        for key, value in parts.items()
        if value not in (None, {}, [])
    )


@dataclass(slots=True)
class ActiveExperience:
    session_id: str
    turn_id: str | None
    input: dict[str, Any]
    context: dict[str, Any]
    sequence_start: int
    started_at: datetime
    events: list[str] = field(default_factory=list)
    closed: bool = False


class ExperienceService:
    def __init__(self, repositories: Repositories, embedding: EmbeddingModel) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.journal = Journal(repositories.journal)

    async def begin(
        self,
        *,
        session_id: str,
        turn_id: str | None,
        input: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ActiveExperience:
        event = await self.journal.append(
            event_type="EXPERIENCE_STARTED",
            session_id=session_id,
            turn_id=turn_id,
            payload={"input": input, "context": context or {}},
        )
        return ActiveExperience(
            session_id=session_id,
            turn_id=turn_id,
            input=input,
            context=context or {},
            sequence_start=event.sequence,
            started_at=event.occurred_at,
            events=[str(event.ref)],
        )

    async def commit(
        self,
        active: ActiveExperience,
        *,
        perception: dict[str, Any],
        decision: dict[str, Any],
        action: dict[str, Any],
        outcome: dict[str, Any],
        feedback: dict[str, Any] | None = None,
        entity_refs: list[RecordRef] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperienceRecord:
        if active.closed:
            raise ValueError("ActiveExperience is already closed")
        final_event = await self.journal.append(
            event_type="EXPERIENCE_COMMITTED",
            session_id=active.session_id,
            turn_id=active.turn_id,
            payload={"outcome": outcome, "feedback": feedback},
        )
        search_text = build_search_text(
            input=active.input,
            context=active.context,
            perception=perception,
            decision=decision,
            action=action,
            outcome=outcome,
            feedback=feedback,
        )
        vector = await self.embedding.embed_document(search_text)
        now = datetime.now(UTC)
        ref = RecordRef(table=RecordTable.EXPERIENCE, key=uuid.uuid4().hex)
        record = ExperienceRecord(
            ref=ref,
            sequence_start=active.sequence_start,
            sequence_end=final_event.sequence,
            session_id=active.session_id,
            turn_id=active.turn_id,
            input=active.input,
            context=active.context,
            perception=perception,
            decision=decision,
            action=action,
            outcome=outcome,
            feedback=feedback,
            search_text=search_text,
            entity_refs=entity_refs or [],
            started_at=active.started_at,
            ended_at=now,
            observed_at=now,
            embedding=vector,
            embedding_model=self.embedding.identity,
            embedding_version=self.embedding.identity,
            provenance={
                "journal_refs": [*active.events, str(final_event.ref)],
                "authority": "observed_experience",
            },
            metadata=metadata or {},
        )
        async with self.repositories.backend.atomic() as transaction:
            tx_repositories = Repositories.create(transaction)
            committed = await tx_repositories.experiences.create(record)
            for entity_ref in entity_refs or []:
                await tx_repositories.relations.create_validated(
                    in_ref=committed.ref,
                    out_ref=entity_ref,
                    kind=RelationKind.ABOUT,
                    source="experience_commit",
                )
        active.closed = True
        return committed

    async def abort(self, active: ActiveExperience, *, reason: str) -> None:
        if active.closed:
            raise ValueError("ActiveExperience is already closed")
        await self.journal.append(
            event_type="EXPERIENCE_ABORTED",
            session_id=active.session_id,
            turn_id=active.turn_id,
            payload={"reason": reason},
        )
        active.closed = True

