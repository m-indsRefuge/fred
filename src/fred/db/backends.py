from __future__ import annotations

import copy
import json
import math
import re
import uuid
from collections import Counter, defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Protocol

from fred.brain.memory.contracts import MemoryStatus, RecordRef, RecordTable
from fred.db.client import SurrealClient

_SAFE_TABLES = {table.value for table in RecordTable}
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _ref(value: str | RecordRef) -> RecordRef:
    return value if isinstance(value, RecordRef) else RecordRef.model_validate(value)


def _plain(value: Any) -> Any:
    if isinstance(value, RecordRef):
        return str(value)
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="python"))
    if isinstance(value, dict):
        if set(value) == {"table", "key"}:
            try:
                return str(RecordRef.model_validate(value))
            except ValueError:
                pass
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    if hasattr(value, "value") and isinstance(value.value, str):
        return value.value
    return value


def _surreal_literal(value: Any) -> str:
    if isinstance(value, RecordRef):
        return str(value)
    if hasattr(value, "model_dump"):
        return _surreal_literal(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        return f"d{json.dumps(value.isoformat())}"
    if isinstance(value, dict):
        if set(value) == {"table", "key"}:
            try:
                return str(RecordRef.model_validate(value))
            except ValueError:
                pass
        fields = ", ".join(
            f"{json.dumps(str(key))}: {_surreal_literal(item)}" for key, item in value.items()
        )
        return "{" + fields + "}"
    if isinstance(value, (list, tuple, set)):
        return "[" + ", ".join(_surreal_literal(item) for item in value) + "]"
    if hasattr(value, "value") and isinstance(value.value, str):
        return json.dumps(value.value)
    if value is None:
        return "NONE"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        try:
            parsed = RecordRef.model_validate(value)
        except ValueError:
            return json.dumps(value)
        return str(parsed)
    return json.dumps(value, default=str)


class Backend(Protocol):
    async def create(
        self, table: str, data: dict[str, Any], key: str | None = None
    ) -> dict[str, Any]: ...
    async def get(self, ref: RecordRef) -> dict[str, Any] | None: ...
    async def list(self, table: str) -> list[dict[str, Any]]: ...
    async def update(self, ref: RecordRef, patch: dict[str, Any]) -> dict[str, Any]: ...
    async def relate(
        self,
        in_ref: RecordRef,
        out_ref: RecordRef,
        data: dict[str, Any],
        key: str | None = None,
    ) -> dict[str, Any]: ...
    async def vector_search(
        self, vector: list[float], object_types: set[str], limit: int
    ) -> list[RecordRef]: ...
    async def lexical_search(
        self, query: str, object_types: set[str], limit: int
    ) -> list[RecordRef]: ...
    async def structured_search(
        self, entity_refs: list[RecordRef], object_types: set[str], limit: int
    ) -> list[RecordRef]: ...
    async def graph_expand(
        self, seeds: list[RecordRef], object_types: set[str], limit: int, max_depth: int = 2
    ) -> list[RecordRef]: ...
    def atomic(self) -> AsyncIterator[Backend]: ...


class InMemoryBackend:
    def __init__(self, identity: str = "memory") -> None:
        self.identity = identity
        self._tables: dict[str, dict[str, dict[str, Any]]] = {
            table: {} for table in _SAFE_TABLES
        }

    async def create(
        self, table: str, data: dict[str, Any], key: str | None = None
    ) -> dict[str, Any]:
        if table not in _SAFE_TABLES:
            raise ValueError(f"unknown table: {table}")
        record_key = key or uuid.uuid4().hex
        if record_key in self._tables[table]:
            raise ValueError(f"duplicate record: {table}:{record_key}")
        record = copy.deepcopy(_plain(data))
        record["id"] = f"{table}:{record_key}"
        self._tables[table][record_key] = record
        return copy.deepcopy(record)

    async def get(self, ref: RecordRef) -> dict[str, Any] | None:
        row = self._tables[ref.table.value].get(ref.key)
        return copy.deepcopy(row) if row is not None else None

    async def list(self, table: str) -> list[dict[str, Any]]:
        if table not in _SAFE_TABLES:
            raise ValueError(f"unknown table: {table}")
        return [copy.deepcopy(row) for row in self._tables[table].values()]

    async def update(self, ref: RecordRef, patch: dict[str, Any]) -> dict[str, Any]:
        if ref.key not in self._tables[ref.table.value]:
            raise KeyError(str(ref))
        self._tables[ref.table.value][ref.key].update(copy.deepcopy(_plain(patch)))
        return copy.deepcopy(self._tables[ref.table.value][ref.key])

    async def relate(
        self,
        in_ref: RecordRef,
        out_ref: RecordRef,
        data: dict[str, Any],
        key: str | None = None,
    ) -> dict[str, Any]:
        payload = {"in": str(in_ref), "out": str(out_ref), **data}
        return await self.create(RecordTable.COGNITIVE_RELATION.value, payload, key)

    async def vector_search(
        self, vector: list[float], object_types: set[str], limit: int
    ) -> list[RecordRef]:
        if not vector:
            return []
        scores: list[tuple[float, RecordRef]] = []
        for table, object_type in (
            ("experience", "EXPERIENCE"),
            ("memory", "MEMORY"),
            ("evaluation", "EVALUATION"),
        ):
            if object_type not in object_types:
                continue
            for row in await self.list(table):
                if table == "memory" and row.get("status") != MemoryStatus.ACTIVE:
                    continue
                candidate = row.get("embedding")
                if not isinstance(candidate, list) or len(candidate) != len(vector):
                    continue
                norm_a = math.sqrt(sum(float(x) ** 2 for x in vector))
                norm_b = math.sqrt(sum(float(x) ** 2 for x in candidate))
                if norm_a == 0 or norm_b == 0:
                    score = 0.0
                else:
                    score = sum(
                        float(a) * float(b)
                        for a, b in zip(vector, candidate, strict=True)
                    ) / (
                        norm_a * norm_b
                    )
                scores.append((score, _ref(row["id"])))
        scores.sort(key=lambda item: (-item[0], str(item[1])))
        return [ref for _, ref in scores[:limit]]

    async def lexical_search(
        self, query: str, object_types: set[str], limit: int
    ) -> list[RecordRef]:
        query_terms = [token.lower() for token in _TOKEN_RE.findall(query)]
        if not query_terms:
            return []
        docs: list[tuple[RecordRef, list[str]]] = []
        for table, object_type, field in (
            ("experience", "EXPERIENCE", "search_text"),
            ("memory", "MEMORY", "content"),
        ):
            if object_type not in object_types:
                continue
            for row in await self.list(table):
                if table == "memory" and row.get("status") != MemoryStatus.ACTIVE:
                    continue
                tokens = [token.lower() for token in _TOKEN_RE.findall(str(row.get(field, "")))]
                docs.append((_ref(row["id"]), tokens))
        if not docs:
            return []
        average_length = sum(len(tokens) for _, tokens in docs) / len(docs)
        doc_frequency: Counter[str] = Counter()
        for _, tokens in docs:
            doc_frequency.update(set(tokens))
        scored: list[tuple[float, RecordRef]] = []
        k1, b = 1.5, 0.75
        for ref, tokens in docs:
            counts = Counter(tokens)
            score = 0.0
            for term in query_terms:
                df = doc_frequency[term]
                if df == 0:
                    continue
                idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
                tf = counts[term]
                denominator = tf + k1 * (
                    1 - b + b * (len(tokens) / average_length if average_length else 0)
                )
                score += idf * ((tf * (k1 + 1)) / denominator) if denominator else 0.0
            if score > 0:
                scored.append((score, ref))
        scored.sort(key=lambda item: (-item[0], str(item[1])))
        return [ref for _, ref in scored[:limit]]

    async def structured_search(
        self, entity_refs: list[RecordRef], object_types: set[str], limit: int
    ) -> list[RecordRef]:
        targets = {str(ref) for ref in entity_refs}
        if not targets:
            return []
        hits: list[RecordRef] = []
        for table, object_type in (("experience", "EXPERIENCE"), ("memory", "MEMORY")):
            if object_type not in object_types:
                continue
            for row in await self.list(table):
                if table == "memory" and row.get("status") != MemoryStatus.ACTIVE:
                    continue
                refs = set(row.get("entity_refs", []))
                refs.update(row.get("metadata", {}).get("entity_refs", []))
                if refs & targets:
                    hits.append(_ref(row["id"]))
        return hits[:limit]

    async def graph_expand(
        self, seeds: list[RecordRef], object_types: set[str], limit: int, max_depth: int = 2
    ) -> list[RecordRef]:
        if not seeds:
            return []
        relations = await self.list(RecordTable.COGNITIVE_RELATION.value)
        adjacency: dict[str, list[str]] = defaultdict(list)
        for relation in relations:
            left, right = relation.get("in"), relation.get("out")
            if isinstance(left, str) and isinstance(right, str):
                adjacency[left].append(right)
                adjacency[right].append(left)
        allowed = {
            "EXPERIENCE": RecordTable.EXPERIENCE,
            "MEMORY": RecordTable.MEMORY,
            "EVALUATION": RecordTable.EVALUATION,
        }
        allowed_tables = {allowed[item] for item in object_types if item in allowed}
        queue = deque((str(seed), 0) for seed in seeds)
        seen = {str(seed) for seed in seeds}
        hits: list[RecordRef] = []
        while queue and len(hits) < limit:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor in adjacency.get(current, []):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                ref = _ref(neighbor)
                if ref.table in allowed_tables:
                    row = await self.get(ref)
                    if row and not (
                        ref.table is RecordTable.MEMORY
                        and row.get("status") != MemoryStatus.ACTIVE
                    ):
                        hits.append(ref)
                queue.append((neighbor, depth + 1))
        return hits[:limit]

    @asynccontextmanager
    async def atomic(self) -> AsyncIterator[InMemoryBackend]:
        snapshot = copy.deepcopy(self._tables)
        try:
            yield self
        except Exception:
            self._tables = snapshot
            raise


class SurrealBackend:
    def __init__(self, client: SurrealClient) -> None:
        self.client = client

    @staticmethod
    def _table(table: str) -> str:
        if table not in _SAFE_TABLES:
            raise ValueError(f"unknown table: {table}")
        return table

    @staticmethod
    def _record_ref(row: dict[str, Any]) -> RecordRef:
        value = row.get("id")
        if not isinstance(value, str):
            raise ValueError(f"SurrealDB record id is not a string: {value!r}")
        return _ref(value)

    @staticmethod
    def _flatten(results: list[Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, list):
                rows.extend(item for item in result if isinstance(item, dict))
            elif isinstance(result, dict):
                rows.append(result)
        return rows

    async def create(
        self, table: str, data: dict[str, Any], key: str | None = None
    ) -> dict[str, Any]:
        table = self._table(table)
        record_ref = RecordRef(table=RecordTable(table), key=key or uuid.uuid4().hex)
        results = await self.client.query(
            f"CREATE ONLY {record_ref} CONTENT {_surreal_literal(data)} RETURN AFTER;"
        )
        rows = self._flatten(results)
        if not rows:
            raise RuntimeError(f"SurrealDB create returned no row for {record_ref}")
        return rows[-1]

    async def get(self, ref: RecordRef) -> dict[str, Any] | None:
        rows = self._flatten(await self.client.query(f"SELECT * FROM ONLY {ref};"))
        return rows[-1] if rows else None

    async def list(self, table: str) -> list[dict[str, Any]]:
        table = self._table(table)
        return self._flatten(await self.client.query(f"SELECT * FROM {table};"))

    async def update(self, ref: RecordRef, patch: dict[str, Any]) -> dict[str, Any]:
        rows = self._flatten(
            await self.client.query(
                f"UPDATE ONLY {ref} MERGE {_surreal_literal(patch)} RETURN AFTER;"
            )
        )
        if not rows:
            raise KeyError(str(ref))
        return rows[-1]

    async def relate(
        self,
        in_ref: RecordRef,
        out_ref: RecordRef,
        data: dict[str, Any],
        key: str | None = None,
    ) -> dict[str, Any]:
        relation_ref = RecordRef(
            table=RecordTable.COGNITIVE_RELATION, key=key or uuid.uuid4().hex
        )
        rows = self._flatten(
            await self.client.query(
                f"RELATE {in_ref}->{relation_ref}->{out_ref} "
                f"CONTENT {_surreal_literal(data)} RETURN AFTER;"
            )
        )
        if not rows:
            raise RuntimeError("SurrealDB relation create returned no row")
        return rows[-1]

    async def vector_search(
        self, vector: list[float], object_types: set[str], limit: int
    ) -> list[RecordRef]:
        refs: list[RecordRef] = []
        mapping = {"EXPERIENCE": "experience", "MEMORY": "memory"}
        for object_type, table in mapping.items():
            if object_type not in object_types:
                continue
            status_filter = " AND status = 'ACTIVE'" if table == "memory" else ""
            sql = (
                f"SELECT id, vector::distance::knn() AS distance FROM {table} "
                f"WHERE embedding <|{int(limit)},100|> {_surreal_literal(vector)}{status_filter} "
                "ORDER BY distance ASC;"
            )
            rows = self._flatten(await self.client.query(sql))
            refs.extend(self._record_ref(row) for row in rows)
        return refs[:limit]

    async def lexical_search(
        self, query: str, object_types: set[str], limit: int
    ) -> list[RecordRef]:
        refs: list[RecordRef] = []
        mapping = {
            "EXPERIENCE": ("experience", "search_text"),
            "MEMORY": ("memory", "content"),
        }
        for object_type, (table, field) in mapping.items():
            if object_type not in object_types:
                continue
            status_filter = " AND status = 'ACTIVE'" if table == "memory" else ""
            sql = (
                f"SELECT id, search::score(0) AS score FROM {table} "
                f"WHERE {field} @0@ {_surreal_literal(query)}{status_filter} "
                f"ORDER BY score DESC LIMIT {int(limit)};"
            )
            rows = self._flatten(await self.client.query(sql))
            refs.extend(self._record_ref(row) for row in rows)
        return refs[:limit]

    async def structured_search(
        self, entity_refs: list[RecordRef], object_types: set[str], limit: int
    ) -> list[RecordRef]:
        # Entity matching remains deterministic and storage-backed. The first
        # MEM-01 qualification keeps this query simple before adding index-specific tuning.
        targets = {str(ref) for ref in entity_refs}
        hits: list[RecordRef] = []
        for table, object_type in (("experience", "EXPERIENCE"), ("memory", "MEMORY")):
            if object_type not in object_types:
                continue
            for row in await self.list(table):
                if table == "memory" and row.get("status") != MemoryStatus.ACTIVE:
                    continue
                refs = {str(value) for value in row.get("entity_refs", [])}
                refs.update(str(value) for value in row.get("metadata", {}).get("entity_refs", []))
                if refs & targets:
                    hits.append(self._record_ref(row))
        return hits[:limit]

    async def graph_expand(
        self, seeds: list[RecordRef], object_types: set[str], limit: int, max_depth: int = 2
    ) -> list[RecordRef]:
        shadow = InMemoryBackend("surreal-graph-projection")
        for table in ("experience", "memory", "evaluation", "cognitive_relation"):
            for row in await self.list(table):
                record = dict(row)
                ref = self._record_ref(record)
                record.pop("id", None)
                await shadow.create(table, record, ref.key)
        return await shadow.graph_expand(seeds, object_types, limit, max_depth)

    @asynccontextmanager
    async def atomic(self) -> AsyncIterator[BufferedSurrealBackend]:
        buffered = BufferedSurrealBackend(self)
        try:
            yield buffered
        except Exception:
            raise
        else:
            await buffered.commit()


class BufferedSurrealBackend:
    def __init__(self, parent: SurrealBackend) -> None:
        self.parent = parent
        self.statements: list[str] = []
        self._overlay: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    async def create(
        self, table: str, data: dict[str, Any], key: str | None = None
    ) -> dict[str, Any]:
        table = self.parent._table(table)
        ref = RecordRef(table=RecordTable(table), key=key or uuid.uuid4().hex)
        self.statements.append(f"CREATE ONLY {ref} CONTENT {_surreal_literal(data)};")
        row = {"id": str(ref), **_plain(data)}
        self._overlay[table][ref.key] = copy.deepcopy(row)
        return copy.deepcopy(row)

    async def update(self, ref: RecordRef, patch: dict[str, Any]) -> dict[str, Any]:
        current = await self.get(ref)
        if current is None:
            raise KeyError(str(ref))
        self.statements.append(f"UPDATE ONLY {ref} MERGE {_surreal_literal(patch)};")
        current.update(copy.deepcopy(_plain(patch)))
        self._overlay[ref.table.value][ref.key] = current
        return copy.deepcopy(current)

    async def get(self, ref: RecordRef) -> dict[str, Any] | None:
        pending = self._overlay.get(ref.table.value, {}).get(ref.key)
        if pending is not None:
            return copy.deepcopy(pending)
        return await self.parent.get(ref)

    async def list(self, table: str) -> list[dict[str, Any]]:
        table = self.parent._table(table)
        merged = {_ref(row["id"]).key: row for row in await self.parent.list(table)}
        merged.update(copy.deepcopy(self._overlay.get(table, {})))
        return [copy.deepcopy(row) for row in merged.values()]

    async def relate(
        self,
        in_ref: RecordRef,
        out_ref: RecordRef,
        data: dict[str, Any],
        key: str | None = None,
    ) -> dict[str, Any]:
        ref = RecordRef(
            table=RecordTable.COGNITIVE_RELATION, key=key or uuid.uuid4().hex
        )
        self.statements.append(
            f"RELATE {in_ref}->{ref}->{out_ref} CONTENT {_surreal_literal(data)};"
        )
        row = {"id": str(ref), "in": str(in_ref), "out": str(out_ref), **_plain(data)}
        self._overlay[RecordTable.COGNITIVE_RELATION.value][ref.key] = copy.deepcopy(row)
        return copy.deepcopy(row)

    async def commit(self) -> None:
        if not self.statements:
            return
        sql = "BEGIN TRANSACTION;\n" + "\n".join(self.statements) + "\nCOMMIT TRANSACTION;"
        await self.parent.client.query(sql)
