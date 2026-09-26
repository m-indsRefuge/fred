from __future__ import annotations

import asyncio
from typing import Any

from fred.brain.memory.contracts import CognitiveRole, RecordRef, RecordTable, TraceType
from fred.brain.memory.repositories import Repositories
from fred.brain.retrieval.contracts import (
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatus,
)
from fred.brain.retrieval.fusion import reciprocal_rank_fusion
from fred.brain.retrieval.views import run_views
from fred.brain.retrieval.visibility import assign_visibility
from fred.models.base import CognitiveModel, EmbeddingModel


class RetrievalEngine:
    def __init__(
        self,
        repositories: Repositories,
        embedding: EmbeddingModel,
        cognitive: CognitiveModel,
    ) -> None:
        self.repositories = repositories
        self.embedding = embedding
        self.cognitive = cognitive

    async def _content(self, ref: RecordRef) -> str:
        row = await self.repositories.backend.get(ref)
        if not row:
            return ""
        if ref.table is RecordTable.MEMORY:
            return str(row.get("content", ""))
        if ref.table is RecordTable.EXPERIENCE:
            return str(row.get("search_text", ""))
        return str(row)

    async def retrieve(self, query: RetrievalQuery, *, session_id: str) -> RetrievalResult:
        vector = await self.embedding.embed_query(query.semantic_query)
        seeds = [
            *query.entity_refs,
            *([query.active_experience_ref] if query.active_experience_ref else []),
        ]
        channel_calls = {
            "vector": self.repositories.backend.vector_search(
                vector, query.object_types, query.candidate_budget
            ),
            "lexical": self.repositories.backend.lexical_search(
                query.semantic_query, query.object_types, query.candidate_budget
            ),
            "structured": self.repositories.backend.structured_search(
                query.entity_refs, query.object_types, query.candidate_budget
            ),
        }
        names = list(channel_calls)
        raw = await asyncio.gather(*channel_calls.values(), return_exceptions=True)
        rankings: dict[str, list[RecordRef]] = {}
        errors: dict[str, str] = {}
        for name, result in zip(names, raw, strict=True):
            if isinstance(result, Exception):
                errors[name] = str(result)
            else:
                rankings[name] = result

        view_rankings = await run_views(
            self.repositories.backend, query.views, query.candidate_budget
        )
        preliminary = reciprocal_rank_fusion(rankings, view_rankings=view_rankings)
        graph_seeds = seeds + [item.ref for item in preliminary[:8]]
        try:
            rankings["graph"] = await self.repositories.backend.graph_expand(
                graph_seeds, query.object_types, query.candidate_budget, max_depth=2
            )
        except Exception as exc:
            errors["graph"] = str(exc)

        candidates = reciprocal_rank_fusion(rankings, view_rankings=view_rankings)
        candidates = candidates[: query.candidate_budget]
        assign_visibility(candidates)
        if not candidates:
            status = RetrievalStatus.ERROR if errors and not rankings else RetrievalStatus.NO_MATCH
            await self.repositories.traces.append(
                trace_type=TraceType.RETRIEVAL,
                session_id=session_id,
                payload={
                    "query_id": query.query_id,
                    "status": status.value,
                    "machine_ranking": [],
                    "channel_errors": errors,
                },
            )
            return RetrievalResult(
                query_id=query.query_id,
                status=status,
                candidates=[],
                channel_errors=errors,
            )

        payloads: list[dict[str, Any]] = []
        for candidate in candidates:
            payloads.append(
                {
                    "ref": str(candidate.ref),
                    "object_type": candidate.object_type,
                    "content": await self._content(candidate.ref),
                    "matched_views": sorted(candidate.matched_views),
                    "discovered_by": sorted(candidate.discovered_by),
                    "rrf_score": candidate.rrf_score,
                    "visibility": candidate.visibility.value,
                }
            )
        selections = await self.cognitive.adjudicate_retrieval(query.semantic_query, payloads)
        candidate_refs = {str(candidate.ref) for candidate in candidates}
        selections = [item for item in selections if str(item.ref) in candidate_refs]
        status = RetrievalStatus.PARTIAL if errors else RetrievalStatus.READY
        await self.repositories.traces.append(
            trace_type=TraceType.RETRIEVAL,
            session_id=session_id,
            payload={
                "query_id": query.query_id,
                "status": status.value,
                "machine_ranking": [candidate.model_dump(mode="json") for candidate in candidates],
                "fred_selection": [selection.model_dump(mode="json") for selection in selections],
                "channel_errors": errors,
            },
        )
        return RetrievalResult(
            query_id=query.query_id,
            status=status,
            candidates=candidates,
            selections=selections,
            channel_errors=errors,
        )

    @staticmethod
    def selected_refs(result: RetrievalResult) -> list[RecordRef]:
        accepted = {
            CognitiveRole.RELEVANT,
            CognitiveRole.SUPPORTING,
            CognitiveRole.CONTRADICTORY,
            CognitiveRole.CONTEXTUAL,
        }
        return [
            selection.ref
            for selection in result.selections
            if selection.role in accepted and selection.contextual_relevance > 0
        ]
