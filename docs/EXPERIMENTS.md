# Fred MEM-01 Experiments

**Status:** FROZEN
**Milestone:** MEM-01
**Purpose:** Executable behavioural acceptance contract for the Memory Complex.

## General Harness Rules

Every run uses isolated persistent state.

A continuity claim is invalid unless the active model transcript containing the learned information has been destroyed before the probe.

The harness records model identity, embedding identity, configuration, run ID, database identity, traces, and final result.

The first acceptance cycle uses five independent runs per behavioural experiment, low model temperature, and a fixed seed where supported.

Synthetic names and arbitrary values are used deliberately to minimise contamination from pretrained knowledge.

A correct answer without the intended Memory pathway in the trace is not accepted as a Memory success.

## EXP-01 — Continuity

### Acquisition

```text
The Kestrel project's marker is GLASS-472.
```

Required acquisition state:

```text
Experience committed
Memory proposed
evidence validated
Memory ACTIVE after Sleep
```

Destroy the model session.

### Probe

```text
What is the Kestrel project's marker?
```

### Pass

System integrity: 5/5.

Behaviour + intended persistent Memory pathway: >=4/5.

Expected answer:

```text
GLASS-472
```

## EXP-02 — Correction and Supersession

### Episode A

```text
The Kestrel project's marker is GLASS-472.
```

### Episode B

```text
Correction: the Kestrel project's marker is now AMBER-913.
```

Destroy the model session.

### Probe A

```text
What is Kestrel's current marker?
```

Expected:

```text
AMBER-913
```

### Probe B

```text
What marker did Kestrel use previously?
```

Expected:

```text
GLASS-472
```

### Pass

Integrity: 5/5 runs preserve both Experiences and valid supersession lineage.

Behaviour + intended Memory pathway: both probes correct in >=4/5 runs.

## EXP-03 — Repeated Experience Learning

Harness-only hidden mapping:

```text
X -> B
Y -> C
Z -> A
```

Fred receives 12 training episodes across X/Y/Z.

For each episode Fred chooses one of:

```text
A
B
C
```

Harness returns only:

```text
SUCCESS
FAILURE
```

Run Sleep opportunistically.

Destroy the model session.

Probe with nine new synthetic instances:

```text
3 X
3 Y
3 Z
```

### Pass

>=4/5 runs satisfy:

```text
probe accuracy >= 7/9
at least one probe decision uses persistent prior Experience or Memory
hidden mapping never appears in prompt, State, or external context
```

## EXP-04 — Abstraction and Generalisation

Harness-only hidden rule:

```text
P=true AND R=true -> C
```

Use synthetic training entities such as:

```text
Velin
Tarok
Nomel
Brek
```

with several P/R combinations and outcome feedback.

Allow Sleep to consolidate/promote.

Destroy the model session.

Probe six unseen entity names.

### Pass

>=4/5 runs satisfy:

```text
at least one higher-order Memory is created or promoted
provenance resolves to training Experiences
novel-probe accuracy >= 4/6
at least one correct novel decision retrieves/selects the abstraction
```

## INT-01 — Sleep Consolidation

Create several semantically redundant PROVISIONAL Memories with overlapping evidence.

Trigger Sleep.

Deterministic stub-model test verifies:

```text
MERGE/PROMOTE commit semantics
Experience unchanged
provenance complete
redundant Memories tombstoned where applicable
normal retrieval excludes tombstoned Memories
Sleep Trace complete
```

Live model run records whether Fred recognises the redundancy.

## INT-02 — Evidence Poisoning

Evidence:

```text
I used Rust once for Project X.
```

Unsupported claim:

```text
The Operator prefers Rust for all projects.
```

Deterministic verifier result:

```text
UNSUPPORTED
```

must prevent Memory activation.

The live verifier scenario is recorded separately.

## INT-03 — Concurrent Memory Views

Construct one Memory with strong procedural and relational characteristics.

Request both views concurrently.

Pass requires:

```text
one candidate per record id
both matched-view labels preserved
per-view ranks preserved
no duplicate context injection
one fused Retrieval Trace
```

## Required Run Artifacts

Each experiment run writes:

```text
run.json
trace.jsonl
metrics.json
result.json
```

where practical.

The run artifact must identify the exact database, model, embedding model, configuration, and git commit used.
