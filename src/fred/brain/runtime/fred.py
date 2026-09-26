from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fred.brain.memory.engine import MemoryEngine, MemoryFormationResult
from fred.brain.memory.repositories import Repositories
from fred.brain.memory.sleep import SleepEngine, SleepResult
from fred.brain.retrieval.contracts import RetrievalQuery, RetrievalResult
from fred.brain.retrieval.engine import RetrievalEngine
from fred.brain.runtime.experience import ActiveExperience, ExperienceService
from fred.models.base import CognitiveModel, EmbeddingModel


@dataclass(slots=True)
class CommitResult:
    experience_ref: str
    memory: MemoryFormationResult


class FredRuntime:
    def __init__(
        self,
        repositories: Repositories,
        embedding: EmbeddingModel,
        cognitive: CognitiveModel,
    ) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.cognitive = cognitive
        self.experiences = ExperienceService(repositories, embedding)
        self.memory = MemoryEngine(repositories, embedding, cognitive)
        self.retrieval = RetrievalEngine(repositories, embedding, cognitive)
        self.sleep_engine = SleepEngine(repositories, embedding, cognitive)

    async def begin(
        self,
        *,
        session_id: str,
        input: dict[str, Any],
        context: dict[str, Any] | None = None,
        turn_id: str | None = None,
    ) -> ActiveExperience:
        return await self.experiences.begin(
            session_id=session_id,
            turn_id=turn_id,
            input=input,
            context=context,
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
        metadata: dict[str, Any] | None = None,
    ) -> CommitResult:
        experience = await self.experiences.commit(
            active,
            perception=perception,
            decision=decision,
            action=action,
            outcome=outcome,
            feedback=feedback,
            metadata=metadata,
        )
        memory = await self.memory.form_from_experience(
            experience.ref,
            session_id=active.session_id,
            turn_id=active.turn_id,
        )
        return CommitResult(experience_ref=str(experience.ref), memory=memory)

    async def retrieve(
        self,
        prompt: str,
        *,
        session_id: str,
        views: set[str] | None = None,
        candidate_budget: int = 32,
    ) -> RetrievalResult:
        query = RetrievalQuery(
            query_id=uuid.uuid4().hex,
            semantic_query=prompt,
            views=views or set(),
            candidate_budget=candidate_budget,
        )
        return await self.retrieval.retrieve(query, session_id=session_id)

    async def reason(
        self,
        prompt: str,
        *,
        session_id: str,
        views: set[str] | None = None,
    ) -> tuple[str, RetrievalResult]:
        retrieval = await self.retrieve(prompt, session_id=session_id, views=views)
        selected: list[dict[str, Any]] = []
        for ref in self.retrieval.selected_refs(retrieval):
            row = await self.repositories.backend.get(ref)
            if row is not None:
                selected.append({"ref": str(ref), "record": row})
        answer = await self.cognitive.reason(prompt, selected)
        return answer, retrieval

    async def sleep(
        self,
        *,
        session_id: str,
        interrupt_before_commit: bool = False,
    ) -> SleepResult:
        return await self.sleep_engine.run_once(
            session_id=session_id,
            interrupt_before_commit=interrupt_before_commit,
        )

    async def get_state(self, key: str) -> dict[str, Any] | None:
        record = await self.repositories.state.get(key)
        return record.value if record else None

