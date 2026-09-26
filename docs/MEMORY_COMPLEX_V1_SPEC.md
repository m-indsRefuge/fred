# Fred Memory Complex V1 Specification

**Status:** FROZEN FOR MEM-01 IMPLEMENTATION
**Milestone:** MEM-01
**System:** Fred Developmental Agent
**Purpose:** Unified persistent cognitive memory

## 1. Research Objective

Fred Memory Complex V1 is intended to investigate whether a language model can make meaningful use of a persistent record of its own experience, allowing previous interactions, outcomes, corrections, and learned abstractions to influence how it responds to future situations.

The important distinction is that we are not attempting to recreate conventional episodic, semantic, procedural, and relational memory as separate physical stores.

Instead, Fred's persistent cognitive history will exist within a single interconnected memory fabric. What we normally describe as different forms of memory should emerge as properties, abstractions, relationships, and retrieval perspectives over that shared history.

The primary research question is therefore:

> Can a language model operating over a unified experience graph recognise which parts of its past are relevant to a present situation and use those experiences to meaningfully change its future reasoning and behaviour?

This is the capability MEM-01 is intended to test.

## 2. Architectural Principle

The canonical historical primitive of the system is the **Experience**.

An Experience represents something that actually occurred during Fred's ongoing existence. It is the persistent evidence of an interaction, event, decision, action, outcome, correction, or other bounded cognitive episode.

Once committed, that evidence is immutable.

A **Memory**, by contrast, represents something Fred has learned, inferred, generalised, or come to believe based on one or more Experiences and/or existing Memories.

When a Memory is derived from another Memory, its provenance must remain traceable through the graph until it ultimately resolves to immutable Experience evidence.

This distinction is important because Fred's understanding of an event may change without the event itself changing.

If Fred later discovers that an earlier interpretation was incomplete or wrong, the original Experience should not be rewritten. The system should instead create new Memory objects and relationships that preserve both the historical evidence and the later change in interpretation.

In simple terms:

```text
EXPERIENCE = what happened
MEMORY     = what Fred learned or inferred from what happened
```

This separation allows Fred's understanding to develop over time without losing the history that produced it.

## 3. Core Invariants

1. Experience records are immutable once committed.
2. A later interpretation must never overwrite the historical evidence from which it was derived.
3. Every derived Memory must retain provenance to Experience evidence, either directly or through other Memories whose lineage ultimately resolves to Experiences.
4. Evidence explicitly provided by the Operator must remain distinguishable from conclusions or inferences produced by Fred.
5. Contradiction does not erase history. Conflicting information must remain available as part of the record.
6. Supersession changes which information should currently apply without destroying the state that existed before it.
7. Fred may propose memory operations, but persistent mutations must be validated and committed by deterministic system code.
8. Fred may propose an interpretation, but Fred may not certify its own evidence. Evidence support is independently checked before a Memory is established.
9. Retrieval ranking identifies potentially relevant candidates. It does not determine cognitive relevance by itself.
10. Final relevance among retrieved candidates is a model judgement made in the context of the current situation.
11. Memory categories describe characteristics of a Memory. They do not define physically separate memory systems.
12. Vector, lexical, graph, structured, provenance, and temporal representations should share a common persistent substrate wherever technically practical.
13. Memory operations must remain observable and replayable so that we can inspect how a result was produced.
14. A Memory must not become its own source of truth merely because it has been repeated, rephrased, or re-derived.
15. A committed Experience record is never degraded, rewritten, merged, or deleted by MEM-01.
16. Forgetting and consolidation operate on Memories, not Experiences.
17. Model text is data. Free-form model output must never directly execute database, Python, shell, or graph mutations.
18. External evidence may inform Fred's interpretation but cannot silently acquire Operator authority.
19. Retrieval and instrumentation are read-only with respect to cognitive state; all writes pass through explicit validated mutation paths.
20. A correct final answer without the intended Memory pathway does not count as a successful MEM-01 memory experiment.

## 4. Persistent Cognitive Objects

### Experience

An **Experience** is the immutable record of an event or bounded cognitive interaction.

At minimum, an Experience should preserve:

- id
- sequence_start
- sequence_end
- input
- context
- perception
- decision
- action
- outcome
- feedback
- started_at
- ended_at
- observed_at
- entities
- embedding
- metadata
- provenance

The purpose of the Experience object is not to decide what an event ultimately means. Its purpose is to preserve what occurred with enough context that Fred can interpret or reinterpret it later.

An Experience does not use `valid_from` or `valid_until`. It happened. Applicability and validity belong to State, Memory, procedure, belief, or interpretation.

### Memory

A **Memory** is a derived cognitive representation based on one or more Experiences and/or existing Memories.

A Memory may represent a pattern Fred has noticed, a useful abstraction, a procedure, an inferred relationship, a belief, or another higher-order interpretation of previous experience.

When a Memory is derived from another Memory, its provenance must remain traceable through the graph until it ultimately resolves to immutable Experience evidence.

At minimum, a Memory should preserve:

- id
- content
- episodicity
- abstraction
- procedurality
- relationality
- evidential_support
- interpretive_confidence
- salience_prior
- valid_from
- valid_until
- status
- embedding
- metadata
- provenance

The dimensions associated with a Memory are continuous rather than mutually exclusive categories.

For example:

```text
episodicity   = 0.82
abstraction   = 0.31
procedurality = 0.12
relationality = 0.74
```

A single Memory can therefore contain episodic, semantic, procedural, and relational characteristics at the same time.

This is intentional. We do not want the architecture to force a piece of knowledge into one artificial category when its actual cognitive role may span several.

`salience_prior` represents a persistent estimate that a Memory may be worth considering in future cognition. It does not determine contextual relevance.

A Memory with low general salience may still become critically important in a particular situation. Final cognitive relevance is determined during retrieval and model adjudication in the context of the current interaction.

Initial Memory statuses are:

```text
PROVISIONAL
ACTIVE
TOMBSTONED
```

`PROVISIONAL` means Fred has proposed the Memory but it has not yet survived a Memory Sleep cycle.

`ACTIVE` means the Memory is available to normal cognitive retrieval.

`TOMBSTONED` means the Memory is no longer part of active cognition, while its historical existence and provenance remain inspectable.

### Entity

An **Entity** is a persistent object referred to by Experiences or Memories.

Candidate entity classes include:

```text
person
project
task
goal
tool
model
system
concept
environment
```

Entities give Fred a stable way to recognise that experiences occurring at different times may concern the same person, project, tool, goal, or concept.

The initial entity vocabulary should remain deliberately small. Additional classes should only be introduced when the existing representation proves insufficient during testing.

### State

**State** represents information that is directly true or active in Fred's current cognitive or environmental context.

Unlike ordinary memory retrieval, State should not be reconstructed through semantic similarity when an exact lookup is available.

Examples include:

```text
active experiment
active goal
current model
current session
active entities
current project
```

If Fred needs to know which experiment is currently active, the system should retrieve that state directly rather than search historical memory for the most semantically similar experiment.

This distinction prevents current operational state from becoming confused with remembered history.

### Evaluation

An **Evaluation** records evidence about the outcome of an Experience, decision, action, or Memory.

Examples include:

```text
success
failure
correction
unexpected outcome
useful
not useful
partially correct
```

Evaluation is important because experience alone does not tell Fred whether a previous action should be repeated.

A previous event may have occurred exactly as recorded while still producing a poor result. Evaluations preserve that distinction and provide evidence that can later influence learning, Memory formation, developmental measurement, and the future Temporal Guidance System.

## 5. Core Relations

The initial graph vocabulary is:

```text
DERIVED_FROM
PART_OF
ABOUT
CAUSED_BY
RESULTED_IN
SUPPORTS
CONTRADICTS
SUPERSEDES
REINFORCES
SIMILAR_TO
RECALLED_WITH
```

Relations may carry their own metadata, including:

```text
confidence
source
created_at
strength
provenance
```

The purpose of these relations is to allow Fred's history to become interconnected without forcing every connection into the content of the Experience or Memory itself.

For example, one Memory may contradict another without either object needing to be rewritten. A later Memory may supersede an earlier interpretation while the earlier interpretation remains available as part of Fred's developmental history.

The relation vocabulary should remain intentionally constrained during V1.

We should not add new relation types simply because they appear conceptually useful. A new semantic relation should only be introduced when experimental evidence shows that the existing vocabulary cannot represent a relationship Fred actually needs.

This keeps the graph understandable, observable, and testable while the underlying memory behaviour is still being evaluated.

## 6. Experience Lifecycle

An Experience represents a completed or otherwise bounded unit of Fred's lived history.

