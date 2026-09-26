from __future__ import annotations

from fred.brain.memory.contracts import CognitiveRelation, RecordRef, RecordTable, RelationKind


class ProvenanceError(ValueError):
    pass


async def resolve_experience_provenance(
    root: RecordRef,
    *,
    memory_get,
    experience_get,
    relations: list[CognitiveRelation],
) -> set[RecordRef]:
    by_memory: dict[str, list[RecordRef]] = {}
    for relation in relations:
        if relation.kind is RelationKind.DERIVED_FROM:
            by_memory.setdefault(str(relation.in_ref), []).append(relation.out_ref)
    resolved: set[RecordRef] = set()
    visiting: set[str] = set()

    async def visit(ref: RecordRef) -> None:
        if ref.table is RecordTable.EXPERIENCE:
            if await experience_get(ref) is None:
                raise ProvenanceError(f"missing Experience evidence: {ref}")
            resolved.add(ref)
            return
        if ref.table is not RecordTable.MEMORY:
            raise ProvenanceError(f"unsupported provenance endpoint: {ref}")
        if str(ref) in visiting:
            raise ProvenanceError(f"provenance cycle at {ref}")
        if await memory_get(ref) is None:
            raise ProvenanceError(f"missing Memory evidence: {ref}")
        visiting.add(str(ref))
        parents = by_memory.get(str(ref), [])
        if not parents:
            raise ProvenanceError(f"Memory has no Experience-resolving provenance: {ref}")
        for parent in parents:
            await visit(parent)
        visiting.remove(str(ref))

    await visit(root)
    return resolved
