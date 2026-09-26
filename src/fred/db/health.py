from __future__ import annotations

from dataclasses import asdict

import httpx

from fred.config import FredConfig
from fred.db.client import SurrealClient


async def health_report(config: FredConfig) -> dict[str, object]:
    client = SurrealClient(
        config.surreal_url,
        config.surreal_user,
        config.surreal_pass,
        config.surreal_namespace,
        config.surreal_database,
    )
    surreal_ok = False
    surreal_error: str | None = None
    try:
        surreal_ok = await client.health()
    except Exception as exc:
        surreal_error = str(exc)

    ollama_ok = False
    models: list[str] = []
    ollama_error: str | None = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            response = await http.get(f"{config.ollama_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
            models = [item["name"] for item in payload.get("models", []) if "name" in item]
            ollama_ok = True
    except Exception as exc:
        ollama_error = str(exc)

    return {
        "config": {
            key: value for key, value in asdict(config).items() if key != "surreal_pass"
        },
        "surreal": {"ok": surreal_ok, "error": surreal_error},
        "ollama": {
            "ok": ollama_ok,
            "models": models,
            "cognitive_model_present": config.cognitive_model in models,
            "embedding_model_present": config.embedding_model in models,
            "error": ollama_error,
        },
    }