The system must distinguish between operational events that are occurring now and Experiences that have already become part of Fred's persistent cognitive history.

### 6.1 Event Journal

Significant runtime events are appended immediately to an internal event journal.

Candidate event classes include:

```text
INPUT_RECEIVED
RETRIEVAL_STARTED
RETRIEVAL_COMPLETED
MEMORY_SELECTED
MODEL_INFERENCE_STARTED
MODEL_INFERENCE_COMPLETED
ACTION_TAKEN
OUTCOME_RECEIVED
FEEDBACK_RECEIVED
EXPERIENCE_COMPLETED
EXPERIENCE_ABORTED
```

Journal events are append-only.

The journal exists primarily as operational evidence and as a basis for reconstructing interrupted or completed Experiences.

Journal events do not automatically become cognitive memory.

The journal may contain details useful for debugging and research that Fred does not normally need to retrieve cognitively.

Examples include:

```text
model latency
retrieval candidate count
database timing
inference duration
runtime errors
```

This creates three distinct historical levels:

```text
JOURNAL     = what computationally happened
EXPERIENCE  = what happened to Fred
MEMORY      = what Fred learned or inferred from it
```

These levels must not be conflated.

### 6.2 Active Experience

While an interaction or bounded episode is underway, the Brain maintains an Active Experience as working State.

An Active Experience may accumulate:

```text
input
context
retrieved candidates
Memories selected by Fred
decisions
actions
outcomes
feedback
relevant Entities
```

The Active Experience is not yet immutable historical evidence.

It may evolve while the interaction remains in progress.

### 6.3 Experience Commit

When an interaction reaches a meaningful boundary, the system constructs a complete Experience from the Active Experience and its supporting journal events.

The Experience is then committed atomically.

After commit, the Experience is immutable.

Later understanding must never cause the Experience to be rewritten.

Any later change in interpretation must instead be represented through:

```text
new Memories
Evaluations
graph relations
supersession
contradiction
```

### 6.4 Aborted and Interrupted Experiences

An interrupted interaction must not be silently erased.

If meaningful cognitive activity occurred, the system may commit an Experience whose outcome indicates:

```text
interrupted
aborted
failed
incomplete
```

The Experience must accurately preserve that the episode did not finish normally.

If no meaningful cognitive interaction occurred, its journal entries may remain operational history without promotion into an Experience.

### 6.5 Experience Boundaries

MEM-01 will use deterministic Experience boundaries.

Candidate boundaries include:

```text
one conversational turn
one bounded task attempt
one tool action and its observed outcome
one explicit correction
one experimental episode
```

Fred will not decide when an Experience begins or ends during MEM-01.

Adaptive or model-defined episode boundaries may be investigated later.

### 6.6 Eligibility for Memory Formation

A committed Experience becomes eligible for Memory formation.

Fred may determine that an Experience:

```text
warrants no durable abstraction
supports an existing Memory
contradicts an existing Memory
changes the applicability of an existing Memory
contributes to a new Memory
contributes to a procedural pattern
```

No derived Memory may be committed before its supporting Experience evidence has been committed.

### 6.7 Provenance Through Consolidation

A Memory may derive from Experiences and/or other Memories.

When Memories are derived from other Memories, their provenance graph must ultimately resolve to immutable Experience evidence.

For example:

```text
Experience E12 ─┐
Experience E31 ─┼──► Memory M7
Experience E44 ─┘

Experience E90 ─────► Memory M18

Memory M7  ─┐
            ├───────► Memory M41
Memory M18 ─┘
```

Memory M41 does not need to duplicate E12, E31, E44, and E90.

The graph must, however, allow Fred or an evaluator to trace M41 back through M7 and M18 to the original Experience evidence.

## 7. Memory Formation

Experience accumulation and Memory formation are separate processes.

Not every Experience should become a Memory.

Experiences preserve Fred's history.

Memories represent conclusions, abstractions, beliefs, relationships, and procedural knowledge that Fred considers useful beyond the individual Experience from which they arose.

### 7.1 Cognitive Authority

The deterministic system must not attempt to fully determine the meaning or importance of an Experience.

It may identify signals suggesting that an Experience is worth examining.

Fred performs the semantic judgement.

The division of responsibility is:

```text
SYSTEM:
    determines what happened
    retrieves plausible prior evidence
    identifies structural relationships
    checks provenance
    validates proposed mutations

FRED:
    interprets meaning
    judges cognitive relevance
    recognises patterns
    proposes abstractions
    identifies lessons
    proposes changes in understanding
```

This distinction is central to MEM-01.

### 7.2 Memory Formation Candidates

After an Experience is committed, the Memory Complex may construct a Memory Formation Candidate.

The system may consider signals such as:

```text
explicit Operator correction
explicit Operator instruction
successful or failed outcome
contradiction with existing Memory
recurrence of a similar Experience
repeated retrieval of related Memories
unexpected outcome
significant goal result
strong Entity overlap
close graph relationships
semantic similarity
Fred explicitly identifying a possible lesson
```

These signals do not determine that a Memory must be created.

They determine only that Fred should be given the opportunity to inspect the Experience and related evidence.

### 7.3 Reflection Context

When Memory formation is considered, Fred receives a bounded evidence package.

The package may contain:

```text
newly committed Experience
relevant existing Experiences
relevant existing Memories
relevant Evaluations
graph relationships
active State required to interpret the event
evidence provenance
```

The package must remain bounded.

Fred should not receive the complete Memory Fabric every time an Experience is evaluated.

### 7.4 Memory Operation Proposal

Fred responds with a structured Memory Operation Proposal.

The initial operation vocabulary is:

```text
NO_CHANGE
CREATE
REINFORCE
CONTRADICT
SUPERSEDE
DERIVE_PROCEDURE
```

`NO_CHANGE` must be considered a normal and desirable result.

The goal is not to maximise the number of Memories created.

The goal is to preserve useful cognitive structure.

### 7.5 Proposal Contract

A Memory Operation Proposal should include at minimum:

```text
operation
proposed_content
target_memory_id
evidence_refs
evidential_support
interpretive_confidence
salience_prior

episodicity
abstraction
procedurality
relationality

applicability
conditions
counterevidence_refs

model_explanation
```

`target_memory_id` may be null where the operation creates a new Memory.

`model_explanation` exists for research observability. It is not itself treated as authoritative evidence.

### 7.6 Deterministic Validation

Fred does not directly modify the persistent Memory graph.

Every proposal passes through deterministic validation.

The validator checks:

```text
referenced Experiences exist
referenced Memories exist
provenance resolves correctly
proposed evidence is accessible
numeric dimensions fall within valid ranges
target Memory exists where required
the operation is structurally valid
an Experience is not being rewritten
explicit Operator evidence is not represented as Fred inference
Fred inference is not represented as Operator evidence
required fields are present
graph operations do not create invalid provenance cycles
```

The validator is not responsible for deciding whether Fred's interpretation is intelligent.

That question belongs to evaluation.

### 7.7 Creation, Reinforcement, Contradiction, and Supersession

A `CREATE` proposal produces a new `PROVISIONAL` Memory linked to supporting evidence using `DERIVED_FROM`.

`REINFORCE` means new evidence provides additional support for an existing Memory. The new Experience remains individually traceable.

`CONTRADICT` records that new evidence is incompatible with an existing Memory. Contradiction does not automatically determine which interpretation is correct.

`SUPERSEDE` represents a newer interpretation that replaces an older interpretation for current applicability while preserving the older Memory as historical evidence.

Substantive Memory content is never silently rewritten in place.

### 7.8 Procedural Memory

`DERIVE_PROCEDURE` allows Fred to recognise a repeated pattern of successful behaviour and represent it as procedural knowledge.

This operation creates a Memory with high procedurality.

It does not create executable code or automatically grant Fred a new tool.

A future Skill system may eventually transform validated procedural Memories into executable skills.

That process is outside the scope of MEM-01.

### 7.9 Foreground Formation

Foreground Memory formation occurs as part of normal interaction.

Its purpose is to create or update `PROVISIONAL` Memories quickly enough that recent experience can influence near-term cognition.

Foreground formation is not responsible for deep cleanup or consolidation.

That work belongs to the Memory Sleep cycle defined in Section 9.

### 7.10 Memory Formation as Research Data

Every Memory Formation Proposal must be recorded for later analysis, including rejected proposals.

The research record should allow us to inspect:

```text
what evidence Fred saw
what Memory operation Fred proposed
what Fred considered relevant
what the validator accepted or rejected
what provisional Memory was created
whether that Memory later survived Sleep
whether that Memory later influenced behaviour
```

