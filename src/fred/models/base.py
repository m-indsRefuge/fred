from __future__ import annotations

from typing import Any, Protocol

from fred.brain.memory.contracts import EvidenceValidation, MemoryProposal, SleepDecision
from fred.brain.retrieval.contracts import CognitiveSelection, RetrievalCandidate


class CognitiveModel(Protocol):
    identity: str

    async def adjudicate_retrieval(
        self, query: str, candidates: list[dict[str, Any]]
    ) -> list[CognitiveSelection]: ...

    async def propose_memory(self, context: dict[str, Any]) -> MemoryProposal: ...

    async def validate_evidence(self, context: dict[str, Any]) -> EvidenceValidation: ...

    async def adjudicate_sleep(self, context: dict[str, Any]) -> SleepDecision: ...

    async def reason(
        self, prompt: str, selected_evidence: list[dict[str, Any]]
    ) -> str: ...


class EmbeddingModel(Protocol):
    identity: str
    dimension: int

    async def embed_query(self, text: str) -> list[float]: ...

    async def embed_document(self, text: str) -> list[float]: ...


def candidate_payload(candidate: RetrievalCandidate, content: str) -> dict[str, Any]:
    return {
        "ref": str(candidate.ref),
        "object_type": candidate.object_type,
        "matched_views": sorted(candidate.matched_views),
        "rrf_score": candidate.rrf_score,
        "visibility": candidate.visibility,
        "content": content,
    }

