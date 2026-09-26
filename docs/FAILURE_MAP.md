# Fred MEM-01 Failure Map

**Status:** FROZEN FOR IMPLEMENTATION
**Milestone:** MEM-01

The purpose of this document is to make predictable failure states explicit before implementation.

| ID | Failure | Detection | Containment / Required Behaviour |
|---|---|---|---|
| FM-01 | Committed Experience is mutated | repository/integration test; hash mismatch | reject operation; record error trace |
| FM-02 | Experience is deleted through Memory maintenance | repository test | no delete authority in normal Memory API |
| FM-03 | Memory has missing provenance | validator | remain PROVISIONAL or reject |
| FM-04 | Provenance cycle introduced | graph validator | reject atomic transaction |
| FM-05 | Illegal relation endpoints | relation validator | reject relation; trace validation failure |
| FM-06 | Model emits invalid structured output | schema parser | retry once where configured; otherwise NO_CHANGE/reject |
| FM-07 | Model attempts free-form DB/tool mutation | model boundary | treat as data; never execute |
| FM-08 | Proposed claim is unsupported by cited evidence | independent evidence validator | cannot become ACTIVE |
| FM-09 | Fred duplicates the same Memory repeatedly | duplicate candidate detection + Sleep | group for MERGE/PROMOTE/TOMBSTONE review |
| FM-10 | Sleep proposes destructive Experience change | validator | reject; Sleep cannot mutate Experience |
| FM-11 | Sleep interrupted mid-review | runtime state | discard uncommitted proposal; resume later |
| FM-12 | Sleep interrupted during commit | DB transaction | atomic rollback or complete transaction |
| FM-13 | Tombstoned Memory appears in normal retrieval | integration test / retrieval trace | retrieval query bug; fail test |
| FM-14 | Relevant Memory exists but retrieval misses it | experiment trace | label RETRIEVAL_MISS; preserve evidence for tuning |
| FM-15 | Retrieval finds Memory but visibility hides it incorrectly | trace | label VISIBILITY_ERROR |
| FM-16 | Fred receives Memory but rejects relevant evidence | trace | label RELEVANCE_REJECTION |
| FM-17 | Fred selects evidence but interprets it incorrectly | trace + evaluator | label MISINTERPRETATION |
| FM-18 | Fred interprets correctly but acts/reasons incorrectly | trace + outcome | label REASONING_ERROR |
| FM-19 | Two retrieval views duplicate the same record | integration test | deduplicate by record ID; preserve view ranks |
| FM-20 | One retrieval channel dominates due incomparable score scale | trace | use rank fusion; never raw-add heterogeneous scores |
| FM-21 | Vector embedding dimension/model mismatch | adapter validation | reject write/query; require explicit re-embedding |
| FM-22 | Retrieval returns nothing | NO_MATCH | expose NO_MATCH; never invent history |
| FM-23 | External evidence acquires Operator authority | authority validator | reject Memory authority classification |
| FM-24 | Current State conflicts with remembered State | State/trace comparison | exact State wins for current operational truth; preserve conflict |
| FM-25 | Observer changes cognitive state | architecture/integration test | Observer read-only; interventions use explicit harness action |
| FM-26 | Experiment leaks state between runs | isolated DB identity check | abort contaminated run |
| FM-27 | Continuity probe still contains acquisition transcript | harness check | invalidate run |
| FM-28 | Correct behavioural answer is only a lucky guess | trace has no relevant Memory path | behavioural Memory test fails |
| FM-29 | SurrealDB unavailable | startup health check | fail clearly; do not silently switch persistence |
| FM-30 | Ollama reasoning/embedding model unavailable | startup health check | fail clearly with required model name |
| FM-31 | Vector index unavailable/not ready | startup/integration check | mark retrieval degraded or fail acceptance run |
| FM-32 | Evidence verifier disagrees with proposer | expected condition | preserve both; activation follows validator policy |
| FM-33 | Promoted Memory loses supporting exceptions/counterevidence | validation/trace | reject promotion or retain required counterevidence refs |
| FM-34 | Memory graph grows through meaningless relations | relation vocabulary + tests | reject relation types outside frozen vocabulary |
| FM-35 | Implementation silently changes frozen architecture | review against spec | stop and document required amendment |

## Failure Classification

Unexpected behavioural outcomes should be classified using the smallest supported label:

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

Do not label every incorrect Fred answer as a Memory failure.

The trace must identify which stage actually failed.