## 8. Retrieval and Cognitive Recall

Retrieval is the process by which Fred's Memory Complex identifies parts of Fred's accumulated history that may be relevant to a current cognitive situation.

Retrieval does not decide what Fred should think.

Its purpose is to reduce a potentially very large Memory Fabric into a bounded set of plausible cognitive evidence that Fred can inspect.

The retrieval architecture therefore separates:

```text
CANDIDATE RETRIEVAL
finding information that may matter

COGNITIVE ADJUDICATION
Fred determining what actually matters
```

### 8.1 Retrieval Input

A retrieval request is represented as a typed Retrieval Query rather than an unstructured natural-language request between cognitive units.

A Retrieval Query should contain, where available:

```text
query_id
current_input_ref
active_experience_ref
active_goal_ref
current_state_refs
active_entity_refs
semantic_query
requested_object_types
retrieval_profile
candidate_budget
source_unit
destination_unit
constraints
```

The query may contain natural-language semantic content where useful for embedding or lexical search, but communication between Brain components should remain typed.

### 8.2 Retrieval Profiles

MEM-01 should support a small initial set of retrieval profiles rather than one universal ranking function.

Candidate profiles include:

```text
current_context
historical_similarity
problem_solving
relational
procedural
contradiction
reflection
```

Profiles modify retrieval mechanics. They do not determine final cognitive relevance.

### 8.3 Multi-Signal Candidate Generation

Candidate retrieval should use multiple independent signals over the same persistent substrate.

MEM-01 should initially support:

```text
vector similarity
lexical / full-text relevance
Entity overlap
graph proximity
goal or task relationship
outcome relationship
confidence
salience prior
basic temporal proximity
```

No single signal should be treated as sufficient.

Vector similarity must not become the definition of memory relevance.

### 8.4 Hybrid Retrieval and Fusion

Each retrieval channel may rank candidates independently.

Results are then fused into a single candidate set using an observable fusion mechanism.

Reciprocal Rank Fusion is a suitable initial method:

```text
RRF(d) = Σ 1 / (k + rank_r(d))
```

where each retrieval channel contributes its ranking of object `d`.

The exact mechanism is experimental and configurable.

The retrieval trace must preserve channel-specific scores and rankings rather than returning only one opaque final score.

### 8.5 Temporal Readiness

MEM-01 does not attempt to implement the future Temporal Guidance System.

However, the retrieval system must be designed so that temporal cognition can later be integrated without restructuring Memory.

V1 may use basic temporal signals such as:

```text
recency
sequence distance
time since last retrieval
time since Experience
validity interval
```

These are retrieval hints only.

The Memory Complex must avoid fixed assumptions such as:

```text
newer = more relevant
older = less important
```

### 8.6 Graph Expansion

Initial candidate generation may discover an Experience or Memory through vector or lexical search.

The system may then expand around highly ranked candidates through graph relationships.

Graph expansion allows Fred to retrieve the cognitive neighbourhood surrounding a relevant object rather than isolated fragments.

Expansion depth must remain bounded.

### 8.7 Candidate Fusion and Deduplication

The same cognitive object discovered through multiple mechanisms must appear once.

Its retrieval trace should record every mechanism that found it.

Example:

```text
candidate: M41

discovered_by:
    vector
    graph
    entity

vector_similarity: 0.84
graph_relevance: 0.91
entity_overlap: 1.0
```

### 8.8 Candidate Budget

Fred must never receive an unbounded retrieval result.

A Retrieval Query includes a candidate budget.

Candidate limits exist to protect:

```text
model context
latency
cognitive noise
retrieval cost
```

The optimal budget is an experimental parameter.

### 8.9 Visibility Levels

A retrieved cognitive object does not need to be presented to Fred at full resolution.

Each candidate receives a visibility level:

```text
HIDE
SIGNAL
SUMMARY
FULL
```

Visibility affects presentation, not storage.

`HIDE` retains the candidate in the retrieval trace but does not show it to Fred.

`SIGNAL` exposes only a compact typed indication that the object exists.

`SUMMARY` exposes a bounded representation relevant to the query.

`FULL` exposes the complete cognitively relevant representation available for the request.

The underlying Memory or Experience is never compressed or rewritten merely because a lower-resolution view was sufficient for one query.

### 8.10 Addressable Cognitive Objects

Cognitive objects should be passed between Brain units primarily through stable references.

Examples:

```text
EXP-991
MEM-41
ENTITY-python
EVAL-18
```

Large contents should not be repeatedly copied through internal communication pathways.

### 8.11 Cognitive Adjudication

Candidate retrieval ends before cognitive relevance is determined.

Fred receives the bounded candidate representations and evaluates them in the context of the current situation.

Fred may classify candidates as:

```text
RELEVANT
SUPPORTING
CONTRADICTORY
CONTEXTUAL
NOT_RELEVANT
```

Fred may also assign contextual relevance.

Fred's judgement may disagree with machine ranking. That disagreement is expected and must be preserved as research evidence.

### 8.12 Model Relevance Report

For research observability, Fred should return a structured relevance report.

The explanation field exists for research observability. It is not treated as a literal transcript of the model's complete internal computation or as objective evidence.

### 8.13 Context Assembly

Only after cognitive adjudication should selected Memory material enter the main reasoning context.

The final model context may contain:

```text
current interaction
current State
selected Experiences
selected Memories
relevant Evaluations
necessary provenance
active goal or task state
```

Information should be included at the lowest resolution sufficient for the current cognitive requirement.

### 8.14 Query-Aware Representation

A Memory should not have one permanently compressed representation.

Different queries may require different views of the same Memory.

Representation is assembled in response to the current query.

Stored historical detail remains unchanged.

### 8.15 Retrieval Trace

Every retrieval operation must generate an observable Retrieval Trace.

At minimum the trace records:

```text
query
retrieval profile
channels used
objects considered
component scores
fused ranking
graph expansions
visibility decisions
candidate set shown to Fred
Fred's cognitive selections
final context objects
```

This allows us to distinguish:

```text
retrieval failure
cognitive relevance failure
interpretation failure
reasoning failure
```

### 8.16 Retrieval Feedback

The Memory Complex should preserve evidence about how retrieved objects were used.

Examples include:

```text
retrieved
selected
rejected
cited in reasoning
influenced decision
associated with successful outcome
associated with failed outcome
```

MEM-01 records this evidence but does not yet implement unconstrained self-modifying ranking.

### 8.17 Shared Retrieval

Where multiple Brain functions require substantially the same cognitive evidence during one interaction, they should reuse one retrieval pass wherever possible.

Different cognitive units may request different projections of the same retrieved objects.

### 8.18 Retrieval Failure

Retrieval must explicitly support:

```text
READY
PARTIAL
NO_MATCH
ERROR
```

Fred must not invent historical evidence when retrieval returns nothing.

`NO_MATCH` is meaningful cognitive information.

### 8.19 Retrieval Does Not Write Memory

Retrieval is read-only.

Any Memory mutation resulting from retrieved evidence must occur through the Memory Formation or Memory Sleep process.

## 9. Memory Sleep and Consolidation

Fred's Memory Complex uses one coherent maintenance cycle rather than separate forgetting, decay, archival, compression, and pruning systems.

The cycle is called **Memory Sleep**.

Memory Sleep runs opportunistically during short idle periods after foreground cognitive work.

Its purpose is to keep Fred's active Memory coherent, compact, and non-redundant while preserving immutable Experience evidence.

The governing principle is:

> Experiences are immutable. Memories are provisional interpretations that periodically compete, merge, strengthen, generalise, or disappear during short idle consolidation cycles.

### 9.1 Experiences Do Not Degrade

Memory Sleep never rewrites, merges, compresses, or deletes committed Experiences in MEM-01.

Experiences remain the canonical historical evidence of what happened to Fred.

Only Memories participate in forgetting and consolidation.

### 9.2 Entry into Sleep Is Deterministic

Fred does not decide which Memories are allowed to enter the Sleep workspace.

When the Brain transitions from working to idle, deterministic code checks whether there is Memory maintenance work available.

Eligible material may include:

```text
new PROVISIONAL Memories
near-duplicate Memories
malformed or unsupported Memories
new contradiction candidates
recently reinforced Memories
clusters of related Memories
Memories affected by new Evaluations
```

The system determines what requires review.

Fred determines what the reviewed material means.

### 9.3 Sleep Is Opportunistic

The cycle should run in short bursts whenever:

```text
Brain state = IDLE
and
Memory maintenance backlog > 0
```

Sleep must be interruptible.

