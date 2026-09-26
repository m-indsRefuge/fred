from __future__ import annotations

from pathlib import Path

from fred.db.client import SurrealClient


def schema_path() -> Path:
    return Path(__file__).resolve().parents[3] / "db" / "FRED_SURREALDB_V1.surql"


async def apply_schema(client: SurrealClient, path: Path | None = None) -> None:
    source = (path or schema_path()).read_text(encoding="utf-8")
    await client.query(source)

