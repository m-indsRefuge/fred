from __future__ import annotations

import asyncio

from fred.brain.memory.contracts import MemoryStatus, RecordRef
from fred.db.backends import Backend

_VIEW_FIELD = {
    "episodic": "episodicity",
    "semantic": "abstraction",
    "procedural": "procedurality",
    "relational": "relationality",
}


async def _project(backend: Backend, view: str, limit: int) -> list[RecordRef]:
    field = _VIEW_FIELD[view]
    rows = [
        row
        for row in await backend.list("memory")
        if row.get("status") == MemoryStatus.ACTIVE
    ]
    rows.sort(key=lambda row: (-float(row.get(field, 0.0)), str(row.get("id", ""))))
    return [
        RecordRef.model_validate(row["id"])
        for row in rows[:limit]
        if float(row.get(field, 0.0)) > 0
    ]


async def run_views(
    backend: Backend, views: set[str], limit: int
) -> dict[str, list[RecordRef]]:
    ordered = sorted(views)
    results = await asyncio.gather(*(_project(backend, view, limit) for view in ordered))
    return dict(zip(ordered, results, strict=True))