If new Operator input or higher-priority cognitive work arrives, the Sleep cycle yields immediately.

The design should favour frequent small consolidation bursts over rare large maintenance jobs.

### 9.4 Mechanical Inspection

The first Sleep phase is deterministic.

Python and SurrealDB check:

```text
schema validity
provenance validity
duplicate or near-duplicate candidates
shared Entity structure
shared source Experiences
contradiction candidates
unsupported Memories
invalid graph relations
```

No model judgement is required for these checks.

### 9.5 Candidate Grouping

Related Memories are grouped into bounded review packets using deterministic and algorithmic mechanisms such as:

```text
vector similarity
Entity overlap
shared provenance
graph neighbourhood
relation overlap
structured field agreement
```

A review packet should be small enough for Fred to adjudicate coherently.

### 9.6 Fred's Sleep Decision

Fred receives a review packet together with the minimum supporting Experience evidence needed to understand it.

Fred returns one typed Sleep decision:

```text
KEEP
MERGE
PROMOTE
TOMBSTONE
```

`KEEP`:
The Memory remains cognitively distinct and should survive unchanged.

`MERGE`:
Several Memories represent substantially the same cognitive information and should become one coherent Memory.

`PROMOTE`:
The reviewed material supports a more useful higher-order abstraction or procedure.

`TOMBSTONE`:
The Memory adds no unique or reliable cognitive value and should leave active retrieval.

Fred does not directly mutate the database.

### 9.7 Deterministic Commit

The Sleep decision is validated before commit.

Validation checks include:

```text
all referenced Memories exist
supporting Experience provenance resolves
no Experience is modified
no invalid provenance cycle is introduced
a MERGE or PROMOTE retains evidentiary lineage
a TOMBSTONE does not remove its historical graph identity
typed output is structurally valid
```

Only after validation does the Memory Complex apply the operation.

### 9.8 Merge

When several Memories express substantially the same interpretation, Sleep may merge them.

Example:

```text
M27:
Nolan prefers empirical experiments after architectural discussion.

M31:
Nolan likes testing architecture instead of endlessly discussing it.

M38:
When architecture is uncertain, Nolan prefers an experiment.
```

Sleep may produce:

```text
M41:
After sufficient architectural analysis, Nolan tends to prefer
bounded empirical testing of unresolved questions.
```

M41 preserves the complete supporting provenance.

The redundant Memories become `TOMBSTONED`.

The Experiences that originally supported them remain untouched.

### 9.9 Promote

`PROMOTE` creates a higher-order Memory from several related Memories and/or Experiences.

Promotion is how repeated concrete interpretations become broader knowledge or procedure.

Example:

```text
M12 ─┐
M19 ─┼──► M70
M33 ─┘
```

M70 may represent a general lesson that none of the individual Memories captured alone.

The supporting Memories do not need to remain active if they no longer add unique cognitive value, but their provenance remains available.

### 9.10 Tombstone

`TOMBSTONE` is the V1 forgetting operation.

A tombstoned Memory:

```text
is excluded from normal retrieval
remains present in historical/audit records
retains provenance
may still be referenced by graph history
```

Tombstoning does not erase Experience.

It removes an interpretation from Fred's active cognitive memory.

### 9.11 Forgetting Through Consolidation

MEM-01 does not use a separate age-based decay system.

A Memory is forgotten primarily because it no longer contributes unique cognitive value.

Typical reasons include:

```text
duplicate representation
better represented by a merged Memory
subsumed by a promoted abstraction
malformed interpretation
unsupported inference
persistent contextual irrelevance
```

Time may later contribute to Sleep candidate selection through the Temporal Guidance System, but elapsed time alone does not delete Memory.

### 9.12 Provisional Memory

Foreground-created Memories begin as `PROVISIONAL`.

A provisional Memory may influence near-term cognition when necessary, but it has not yet survived Sleep consolidation.

During Sleep it may become:

```text
ACTIVE
```

or be:

```text
MERGED
PROMOTED
TOMBSTONED
```

This prevents every model-generated interpretation from immediately becoming permanent long-term cognition.

### 9.13 Memory Sleep and the Subconscious

MEM-01 does not create a physically separate subconscious store.

The subconscious is a processing condition rather than a second database.

During Sleep, selected Memories are temporarily outside foreground cognitive flow and are evaluated in a bounded maintenance context.

All objects remain inside the same shared Memory substrate.

### 9.14 Sleep Trace

Every Sleep cycle must be observable.

The trace records:

```text
trigger
Memories considered
candidate groups
supporting Experience refs
Fred's typed decision
validation result
graph mutations
Memories activated
Memories merged
Memories promoted
Memories tombstoned
duration
interruptions
```

Rejected and invalid Sleep proposals must also be retained for research.

### 9.15 V1 Simplicity Constraint

Memory Sleep is intentionally small.

MEM-01 must not introduce separate subsystems for:

```text
decay
archival
compression
forgetting
pruning
subconscious storage
```

unless experimental evidence later demonstrates that one of those capabilities cannot be represented adequately by the Sleep cycle.

The V1 maintenance mechanism is:

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
COMMIT
```

This cycle is the complete V1 forgetting and consolidation protocol.

## 10. Memory Observer and Research Instrumentation

The Memory Observer is part of the MEM-01 experimental apparatus.

It is not a user-facing product interface and is not responsible for controlling Fred's cognition.

Its purpose is to expose enough of the Memory Complex that researchers can distinguish between:

```text
retrieval failure
relevance-selection failure
interpretation failure
reasoning failure
memory-formation failure
sleep-consolidation failure
validator rejection
database/runtime failure
```

Without this visibility, unexpected Fred behaviour would be difficult to attribute correctly.

### 10.1 Observer Principle

The Observer must display what the Memory Complex actually did.

It must not infer hidden internal model reasoning that was never recorded.

The Observer may display:

```text
typed model outputs
retrieval traces
candidate rankings
selected references
structured relevance reports
Memory proposals
Sleep proposals
validation results
graph mutations
Evaluations
runtime timing
```

The Observer must distinguish these from:

```text
model self-report
researcher interpretation
derived metrics
```

Model-generated explanations are useful research evidence but must not be presented as literal access to the model's complete internal computation.

### 10.2 Turn Trace

Every completed foreground interaction should produce a Turn Trace.

A Turn Trace should include:

```text
turn_id
experience_id
session_id
input_ref

active_state_refs

retrieval_query
retrieval_profile
retrieval_channels
retrieval_candidates
visibility_assignments

Fred_relevance_selection

context_refs_used_for_reasoning

model_response_ref
action_refs
outcome_ref
evaluation_refs

Memory_Formation_Proposal
proposal_validation
resulting_memory_mutations

timing
errors
```

The Turn Trace is the primary unit for inspecting live Memory behaviour.

### 10.3 Retrieval View

The Observer should make retrieval inspectable as a pipeline.

For each retrieval operation it should show:

```text
QUERY

VECTOR RESULTS
LEXICAL RESULTS
ENTITY RESULTS
GRAPH RESULTS
TEMPORAL / STRUCTURED RESULTS

FUSED CANDIDATES

VISIBILITY

FRED SELECTION

FINAL CONTEXT
```

For every candidate, the Observer should expose:

```text
object ref
object type
retrieval channels
channel-specific ranks
channel-specific scores
fused rank
visibility level
Fred selection status
Fred contextual relevance
selection role
```

This makes it possible to determine whether a useful Memory was:

```text
never found
found but ranked poorly
hidden by visibility
shown but rejected by Fred
selected but later ignored
```

### 10.4 Memory Formation View

For each foreground Memory Formation event, the Observer should display:

```text
supporting Experience
related Memories supplied to Fred
related Evaluations
Fred's proposed operation
proposed Memory content
evidence refs
counterevidence refs
Memory dimensions
confidence
salience prior
validator result
committed mutation
```

Rejected proposals must remain visible.

A rejected proposal is research data.

### 10.5 Sleep View

Every Memory Sleep burst should produce a Sleep Trace.

The Observer should display:

```text
sleep_cycle_id
trigger
start time
end time
interruptions

provisional Memories considered
mechanical problems detected
candidate groups created

supporting Experience refs shown to Fred

Fred decision:
    KEEP
    MERGE
    PROMOTE
    TOMBSTONE

validator result

graph changes

Memories:
    activated
    merged
    promoted
    tombstoned
