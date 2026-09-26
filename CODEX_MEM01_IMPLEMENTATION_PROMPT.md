# CODEX IMPLEMENTATION PROMPT — FRED MEM-01

You are responsible for implementing **Fred Memory Complex V1 / MEM-01** end to end in the existing repository:

```text
C:\Users\nolan\AIProjects\fred
```

This is an implementation task, not a design exercise.

Do not stop after inspecting, planning, scaffolding, or describing what should be built. Build the working system, run the deterministic test suite, run the live behavioural acceptance experiments when the configured local models are available, fix defects you discover, and leave the repository in a reproducible state.

Do not ask the Operator to make routine implementation decisions. Make defensible local engineering decisions yourself. Do not silently change a frozen architectural decision.

## 1. Governing documents

Before changing code, read these files completely and treat them as the implementation contract:

```text
docs/MEMORY_COMPLEX_V1_SPEC.md
docs/MEM01_BUILD_CONTRACT.md
docs/PYTHON_CONTRACTS_V1.md
docs/EXPERIMENTS.md
docs/FAILURE_MAP.md
db/FRED_SURREALDB_V1.surql
```

Priority if wording conflicts:

```text
1. docs/MEMORY_COMPLEX_V1_SPEC.md
2. docs/MEM01_BUILD_CONTRACT.md
3. docs/PYTHON_CONTRACTS_V1.md
4. docs/EXPERIMENTS.md
5. docs/FAILURE_MAP.md
6. db/FRED_SURREALDB_V1.surql
```

The `.surql` file is a schema draft governed by the specification. If current SurrealDB syntax requires a mechanical correction, make the smallest correction necessary, add a regression test or migration check, and document it. Do not use a syntax issue as permission to redesign the data model.

## 2. First actions

Inspect the repository before writing anything:

```text
git status
git branch --show-current
git log -5 --oneline
tree / file inventory
pyproject.toml
existing source
existing tests
existing docs
```

Preserve unrelated user changes.

If the working tree is clean, create a focused implementation branch such as:

```text
codex/mem01-memory-complex
```

Do not push.

Determine the actual available runtime:

```text
Python
Docker / SurrealDB
Ollama
installed Ollama models
pytest
ruff
```

The intended local defaults are:

```text
Python: 3.12
temporary cognitive model: qwen3:8b via Ollama
embedding model: qwen3-embedding:0.6b via Ollama
embedding dimension: 1024
persistence: SurrealDB 3.3.x
```

Do not silently substitute a different embedding model, vector dimension, database, or persistence architecture.

If a required local model is absent, you may pull it if normal network/model installation is available. If it cannot be obtained, implement and test the adapter with deterministic fakes, mark live acceptance BLOCKED for that exact environmental reason, and provide the exact command needed to unblock it. Do not fake a live pass.

## 3. Architecture that must remain intact

The build must preserve all of the following:

```text
one SurrealDB cognitive substrate

Experience is immutable historical evidence

Memory is derived interpretation

episodic / semantic / procedural / relational are views over the same substrate,
not physically separate memory stores

State is direct exact state, not reconstructed through semantic retrieval

retrieval is hybrid:
    vector
    BM25/full text
    structured/entity
    graph
    rank fusion

Fred performs semantic adjudication

Python/database code owns authority and commits

Fred may propose a Memory but cannot certify its own evidence

proposer and evidence verifier are separate inference calls

normal model output cannot execute SurrealQL, Python, shell, or arbitrary writes

foreground-created Memories are PROVISIONAL

Memory Sleep is the single V1 consolidation/forgetting mechanism

Sleep operations are exactly:
    KEEP
    MERGE
    PROMOTE
    TOMBSTONE

Sleep acts on Memories, never Experiences

normal retrieval excludes TOMBSTONED Memory

Observer/instrumentation is read-only with respect to cognitive state
```

If implementation evidence shows that one of these is technically impossible or materially incorrect, stop at that boundary, preserve completed work, document the evidence, and propose the smallest required amendment. Do not silently replace the architecture.

## 4. Keep the implementation physically simple

This is a research build with architectural completeness, but it should not become a distributed system.

Use one Python process for the Fred runtime and one local SurrealDB service.

Do not add:

```text
Redis
Kafka
RabbitMQ
Qdrant
Chroma
Neo4j
Elasticsearch
LangGraph
Celery
separate microservices
```

unless a governing contract explicitly requires them. It currently does not.

Internal communication should use typed Python objects, object references, direct calls, shared state, and selective asynchronous tasks.

Natural language belongs at model/human boundaries, not as the Brain's internal protocol.

## 5. Recommended source structure

Respect existing repository conventions if they already define a better equivalent. Otherwise converge toward:

