from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


class RecordTable(StrEnum):
    EXPERIENCE = "experience"
    MEMORY = "memory"
    ENTITY = "entity"
    EVALUATION = "evaluation"
    STATE = "state"
    JOURNAL_EVENT = "journal_event"
    COGNITIVE_RELATION = "cognitive_relation"
    TRACE_EVENT = "trace_event"


class RecordRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    table: RecordTable
    key: str = Field(min_length=1)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not _ID_RE.fullmatch(value):
            raise ValueError("record key may contain only letters, digits, '_' and '-'")
        return value

    @model_validator(mode="before")
    @classmethod
    def parse_string(cls, value: Any) -> Any:
        if isinstance(value, str):
            table, separator, key = value.partition(":")
            if not separator:
                raise ValueError("record reference must have table:key form")
            return {"table": table, "key": key}
        return value

    def __str__(self) -> str:
        return f"{self.table.value}:{self.key}"


class MemoryStatus(StrEnum):
    PROVISIONAL = "PROVISIONAL"
    ACTIVE = "ACTIVE"
    TOMBSTONED = "TOMBSTONED"


class MemoryOperation(StrEnum):
    NO_CHANGE = "NO_CHANGE"
    CREATE = "CREATE"
    REINFORCE = "REINFORCE"
    CONTRADICT = "CONTRADICT"
    SUPERSEDE = "SUPERSEDE"
    DERIVE_PROCEDURE = "DERIVE_PROCEDURE"


class SleepOperation(StrEnum):
    KEEP = "KEEP"
    MERGE = "MERGE"
    PROMOTE = "PROMOTE"
    TOMBSTONE = "TOMBSTONE"


class EvidenceVerdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class Visibility(StrEnum):
    HIDE = "HIDE"
    SIGNAL = "SIGNAL"
    SUMMARY = "SUMMARY"
    FULL = "FULL"


class CognitiveRole(StrEnum):
    RELEVANT = "RELEVANT"
    SUPPORTING = "SUPPORTING"
    CONTRADICTORY = "CONTRADICTORY"
    CONTEXTUAL = "CONTEXTUAL"
    NOT_RELEVANT = "NOT_RELEVANT"


class RelationKind(StrEnum):
    DERIVED_FROM = "DERIVED_FROM"
    PART_OF = "PART_OF"
    ABOUT = "ABOUT"
    CAUSED_BY = "CAUSED_BY"
    RESULTED_IN = "RESULTED_IN"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    REINFORCES = "REINFORCES"
    SIMILAR_TO = "SIMILAR_TO"
    RECALLED_WITH = "RECALLED_WITH"


class TraceType(StrEnum):
    RETRIEVAL = "RETRIEVAL"
    COGNITIVE_SELECTION = "COGNITIVE_SELECTION"
    MEMORY_PROPOSAL = "MEMORY_PROPOSAL"
    MEMORY_VALIDATION = "MEMORY_VALIDATION"
    SLEEP = "SLEEP"
    MODEL_CALL = "MODEL_CALL"
    EXPERIMENT_CHECKPOINT = "EXPERIMENT_CHECKPOINT"
    ERROR = "ERROR"


class FailureLabel(StrEnum):
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RETRIEVAL_NOISE = "RETRIEVAL_NOISE"
    VISIBILITY_ERROR = "VISIBILITY_ERROR"
    RELEVANCE_REJECTION = "RELEVANCE_REJECTION"
    MISINTERPRETATION = "MISINTERPRETATION"
    REASONING_ERROR = "REASONING_ERROR"
    BAD_MEMORY_PROPOSAL = "BAD_MEMORY_PROPOSAL"
    INVALID_MEMORY_PROPOSAL = "INVALID_MEMORY_PROPOSAL"
    DUPLICATE_MEMORY = "DUPLICATE_MEMORY"
    BAD_CONSOLIDATION = "BAD_CONSOLIDATION"
    BAD_TOMBSTONE = "BAD_TOMBSTONE"
    STATE_ERROR = "STATE_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    UNKNOWN = "UNKNOWN"


