from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from fred.brain.memory.contracts import CognitiveRole, RecordRef, Visibility


class RetrievalStatus(StrEnum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    NO_MATCH = "NO_MATCH"
    ERROR = "ERROR"


class RetrievalQuery(BaseModel):
    query_id: str
    semantic_query: str
    active_experience_ref: RecordRef | None = None
    active_goal_ref: RecordRef | None = None
    state_refs: list[RecordRef] = Field(default_factory=list)
    entity_refs: list[RecordRef] = Field(default_factory=list)
    object_types: set[Literal["EXPERIENCE", "MEMORY", "EVALUATION"]] = Field(
        default_factory=lambda: {"EXPERIENCE", "MEMORY"}
    )
    views: set[Literal["episodic", "semantic", "procedural", "relational"]] = Field(
        default_factory=set
    )
    profile: str = "current_context"
    candidate_budget: int = Field(default=32, ge=1, le=256)


class RetrievalCandidate(BaseModel):
    ref: RecordRef
    object_type: Literal["EXPERIENCE", "MEMORY", "EVALUATION"]
    discovered_by: set[str] = Field(default_factory=set)
    matched_views: set[str] = Field(default_factory=set)
    vector_rank: int | None = None
    lexical_rank: int | None = None
    graph_rank: int | None = None
    structured_rank: int | None = None
    view_ranks: dict[str, int] = Field(default_factory=dict)
    rrf_score: float | None = None
    visibility: Visibility = Visibility.SIGNAL


class CognitiveSelection(BaseModel):
    ref: RecordRef
    role: CognitiveRole
    contextual_relevance: float = Field(ge=0, le=1)
    model_explanation: str


class RetrievalResult(BaseModel):
    query_id: str
    status: RetrievalStatus
    candidates: list[RetrievalCandidate] = Field(default_factory=list)
    selections: list[CognitiveSelection] = Field(default_factory=list)
    channel_errors: dict[str, str] = Field(default_factory=dict)

