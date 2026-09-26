# Fred MEM-01 Build Contract

**Status:** READY FOR CODEX IMPLEMENTATION BRIEF

## Governing Documents

Implementation is governed by:

1. `MEMORY_COMPLEX_V1_SPEC.md`
2. `FRED_SURREALDB_V1.surql`
3. `PYTHON_CONTRACTS_V1.md`
4. `EXPERIMENTS.md`
5. `FAILURE_MAP.md`

Where wording differs, architectural invariants in `MEMORY_COMPLEX_V1_SPEC.md` take precedence.

## Build Objective

Implement Fred Memory Complex V1 so that Fred can:

```text
accumulate immutable Experiences
derive provisional Memories
validate Memory evidence independently
retrieve prior Experience/Memory through hybrid retrieval
adjudicate contextual relevance
use selected Memory in reasoning
consolidate Memory during idle Sleep bursts
preserve complete research traces
survive model-session restarts
```

## Non-Negotiable Architecture

```text
one SurrealDB cognitive substrate

Experience is immutable

Memory is derived interpretation

episodic / semantic / procedural / relational are views,
not separate databases

hybrid retrieval:
    vector
    BM25
    structured/entity
    graph
    rank fusion

Fred proposes meaning

deterministic Python validates and commits

Fred does not certify his own evidence

Sleep is the only V1 forgetting/consolidation protocol

Sleep operations:
    KEEP
    MERGE
    PROMOTE
    TOMBSTONE
```

## Implementation Deliverables

```text
SurrealDB migration/startup path
repositories
typed contracts
validators
Qwen embedding adapter
Ollama cognitive adapter
Retrieval Engine
Memory Engine
Sleep Engine
Observer
experiment harness
pytest suite
README
```

## Required Acceptance

```text
all deterministic tests pass

EXP-01 continuity accepted
EXP-02 correction accepted
EXP-03 repeated-learning accepted
EXP-04 generalisation accepted

Sleep consolidation integration passes
evidence-poisoning integration passes
concurrent-view integration passes

all required traces/artifacts produced
```

## Architecture Change Rule

If a frozen design choice cannot be implemented safely or correctly:

```text
do not silently substitute another architecture
stop at the boundary
record evidence
propose the smallest amendment
```

## MEM-01 Stop Condition

The milestone stops when the Definition of Done in the main specification is satisfied.

Do not add Temporal Guidance, Digital Cerebellum, full-weight training, distributed services, production UI polish, or unrelated cognitive systems during this build.
