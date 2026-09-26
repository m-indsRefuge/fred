from __future__ import annotations

import httpx


class OllamaEmbeddingError(RuntimeError):
    pass


class OllamaEmbeddingModel:
    def __init__(
        self,
        *,
        base_url: str,
        model: str = "qwen3-embedding:0.6b",
        dimension: int = 1024,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self.timeout = timeout
        self.identity = model

    async def _embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
        embeddings = payload.get("embeddings")
        if (
            not isinstance(embeddings, list)
            or not embeddings
            or not isinstance(embeddings[0], list)
        ):
            raise OllamaEmbeddingError("Ollama returned no embedding vector")
        vector = [float(value) for value in embeddings[0]]
        if len(vector) != self.dimension:
            raise OllamaEmbeddingError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {len(vector)}"
            )
        return vector

    async def embed_query(self, text: str) -> list[float]:
        return await self._embed(text)

    async def embed_document(self, text: str) -> list[float]:
        return await self._embed(text)
