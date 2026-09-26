from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fred.brain.memory.contracts import (
    CognitiveRelation,
    EntityRecord,
    EvaluationRecord,
    EvidenceValidation,
    ExperienceRecord,
    JournalEvent,
    MemoryProposal,
    MemoryRecord,
    MemoryStatus,
    RecordRef,
    RecordTable,
    RelationKind,
    StateRecord,
    TraceEvent,
    TraceType,
)
from fred.brain.memory.validators import (
    evidence_allows_activation,
    validate_relation_endpoints,
    would_create_provenance_cycle,
)
from fred.db.backends import Backend


def _record_ref(table: RecordTable) -> RecordRef:
    return RecordRef(table=table, key=uuid.uuid4().hex)


def _as_model(row: dict[str, Any], model):
    payload = dict(row)
    payload["ref"] = payload.pop("id")
    return model.model_validate(payload)


class ExperienceRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def create(self, record: ExperienceRecord) -> ExperienceRecord:
        if await self.get(record.ref) is not None:
            raise ValueError(f"Experience already exists: {record.ref}")
        payload = record.model_dump(mode="python", exclude={"ref"})
        row = await self.backend.create("experience", payload, record.ref.key)
        return _as_model(row, ExperienceRecord)

    async def get(self, ref: RecordRef) -> ExperienceRecord | None:
        if ref.table is not RecordTable.EXPERIENCE:
            raise ValueError("ExperienceRepository requires experience ref")
        row = await self.backend.get(ref)
        return _as_model(row, ExperienceRecord) if row else None

    async def search(self) -> list[ExperienceRecord]:
        return [_as_model(row, ExperienceRecord) for row in await self.backend.list("experience")]


class MemoryRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def create_provisional(
        self,
        proposal: MemoryProposal,
        *,
        embedding: list[float],
        embedding_model: str,
        embedding_version: str,
        metadata: dict[str, Any] | None = None,
        ref: RecordRef | None = None,
    ) -> MemoryRecord:
        ref = ref or _record_ref(RecordTable.MEMORY)
        if ref.table is not RecordTable.MEMORY:
            raise ValueError("MemoryRepository requires memory ref")
        record = MemoryRecord(
            ref=ref,
            content=proposal.proposed_content or "",
            status=MemoryStatus.PROVISIONAL,
            episodicity=proposal.episodicity,
            abstraction=proposal.abstraction,
            procedurality=proposal.procedurality,
            relationality=proposal.relationality,
            evidential_support=proposal.evidential_support,
            interpretive_confidence=proposal.interpretive_confidence,
            salience_prior=proposal.salience_prior,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            provenance={
                "evidence_refs": [str(ref) for ref in proposal.evidence_refs],
                "counterevidence_refs": [str(ref) for ref in proposal.counterevidence_refs],
            },
            metadata={
                "proposal_operation": proposal.operation.value,
                "applicability": proposal.applicability,
                "conditions": proposal.conditions,
                "proposal_explanation": proposal.model_explanation,
                **(metadata or {}),
            },
        )
        row = await self.backend.create(
            "memory", record.model_dump(mode="python", exclude={"ref"}), ref.key
        )
        return _as_model(row, MemoryRecord)

    async def record_validation(
        self, ref: RecordRef, validation: EvidenceValidation
    ) -> MemoryRecord:
        record = await self.get(ref)
        if record is None:
            raise KeyError(str(ref))
        if validation.proposal_ref != ref:
            raise ValueError("evidence validation does not refer to target Memory")
        row = await self.backend.update(
            ref,
            {
                "metadata": {
                    **record.metadata,
                    "evidence_validation": validation.model_dump(mode="json"),
                    "evidence_verdict": validation.verdict.value,
                    "evidence_verifier": validation.verifier,
                    "evidence_explanation": validation.explanation,
                }
            },
        )
        return _as_model(row, MemoryRecord)

    async def get(self, ref: RecordRef) -> MemoryRecord | None:
        if ref.table is not RecordTable.MEMORY:
            raise ValueError("MemoryRepository requires memory ref")
        row = await self.backend.get(ref)
        return _as_model(row, MemoryRecord) if row else None

    async def list_all(self) -> list[MemoryRecord]:
        return [_as_model(row, MemoryRecord) for row in await self.backend.list("memory")]

    async def search_active(self) -> list[MemoryRecord]:
        return [record for record in await self.list_all() if record.status is MemoryStatus.ACTIVE]

    async def activate(
        self, ref: RecordRef, validation: EvidenceValidation
    ) -> MemoryRecord:
        record = await self.get(ref)
        if record is None:
            raise KeyError(str(ref))
        if validation.proposal_ref != ref:
            raise ValueError("evidence validation does not refer to target Memory")
        if not evidence_allows_activation(validation):
            raise ValueError(f"evidence verdict {validation.verdict} cannot activate Memory")
        if not record.provenance.get("evidence_refs"):
            raise ValueError("Memory cannot become ACTIVE without provenance")
        row = await self.backend.update(
            ref,
            {
                "status": MemoryStatus.ACTIVE,
                "metadata": {
                    **record.metadata,
                    "evidence_verdict": validation.verdict.value,
                    "evidence_verifier": validation.verifier,
                    "evidence_explanation": validation.explanation,
                },
            },
        )
        return _as_model(row, MemoryRecord)

    async def reinforce(self, ref: RecordRef, amount: float = 0.05) -> MemoryRecord:
        record = await self.get(ref)
        if record is None:
            raise KeyError(str(ref))
        row = await self.backend.update(
            ref,
            {
                "salience_prior": min(1.0, record.salience_prior + amount),
                "metadata": {
                    **record.metadata,
                    "reinforced_at": datetime.now(UTC).isoformat(),
                },
            },
        )
        return _as_model(row, MemoryRecord)

    async def tombstone(self, ref: RecordRef, reason: str) -> MemoryRecord:
        record = await self.get(ref)
        if record is None:
            raise KeyError(str(ref))
        row = await self.backend.update(
            ref,
            {
                "status": MemoryStatus.TOMBSTONED,
                "metadata": {**record.metadata, "tombstone_reason": reason},
            },
        )
        return _as_model(row, MemoryRecord)


class EntityRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def resolve(self, canonical_key: str) -> EntityRecord | None:
        for row in await self.backend.list("entity"):
            if row.get("canonical_key") == canonical_key:
                return _as_model(row, EntityRecord)
        return None

    async def get(self, ref: RecordRef) -> EntityRecord | None:
        row = await self.backend.get(ref)
        return _as_model(row, EntityRecord) if row else None

    async def create_if_absent(
        self, *, kind: str, canonical_key: str, name: str, aliases: list[str] | None = None
    ) -> EntityRecord:
        existing = await self.resolve(canonical_key)
        if existing:
            return existing
        ref = _record_ref(RecordTable.ENTITY)
        record = EntityRecord(
            ref=ref,
            kind=kind,
            canonical_key=canonical_key,
            name=name,
            aliases=aliases or [],
        )
        row = await self.backend.create(
            "entity", record.model_dump(mode="python", exclude={"ref"}), ref.key
        )
        return _as_model(row, EntityRecord)


class EvaluationRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def create(
        self,
        *,
        target_ref: RecordRef,
        kind: str,
        source: str,
        value: float | None = None,
        evidence_refs: list[RecordRef] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvaluationRecord:
        ref = _record_ref(RecordTable.EVALUATION)
        record = EvaluationRecord(
            ref=ref,
            target_ref=target_ref,
            kind=kind,
            value=value,
            source=source,
            evidence_refs=evidence_refs or [],
            metadata=metadata or {},
        )
        row = await self.backend.create(
            "evaluation", record.model_dump(mode="python", exclude={"ref"}), ref.key
        )
        return _as_model(row, EvaluationRecord)

    async def get_for_target(self, target_ref: RecordRef) -> list[EvaluationRecord]:
        return [
            _as_model(row, EvaluationRecord)
            for row in await self.backend.list("evaluation")
            if row.get("target_ref") == str(target_ref)
        ]


class StateRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def get(self, key: str) -> StateRecord | None:
        for row in await self.backend.list("state"):
            if row.get("key") == key:
                return _as_model(row, StateRecord)
        return None

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        *,
        authority: str,
        metadata: dict[str, Any] | None = None,
    ) -> StateRecord:
        existing = await self.get(key)
        if existing:
            row = await self.backend.update(
                existing.ref,
                {
                    "value": value,
                    "authority": authority,
                    "updated_at": datetime.now(UTC),
                    "metadata": metadata or existing.metadata,
                },
            )
            return _as_model(row, StateRecord)
        ref = _record_ref(RecordTable.STATE)
        record = StateRecord(
            ref=ref,
            key=key,
            value=value,
            authority=authority,
            metadata=metadata or {},
        )
        row = await self.backend.create(
            "state", record.model_dump(mode="python", exclude={"ref"}), ref.key
        )
        return _as_model(row, StateRecord)

    async def clear(self, key: str) -> None:
        existing = await self.get(key)
        if existing:
            await self.backend.update(
                existing.ref,
                {"value": {}, "authority": "CLEARED", "updated_at": datetime.now(UTC)},
            )

    async def list_all(self) -> list[StateRecord]:
        return [_as_model(row, StateRecord) for row in await self.backend.list("state")]


class RelationRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def list_all(self) -> list[CognitiveRelation]:
        records: list[CognitiveRelation] = []
        for row in await self.backend.list("cognitive_relation"):
            payload = dict(row)
            payload["ref"] = payload.pop("id")
            payload["in_ref"] = payload.pop("in")
            payload["out_ref"] = payload.pop("out")
            records.append(CognitiveRelation.model_validate(payload))
        return records

    async def create_validated(
        self,
        *,
        in_ref: RecordRef,
        out_ref: RecordRef,
        kind: RelationKind,
        confidence: float = 1.0,
        strength: float = 1.0,
        source: str = "system",
        provenance: list[RecordRef] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CognitiveRelation:
        validate_relation_endpoints(kind, in_ref, out_ref)
        existing = await self.list_all()
        if kind is RelationKind.DERIVED_FROM and would_create_provenance_cycle(
            in_ref, [out_ref], existing
        ):
            raise ValueError("provenance cycle rejected")
        ref = _record_ref(RecordTable.COGNITIVE_RELATION)
        payload = {
            "kind": kind,
            "confidence": confidence,
            "strength": strength,
            "source": source,
            "created_at": datetime.now(UTC),
            "provenance": provenance or [],
            "metadata": metadata or {},
        }
        row = await self.backend.relate(in_ref, out_ref, payload, ref.key)
        model_payload = dict(row)
        model_payload["ref"] = model_payload.pop("id")
        model_payload["in_ref"] = model_payload.pop("in")
        model_payload["out_ref"] = model_payload.pop("out")
        return CognitiveRelation.model_validate(model_payload)

    async def traverse(self, ref: RecordRef) -> list[CognitiveRelation]:
        return [
            relation
            for relation in await self.list_all()
            if relation.in_ref == ref or relation.out_ref == ref
        ]

    async def find(self, kind: RelationKind | None = None) -> list[CognitiveRelation]:
        relations = await self.list_all()
        return [relation for relation in relations if kind is None or relation.kind is kind]


class TraceRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def append(
        self,
        *,
        trace_type: TraceType,
        session_id: str,
        payload: dict[str, Any],
        turn_id: str | None = None,
        experience_ref: RecordRef | None = None,
    ) -> TraceEvent:
        ref = _record_ref(RecordTable.TRACE_EVENT)
        record = TraceEvent(
            ref=ref,
            trace_type=trace_type,
            session_id=session_id,
            turn_id=turn_id,
            experience_ref=experience_ref,
            payload=payload,
        )
        row = await self.backend.create(
            "trace_event", record.model_dump(mode="python", exclude={"ref"}), ref.key
        )
        return _as_model(row, TraceEvent)

    async def query(self, session_id: str | None = None) -> list[TraceEvent]:
        records = [_as_model(row, TraceEvent) for row in await self.backend.list("trace_event")]
        if session_id is None:
            return records
        return [record for record in records if record.session_id == session_id]


class JournalRepository:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    async def append(
        self,
        *,
        sequence: int,
        event_type: str,
        session_id: str,
        payload: dict[str, Any],
        turn_id: str | None = None,
    ) -> JournalEvent:
        ref = _record_ref(RecordTable.JOURNAL_EVENT)
        record = JournalEvent(
            ref=ref,
            sequence=sequence,
            event_type=event_type,
            session_id=session_id,
            turn_id=turn_id,
            payload=payload,
        )
        row = await self.backend.create(
            "journal_event", record.model_dump(mode="python", exclude={"ref"}), ref.key
        )
        return _as_model(row, JournalEvent)

    async def query(self, session_id: str) -> list[JournalEvent]:
        records = [
            _as_model(row, JournalEvent)
            for row in await self.backend.list("journal_event")
            if row.get("session_id") == session_id
        ]
        return sorted(records, key=lambda item: item.sequence)


@dataclass(slots=True)
class Repositories:
    backend: Backend
    experiences: ExperienceRepository
    memories: MemoryRepository
    entities: EntityRepository
    evaluations: EvaluationRepository
    state: StateRepository
    relations: RelationRepository
    traces: TraceRepository
    journal: JournalRepository

    @classmethod
    def create(cls, backend: Backend) -> Repositories:
        return cls(
            backend=backend,
            experiences=ExperienceRepository(backend),
            memories=MemoryRepository(backend),
            entities=EntityRepository(backend),
            evaluations=EvaluationRepository(backend),
            state=StateRepository(backend),
            relations=RelationRepository(backend),
            traces=TraceRepository(backend),
            journal=JournalRepository(backend),
        )