class MemoryProposal(BaseModel):
    operation: MemoryOperation
    proposed_content: str | None = None
    target_memory_ref: RecordRef | None = None
    evidence_refs: list[RecordRef]
    counterevidence_refs: list[RecordRef] = Field(default_factory=list)
    evidential_support: float = Field(ge=0, le=1)
    interpretive_confidence: float = Field(ge=0, le=1)
    salience_prior: float = Field(ge=0, le=1)
    episodicity: float = Field(ge=0, le=1)
    abstraction: float = Field(ge=0, le=1)
    procedurality: float = Field(ge=0, le=1)
    relationality: float = Field(ge=0, le=1)
    applicability: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    model_explanation: str

    @model_validator(mode="after")
    def content_required_for_mutation(self) -> MemoryProposal:
        content_ops = {
            MemoryOperation.CREATE,
            MemoryOperation.DERIVE_PROCEDURE,
            MemoryOperation.SUPERSEDE,
            MemoryOperation.CONTRADICT,
            MemoryOperation.REINFORCE,
        }
        target_ops = {
            MemoryOperation.REINFORCE,
            MemoryOperation.CONTRADICT,
            MemoryOperation.SUPERSEDE,
        }
        if self.operation in content_ops and not self.proposed_content:
            raise ValueError(f"{self.operation} requires proposed_content")
        if self.operation in target_ops and self.target_memory_ref is None:
            raise ValueError(f"{self.operation} requires target_memory_ref")
        return self


class EvidenceValidation(BaseModel):
    proposal_ref: RecordRef
    verdict: EvidenceVerdict
    supported_refs: list[RecordRef] = Field(default_factory=list)
    unsupported_refs: list[RecordRef] = Field(default_factory=list)
    contradictory_refs: list[RecordRef] = Field(default_factory=list)
    verifier: str
    explanation: str


class SleepDecision(BaseModel):
    operation: SleepOperation
    source_memory_refs: list[RecordRef]
    proposed_memory: MemoryProposal | None = None
    evidence_refs: list[RecordRef]
    model_explanation: str


class ExperienceRecord(BaseModel):
    ref: RecordRef
    sequence_start: int
    sequence_end: int
    session_id: str
    turn_id: str | None = None
    input: dict[str, Any]
    context: dict[str, Any]
    perception: dict[str, Any]
    decision: dict[str, Any]
    action: dict[str, Any]
    outcome: dict[str, Any]
    feedback: dict[str, Any] | None = None
    search_text: str
    entity_refs: list[RecordRef] = Field(default_factory=list)
    started_at: datetime
    ended_at: datetime
    observed_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float]
    embedding_model: str
    embedding_version: str
    provenance: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_experience(self) -> ExperienceRecord:
        if self.sequence_end < self.sequence_start:
            raise ValueError("sequence_end must be >= sequence_start")
        if self.ref.table is not RecordTable.EXPERIENCE:
            raise ValueError("ExperienceRecord ref must use experience table")
        return self


class MemoryRecord(BaseModel):
    ref: RecordRef
    content: str
    status: MemoryStatus = MemoryStatus.PROVISIONAL
    episodicity: float = Field(ge=0, le=1)
    abstraction: float = Field(ge=0, le=1)
    procedurality: float = Field(ge=0, le=1)
    relationality: float = Field(ge=0, le=1)
    evidential_support: float = Field(ge=0, le=1)
    interpretive_confidence: float = Field(ge=0, le=1)
    salience_prior: float = Field(ge=0, le=1)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    embedding: list[float]
    embedding_model: str
    embedding_version: str
    provenance: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_memory(self) -> MemoryRecord:
        if self.ref.table is not RecordTable.MEMORY:
            raise ValueError("MemoryRecord ref must use memory table")
        return self


class EntityRecord(BaseModel):
    ref: RecordRef
    kind: str
    canonical_key: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationRecord(BaseModel):
    ref: RecordRef
    target_ref: RecordRef
    kind: Literal[
        "SUCCESS",
        "FAILURE",
        "CORRECTION",
        "UNEXPECTED",
        "USEFUL",
        "NOT_USEFUL",
        "PARTIAL",
    ]
    value: float | None = None
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence_refs: list[RecordRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CognitiveRelation(BaseModel):
    ref: RecordRef
    in_ref: RecordRef
    out_ref: RecordRef
    kind: RelationKind
    confidence: float = Field(ge=0, le=1)
    strength: float = Field(ge=0, le=1)
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provenance: list[RecordRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceEvent(BaseModel):
    ref: RecordRef
    trace_type: TraceType
    session_id: str
    turn_id: str | None = None
    experience_ref: RecordRef | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]


class JournalEvent(BaseModel):
    ref: RecordRef
    sequence: int
    event_type: str
    session_id: str
    turn_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any]


class StateRecord(BaseModel):
    ref: RecordRef
    key: str
    value: dict[str, Any]
    authority: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