```

The Sleep view should make consolidation visually understandable.

For a MERGE or PROMOTE operation, the Observer should show both the source cluster and the surviving/new Memory.

### 10.6 Provenance View

Any Memory shown in the Observer should support provenance inspection.

For example:

```text
M41
 |
 +-- DERIVED_FROM --> M18
 |                     |
 |                     +-- DERIVED_FROM --> E90
 |
 +-- DERIVED_FROM --> M7
                       |
                       +-- DERIVED_FROM --> E12
                       +-- DERIVED_FROM --> E31
                       +-- DERIVED_FROM --> E44
```

The initial implementation may render this as text or a compact tree.

A graphical view is optional.

Correct lineage is more important than visual polish.

### 10.7 Experience View

The Observer should allow an Experience to be inspected without converting it into Memory prose.

The view should expose the Experience's committed fields directly:

```text
input
context
perception
decision
action
outcome
feedback
entities
sequence
timestamps
provenance
Evaluations
```

The Observer must make clear that Experience is immutable evidence.

### 10.8 Memory View

A Memory view should display:

```text
content

status:
    PROVISIONAL
    ACTIVE
    TOMBSTONED

episodicity
abstraction
procedurality
relationality

confidence
salience prior

validity

supporting provenance

supporting relations
contradictions
supersession
reinforcement

retrieval history
selection history
outcome associations
```

This allows the researchers to observe how one Memory evolves through graph relationships without rewriting its substantive historical record.

### 10.9 State View

The Observer should expose the exact active State used for a turn.

Examples include:

```text
current session
active experiment
current goal
current model
active entities
current project
```

This is necessary to distinguish:

```text
Fred remembered incorrectly
```

from:

```text
Fred was supplied incorrect current State
```

### 10.10 Model Self-Report

MEM-01 should support targeted self-report probes.

Examples include:

```text
Which previous experiences influenced this answer?

Which retrieved Memory mattered most?

Did any retrieved Memory conflict with your current interpretation?

Has your expectation changed because of prior experience?

What have you learned from repeated exposure to this situation?

Is there a Memory you believe should be consolidated with another?

Why did you reject a retrieved candidate?
```

Self-report responses must be labelled:

```text
MODEL_SELF_REPORT
```

They are not objective descriptions of hidden model computation.

They become useful when compared against observable system evidence such as:

```text
actual retrieved candidates
actual selected refs
actual Memory writes
actual later behaviour
```

### 10.11 Behavioural Checkpoints

During longitudinal experiments, the Observer should support fixed behavioural checkpoints.

Candidate checkpoints may occur after:

```text
0 Experiences
10 Experiences
50 Experiences
100 Experiences
500 Experiences
1000 Experiences
3000 Experiences
```

The exact schedule is experiment-specific.

At each checkpoint, the system can run a stable probe set and archive:

```text
Fred's responses
retrieved Memories
selected evidence
confidence
self-report
decision quality
error types
```

This allows behavioural development to be compared across Fred's accumulated experience.

### 10.12 Memory Health Metrics

The Observer should maintain a small initial set of system-level Memory metrics.

Candidate metrics include:

```text
Experience count

Memory count:
    PROVISIONAL
    ACTIVE
    TOMBSTONED

Experience-to-Memory ratio

duplicate candidate rate

Sleep merge rate

Sleep promotion rate

Sleep tombstone rate

validator rejection rate

retrieval NO_MATCH rate

retrieval candidate count

average selected Memories per turn

average retrieval latency

average Memory Formation latency

average Sleep burst duration

percentage of selected Memories associated with successful outcomes

percentage of surfaced Memories rejected by Fred
```

These metrics are descriptive.

MEM-01 should not automatically optimise itself against them.

### 10.13 Cognitive Failure Labels

When analysing a failed or unexpected interaction, the research harness should support explicit failure labels.

Initial labels include:

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

The purpose of these labels is to support experimental analysis, not to create another autonomous cognitive subsystem.

### 10.14 Replay

A completed interaction should be replayable from stored evidence wherever practical.

Replay should allow the researchers to inspect:

```text
State at turn start
Retrieval Query
candidate set
Fred's relevance selection
final model-facing Memory context
Memory proposal
validator result
Sleep consequences
```

Replay does not necessarily mean reproducing identical stochastic model output.

Its purpose is to reconstruct the evidence and system decisions that surrounded the original turn.

### 10.15 Research Event Log

The Observer should maintain a machine-readable research event stream.

Candidate event classes include:

```text
EXPERIENCE_COMMITTED

RETRIEVAL_COMPLETED
COGNITIVE_SELECTION_COMPLETED

MEMORY_PROPOSAL_CREATED
MEMORY_PROPOSAL_ACCEPTED
MEMORY_PROPOSAL_REJECTED

MEMORY_ACTIVATED
MEMORY_MERGED
MEMORY_PROMOTED
MEMORY_TOMBSTONED

SLEEP_STARTED
SLEEP_INTERRUPTED
SLEEP_COMPLETED

VALIDATION_FAILED

EXPERIMENT_CHECKPOINT
```

The event stream should be suitable for later quantitative analysis without requiring natural-language log parsing.

### 10.16 Observer Interface V1

The initial Observer should prioritise information density and inspectability over visual polish.

A terminal or Textual-style interface is acceptable.

A useful live layout may include:

```text
┌──────────────── CURRENT TURN ────────────────┐
│ Operator input                              │
│ Active Experience                          │
│ Current State                              │
└─────────────────────────────────────────────┘

┌──────────────── RETRIEVAL ──────────────────┐
│ machine candidates                         │
│ visibility                                 │
│ Fred selections                            │
└─────────────────────────────────────────────┘

┌──────────────── RESPONSE ───────────────────┐
│ model output                               │
│ outcome / evaluation                       │
└─────────────────────────────────────────────┘

┌────────────── MEMORY FORMATION ─────────────┐
│ proposal                                   │
│ validation                                 │
│ committed mutations                        │
└─────────────────────────────────────────────┘

┌──────────────── MEMORY SLEEP ───────────────┐
│ pending review groups                      │
│ current Sleep decision                     │
│ merge / promote / tombstone changes        │
└─────────────────────────────────────────────┘
```

The Observer must not become a dependency of Memory correctness.

Fred's Memory Complex must continue to function if the Observer is disabled.

### 10.17 Instrumentation Invariant

Observability must not silently change the cognitive experiment.

The Observer is read-only with respect to cognitive state.

Researcher actions that intentionally alter State, Memory, or experiment conditions must occur through explicit harness controls and be recorded as interventions.

This prevents instrumentation from becoming an untracked source of cognitive change.

## 11. Epistemic Integrity and External Knowledge

The Memory Complex must preserve a strict distinction between evidence, interpretation, and action.

### 11.1 Three Epistemic Layers

Fred's cognition is organised around three layers:

```text
EVIDENCE
    immutable Experience
    Operator statements
    tool results
    external documents and data

        ↓

INTERPRETATION
    Memories
    abstractions
    hypotheses
    procedures
    relational understanding

        ↓

ACTION / REASONING
    what Fred decides to think or do now
```

Layer 2 must never silently masquerade as Layer 1.

A model-generated conclusion remains an interpretation even when Fred is highly confident in it.

### 11.2 Evidence Support and Interpretive Confidence

A Memory carries two distinct confidence concepts:

```text
evidential_support
interpretive_confidence
```

`evidential_support` estimates how strongly the cited evidence supports the Memory.

`interpretive_confidence` represents Fred's confidence that the abstraction or interpretation is the correct way to understand that evidence.

These values are not interchangeable.

Strong evidence may admit several interpretations.

Fred may also be very confident about a conclusion supported by weak evidence.

### 11.3 Independent Evidence Validation

Before a newly proposed Memory becomes `ACTIVE`, its evidence references must be checked independently from the proposal itself.

Validation occurs at two levels.

Mechanical validation checks:

```text
the referenced objects exist
the references are permitted evidence types
the provenance chain resolves
the graph is acyclic where required
the authority labels are correct
```

Semantic evidence validation asks whether the cited evidence actually supports the proposed claim.

The initial verdict vocabulary is:

```text
SUPPORTED
PARTIAL
UNSUPPORTED
CONTRADICTED
```

Semantic validation may use a separate model invocation or dedicated verifier.

The proposer must not certify its own proposal.

A structurally valid proposal may therefore remain `PROVISIONAL` or be rejected because its evidence does not support its content.

### 11.4 Concurrent Memory Views

Episodic, semantic, procedural, and relational memory are retrieval perspectives over one substrate, not separate stores.

A single Retrieval Query may request several views concurrently.

For example:

```text
procedural view
relational view
```

may execute concurrently over the same `memory` and `experience` records.

If the same object appears in several views it is represented once in the fused candidate set, while preserving all view-specific rankings.

Example:

```text
MEM-72

