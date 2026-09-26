from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fred.brain.memory.contracts import (
    EvidenceValidation,
    MemoryProposal,
    MemoryRecord,
    MemoryStatus,
    RecordRef,
    RecordTable,
    RelationKind,
    SleepDecision,
    SleepOperation,
    TraceType,
)
from fred.brain.memory.repositories import Repositories
from fred.brain.memory.validators import evidence_allows_activation, validate_memory_proposal
from fred.models.base import CognitiveModel, EmbeddingModel


@dataclass(slots=True)
class SleepResult:
    decision: SleepDecision | None
    considered: list[RecordRef]
    activated: list[RecordRef] = field(default_factory=list)
    created: list[RecordRef] = field(default_factory=list)
    tombstoned: list[RecordRef] = field(default_factory=list)
    validation: EvidenceValidation | None = None
    interrupted: bool = False
    committed: bool = False


class SleepEngine:
    def __init__(
        self,
        repositories: Repositories,
        embedding: EmbeddingModel,
        cognitive: CognitiveModel,
        *,
        packet_limit: int = 8,
    ) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.cognitive = cognitive
        self.packet_limit = packet_limit

    @staticmethod
    def _evidence_keys(memory: MemoryRecord) -> set[str]:
        return {
            str(value)
            for value in memory.provenance.get("evidence_refs", [])
            if value is not None
        }

    async def _candidate_group(self) -> list[MemoryRecord]:
        memories = [
            item
            for item in await self.repositories.memories.list_all()
            if item.status is not MemoryStatus.TOMBSTONED
        ]
        if not memories:
            return []
        memories.sort(
            key=lambda item: (
                0 if item.status is MemoryStatus.PROVISIONAL else 1,
                item.created_at,
                str(item.ref),
            )
        )
        provisional = [item for item in memories if item.status is MemoryStatus.PROVISIONAL]
        seed = provisional[0] if provisional else None
        if seed is None:
            for index, candidate in enumerate(memories):
                candidate_evidence = self._evidence_keys(candidate)
                if any(
                    candidate_evidence & self._evidence_keys(other)
                    for other in memories[index + 1 :]
                ):
                    seed = candidate
                    break
        if seed is None:
            return []
        group = [seed]
        evidence = self._evidence_keys(seed)
        for candidate in memories:
            if candidate.ref == seed.ref:
                continue
            if len(group) >= self.packet_limit:
                break
            candidate_evidence = self._evidence_keys(candidate)
            if evidence & candidate_evidence:
                group.append(candidate)
                evidence.update(candidate_evidence)
        return group

    async def _row(
        self, ref: RecordRef, repositories: Repositories | None = None
    ) -> dict[str, Any]:
        repos = repositories or self.repositories
        row = await repos.backend.get(ref)
        if row is None:
            raise ValueError(f"missing referenced record: {ref}")
        return row

    async def _packet(self, group: list[MemoryRecord]) -> dict[str, Any]:
        evidence_refs: dict[str, RecordRef] = {}
        for memory in group:
            for raw in memory.provenance.get("evidence_refs", []):
                try:
                    ref = RecordRef.model_validate(raw)
                except ValueError:
                    continue
                evidence_refs[str(ref)] = ref
        evidence = [
            {"ref": str(ref), "record": await self._row(ref)}
            for ref in evidence_refs.values()
        ]
        return {
            "memories": [item.model_dump(mode="json") for item in group],
            "supporting_evidence": evidence,
            "allowed_operations": [item.value for item in SleepOperation],
            "rules": {
                "experience_is_immutable": True,
                "model_text_has_no_persistence_authority": True,
                "merge_or_promote_must_preserve_lineage": True,
            },
        }

    @staticmethod
    def _validate_decision(decision: SleepDecision, group: list[MemoryRecord]) -> None:
        group_refs = {str(item.ref) for item in group}
        if not decision.source_memory_refs:
            raise ValueError("Sleep decision requires at least one source Memory")
        for ref in decision.source_memory_refs:
            if ref.table is not RecordTable.MEMORY or str(ref) not in group_refs:
                raise ValueError(f"Sleep decision references Memory outside review packet: {ref}")
        if decision.operation in {SleepOperation.MERGE, SleepOperation.PROMOTE}:
            if decision.proposed_memory is None:
                raise ValueError(f"{decision.operation} requires proposed_memory")
            validate_memory_proposal(decision.proposed_memory)
            if not decision.proposed_memory.proposed_content:
                raise ValueError(f"{decision.operation} requires proposed content")
        elif decision.proposed_memory is not None:
            raise ValueError(f"{decision.operation} must not create a proposed Memory")

    async def _stored_validation(self, memory: MemoryRecord) -> EvidenceValidation | None:
        raw = memory.metadata.get("evidence_validation")
        if not isinstance(raw, dict):
            return None
        validation = EvidenceValidation.model_validate(raw)
        if validation.proposal_ref != memory.ref:
            raise ValueError("stored evidence validation targets the wrong Memory")
        return validation

    async def _validate_new_memory(
        self,
        ref: RecordRef,
        proposal: MemoryProposal,
        source_refs: list[RecordRef],
    ) -> EvidenceValidation:
        all_refs: dict[str, RecordRef] = {
            str(item): item
            for item in proposal.evidence_refs + proposal.counterevidence_refs + source_refs
        }
        evidence = [
            {"ref": str(item), "record": await self._row(item)} for item in all_refs.values()
        ]
        validation = await self.cognitive.validate_evidence(
            {
                "proposal_ref": str(ref),
                "proposal": proposal.model_dump(mode="json"),
                "source_memory_refs": [str(item) for item in source_refs],
                "evidence": evidence,
                "instruction": "Independently judge support for the consolidated interpretation.",
            }
        )
        if validation.proposal_ref != ref:
            raise ValueError("Sleep evidence validator returned the wrong proposal_ref")
        allowed = set(all_refs)
        returned = {
            str(item)
            for item in (
                validation.supported_refs
                + validation.unsupported_refs
                + validation.contradictory_refs
            )
        }
        if not returned.issubset(allowed):
            raise ValueError(
                "Sleep evidence validator referenced evidence outside the review packet"
            )
        return validation

    async def _commit_created_memory(
        self,
        *,
        decision: SleepDecision,
        planned_ref: RecordRef,
        proposal: MemoryProposal,
        validation: EvidenceValidation,
        embedding: list[float],
    ) -> tuple[MemoryRecord, list[RecordRef]]:
        source_refs = list(dict.fromkeys(decision.source_memory_refs))
        evidence_refs = list(
            dict.fromkeys(proposal.evidence_refs + source_refs)
        )
        persisted_proposal = proposal.model_copy(update={"evidence_refs": evidence_refs})
        tombstoned: list[RecordRef] = []
        async with self.repositories.backend.atomic() as transaction:
            repos = Repositories.create(transaction)
            memory = await repos.memories.create_provisional(
                persisted_proposal,
                embedding=embedding,
                embedding_model=self.embedding.identity,
                embedding_version=self.embedding.identity,
                metadata={
                    "sleep_operation": decision.operation.value,
                    "sleep_source_memory_refs": [str(item) for item in source_refs],
                },
                ref=planned_ref,
            )
            for ref in evidence_refs:
                if ref.table in {RecordTable.EXPERIENCE, RecordTable.MEMORY}:
                    await repos.relations.create_validated(
                        in_ref=memory.ref,
                        out_ref=ref,
                        kind=RelationKind.DERIVED_FROM,
                        source="memory_sleep",
                    )
                elif ref.table is RecordTable.EVALUATION:
                    await repos.relations.create_validated(
                        in_ref=ref,
                        out_ref=memory.ref,
                        kind=RelationKind.SUPPORTS,
                        source="memory_sleep",
                    )
            memory = await repos.memories.record_validation(memory.ref, validation)
            memory = await repos.memories.activate(memory.ref, validation)
            if decision.operation is SleepOperation.MERGE:
                for ref in source_refs:
                    await repos.memories.tombstone(ref, f"merged into {memory.ref}")
                    tombstoned.append(ref)
        return memory, tombstoned

    async def run_once(
        self,
        *,
        session_id: str,
        trigger: str = "IDLE",
        interrupt_before_commit: bool = False,
    ) -> SleepResult:
        started = time.perf_counter()
        group = await self._candidate_group()
        considered = [item.ref for item in group]
        if not group:
            result = SleepResult(decision=None, considered=[])
            await self.repositories.traces.append(
                trace_type=TraceType.SLEEP,
                session_id=session_id,
                payload={
                    "trigger": trigger,
                    "memories_considered": [],
                    "candidate_groups": [],
                    "validation_result": "NO_WORK",
                    "mutations": [],
                    "duration_ms": (time.perf_counter() - started) * 1000,
                    "interrupted": False,
                },
            )
            return result

        packet = await self._packet(group)
        decision = await self.cognitive.adjudicate_sleep(packet)
        self._validate_decision(decision, group)

        validation: EvidenceValidation | None = None
        planned_ref: RecordRef | None = None
        vector: list[float] | None = None
        if decision.operation in {SleepOperation.MERGE, SleepOperation.PROMOTE}:
            assert decision.proposed_memory is not None
            proposal_refs = (
                decision.proposed_memory.evidence_refs
                + decision.proposed_memory.counterevidence_refs
            )
            for ref in proposal_refs:
                await self._row(ref)
            planned_ref = RecordRef(table=RecordTable.MEMORY, key=uuid.uuid4().hex)
            validation = await self._validate_new_memory(
                planned_ref, decision.proposed_memory, decision.source_memory_refs
            )
            if not evidence_allows_activation(validation):
                await self.repositories.traces.append(
                    trace_type=TraceType.SLEEP,
                    session_id=session_id,
                    payload={
                        "trigger": trigger,
                        "memories_considered": [str(item) for item in considered],
                        "candidate_groups": [[str(item) for item in considered]],
                        "decision": decision.model_dump(mode="json"),
                        "validation_result": validation.model_dump(mode="json"),
                        "mutations": [],
                        "duration_ms": (time.perf_counter() - started) * 1000,
                        "interrupted": False,
                        "committed": False,
                    },
                )
                return SleepResult(
                    decision=decision,
                    considered=considered,
                    validation=validation,
                )
            vector = await self.embedding.embed_document(
                decision.proposed_memory.proposed_content or ""
            )

        if interrupt_before_commit:
            await self.repositories.traces.append(
                trace_type=TraceType.SLEEP,
                session_id=session_id,
                payload={
                    "trigger": trigger,
                    "memories_considered": [str(item) for item in considered],
                    "candidate_groups": [[str(item) for item in considered]],
                    "decision": decision.model_dump(mode="json"),
                    "validation_result": (
                        validation.model_dump(mode="json") if validation else "PRECOMMIT"
                    ),
                    "mutations": [],
                    "duration_ms": (time.perf_counter() - started) * 1000,
                    "interrupted": True,
                    "committed": False,
                },
            )
            return SleepResult(
                decision=decision,
                considered=considered,
                validation=validation,
                interrupted=True,
            )

        activated: list[RecordRef] = []
        created: list[RecordRef] = []
        tombstoned: list[RecordRef] = []

        if decision.operation is SleepOperation.KEEP:
            async with self.repositories.backend.atomic() as transaction:
                repos = Repositories.create(transaction)
                for ref in decision.source_memory_refs:
                    memory = await repos.memories.get(ref)
                    if memory is None:
                        raise ValueError(f"missing source Memory: {ref}")
                    if memory.status is MemoryStatus.ACTIVE:
                        continue
                    stored_validation = await self._stored_validation(memory)
                    if stored_validation and evidence_allows_activation(stored_validation):
                        await repos.memories.activate(ref, stored_validation)
                        activated.append(ref)
        elif decision.operation is SleepOperation.TOMBSTONE:
            async with self.repositories.backend.atomic() as transaction:
                repos = Repositories.create(transaction)
                for ref in decision.source_memory_refs:
                    await repos.memories.tombstone(ref, decision.model_explanation)
                    tombstoned.append(ref)
        else:
            assert planned_ref is not None
            assert decision.proposed_memory is not None
            assert validation is not None
            assert vector is not None
            memory, tombstoned = await self._commit_created_memory(
                decision=decision,
                planned_ref=planned_ref,
                proposal=decision.proposed_memory,
                validation=validation,
                embedding=vector,
            )
            created.append(memory.ref)
            activated.append(memory.ref)

        mutations = [
            *({"operation": "ACTIVATE", "ref": str(ref)} for ref in activated),
            *({"operation": "CREATE", "ref": str(ref)} for ref in created),
            *({"operation": "TOMBSTONE", "ref": str(ref)} for ref in tombstoned),
        ]
        await self.repositories.traces.append(
            trace_type=TraceType.SLEEP,
            session_id=session_id,
            payload={
                "trigger": trigger,
                "memories_considered": [str(item) for item in considered],
                "candidate_groups": [[str(item) for item in considered]],
                "supporting_experience_refs": [
                    item["ref"]
                    for item in packet["supporting_evidence"]
                    if str(item["ref"]).startswith("experience:")
                ],
                "decision": decision.model_dump(mode="json"),
                "validation_result": (
                    validation.model_dump(mode="json") if validation else "VALID"
                ),
                "mutations": mutations,
                "memories_activated": [str(item) for item in activated],
                "memories_merged": (
                    [str(item) for item in decision.source_memory_refs]
                    if decision.operation is SleepOperation.MERGE
                    else []
                ),
                "memories_promoted": (
                    [str(item) for item in created]
                    if decision.operation is SleepOperation.PROMOTE
                    else []
                ),
                "memories_tombstoned": [str(item) for item in tombstoned],
                "duration_ms": (time.perf_counter() - started) * 1000,
                "interrupted": False,
                "committed": True,
            },
        )
        return SleepResult(
            decision=decision,
            considered=considered,
            activated=activated,
            created=created,
            tombstoned=tombstoned,
            validation=validation,
            committed=True,
        )
