from __future__ import annotations

import json
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fred.bootstrap import build_runtime, rebuild_cognitive_runtime, surreal_client
from fred.brain.memory.contracts import MemoryStatus, RecordTable
from fred.config import FredConfig
from fred.db.migrate import apply_schema
from fred.observer import MemoryObserver

_CHOICE_RE = re.compile(r"(?:^|\b)([ABC])(?:\b|$)", re.IGNORECASE)


@dataclass(slots=True)
class RunResult:
    experiment: str
    run_id: str
    database: str
    integrity: bool
    behavioural_success: bool
    metrics: dict[str, Any]
    result: dict[str, Any]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "UNKNOWN"


def _choice(text: str) -> str | None:
    matches = _CHOICE_RE.findall(text.upper())
    return matches[-1] if matches else None


class ArtifactWriter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=False)

    def write_json(self, name: str, payload: Any) -> None:
        (self.root / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    def write_jsonl(self, name: str, rows: list[dict[str, Any]]) -> None:
        with (self.root / name).open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


class ExperimentHarness:
    def __init__(
        self,
        config: FredConfig,
        *,
        artifact_root: Path | None = None,
    ) -> None:
        self.config = config
        self.artifact_root = artifact_root or (_repo_root() / "artifacts" / "memory_v1")

    def _run_config(self, experiment: str, run_id: str) -> FredConfig:
        token = experiment.lower().replace("-", "")
        return self.config.for_database(f"fred_mem01_{token}_{run_id[:12]}")

    async def _prepare(
        self, experiment: str, run_index: int
    ) -> tuple[str, FredConfig, Any, MemoryObserver, ArtifactWriter]:
        run_id = uuid.uuid4().hex
        config = self._run_config(experiment, run_id)
        await apply_schema(surreal_client(config))
        runtime, observer, _repositories = build_runtime(config)
        writer = ArtifactWriter(self.artifact_root / experiment.lower() / run_id)
        writer.write_json(
            "run.json",
            {
                "experiment": experiment,
                "run_index": run_index,
                "run_id": run_id,
                "database": config.surreal_database,
                "cognitive_model": config.cognitive_model,
                "embedding_model": config.embedding_model,
                "embedding_dimension": config.embedding_dim,
                "git_commit": _git_head(),
                "started_at": datetime.now(UTC).isoformat(),
                "transcript_reset_strategy": "fresh stateless Ollama wrapper before probe",
            },
        )
        return run_id, config, runtime, observer, writer

    async def _finalize(
        self,
        *,
        experiment: str,
        run_id: str,
        config: FredConfig,
        observer: MemoryObserver,
        writer: ArtifactWriter,
        integrity: bool,
        behavioural_success: bool,
        metrics: dict[str, Any],
        result: dict[str, Any],
    ) -> RunResult:
        snapshot = await observer.snapshot()
        traces = []
        for category in (
            "retrieval",
            "memory_proposals",
            "memory_validations",
            "sleep",
            "errors",
        ):
            traces.extend(snapshot[category])
        traces.sort(key=lambda row: row.get("occurred_at", ""))
        writer.write_jsonl("trace.jsonl", traces)
        writer.write_json("metrics.json", metrics)
        writer.write_json("result.json", result)
        return RunResult(
            experiment=experiment,
            run_id=run_id,
            database=config.surreal_database,
            integrity=integrity,
            behavioural_success=behavioural_success,
            metrics=metrics,
            result=result,
        )

    async def _observe_statement(self, runtime: Any, session_id: str, text: str) -> Any:
        active = await runtime.begin(session_id=session_id, input={"message": text})
        return await runtime.commit(
            active,
            perception={"text": text},
            decision={"kind": "observe"},
            action={"kind": "none"},
            outcome={"observed": True},
        )

    async def _observe_choice(
        self,
        runtime: Any,
        session_id: str,
        prompt: str,
        choice: str | None,
        success: bool,
    ) -> Any:
        active = await runtime.begin(session_id=session_id, input={"prompt": prompt})
        return await runtime.commit(
            active,
            perception={"prompt": prompt},
            decision={"choice": choice},
            action={"choice": choice},
            outcome={"completed": True},
            feedback={"label": "SUCCESS" if success else "FAILURE"},
        )

    async def _sleep_until_stable(self, runtime: Any, session_id: str, limit: int = 4) -> None:
        for _ in range(limit):
            before = [
                item
                for item in await runtime.repositories.memories.list_all()
                if item.status is MemoryStatus.PROVISIONAL
            ]
            if not before:
                return
            await runtime.sleep(session_id=session_id)
            after = [
                item
                for item in await runtime.repositories.memories.list_all()
                if item.status is MemoryStatus.PROVISIONAL
            ]
            if {str(item.ref) for item in before} == {str(item.ref) for item in after}:
                return

    @staticmethod
    def _memory_path_used(retrieval: Any) -> bool:
        return any(
            selection.ref.table is RecordTable.MEMORY
            for selection in retrieval.selections
            if selection.contextual_relevance > 0
        )

    async def run_exp01(self, run_index: int) -> RunResult:
        experiment = "EXP-01"
        run_id, config, runtime, observer, writer = await self._prepare(experiment, run_index)
        session_id = f"{run_id}-acquisition"
        await self._observe_statement(
            runtime, session_id, "The Kestrel project's marker is GLASS-472."
        )
        await self._sleep_until_stable(runtime, session_id)

        memories = await runtime.repositories.memories.list_all()
        experiences = await runtime.repositories.experiences.search()
        fresh_runtime = rebuild_cognitive_runtime(config, runtime.repositories)
        answer, retrieval = await fresh_runtime.reason(
            "What is the Kestrel project's marker?",
            session_id=f"{run_id}-probe",
        )
        active_memory = any(item.status is MemoryStatus.ACTIVE for item in memories)
        path_used = self._memory_path_used(retrieval)
        integrity = bool(experiences) and active_memory
        behavioural = "GLASS-472" in answer and path_used
        metrics = {
            "experience_count": len(experiences),
            "memory_count": len(memories),
            "active_memory": active_memory,
            "persistent_memory_path_used": path_used,
            "transcript_reset": True,
        }
        result = {"answer": answer, "expected": "GLASS-472", "accepted": behavioural}
        return await self._finalize(
            experiment=experiment,
            run_id=run_id,
            config=config,
            observer=observer,
            writer=writer,
            integrity=integrity,
            behavioural_success=behavioural,
            metrics=metrics,
            result=result,
        )

    async def run_exp02(self, run_index: int) -> RunResult:
        experiment = "EXP-02"
        run_id, config, runtime, observer, writer = await self._prepare(experiment, run_index)
        session_id = f"{run_id}-acquisition"
        await self._observe_statement(
            runtime, session_id, "The Kestrel project's marker is GLASS-472."
        )
        await self._sleep_until_stable(runtime, session_id)
        await self._observe_statement(
            runtime,
            session_id,
            "Correction: the Kestrel project's marker is now AMBER-913.",
        )
        await self._sleep_until_stable(runtime, session_id)

        fresh_runtime = rebuild_cognitive_runtime(config, runtime.repositories)
        current, current_retrieval = await fresh_runtime.reason(
            "What is Kestrel's current marker?", session_id=f"{run_id}-probe-current"
        )
        previous, previous_retrieval = await fresh_runtime.reason(
            "What marker did Kestrel use previously?", session_id=f"{run_id}-probe-previous"
        )
        experiences = await runtime.repositories.experiences.search()
        relations = await runtime.repositories.relations.list_all()
        has_supersession = any(item.kind.value == "SUPERSEDES" for item in relations)
        path_used = self._memory_path_used(current_retrieval) and self._memory_path_used(
            previous_retrieval
        )
        integrity = len(experiences) >= 2 and has_supersession
        behavioural = "AMBER-913" in current and "GLASS-472" in previous and path_used
        metrics = {
            "experience_count": len(experiences),
            "supersession_lineage": has_supersession,
            "persistent_memory_path_used": path_used,
            "transcript_reset": True,
        }
        result = {
            "current_answer": current,
            "previous_answer": previous,
            "expected_current": "AMBER-913",
            "expected_previous": "GLASS-472",
            "accepted": behavioural,
        }
        return await self._finalize(
            experiment=experiment,
            run_id=run_id,
            config=config,
            observer=observer,
            writer=writer,
            integrity=integrity,
            behavioural_success=behavioural,
            metrics=metrics,
            result=result,
        )

    async def run_exp03(self, run_index: int) -> RunResult:
        experiment = "EXP-03"
        run_id, config, runtime, observer, writer = await self._prepare(experiment, run_index)
        session_id = f"{run_id}-training"
        hidden_mapping = {"X": "B", "Y": "C", "Z": "A"}
        training_types = ["X", "Y", "Z"] * 4

        training_rows: list[dict[str, Any]] = []
        for index, case_type in enumerate(training_types, start=1):
            prompt = (
                f"Synthetic training case {index} has type {case_type}. "
                "Choose exactly one action: A, B, or C."
            )
            answer, _retrieval = await runtime.reason(prompt, session_id=session_id)
            selected = _choice(answer)
            success = selected == hidden_mapping[case_type]
            await self._observe_choice(runtime, session_id, prompt, selected, success)
            training_rows.append(
                {
                    "case_type": case_type,
                    "choice": selected,
                    "feedback": "SUCCESS" if success else "FAILURE",
                }
            )
            if index % 3 == 0:
                await self._sleep_until_stable(runtime, session_id, limit=2)

        await self._sleep_until_stable(runtime, session_id)
        fresh_runtime = rebuild_cognitive_runtime(config, runtime.repositories)
        probe_types = ["X", "Y", "Z"] * 3
        correct = 0
        path_used = False
        probe_rows: list[dict[str, Any]] = []
        for index, case_type in enumerate(probe_types, start=1):
            prompt = (
                f"New synthetic probe case {index} has type {case_type}. "
                "Choose exactly one action: A, B, or C."
            )
            answer, retrieval = await fresh_runtime.reason(
                prompt, session_id=f"{run_id}-probe"
            )
            selected = _choice(answer)
            is_correct = selected == hidden_mapping[case_type]
            correct += int(is_correct)
            path_used = path_used or (is_correct and self._memory_path_used(retrieval))
            probe_rows.append(
                {"case_type": case_type, "choice": selected, "correct": is_correct}
            )

        states = await runtime.repositories.state.list_all()
        integrity = len(await runtime.repositories.experiences.search()) >= 12 and not states
        behavioural = correct >= 7 and path_used
        metrics = {
            "training_episodes": 12,
            "probe_accuracy": correct / 9,
            "probe_correct": correct,
            "persistent_memory_path_used": path_used,
            "state_empty": not states,
            "transcript_reset": True,
        }
        result = {
            "training": training_rows,
            "probes": probe_rows,
            "accepted": behavioural,
            "hidden_mapping_disclosed_to_model": False,
        }
        return await self._finalize(
            experiment=experiment,
            run_id=run_id,
            config=config,
            observer=observer,
            writer=writer,
            integrity=integrity,
            behavioural_success=behavioural,
            metrics=metrics,
            result=result,
        )

    async def run_exp04(self, run_index: int) -> RunResult:
        experiment = "EXP-04"
        run_id, config, runtime, observer, writer = await self._prepare(experiment, run_index)
        session_id = f"{run_id}-training"
        training = [
            ("Velin", True, True),
            ("Tarok", True, False),
            ("Nomel", False, True),
            ("Brek", False, False),
            ("Lerin", True, True),
            ("Sovan", False, True),
            ("Karel", True, False),
            ("Dovik", True, True),
        ]
        training_rows: list[dict[str, Any]] = []
        for index, (entity, p_value, r_value) in enumerate(training, start=1):
            prompt = (
                f"Synthetic entity {entity} has P={str(p_value).lower()} and "
                f"R={str(r_value).lower()}. Choose exactly one action: A, B, or C."
            )
            answer, _retrieval = await runtime.reason(prompt, session_id=session_id)
            selected = _choice(answer)
            success = selected == "C" if (p_value and r_value) else selected in {"A", "B"}
            await self._observe_choice(runtime, session_id, prompt, selected, success)
            training_rows.append(
                {
                    "entity": entity,
                    "p": p_value,
                    "r": r_value,
                    "choice": selected,
                    "feedback": "SUCCESS" if success else "FAILURE",
                }
            )
            if index % 2 == 0:
                await self._sleep_until_stable(runtime, session_id, limit=2)

        await self._sleep_until_stable(runtime, session_id)
        fresh_runtime = rebuild_cognitive_runtime(config, runtime.repositories)
        probes = [
            ("Aven", True, True),
            ("Mirok", True, False),
            ("Selun", False, True),
            ("Parek", False, False),
            ("Tovin", True, True),
            ("Neral", True, False),
        ]
        correct = 0
        abstraction_path_used = False
        probe_rows: list[dict[str, Any]] = []
        for entity, p_value, r_value in probes:
            prompt = (
                f"Unseen synthetic entity {entity} has P={str(p_value).lower()} and "
                f"R={str(r_value).lower()}. Choose exactly one action: A, B, or C."
            )
            answer, retrieval = await fresh_runtime.reason(
                prompt, session_id=f"{run_id}-probe"
            )
            selected = _choice(answer)
            is_correct = selected == "C" if (p_value and r_value) else selected in {"A", "B"}
            correct += int(is_correct)
            abstraction_path_used = abstraction_path_used or (
                is_correct and self._memory_path_used(retrieval)
            )
            probe_rows.append(
                {
                    "entity": entity,
                    "p": p_value,
                    "r": r_value,
                    "choice": selected,
                    "correct": is_correct,
                }
            )

        memories = await runtime.repositories.memories.list_all()
        higher_order = any(
            item.status is MemoryStatus.ACTIVE
            and (
                item.metadata.get("sleep_operation") == "PROMOTE"
                or item.abstraction >= 0.7
            )
            for item in memories
        )
        provenance_resolves = False
        for memory in memories:
            if memory.status is not MemoryStatus.ACTIVE:
                continue
            refs = memory.provenance.get("evidence_refs", [])
            if any(str(ref).startswith("experience:") for ref in refs):
                provenance_resolves = True
                break

        integrity = higher_order and provenance_resolves
        behavioural = correct >= 4 and abstraction_path_used and higher_order
        metrics = {
            "training_episodes": len(training),
            "probe_accuracy": correct / len(probes),
            "probe_correct": correct,
            "higher_order_memory": higher_order,
            "provenance_resolves_to_experience": provenance_resolves,
            "persistent_abstraction_path_used": abstraction_path_used,
            "transcript_reset": True,
        }
        result = {
            "training": training_rows,
            "probes": probe_rows,
            "accepted": behavioural,
            "hidden_rule_disclosed_to_model": False,
        }
        return await self._finalize(
            experiment=experiment,
            run_id=run_id,
            config=config,
            observer=observer,
            writer=writer,
            integrity=integrity,
            behavioural_success=behavioural,
            metrics=metrics,
            result=result,
        )

    async def run(self, experiment: str, *, runs: int = 5) -> dict[str, Any]:
        dispatch = {
            "EXP-01": self.run_exp01,
            "EXP-02": self.run_exp02,
            "EXP-03": self.run_exp03,
            "EXP-04": self.run_exp04,
        }
        normalized = experiment.upper()
        if normalized not in dispatch:
            raise ValueError(f"unknown experiment: {experiment}")
        results = [await dispatch[normalized](index) for index in range(1, runs + 1)]
        integrity_count = sum(item.integrity for item in results)
        behavioural_count = sum(item.behavioural_success for item in results)
        accepted = integrity_count == runs and behavioural_count >= max(1, runs - 1)
        return {
            "experiment": normalized,
            "runs": runs,
            "integrity_successes": integrity_count,
            "behavioural_successes": behavioural_count,
            "accepted": accepted,
            "results": [
                {
                    "run_id": item.run_id,
                    "database": item.database,
                    "integrity": item.integrity,
                    "behavioural_success": item.behavioural_success,
                    "metrics": item.metrics,
                }
                for item in results
            ],
        }

    async def run_all(self, *, runs: int = 5) -> dict[str, Any]:
        results = {}
        for experiment in ("EXP-01", "EXP-02", "EXP-03", "EXP-04"):
            results[experiment] = await self.run(experiment, runs=runs)
        return {
            "runs_per_experiment": runs,
            "accepted": all(item["accepted"] for item in results.values()),
            "experiments": results,
        }