```text
src/fred/
    __init__.py
    config.py
    cli.py

    db/
        __init__.py
        client.py
        migrate.py
        health.py

    brain/
        memory/
            __init__.py
            contracts.py
            repositories.py
            validators.py
            evidence.py
            engine.py
            sleep.py

        retrieval/
            __init__.py
            contracts.py
            vector.py
            lexical.py
            structured.py
            graph.py
            fusion.py
            visibility.py
            engine.py

        state/
            __init__.py
            repository.py

        runtime/
            __init__.py
            journal.py
            experience.py
            scheduler.py

    models/
        __init__.py
        base.py
        ollama/
            __init__.py
            cognitive.py
            embeddings.py
            structured.py

    observer/
        __init__.py
        events.py
        queries.py
        tui.py

    experiments/
        __init__.py
        memory_v1/
            __init__.py
            runner.py
            continuity.py
            correction.py
            repeated_learning.py
            generalisation.py
```

Tests should mirror the functional boundaries rather than one giant test file.

## 6. Configuration

Use explicit configuration rather than hard-coded local assumptions.

Support environment/config values equivalent to:

```text
FRED_SURREAL_URL
FRED_SURREAL_USER
FRED_SURREAL_PASS
FRED_SURREAL_NAMESPACE
FRED_SURREAL_DATABASE

FRED_COGNITIVE_MODEL=qwen3:8b
FRED_EMBEDDING_MODEL=qwen3-embedding:0.6b
FRED_EMBEDDING_DIM=1024

FRED_OLLAMA_URL
```

Provide safe local defaults where appropriate, but never commit secrets.

Add `.env.example` if useful.

## 7. SurrealDB

Implement a reproducible local startup path.

Docker Compose is preferred if it is the cleanest valid approach for the installed environment; otherwise provide an equally reproducible local SurrealDB command.

Pin the exact working SurrealDB version in the repository once qualified.

Implement:

```text
database health check
migration/schema application
idempotent setup
clean test database creation
isolated experiment database creation
```

Apply and validate the schema against a real empty database.

Do not merely assume the draft SurrealQL parses.

The core physical tables remain:

```text
experience
memory
entity
evaluation
state
journal_event
cognitive_relation
trace_event
```

Do not introduce four physical memory tables.

### Experience immutability

The application authority surface for committed Experience must expose create/read/search, not semantic update/delete.

Add direct tests proving normal repository APIs cannot mutate a committed Experience.

Use the strongest practical database constraint compatible with the qualified SurrealDB version in addition to the application boundary where possible.

## 8. Typed contracts

Implement the contracts in `docs/PYTHON_CONTRACTS_V1.md` using Pydantic v2 or the repository's established equivalent.

Avoid mutable default values.

All model-facing outputs must parse into typed schemas before they can influence persistent state.

A parsing failure must never fall through into a best-effort database write.

Implement explicit enums for:

```text
MemoryStatus
MemoryOperation
SleepOperation
EvidenceVerdict
Visibility
CognitiveRole
relation kinds
trace types
```

Use explicit typed refs or a small validated reference wrapper rather than arbitrary unvalidated strings through the core Memory Engine.

## 9. Ollama adapters

Implement two separate abstractions:

```text
CognitiveModel
EmbeddingModel
```

The temporary cognitive model defaults to:

```text
qwen3:8b
```

The embedding baseline defaults to:

```text
qwen3-embedding:0.6b
1024 dimensions
```

Validate embedding length before persistence/query.

Store embedding model identity/version with each embedded object.

Do not mix vectors from different model/version spaces silently.

### Structured cognition

Implement separate structured inference calls for at least:

```text
adjudicate_retrieval
propose_memory
validate_evidence
adjudicate_sleep
reason
```

The proposal-generating call and evidence-validation call must be logically separate. Even if MEM-01 uses the same underlying Qwen model, it must not simply copy the proposer's confidence into the validator result.

Use constrained/structured JSON generation where Ollama supports it. Parse and validate every result.

## 10. Journal and Experience lifecycle

Implement:

```text
append-only journal event recording
Active Experience working state
deterministic Experience boundary
atomic Experience commit
explicit incomplete/aborted Experience
```

A committed Experience is the permanent record of what happened.

Do not write later interpretations back into Experience.

Construct a deterministic `search_text` projection for Experience embedding/BM25 indexing. Make this function testable.

## 11. Memory formation

After Experience commit, construct a bounded Memory Formation context.

Fred may return:

```text
NO_CHANGE
CREATE
REINFORCE
CONTRADICT
SUPERSEDE
DERIVE_PROCEDURE
```

A created Memory begins as:

```text
PROVISIONAL
```

Before activation:

