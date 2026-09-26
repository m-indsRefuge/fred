from __future__ import annotations

import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from fred.brain.memory.contracts import EvidenceValidation, MemoryProposal, SleepDecision
from fred.brain.retrieval.contracts import CognitiveSelection

T = TypeVar("T")


class OllamaStructuredError(RuntimeError):
    pass


class OllamaCognitiveModel:
    def __init__(
        self,
        *,
        base_url: str,
        model: str = "qwen3:8b",
        temperature: float = 0.1,
        seed: int | None = 42,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.timeout = timeout
        self.identity = model

    async def _chat(self, system: str, user: str, schema: dict[str, Any] | None = None) -> str:
        options: dict[str, Any] = {"temperature": self.temperature}
        if self.seed is not None:
            options["seed"] = self.seed
        body: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": options,
        }
        if schema is not None:
            body["format"] = schema
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=body)
            response.raise_for_status()
            payload = response.json()
        try:
            return str(payload["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise OllamaStructuredError("Ollama response did not contain message.content") from exc

    async def _structured(self, system: str, payload: dict[str, Any], model: type[T]) -> T:
        if not issubclass(model, BaseModel):
            raise TypeError("structured model must be a Pydantic BaseModel")
        content = await self._chat(
            system,
            json.dumps(payload, default=str),
            model.model_json_schema(),
        )
        try:
            return model.model_validate_json(content)
        except ValidationError as exc:
            raise OllamaStructuredError(f"Invalid structured output: {exc}") from exc

    async def adjudicate_retrieval(
        self, query: str, candidates: list[dict[str, Any]]
    ) -> list[CognitiveSelection]:
        adapter = TypeAdapter(list[CognitiveSelection])
        content = await self._chat(
            "Select only contextually relevant evidence. Return the requested JSON array.",
            json.dumps({"query": query, "candidates": candidates}, default=str),
            adapter.json_schema(),
        )
        try:
            return adapter.validate_json(content)
        except ValidationError as exc:
            raise OllamaStructuredError(f"Invalid retrieval adjudication: {exc}") from exc

    async def propose_memory(self, context: dict[str, Any]) -> MemoryProposal:
        return await self._structured(
            "Propose a typed memory operation from the supplied evidence. Do not invent evidence.",
            context,
            MemoryProposal,
        )

    async def validate_evidence(self, context: dict[str, Any]) -> EvidenceValidation:
        return await self._structured(
            (
                "Independently verify whether the proposed interpretation is supported "
                "by the evidence."
            ),
            context,
            EvidenceValidation,
        )

    async def adjudicate_sleep(self, context: dict[str, Any]) -> SleepDecision:
        return await self._structured(
            "Choose exactly one allowed Memory Sleep operation for this bounded review packet.",
            context,
            SleepDecision,
        )

    async def reason(self, prompt: str, selected_evidence: list[dict[str, Any]]) -> str:
        return await self._chat(
            "Answer using the selected persistent evidence. If evidence is insufficient, say so.",
            json.dumps({"prompt": prompt, "selected_evidence": selected_evidence}, default=str),
        )