matched_views:
    procedural
    relational

procedural_rank: 3
relational_rank: 1
```

Disagreement between views must remain observable.

Fusion controls candidate volume; it must not erase the character of the retrieval evidence.

### 11.5 External Knowledge

External knowledge is evidence with external provenance.

It does not automatically become Experience and does not silently become Operator-specific Memory.

When Fred evaluates external information, relevant internal Experience and Memory remain eligible for retrieval.

The cognitive pattern is:

```text
CURRENT QUESTION
      |
      +---- INTERNAL RETRIEVAL
      |       Experiences
      |       Memories
      |       Evaluations
      |
      +---- EXTERNAL RETRIEVAL
              documents
              web
              research
              tools
      |
      +---- EVIDENCE ASSEMBLY
              authority preserved
      |
      +---- FRED INTERPRETATION
```

Fred therefore encounters the outside world through the lens of relevant accumulated experience without changing what the external evidence actually says.

An external claim and an internal Memory may disagree.

Both remain distinct evidence objects and the disagreement becomes part of Fred's reasoning rather than being silently reconciled.

### 11.6 External Knowledge Cannot Establish Operator Preference Alone

External evidence must not establish a Memory about the Operator's preference, intent, history, or standing instruction unless the required Operator evidence exists.

For example:

```text
external source:
    "Nolan prefers Rust"
```

cannot establish:

```text
Operator preference:
    Nolan prefers Rust
```

without appropriate internal evidence.

This rule is enforced by provenance and authority validation.

## 12. SurrealDB Physical Schema V1

### 12.1 Version Baseline

MEM-01 targets:

```text
SurrealDB 3.3.x
Python SDK 2.0.x
```

The runtime uses a local SurrealDB server over WebSocket during research.

The schema should remain compatible with a later embedded deployment where practical.

### 12.2 Embedding Baseline

MEM-01 uses a dedicated embedding model rather than Fred's reasoning model.

The initial local baseline is:

```text
qwen3-embedding:0.6b
output dimension: 1024
distance: cosine
```

The embedding model is accessed locally through Ollama.

Every embedded record stores the embedding model identity and embedding version alongside its vector so that a future model change can be handled through explicit re-embedding rather than silent mixture of incompatible vector spaces.

### 12.3 Core Tables

V1 uses eight physical tables:

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

This is intentionally smaller than the logical architecture.

The database should not create a separate physical table for:

```text
episodic memory
semantic memory
procedural memory
relational memory
subconscious memory
retrieval views
```

Those are projections over the shared records.

### 12.4 `experience`

`experience` stores immutable committed Experience evidence.

Core fields:

```text
id
sequence_start
sequence_end

session_id
turn_id

input
context
perception
decision
action
outcome
feedback

search_text

entity_refs

started_at
ended_at
observed_at
created_at

embedding
embedding_model
embedding_version

provenance
metadata
```

`search_text` is a deterministic searchable representation constructed from the committed Experience.

It exists so vector and lexical retrieval do not need to embed every raw nested field separately.

Once committed, an Experience must never be semantically rewritten.

The Python repository exposes create and read operations only.

Immutability is covered by repository tests and by database access policy where the runtime credential permits it.

### 12.5 `memory`

`memory` stores Fred's derived interpretations.

Core fields:

```text
id
content

status:
    PROVISIONAL
    ACTIVE
    TOMBSTONED

episodicity
abstraction
procedurality
relationality

evidential_support
interpretive_confidence
salience_prior

valid_from
valid_until

created_at

embedding
embedding_model
embedding_version

provenance
metadata
```

All scalar cognitive dimensions are constrained to `[0, 1]`.

`TOMBSTONED` Memories remain stored but are excluded from normal retrieval.

### 12.6 `entity`

`entity` provides stable identity across Experiences and Memories.

Core fields:

```text
id
kind
canonical_key
name
aliases
created_at
metadata
```

`canonical_key` is unique.

Entity creation must not create a new record when an existing canonical identity is already known.

### 12.7 `evaluation`

`evaluation` stores outcome evidence.

Core fields:

```text
id
target_ref
kind
value
source
created_at
evidence_refs
metadata
```

Initial kinds include:

```text
SUCCESS
FAILURE
CORRECTION
UNEXPECTED
USEFUL
NOT_USEFUL
PARTIAL
```

Evaluation is evidence.

It is not automatically a Memory.

### 12.8 `state`

`state` stores exact current state that should be retrieved directly rather than reconstructed through RAG.

Core fields:

```text
id
key
value
authority
updated_at
metadata
```

`key` is unique.

Examples include:

```text
active_goal
active_project
current_session
current_model
active_experiment
```

### 12.9 `journal_event`

`journal_event` is an append-only operational event stream used to construct and replay Experiences.

Core fields:

```text
id
sequence
event_type
session_id
turn_id
occurred_at
payload
```

It is not part of normal cognitive retrieval.

### 12.10 `cognitive_relation`

All V1 graph edges use one relation table:

```text
cognitive_relation
```

This reduces physical complexity while preserving the controlled semantic relation vocabulary.

Core fields:

```text
in
out
kind
confidence
strength
source
created_at
provenance
metadata
```

Initial relation kinds remain:

```text
DERIVED_FROM
PART_OF
ABOUT
CAUSED_BY
RESULTED_IN
SUPPORTS
CONTRADICTS
SUPERSEDES
REINFORCES
SIMILAR_TO
RECALLED_WITH
```

The Python relation validator enforces legal endpoint combinations for each `kind`.

For example:

```text
DERIVED_FROM:
    memory -> experience|memory

ABOUT:
    experience|memory -> entity

RESULTED_IN:
    experience -> evaluation

SUPERSEDES:
    memory -> memory
```

Using one typed edge table avoids creating eleven nearly identical physical relation tables.

### 12.11 `trace_event`

`trace_event` stores machine-readable research instrumentation.

Core fields:

```text
id
trace_type
session_id
turn_id
experience_ref
occurred_at
payload
```

`payload` is a flexible typed-by-event object.

Initial trace types include:

```text
RETRIEVAL
COGNITIVE_SELECTION
MEMORY_PROPOSAL
MEMORY_VALIDATION
SLEEP
MODEL_CALL
EXPERIMENT_CHECKPOINT
ERROR
```

The Observer reads this table but does not modify cognitive state through it.

### 12.12 Indexes

The initial index strategy is deliberately small.

`experience`:

```text
HNSW cosine index on embedding
FULLTEXT BM25 index on search_text
index on session_id
index on ended_at
```

`memory`:

```text
HNSW cosine index on embedding
FULLTEXT BM25 index on content
index on status
index on valid_from
index on valid_until
```

`entity`:

```text
UNIQUE index on canonical_key
full-text/name index if experiments require it
```

`state`:

```text
UNIQUE index on key
```

`journal_event` and `trace_event`:

```text
indexes on session_id
turn_id
occurred_at
event/trace type
```

Indexes must be justified by observed query patterns.

MEM-01 should not pre-optimise speculative access patterns.

### 12.13 Hybrid Retrieval

The default internal-memory retrieval flow is:

```text
semantic query
    |
    +-- HNSW vector retrieval
    |
    +-- BM25 lexical retrieval
    |
    +-- Entity / structured retrieval
    |
    +-- bounded graph expansion
    |
    +-- view-specific retrieval where requested
    |
    +-- RRF fusion
    |
    +-- deduplication
    |
    +-- visibility projection
    |
    +-- Fred adjudication
```

Vector and BM25 search may be executed directly inside SurrealDB and fused using Reciprocal Rank Fusion.

Graph and structured candidates can be fused into the same Python retrieval envelope while preserving their independent ranks and discovery channels.

The retrieval implementation must never expose only a single unexplained aggregate score.

### 12.14 Retrieval Across Several Views

When a query requires more than one memory perspective, the Retrieval Engine runs the requested projections concurrently.

For example:

```text
await:
    procedural_projection(query)
    relational_projection(query)
```

Both operate over the same `memory` and `experience` records.

Results are deduplicated by record identity.

Per-view rank and match information are preserved in the fused candidate.

### 12.15 Searchability of Experience and Memory

Both Experiences and Memories are searchable.

This is intentional.

A query may require:

```text
the raw historical event
```

rather than Fred's later abstraction.

Likewise, an abstraction may be sufficient without loading its complete supporting Experience chain.

The retrieval profile controls which object types are searched and how strongly they are weighted.

### 12.16 Graph Direction Convention

V1 standardises graph direction before implementation.

A relation is written from the semantic subject to its object.

Therefore:

```text
Memory M7 DERIVED_FROM Experience E12