```text
schema validation
record existence
authority/provenance checks
relation legality
cycle detection
semantic evidence validation
```

must occur.

If evidence is:

```text
UNSUPPORTED
CONTRADICTED
```

the Memory cannot become ACTIVE.

Do not silently delete rejected/provisional proposals; preserve research traces.

## 12. Hybrid retrieval engine

Implement actual multi-channel retrieval over the unified substrate.

At minimum:

```text
HNSW vector retrieval
BM25 lexical retrieval
structured/entity retrieval
bounded graph expansion
```

Use concurrent execution where appropriate.

Fuse independent rankings using Reciprocal Rank Fusion rather than raw addition of incomparable score scales.

Deduplicate by database record identity.

Preserve:

```text
which channels found the candidate
per-channel rank
per-view rank
matched views
fused rank/score
```

Do not reduce the trace to one opaque score.

### Concurrent memory views

Support any combination of:

```text
episodic
semantic
procedural
relational
```

in one Retrieval Query.

These are projections over the same records.

Run requested projections concurrently where useful.

One record matching three views must enter the candidate set once with all three matches preserved.

### Retrieval outcome

Support:

```text
READY
PARTIAL
NO_MATCH
ERROR
```

NO_MATCH is valid evidence. Never invent Memory because retrieval is empty.

## 13. Visibility and model adjudication

Implement:

```text
HIDE
SIGNAL
SUMMARY
FULL
```

as query-time representations, not stored degraded copies.

The machine Retrieval Engine determines candidates and bounded representations.

Fred then semantically adjudicates the candidate set.

Only selected relevant evidence enters the main reasoning context.

Record both:

```text
machine ranking
Fred selection
```

so retrieval failure and relevance failure remain distinguishable.

Keep this V1 implementation simple. Visibility policy may be rule-based/configurable initially; do not create an unnecessary learned visibility subsystem.

## 14. Memory Sleep

Implement the exact V1 cycle:

```text
IDLE
  ↓
INSPECT
  ↓
GROUP
  ↓
FRED ADJUDICATES
  ↓
KEEP / MERGE / PROMOTE / TOMBSTONE
  ↓
VALIDATE
  ↓
ATOMIC COMMIT
```

Sleep is opportunistic and interruptible before commit.

A transaction commit itself must remain atomic.

Candidate inspection/grouping should use deterministic mechanisms first:

```text
schema/provenance problems
vector near-duplicates
shared entities
shared evidence
graph neighbourhood
contradiction candidates
```

Fred does not choose what is allowed into the Sleep workspace.

Fred chooses semantic consolidation for the bounded review packet.

Do not implement age-based decay, archive tiers, destructive Experience pruning, or a second subconscious database.

## 15. Evidence integrity

Implement the three-layer distinction:

```text
EVIDENCE
INTERPRETATION
ACTION / REASONING
```

Operator statements, Experience, tool outputs, and external evidence retain provenance/authority.

Memory is interpretation.

A model-generated interpretation must not be stored as if it were Operator evidence.

Track separately:

```text
evidential_support
interpretive_confidence
```

The proposer may suggest both, but the accepted evidence verdict comes from the independent validation path.

## 16. Graph rules

Standard direction is:

```text
subject -> relation -> object
```

Therefore:

```text
Memory M7 -> DERIVED_FROM -> Experience E12
Experience E12 -> RESULTED_IN -> Evaluation EV4
```

Implement and test legal endpoint combinations.

Reject illegal relations and provenance cycles.

Do not silently invent new relation kinds beyond the frozen vocabulary.

## 17. Observer and traces

Implement a simple read-only terminal Observer.

It does not need production visual polish.

It must make it possible to inspect:

```text
latest turn
active State
Experience
retrieval channels
fused candidates
visibility
Fred selections
Memory proposal
evidence validation
committed mutations
Sleep cycle
provenance tree
failure label
```

A Textual interface is acceptable if useful; a robust CLI/read-only terminal view is also acceptable.

Do not let Observer implementation delay correctness.

Every significant event must also be available as machine-readable `trace_event` data.

Experiment runs must produce where practical:

```text
run.json
trace.jsonl
metrics.json
result.json
```

## 18. Deterministic tests

Build a substantial pytest suite using fakes/stubs so core correctness does not depend on Qwen behaving consistently.

Required areas include:

```text
schema application

Experience immutability

journal -> Experience commit

Memory proposal parsing

provenance resolution

provenance-cycle rejection

relation endpoint validation

evidence verdict gating

tombstoned retrieval exclusion

HNSW retrieval

BM25 retrieval

structured retrieval

bounded graph expansion

RRF fusion

candidate deduplication

concurrent memory views

NO_MATCH

Sleep KEEP
Sleep MERGE
Sleep PROMOTE
Sleep TOMBSTONE

Sleep cannot mutate Experience

Sleep transaction rollback / interruption behaviour

Observer read-only invariant

cross-run database isolation

context-reset harness enforcement
```

