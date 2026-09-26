from __future__ import annotations

from fred.brain.memory.repositories import Repositories
from fred.brain.runtime import FredRuntime
from fred.config import FredConfig
from fred.db import SurrealBackend, SurrealClient
from fred.models.ollama.cognitive import OllamaCognitiveModel
from fred.models.ollama.embeddings import OllamaEmbeddingModel
from fred.observer import MemoryObserver


def surreal_client(config: FredConfig) -> SurrealClient:
    return SurrealClient(
        config.surreal_url,
        config.surreal_user,
        config.surreal_pass,
        config.surreal_namespace,
        config.surreal_database,
    )


def build_runtime(
    config: FredConfig,
) -> tuple[FredRuntime, MemoryObserver, Repositories]:
    backend = SurrealBackend(surreal_client(config))
    repositories = Repositories.create(backend)
    embedding = OllamaEmbeddingModel(
        base_url=config.ollama_url,
        model=config.embedding_model,
        dimension=config.embedding_dim,
    )
    cognitive = OllamaCognitiveModel(
        base_url=config.ollama_url,
        model=config.cognitive_model,
    )
    runtime = FredRuntime(repositories, embedding, cognitive)
    return runtime, MemoryObserver(repositories), repositories


def rebuild_cognitive_runtime(
    config: FredConfig,
    repositories: Repositories,
) -> FredRuntime:
    embedding = OllamaEmbeddingModel(
        base_url=config.ollama_url,
        model=config.embedding_model,
        dimension=config.embedding_dim,
    )
    cognitive = OllamaCognitiveModel(
        base_url=config.ollama_url,
        model=config.cognitive_model,
    )
    return FredRuntime(repositories, embedding, cognitive)
