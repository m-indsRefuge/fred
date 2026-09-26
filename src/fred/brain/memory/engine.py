from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fred.brain.memory.contracts import (
    EvidenceValidation,
    MemoryOperation,
    MemoryProposal,
    MemoryRecord,
    RecordRef,
    RecordTable,
    RelationKind,
    TraceType,
)
from fred.brain.memory.repositories import Repositories
from fred.brain.memory.validators import validate_memory_proposal
from fred.models.base import CognitiveModel, EmbeddingModel

_OPERATION_RELATION = {
    MemoryOperation.REINFORCE: RelationKind.REINFORCES,
    MemoryOperation.CONTRADICT: RelationKind.CONTRADICTS,
    MemoryOperation.SUPERSEDE: RelationKind.SUPERSEDES,
}


@dataclass(slots=True)
class MemoryFormationResult:
    proposal: MemoryProposal
    memory: MemoryRecord | None
    validation: EvidenceValidation | None


class MemoryEngine:
    def __init__(
        self,
        repositories: Repositories,
        embedding: EmbeddingModel,
        cognitive: CognitiveModel,
        *,
        context_memory_limit: int = 8,
    ) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.cognitive = cognitive
        self.context_memory_limit = context_memory_limit

    async def _row(self, ref: RecordRef) -> dict[str, Any]:
        row = await self.repositories.backend.get(ref)
        if row is None:
            raise ValueError(f"missing referenced record: {ref}")
        return row

    async def _validate_references(self, proposal: MemoryProposal) -> None:
        validate_memory_proposal(proposal)
        for ref in proposal.evidence_refs + proposal.counterevidence_refs:
            await self._row(ref)
        if proposal.target_memory_ref is not None:
            if proposal.target_memory_ref.table is not RecordTable.MEMORY:
                raise ValueError("target_memory_ref must refer to a Memory")
            if await self.repositories.memories.get(proposal.target_memory_ref) is None:
                raise ValueError(f"missing target Memory: {proposal.target_memory_ref}")

    async def _context(self, experience_ref: RecordRef) -> dict[str, Any]:
        experience = await self.repositories.experiences.get(experience_ref)
        if experience is None:
            raise ValueError(f"missing committed Experience: {experience_ref}")
        memories = sorted(
            await self.repositories.memories.search_active(),
            key=lambda item: item.created_at,
            reverse=True,
        )[: self.context_memory_limit]
        return {
            "committed_experience": experience.model_dump(mode="json"),
            "active_memory_context": [item.model_dump(mode="json") for item in memories],
            "rules": {
                "foreground_memory_status": "PROVISIONAL",
                "model_text_has_no_persistence_authority": True,
            },
        }

    async def _validation_context(
        self, memory: MemoryRecord, proposal: MemoryProposal
    ) -> dict[str, Any]:
        evidence = [
            {"ref": str(ref), "record": await self._row(ref)}
            for ref in proposal.evidence_refs + proposal.counterevidence_refs
        ]
        return {
            "proposal_ref": str(memory.ref),
            "proposal": proposal.model_dump(mode="json"),
            "evidence": evidence,
            "instruction": "Judge evidence support independently from proposer confidence.",
        }

    @staticmethod
    def _check_validation(
        memory: MemoryRecord,
        proposal: MemoryProposal,
        validation: EvidenceValidation,
    ) -> None:
        if validation.proposal_ref != memory.ref:
            raise ValueError("evidence validator returned the wrong proposal_ref")
        allowed = {
            str(ref)
            for ref in proposal.evidence_refs + proposal.counterevidence_refs
        }
        returned = {
            str(ref)
            for ref in (
                validation.supported_refs
                + validation.unsupported_refs
                + validation.contradictory_refs
            )
        }
        if not returned.issubset(allowed):
            raise ValueError("evidence validator referenced records outside the proposal evidence")

    async def form_from_experience(
        self,
        experience_ref: RecordRef,
        *,
        session_id: str,
        turn_id: str | None = None,
    ) -> MemoryFormationResult:
        context = await self._context(experience_ref)
        proposal = await self.cognitive.propose_memory(context)
        await self.repositories.traces.append(
            trace_type=TraceType.MEMORY_PROPOSAL,
            session_id=session_id,
            turn_id=turn_id,
            experience_ref=experience_ref,
            payload={"proposal": proposal.model_dump(mode="json")},
        )
        if proposal.operation is MemoryOperation.NO_CHANGE:
            return MemoryFormationResult(proposal=proposal, memory=None, validation=None)

        await self._validate_references(proposal)
        vector = await self.embedding.embed_document(proposal.proposed_content or "")
        memory = await self.repositories.memories.create_provisional(
            proposal,
            embedding=vector,
            embedding_model=self.embedding.identity,
            embedding_version=self.embedding.identity,
            metadata={
                "formation_experience_ref": str(experience_ref),
                "target_memory_ref": (
                    str(proposal.target_memory_ref)
                    if proposal.target_memory_ref is not None
                    else None
                ),
            },
        )

        for evidence_ref in proposal.evidence_refs:
            if evidence_ref.table in {RecordTable.EXPERIENCE, RecordTable.MEMORY}:
                await self.repositories.relations.create_validated(
                    in_ref=memory.ref,
                    out_ref=evidence_ref,
                    kind=RelationKind.DERIVED_FROM,
                    source="memory_formation",
                )
            elif evidence_ref.table is RecordTable.EVALUATION:
                await self.repositories.relations.create_validated(
                    in_ref=evidence_ref,
                    out_ref=memory.ref,
                    kind=RelationKind.SUPPORTS,
                    source="memory_formation",
                )

        relation_kind = _OPERATION_RELATION.get(proposal.operation)
        if relation_kind is not None and proposal.target_memory_ref is not None:
            await self.repositories.relations.create_validated(
                in_ref=memory.ref,
                out_ref=proposal.target_memory_ref,
                kind=relation_kind,
                source="memory_formation",
            )

        validation = await self.cognitive.validate_evidence(
            await self._validation_context(memory, proposal)
        )
        self._check_validation(memory, proposal, validation)
        memory = await self.repositories.memories.record_validation(memory.ref, validation)
        await self.repositories.traces.append(
            trace_type=TraceType.MEMORY_VALIDATION,
            session_id=session_id,
            turn_id=turn_id,
            experience_ref=experience_ref,
            payload={
                "memory_ref": str(memory.ref),
                "validation": validation.model_dump(mode="json"),
                "status_after_validation": memory.status.value,
            },
        )
        return MemoryFormationResult(
            proposal=proposal,
            memory=memory,
            validation=validation,
        )