Also implement the deterministic integration scenarios in `docs/EXPERIMENTS.md`:

```text
INT-01 Sleep consolidation
INT-02 Evidence poisoning
INT-03 Concurrent views
```

Do not weaken tests merely to make implementation pass.

## 19. Behavioural experiments

Implement the four frozen experiments exactly enough that their acceptance conditions remain meaningful:

```text
EXP-01 Continuity
EXP-02 Correction and Supersession
EXP-03 Repeated Experience Learning
EXP-04 Abstraction and Generalisation
```

The harness must enforce model-context reset where specified.

The hidden rules for EXP-03 and EXP-04 must never appear in:

```text
Fred prompt
State
Memory
external context
```

except as consequences Fred legitimately derives from Experience.

Run five isolated runs per experiment for final acceptance if the required local models and service are available.

Do not count a correct final answer as a Memory success unless the trace shows the intended persistent Memory/Experience path.

Produce an experiment summary containing:

```text
per-run result
aggregate pass count
retrieval path
selected evidence
Memory/Sleep changes
failure classification
```

## 20. Failure-aware engineering

Use `docs/FAILURE_MAP.md` during implementation.

When a failure occurs, classify it at the actual failing stage where evidence permits:

```text
RETRIEVAL_MISS
RETRIEVAL_NOISE
VISIBILITY_ERROR
RELEVANCE_REJECTION
MISINTERPRETATION
REASONING_ERROR
BAD_MEMORY_PROPOSAL
INVALID_MEMORY_PROPOSAL
DUPLICATE_MEMORY
BAD_CONSOLIDATION
BAD_TOMBSTONE
STATE_ERROR
RUNTIME_ERROR
UNKNOWN
```

Do not describe every wrong model answer as a Memory failure.

Add newly discovered concrete failure modes to `docs/FAILURE_MAP.md` only when implementation/testing demonstrates they are real.

## 21. Developer ergonomics

Provide straightforward commands for:

```text
start SurrealDB
apply migration
check service/model health
run unit/integration tests
run one experiment
run all MEM-01 experiments
launch Observer
reset an experiment database
```

A fresh checkout should not require manual database editing.

Update README with Windows/PowerShell instructions appropriate to this repository.

Prefer commands compatible with the Operator's environment:

```text
Windows 11
PowerShell
Python 3.12
Docker Desktop
Ollama
```

## 22. Quality requirements

Use the repository's Ruff/typing/test conventions.

Keep functions and modules focused.

Do not use bare `except`.

Do not use mutable defaults.

Do not bury DB queries throughout the codebase; route persistence through repository/query modules.

Do not put model-provider response objects into core cognitive contracts.

Do not duplicate authoritative state across multiple stores.

Add comments for invariants and non-obvious research decisions, not narration of obvious Python.

## 23. Execution order

Use this order unless existing repository evidence justifies a small change:

```text
A. qualify environment
B. make schema apply cleanly
C. implement contracts/repositories/validators
D. implement deterministic Experience lifecycle
E. implement embedding + retrieval channels
F. implement fusion/views/trace
G. implement cognitive-model structured calls
H. implement Memory formation + independent evidence validation
I. implement Sleep
J. implement Observer
K. implement experiment harness
L. run deterministic suite
M. run live behavioural acceptance
N. fix failures
O. rerun acceptance
P. update docs / final report
```

Do not begin by building the TUI.

## 24. Final verification

Before declaring MEM-01 complete, run at minimum:

```text
python compilation/import check
ruff
pytest
SurrealDB schema apply against a clean DB
database health check
Ollama health/model check
deterministic integrations
all available behavioural experiments
git diff / git status
```

If a live acceptance run cannot execute because an external/local prerequisite is unavailable, state exactly which prerequisite prevented it and provide evidence. All non-blocked work must still be complete.

## 25. Final response to the Operator

Report:

```text
branch
HEAD or working-tree state

what was built

key architectural choices actually implemented

files added/changed

SurrealDB version qualified

cognitive model used
embedding model used

test commands
test counts

EXP-01 result
EXP-02 result
EXP-03 result
EXP-04 result

Sleep integration result
evidence-poisoning result
concurrent-view result

known failures / deviations

exact launch commands:
    services
    Fred / experiment runner
    Observer
```

Do not report a milestone as PASS unless the evidence satisfies the frozen acceptance contract.

Begin by reading the governing documents and inspecting the repository. Then implement MEM-01 to completion.
