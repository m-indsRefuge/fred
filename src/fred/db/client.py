from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class SurrealError(RuntimeError):
    pass


@dataclass(slots=True)
class SurrealClient:
    url: str
    user: str
    password: str
    namespace: str
    database: str
    timeout: float = 20.0

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "surreal-ns": self.namespace,
            "surreal-db": self.database,
        }

    async def health(self) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.url}/health")
            return response.status_code < 400

    async def query(self, sql: str) -> list[Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/sql",
                headers=self.headers,
                auth=(self.user, self.password),
                content=sql.encode("utf-8"),
            )
        if response.status_code >= 400:
            raise SurrealError(f"SurrealDB HTTP {response.status_code}: {response.text}")
        payload = response.json()
        if not isinstance(payload, list):
            raise SurrealError(f"Unexpected SurrealDB response: {payload!r}")
        results: list[Any] = []
        for item in payload:
            if not isinstance(item, dict):
                raise SurrealError(f"Unexpected SurrealDB statement result: {item!r}")
            if item.get("status") != "OK":
                raise SurrealError(str(item.get("result", item)))
            results.append(item.get("result"))
        return results