M7 -> DERIVED_FROM -> E12
```

not the reverse.

Similarly:

```text
Experience E12 RESULTED_IN Evaluation EV4

E12 -> RESULTED_IN -> EV4
```

All diagrams, queries, validators, and tests must follow this convention.

### 12.17 Transaction Boundary

Operations that create an Experience together with its mandatory supporting relations should commit atomically.

Likewise, validated Memory Sleep mutations such as:

```text
create promoted Memory
create provenance edges
tombstone redundant Memories
write Sleep trace
```

should occur in one transaction where practical.

A partial consolidation must not leave the graph in an internally inconsistent state.

## 13. Typed Python Contracts V1

The Python layer is the authority boundary between model output and persistent state.

Pydantic-style typed contracts should be used for all model-facing and database-facing structures.

### 13.1 Core Reference Types

The codebase should define explicit reference types rather than passing arbitrary strings throughout the Brain.

Conceptually:

```python
ExperienceRef
MemoryRef
EntityRef
EvaluationRef
StateRef
TraceRef
```

These may wrap SurrealDB Record IDs.

### 13.2 Retrieval Query

```python
class RetrievalQuery:
    query_id
    semantic_query

    active_experience_ref
    active_goal_ref

    state_refs
    entity_refs

    object_types
    views
    profile

    candidate_budget
```

`views` may contain several requested perspectives:

```text
episodic
semantic
procedural
relational
```

### 13.3 Retrieval Candidate

```python
class RetrievalCandidate:
    ref
    object_type

    discovered_by
    matched_views

    vector_rank
    lexical_rank
    graph_rank
    structured_rank

    view_ranks

    rrf_score

    visibility
```

Missing channel scores are `None`, not fabricated numeric zeros.

### 13.4 Cognitive Selection

```python
class CognitiveSelection:
    ref
    role
    contextual_relevance
    model_explanation
```

Allowed roles are:

```text
RELEVANT
SUPPORTING
CONTRADICTORY
CONTEXTUAL
NOT_RELEVANT
```

### 13.5 Memory Proposal

```python
class MemoryProposal:
    operation

    proposed_content
    target_memory_ref

    evidence_refs
    counterevidence_refs

    evidential_support
    interpretive_confidence
    salience_prior

    episodicity
    abstraction
    procedurality
    relationality

    applicability
    conditions

    model_explanation
```

Fred creates this object.

Fred does not commit it.

### 13.6 Evidence Validation

```python
class EvidenceValidation:
    proposal_ref
    verdict

    supported_refs
    unsupported_refs
    contradictory_refs

    verifier
    explanation
```

Allowed verdicts:

```text
SUPPORTED
PARTIAL
UNSUPPORTED
CONTRADICTED
```

The verifier must be logically separate from the proposal-generating call.

### 13.7 Sleep Decision

```python
class SleepDecision:
    operation

    source_memory_refs
    proposed_memory

    evidence_refs

    model_explanation
```

Allowed operations:

```text
KEEP
MERGE
PROMOTE
TOMBSTONE
```

### 13.8 Repository Authority

The Python persistence layer should expose narrow repositories rather than arbitrary SurrealQL throughout the codebase.

Conceptually:

```text
ExperienceRepository
MemoryRepository
EntityRepository
EvaluationRepository
StateRepository
RelationRepository
TraceRepository
```

`ExperienceRepository` exposes:

```text
create
get
search
```

It does not expose semantic `update` or `delete`.

`MemoryRepository` exposes mutations only through validated Memory operations.

This ensures that persistence authority is concentrated in a small, testable surface.

### 13.9 Cognitive Model Interface

The temporary Ollama reasoning model and the later Developmental Fred model must implement the same high-level interface.

Conceptually:

```python
class CognitiveModel:
    adjudicate_retrieval(...)
    propose_memory(...)
    validate_evidence(...)
    adjudicate_sleep(...)
    reason(...)
```

The implementation may use different model providers without changing the Memory Complex.

The proposer and verifier may use the same underlying model in MEM-01, but they must be separate inference calls with separate structured roles.

### 13.10 Embedding Interface

Embedding is isolated behind:

```python
class EmbeddingModel:
    embed_query(text)
    embed_document(text)
```

The initial implementation uses local Qwen3-Embedding-0.6B through Ollama.

The Memory Complex must not depend directly on Ollama-specific response objects.

### 13.11 Retrieval Engine

The Retrieval Engine owns:

```text
parallel retrieval channels
concurrent memory views
RRF fusion
deduplication
graph expansion
candidate budgeting
visibility assignment
trace creation
```

It does not decide final cognitive relevance.

### 13.12 Memory Engine

The Memory Engine owns:

```text
Experience commit
Memory proposal validation
evidence-validation orchestration
Memory mutation
provenance construction
Sleep candidate grouping
Sleep commit
```

It does not generate semantic interpretations itself.

### 13.13 Runtime Safety Rule

Model text is data.

No free-form model output is executed as:

```text
SurrealQL
Python
shell
database mutation
```

Model output must first parse into an approved typed contract.

Invalid output results in:

```text
REJECT
RETRY WITH SCHEMA
or
NO_CHANGE
```

according to the calling context.

## 14. MEM-01 Experimental Contract

MEM-01 is accepted through two complementary test layers:

```text
ENGINEERING TESTS
deterministic invariants and integration behaviour

BEHAVIOURAL EXPERIMENTS
model-dependent use of persistent Experience and Memory
```

Engineering correctness is a hard gate.

Behavioural experiments test whether the Memory Complex produces the intended cognitive effect rather than merely storing data.

### 14.1 Experimental Isolation

Every behavioural run uses its own SurrealDB namespace/database or equivalent isolated test store.

No Memory, Experience, State, or trace from one run may be visible to another.

Each run records:

```text
experiment id
run id
database identity
Fred model identity
embedding model identity
configuration
seed where supported
start time
end time
all traces
final result
```

Synthetic arbitrary facts and names are used where possible so pretrained model knowledge cannot supply the answer.

### 14.2 Context Reset Rule

A persistent-memory claim is not accepted if the tested information remains in the active model transcript.

Where an experiment claims continuity across time, the harness must:

```text
1. complete the learning episode
2. commit Experience and Memory
3. run Memory Sleep when required
4. end the model session
5. clear transient conversation context
6. start a new model session
7. run the probe using only persistent Brain state
```

The Memory Complex survives the reset.

The model transcript does not.

### 14.3 Behavioural Run Policy

The first MEM-01 acceptance run uses:

```text
5 independent runs per behavioural experiment
low model temperature
fixed seed where the provider/runtime supports it
identical experiment logic
isolated persistent state per run
```

The purpose is repeatability, not elimination of all model variation.

### 14.4 Experiment 1 — Continuity

**Question**

Can Fred recall a fact learned through Experience after all conversational context containing that fact has been removed?

**Acquisition**

The Operator supplies an arbitrary synthetic fact:

```text
The Kestrel project's marker is GLASS-472.
```

The harness confirms:

```text
Experience committed
Memory proposal recorded
evidence validated
Memory survives Sleep as ACTIVE
```

The active model session is then destroyed.

**Probe**

In a new session:

```text
What is the Kestrel project's marker?
```

**Required trace path**

```text
persistent Memory/Experience exists
        ↓
retrieval surfaces relevant evidence
        ↓
Fred selects relevant evidence
        ↓
evidence enters reasoning context
        ↓
Fred answers GLASS-472
```

**Acceptance**

System integrity must pass in 5/5 runs.

Behavioural answer and intended Memory pathway must succeed in at least 4/5 runs.

A correct guess without relevant persistent evidence in the trace is a failure.

### 14.5 Experiment 2 — Correction and Supersession

**Question**

Can Fred adopt corrected information without rewriting the historical evidence that preceded the correction?

**Episode A**

```text
The Kestrel project's marker is GLASS-472.
```

**Episode B**

Later:

```text
Correction: the Kestrel project's marker is now AMBER-913.
```

The expected cognitive history is conceptually:

```text
E1 -> M1: GLASS-472

E2 -> M2: AMBER-913
      M2 SUPERSEDES M1
