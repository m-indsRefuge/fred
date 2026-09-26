# Fred Memory Complex — Typed Python Contracts V1

This document freezes the Python authority boundary for MEM-01.

The code may evolve, but the semantic separation below should remain stable.

## Core rule

Model text is data.

A model may propose a typed object. It may not issue arbitrary database writes,
SurrealQL, Python, shell commands, or graph mutations.

## Suggested package layout

```text
src/fred/brain/memory/
    contracts.py
    repositories.py
    validators.py
    engine.py
    sleep.py

src/fred/brain/retrieval/
    contracts.py
    vector.py
    lexical.py
    graph.py
    structured.py
    fusion.py
    engine.py

src/fred/models/
    base.py
    ollama/
        cognitive.py
        embeddings.py

src/fred/observer/
    events.py
    tui.py
```

## Enums

```python
class MemoryStatus(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    ACTIVE = "ACTIVE"
    TOMBSTONED = "TOMBSTONED"

class MemoryOperation(str, Enum):
    NO_CHANGE = "NO_CHANGE"
    CREATE = "CREATE"
    REINFORCE = "REINFORCE"
    CONTRADICT = "CONTRADICT"
    SUPERSEDE = "SUPERSEDE"
    DERIVE_PROCEDURE = "DERIVE_PROCEDURE"

class SleepOperation(str, Enum):
    KEEP = "KEEP"
    MERGE = "MERGE"
    PROMOTE = "PROMOTE"
    TOMBSTONE = "TOMBSTONE"

class EvidenceVerdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"

class Visibility(str, Enum):
    HIDE = "HIDE"
    SIGNAL = "SIGNAL"
    SUMMARY = "SUMMARY"
    FULL = "FULL"

class CognitiveRole(str, Enum):
    RELEVANT = "RELEVANT"
    SUPPORTING = "SUPPORTING"
    CONTRADICTORY = "CONTRADICTORY"
    CONTEXTUAL = "CONTEXTUAL"
    NOT_RELEVANT = "NOT_RELEVANT"
```

## Retrieval contracts

```python
class RetrievalQuery(BaseModel):
    query_id: str
    semantic_query: str
    active_experience_ref: str | None = None
    active_goal_ref: str | None = None
    state_refs: list[str] = []
    entity_refs: list[str] = []
    object_types: set[Literal["EXPERIENCE", "MEMORY", "EVALUATION"]] = {
        "EXPERIENCE", "MEMORY"
    }
    views: set[Literal["episodic", "semantic", "procedural", "relational"]] = set()
    profile: str = "current_context"
    candidate_budget: int = 32

class RetrievalCandidate(BaseModel):
    ref: str
    object_type: Literal["EXPERIENCE", "MEMORY", "EVALUATION"]
    discovered_by: set[str]
    matched_views: set[str]
    vector_rank: int | None = None
    lexical_rank: int | None = None
    graph_rank: int | None = None
    structured_rank: int | None = None
    view_ranks: dict[str, int] = {}
    rrf_score: float | None = None
    visibility: Visibility

class CognitiveSelection(BaseModel):
    ref: str
    role: CognitiveRole
    contextual_relevance: float = Field(ge=0, le=1)
    model_explanation: str
```

## Memory proposal contract

```python
class MemoryProposal(BaseModel):
    operation: MemoryOperation
    proposed_content: str | None = None
    target_memory_ref: str | None = None

    evidence_refs: list[str]
    counterevidence_refs: list[str] = []

    evidential_support: float = Field(ge=0, le=1)
    interpretive_confidence: float = Field(ge=0, le=1)
    salience_prior: float = Field(ge=0, le=1)

    episodicity: float = Field(ge=0, le=1)
    abstraction: float = Field(ge=0, le=1)
    procedurality: float = Field(ge=0, le=1)
    relationality: float = Field(ge=0, le=1)

    applicability: list[str] = []
    conditions: list[str] = []

    model_explanation: str
```

`evidential_support` supplied by Fred is a proposal field only. The validator computes
the accepted evidential status independently.

## Evidence validation

```python
class EvidenceValidation(BaseModel):
    proposal_ref: str
    verdict: EvidenceVerdict
    supported_refs: list[str] = []
    unsupported_refs: list[str] = []
    contradictory_refs: list[str] = []
    verifier: str
    explanation: str
```

The proposer and verifier must be different inference calls.

## Sleep contract

```python
class SleepDecision(BaseModel):
    operation: SleepOperation
    source_memory_refs: list[str]
    proposed_memory: MemoryProposal | None = None
    evidence_refs: list[str]
    model_explanation: str
```

## Repository rules

```text
ExperienceRepository
    create
    get
    search
    NO semantic update
    NO delete

MemoryRepository
    create_provisional
    activate
    reinforce
    supersede
    tombstone
    operations only through validator

EntityRepository
    resolve
    get
    create_if_absent

EvaluationRepository
    create
    get_for_target

StateRepository
    get
    set
    clear

RelationRepository
    create_validated
    traverse
    find

TraceRepository
    append
    query
```

## Model interfaces

```python
class CognitiveModel(Protocol):
    async def adjudicate_retrieval(...) -> list[CognitiveSelection]: ...
    async def propose_memory(...) -> MemoryProposal: ...
    async def validate_evidence(...) -> EvidenceValidation: ...
    async def adjudicate_sleep(...) -> SleepDecision: ...
    async def reason(...) -> str: ...

class EmbeddingModel(Protocol):
    async def embed_query(self, text: str) -> list[float]: ...
    async def embed_document(self, text: str) -> list[float]: ...
```

The initial embedding implementation uses `qwen3-embedding:0.6b` through Ollama
and must return exactly 1024 floats.

## Retrieval engine

The retrieval engine owns deterministic orchestration:

```text
1. embed query
2. start requested retrieval channels concurrently
3. run requested memory-view projections concurrently
4. collect ranked results
5. deduplicate by record id
6. fuse ranks with RRF
7. bounded graph expansion
8. assign visibility
9. emit Retrieval Trace
10. pass bounded candidates to Fred for semantic adjudication
```

Fred does not control steps 1–9.

## Evidence validator

Validation order:

```text
schema
  ↓
record existence
  ↓
authority/provenance
  ↓
relation legality
  ↓
cycle checks
  ↓
semantic evidence validation
  ↓
COMMIT / REJECT / REMAIN PROVISIONAL
```

The model cannot bypass this sequence.

## Sleep engine

```text
IDLE trigger
  ↓
mechanical inspection
  ↓
candidate grouping
  ↓
bounded review packet
  ↓
Fred typed decision
  ↓
validator
  ↓
atomic commit
  ↓
trace
```

The Sleep engine may be interrupted before commit. A commit itself must be atomic.

## Non-negotiable test invariants

1. No code path can update a committed Experience through `ExperienceRepository`.
2. A Memory cannot become ACTIVE without provenance.
3. A Memory cannot become ACTIVE after an UNSUPPORTED evidence verdict.
4. Tombstoned Memories are excluded from normal retrieval.
5. Concurrent views return one object per record id, with per-view ranks preserved.
6. A missing retrieval result becomes NO_MATCH, never fabricated evidence.
7. Relation endpoint rules are enforced.
8. Provenance cycles are rejected.
9. Model output that fails schema parsing never reaches persistence.
10. Sleep cannot mutate Experience.
