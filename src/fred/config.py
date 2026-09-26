from __future__ import annotations

import os
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class FredConfig:
    surreal_url: str = "http://127.0.0.1:8000"
    surreal_user: str = "root"
    surreal_pass: str = "root"
    surreal_namespace: str = "fred"
    surreal_database: str = "fred_mem01"
    cognitive_model: str = "qwen3:8b"
    embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dim: int = 1024
    ollama_url: str = "http://127.0.0.1:11434"

    @classmethod
    def from_env(cls) -> FredConfig:
        default = cls()
        return cls(
            surreal_url=os.getenv("FRED_SURREAL_URL", default.surreal_url).rstrip("/"),
            surreal_user=os.getenv("FRED_SURREAL_USER", default.surreal_user),
            surreal_pass=os.getenv("FRED_SURREAL_PASS", default.surreal_pass),
            surreal_namespace=os.getenv("FRED_SURREAL_NAMESPACE", default.surreal_namespace),
            surreal_database=os.getenv("FRED_SURREAL_DATABASE", default.surreal_database),
            cognitive_model=os.getenv("FRED_COGNITIVE_MODEL", default.cognitive_model),
            embedding_model=os.getenv("FRED_EMBEDDING_MODEL", default.embedding_model),
            embedding_dim=int(os.getenv("FRED_EMBEDDING_DIM", str(default.embedding_dim))),
            ollama_url=os.getenv("FRED_OLLAMA_URL", default.ollama_url).rstrip("/"),
        )

    def for_database(self, database: str) -> FredConfig:
        return replace(self, surreal_database=database)
