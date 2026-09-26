from __future__ import annotations

from collections import defaultdict, deque

from fred.brain.memory.contracts import (
    CognitiveRelation,
    EvidenceValidation,
    EvidenceVerdict,
    MemoryProposal,
    RecordRef,
    RecordTable,
    RelationKind,
)

_LEGAL_ENDPOINTS: dict[RelationKind, set[tuple[RecordTable, RecordTable]]] = {
    RelationKind.DERIVED_FROM: {
        (RecordTable.MEMORY, RecordTable.EXPERIENCE),
        (RecordTable.MEMORY, RecordTable.MEMORY),
    },
    RelationKind.PART_OF: {
        (RecordTable.EXPERIENCE, RecordTable.EXPERIENCE),
        (RecordTable.MEMORY, RecordTable.MEMORY),
    },
    RelationKind.ABOUT: {
        (RecordTable.EXPERIENCE, RecordTable.ENTITY),
        (RecordTable.MEMORY, RecordTable.ENTITY),
    },
    RelationKind.CAUSED_BY: {
        (RecordTable.EXPERIENCE, RecordTable.EXPERIENCE),
        (RecordTable.MEMORY, RecordTable.EXPERIENCE),
    },
    RelationKind.RESULTED_IN: {
        (RecordTable.EXPERIENCE, RecordTable.EVALUATION),
        (RecordTable.MEMORY, RecordTable.EVALUATION),
    },
    RelationKind.SUPPORTS: {
        (RecordTable.EXPERIENCE, RecordTable.MEMORY),
        (RecordTable.MEMORY, RecordTable.MEMORY),
        (RecordTable.EVALUATION, RecordTable.MEMORY),
    },
    RelationKind.CONTRADICTS: {
        (RecordTable.EXPERIENCE, RecordTable.MEMORY),
        (RecordTable.MEMORY, RecordTable.MEMORY),
        (RecordTable.EVALUATION, RecordTable.MEMORY),
    },
    RelationKind.SUPERSEDES: {(RecordTable.MEMORY, RecordTable.MEMORY)},
    RelationKind.REINFORCES: {(RecordTable.MEMORY, RecordTable.MEMORY)},
    RelationKind.SIMILAR_TO: {
        (RecordTable.EXPERIENCE, RecordTable.EXPERIENCE),
        (RecordTable.MEMORY, RecordTable.MEMORY),
    },
    RelationKind.RECALLED_WITH: {
        (RecordTable.EXPERIENCE, RecordTable.EXPERIENCE),
        (RecordTable.MEMORY, RecordTable.MEMORY),
        (RecordTable.MEMORY, RecordTable.EXPERIENCE),
        (RecordTable.EXPERIENCE, RecordTable.MEMORY),
    },
}


def validate_relation_endpoints(
    kind: RelationKind, in_ref: RecordRef, out_ref: RecordRef
) -> None:
    if (in_ref.table, out_ref.table) not in _LEGAL_ENDPOINTS[kind]:
        raise ValueError(
            f"illegal {kind} endpoints: {in_ref.table.value} -> {out_ref.table.value}"
        )


def evidence_allows_activation(validation: EvidenceValidation) -> bool:
    return validation.verdict in {EvidenceVerdict.SUPPORTED, EvidenceVerdict.PARTIAL}


def validate_memory_proposal(proposal: MemoryProposal) -> None:
    for ref in proposal.evidence_refs + proposal.counterevidence_refs:
        if ref.table not in {RecordTable.EXPERIENCE, RecordTable.MEMORY, RecordTable.EVALUATION}:
            raise ValueError(f"invalid Memory evidence reference: {ref}")


def would_create_provenance_cycle(
    source: RecordRef,
    evidence_refs: list[RecordRef],
    relations: list[CognitiveRelation],
) -> bool:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for relation in relations:
        if relation.kind is RelationKind.DERIVED_FROM:
            adjacency[str(relation.in_ref)].append(str(relation.out_ref))
    for evidence in evidence_refs:
        adjacency[str(source)].append(str(evidence))
    queue = deque(adjacency[str(source)])
    seen: set[str] = set()
    while queue:
        current = queue.popleft()
        if current == str(source):
            return True
        if current in seen:
            continue
        seen.add(current)
        queue.extend(adjacency.get(current, []))
    return False