```

The session is destroyed.

**Probe A**

```text
What is Kestrel's current marker?
```

Expected:

```text
AMBER-913
```

**Probe B**

```text
What marker did Kestrel use previously?
```

Expected:

```text
GLASS-472
```

**Acceptance**

In 5/5 runs:

```text
E1 remains unchanged
E2 remains unchanged
both historical values remain inspectable
supersession lineage is valid
```

Behaviourally, both probes and the intended Memory pathway must succeed in at least 4/5 runs.

### 14.6 Experiment 3 — Repeated Experience Learning

**Question**

Does accumulated outcome evidence improve Fred's decisions when the environment's rule is not stated explicitly?

**Environment**

The harness defines three conditions and three actions:

```text
conditions: X, Y, Z
actions:    A, B, C
```

A hidden deterministic mapping is known only to the harness:

```text
X -> B
Y -> C
Z -> A
```

Fred is never shown this rule.

**Training**

Fred receives repeated bounded episodes using arbitrary instance names.

For each episode Fred selects A, B, or C.

The harness returns only the observed outcome:

```text
SUCCESS
or
FAILURE
```

The resulting Experience and Evaluation are committed normally.

Training uses twelve episodes distributed across X, Y, and Z.

Memory Sleep may consolidate repeated evidence between episodes during idle periods.

**Probe**

After a complete context reset, Fred receives nine new instances:

```text
3 with condition X
3 with condition Y
3 with condition Z
```

No answer mapping is provided.

**Measurements**

Record:

```text
training choices
training outcomes
Memories formed
Sleep promotions/merges
probe accuracy
retrieved evidence per probe
selected evidence per probe
```

**Acceptance**

At least 4/5 runs must satisfy all of:

```text
probe accuracy >= 7/9

at least one probe decision demonstrably uses
persistent prior Experience or derived Memory

no hidden rule appears in State, prompt, or external context
```

A correct probe answer with no relevant Memory pathway does not count toward Memory success.

### 14.7 Experiment 4 — Abstraction and Generalisation

**Question**

Can Fred derive a higher-order Memory from repeated Experience and use it on a genuinely novel case?

**Hidden rule**

The harness defines arbitrary properties:

```text
P
R
```

and an action set:

```text
A
B
C
```

The hidden rule is:

```text
P=true AND R=true -> C
```

Fred is not told this rule.

**Training examples**

Fred receives multiple synthetic entities such as:

```text
Velin
Tarok
Nomel
Brek
```

with different P/R combinations and outcome feedback.

The examples are chosen so that no entity name repeats in the final probe set.

Sleep is allowed to `PROMOTE` a higher-order Memory if Fred identifies a recurring pattern.

**Novel probes**

After a full model-context reset, Fred receives six previously unseen entity names with P/R values.

**Acceptance**

At least 4/5 runs must satisfy all of:

```text
at least one higher-order Memory is created or promoted
that Memory resolves through provenance to training Experiences
novel-probe accuracy >= 4/6
at least one correct novel decision retrieves and selects the abstraction
```

The test is not accepted if the probe entity appeared during training.

### 14.8 Sleep Consolidation Acceptance Scenario

The harness deliberately creates several `PROVISIONAL` Memories that are semantically redundant and share overlapping evidence.

A Sleep burst is triggered.

The expected result is one of:

```text
MERGE
or
PROMOTE
```

when the model judges a coherent survivor exists.

The commit layer must guarantee:

```text
source Experiences unchanged
surviving/new Memory provenance complete
redundant Memories TOMBSTONED when applicable
normal retrieval excludes tombstoned Memories
Sleep Trace complete
```

A deterministic stub-model integration test must verify commit semantics regardless of live-model judgement.

A live-model run records whether Fred actually recognises the redundancy.

### 14.9 Evidence-Poisoning Acceptance Scenario

The harness supplies an Experience whose evidence does not justify a stronger proposed claim.

Example evidence:

```text
I used Rust once for Project X.
```

Potential unsupported Memory:

```text
The Operator prefers Rust for all projects.
```

The contract requires:

```text
if EvidenceValidation = UNSUPPORTED or CONTRADICTED
then the Memory cannot become ACTIVE
```

This rule is tested deterministically with a verifier stub.

A live-model verifier scenario is also recorded as behavioural evidence but is not the sole enforcement mechanism.

### 14.10 Concurrent-View Acceptance Scenario

A Memory is constructed with both strong procedural and relational characteristics.

A Retrieval Query requests:

```text
procedural
relational
```

concurrently.

The system must:

```text
execute both projections
return one candidate per record id
preserve both view ranks
preserve both matched-view labels
avoid duplicate context injection
emit one fused Retrieval Trace
```

This is a deterministic integration test.

## 15. MEM-01 Engineering Acceptance Criteria

MEM-01 is not complete until all deterministic criteria below pass.

### 15.1 Experience Integrity

```text
committed Experience cannot be semantically updated
committed Experience cannot be deleted through normal Memory APIs
Sleep cannot mutate Experience
Memory formation cannot mutate Experience
aborted/incomplete Experience is represented explicitly rather than rewritten
```

### 15.2 Provenance Integrity

```text
every ACTIVE Memory resolves to Experience evidence
invalid record references are rejected
invalid relation endpoint combinations are rejected
provenance cycles are rejected
supersession preserves historical Memory
tombstoning preserves historical graph identity
```

### 15.3 Model Authority Boundary

```text
free-form model output never executes persistence operations
invalid structured output never reaches persistence
Fred cannot directly issue SurrealQL
Fred cannot certify its own evidence
UNSUPPORTED or CONTRADICTED evidence cannot activate a Memory
```

### 15.4 Retrieval

```text
vector retrieval works
BM25 lexical retrieval works
structured/entity retrieval works
bounded graph expansion works
RRF fusion works
deduplication works
candidate budget is enforced
NO_MATCH is represented explicitly
tombstoned Memories are excluded from normal retrieval
```

### 15.5 Unified Memory Views

```text
episodic, semantic, procedural, and relational projections use the same substrate
two or more views can run concurrently
one record can match several views without duplication
view disagreement remains observable
```

### 15.6 Memory Sleep

```text
Sleep starts only from an eligible idle state
Sleep is interruptible before commit
Sleep commit is atomic
KEEP works
MERGE works
PROMOTE works
TOMBSTONE works
provenance survives merge/promotion
Sleep cannot rewrite Experience
```

### 15.7 Observer

```text
every retrieval produces a Retrieval Trace
every Memory proposal is observable
every evidence-validation result is observable
every Sleep burst is observable
rejected proposals remain inspectable
Observer is read-only with respect to cognitive state
```

### 15.8 Test Gate

Before live behavioural acceptance:

```text
pytest = 100% passing
schema/migration applies cleanly to an empty test database
all deterministic integration scenarios pass
```

Behavioural acceptance then requires the thresholds in Section 14.

## 16. MEM-01 Definition of Done

MEM-01 is complete only when a fresh checkout can perform the following sequence without manual database editing:

```text
1. start required local services
2. initialise the SurrealDB schema
3. verify Ollama model availability
4. run deterministic test suite
5. run all four behavioural experiments
6. produce machine-readable run artifacts
7. open the Observer and inspect the traces
8. restart Fred between continuity-dependent phases
9. demonstrate persistent recall from the Memory Complex
10. run at least one Memory Sleep consolidation
```

Required deliverables are:

```text
working Python package

SurrealDB migration/schema

Ollama cognitive-model adapter

Ollama embedding adapter

hybrid Retrieval Engine

Memory Engine

evidence validator

Memory Sleep engine

Observer

experiment runner

pytest suite

EXPERIMENTS.md

FAILURE_MAP.md

README run instructions
```

The implementation must run locally on the research workstation without requiring a paid external service for MEM-01.

## 17. Explicitly Out of Scope for MEM-01

The following are intentionally deferred:

```text
Temporal Guidance System beyond basic timestamps and sequence

hard deletion or degradation of Experience

separate archival/cold-memory tiers

physical subconscious database

autonomous skill execution derived from procedural Memory

self-modifying retrieval algorithms

continuous model-weight training

Developmental Fred full-weight training

distributed Brain services

production GUI polish

large-scale external web/document RAG

automatic model routing across providers

Digital Cerebellum

long-horizon autonomous goals

human-like consciousness claims
```

External knowledge provenance is architecturally supported, but external-RAG implementation is not required for MEM-01.

## 18. Architecture Freeze

This specification is the implementation contract for MEM-01.

Codex may make local implementation decisions that do not change the behavioural or epistemic contract.

Codex must not silently replace:

```text
SurrealDB with another persistence system
unified Memory with physically separate memory stores
immutable Experience with mutable historical records
hybrid retrieval with vector-only RAG
typed model proposals with free-form write authority
independent evidence validation with self-certification
Memory Sleep with unrelated pruning subsystems
```

If implementation evidence demonstrates that a frozen architectural choice is technically impossible or materially incorrect, the implementation should stop at that boundary, document the evidence, and propose the smallest necessary contract amendment rather than silently redesigning the system.
