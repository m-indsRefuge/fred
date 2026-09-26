from __future__ import annotations

from collections import defaultdict

from fred.brain.memory.contracts import RecordRef
from fred.brain.retrieval.contracts import RetrievalCandidate


def reciprocal_rank_fusion(
    rankings: dict[str, list[RecordRef]],
    *,
    view_rankings: dict[str, list[RecordRef]] | None = None,
    k: int = 60,
) -> list[RetrievalCandidate]:
    view_rankings = view_rankings or {}
    scores: dict[str, float] = defaultdict(float)
    refs: dict[str, RecordRef] = {}
    channels: dict[str, set[str]] = defaultdict(set)
    views: dict[str, set[str]] = defaultdict(set)
    ranks: dict[str, dict[str, int]] = defaultdict(dict)
    per_view: dict[str, dict[str, int]] = defaultdict(dict)

    for channel, ordered in rankings.items():
        for rank, ref in enumerate(ordered, start=1):
            key = str(ref)
            refs[key] = ref
            scores[key] += 1.0 / (k + rank)
            channels[key].add(channel)
            ranks[key][channel] = rank
    for view, ordered in view_rankings.items():
        for rank, ref in enumerate(ordered, start=1):
            key = str(ref)
            refs[key] = ref
            scores[key] += 1.0 / (k + rank)
            views[key].add(view)
            per_view[key][view] = rank

    candidates: list[RetrievalCandidate] = []
    for key, score in scores.items():
        ref = refs[key]
        object_type = {
            "experience": "EXPERIENCE",
            "memory": "MEMORY",
            "evaluation": "EVALUATION",
        }[ref.table.value]
        candidates.append(
            RetrievalCandidate(
                ref=ref,
                object_type=object_type,
                discovered_by=channels[key],
                matched_views=views[key],
                vector_rank=ranks[key].get("vector"),
                lexical_rank=ranks[key].get("lexical"),
                graph_rank=ranks[key].get("graph"),
                structured_rank=ranks[key].get("structured"),
                view_ranks=per_view[key],
                rrf_score=score,
            )
        )
    candidates.sort(key=lambda item: (-(item.rrf_score or 0.0), str(item.ref)))
    return candidates

