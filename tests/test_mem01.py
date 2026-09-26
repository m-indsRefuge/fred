from __future__ import annotations

import asyncio
import copy
from pathlib import Path
from typing import Any

import pytest

from fred.bootstrap import rebuild_cognitive_runtime
from fred.brain.memory.contracts import (
    CognitiveRole,
    EvidenceValidation,
    EvidenceVerdict,
    ExperienceRecord,
    MemoryOperation,
    MemoryProposal,
    MemoryStatus,
    RecordRef,
    RecordTable,
    RelationKind,
    SleepDecision,
    SleepOperation,
)
from fred.brain.memory.evidence import ProvenanceError, resolve_experience_provenance
from fred.brain.memory.repositories import Repositories
from fred.brain.memory.sleep import SleepEngine
from fred.brain.memory.validators import (
    evidence_allows_activation,
    validate_relation_endpoints,
)
from fred.brain.retrieval.contracts import CognitiveSelection, RetrievalQuery, RetrievalStatus
from fred.brain.retrieval.engine import RetrievalEngine
from fred.brain.retrieval.fusion import reciprocal_rank_fusion
from fred.brain.retrieval.views import run_views
from fred.brain.runtime.experience import ExperienceService
from fred.config import FredConfig
from fred.db.backends import InMemoryBackend
from fred.db.migrate import apply_schema
from fred.experiments.memory_v1.harness import ExperimentHarness
from fred.observer.service import MemoryObserver


def arun(coro):
    return asyncio.run(coro)


class FakeEmbedding:
    identity = "fake-embedding-v1"
    dimension = 3

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    async def embed_document(self, text: str) -> list[float]:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.lower()
        if "alpha" in lowered or "rust" in lowered:
            return [1.0, 0.0, 0.0]
        if "beta" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


class FakeCognitive:
    identity = "fake-cognitive-v1"

    def __init__(
        self,
        *,
        proposal: MemoryProposal | None = None,
        verdict: EvidenceVerdict = EvidenceVerdict.SUPPORTED,
        sleep_decision: SleepDecision | None = None,
    ) -> None:
        self.proposal = proposal
        self.verdict = verdict
        self.sleep_decision = sleep_decision

    async def adjudicate_retrieval(
        self, query: str, candidates: list[dict[str, Any]]
    ) -> list[CognitiveSelection]:
        return [
            CognitiveSelection(
                ref=RecordRef.model_validate(item["ref"]),
                role=CognitiveRole.RELEVANT,
                contextual_relevance=1.0,
                model_explanation="deterministic test selection",
            )
            for item in candidates
        ]

    async def propose_memory(self, context: dict[str, Any]) -> MemoryProposal:
        if self.proposal is None:
            return MemoryProposal(
                operation=MemoryOperation.NO_CHANGE,
                evidence_refs=[],
                evidential_support=0.0,
                interpretive_confidence=0.0,
                salience_prior=0.0,
                episodicity=0.0,
                abstraction=0.0,
                procedurality=0.0,
                relationality=0.0,
                model_explanation="no change",
            )
        return self.proposal

    async def validate_evidence(self, context: dict[str, Any]) -> EvidenceValidation:
        proposal_ref = RecordRef.model_validate(context["proposal_ref"])
        refs = [RecordRef.model_validate(item["ref"]) for item in context.get("evidence", [])]
        supported = (
            refs
            if self.verdict in {EvidenceVerdict.SUPPORTED, EvidenceVerdict.PARTIAL}
            else []
        )
        unsupported = refs if self.verdict is EvidenceVerdict.UNSUPPORTED else []
        contradictory = refs if self.verdict is EvidenceVerdict.CONTRADICTED else []
        return EvidenceValidation(
            proposal_ref=proposal_ref,
            verdict=self.verdict,
            supported_refs=supported,
            unsupported_refs=unsupported,
            contradictory_refs=contradictory,
            verifier=self.identity,
            explanation="deterministic verifier",
        )

    async def adjudicate_sleep(self, context: dict[str, Any]) -> SleepDecision:
        if self.sleep_decision is None:
            source = RecordRef.model_validate(context["memories"][0]["ref"])
            return SleepDecision(
                operation=SleepOperation.KEEP,
                source_memory_refs=[source],
                evidence_refs=[],
                model_explanation="keep",
            )
        return self.sleep_decision

    async def reason(self, prompt: str, selected_evidence: list[dict[str, Any]]) -> str:
        return "ok"


def proposal(
    content: str,
    evidence_refs: list[RecordRef],
    *,
    operation: MemoryOperation = MemoryOperation.CREATE,
    target: RecordRef | None = None,
    episodicity: float = 0.4,
    abstraction: float = 0.6,
    procedurality: float = 0.2,
    relationality: float = 0.2,
) -> MemoryProposal:
    return MemoryProposal(
        operation=operation,
        proposed_content=content,
        target_memory_ref=target,
        evidence_refs=evidence_refs,
        evidential_support=0.9,
        interpretive_confidence=0.8,
        salience_prior=0.7,
        episodicity=episodicity,
        abstraction=abstraction,
        procedurality=procedurality,
        relationality=relationality,
        model_explanation="test proposal",
    )


async def committed_experience(
    repositories: Repositories,
    *,
    session_id: str = "session",
    text: str = "alpha evidence",
) -> ExperienceRecord:
    service = ExperienceService(repositories, FakeEmbedding())
    active = await service.begin(
        session_id=session_id,
        turn_id="turn-1",
        input={"message": text},
        context={"source": "operator"},
    )
    return await service.commit(
        active,
        perception={"text": text},
        decision={"kind": "observe"},
        action={"kind": "none"},
        outcome={"observed": True},
    )


async def stored_memory(
    repositories: Repositories,
    evidence: RecordRef,
    *,
    content: str = "alpha memory",
    status: MemoryStatus = MemoryStatus.PROVISIONAL,
    procedurality: float = 0.2,
    relationality: float = 0.2,
) -> RecordRef:
    created = await repositories.memories.create_provisional(
        proposal(
            content,
            [evidence],
            procedurality=procedurality,
            relationality=relationality,
        ),
        embedding=FakeEmbedding._vector(content),
        embedding_model=FakeEmbedding.identity,
        embedding_version=FakeEmbedding.identity,
    )
    await repositories.relations.create_validated(
        in_ref=created.ref,
        out_ref=evidence,
        kind=RelationKind.DERIVED_FROM,
        source="test",
    )
    validation = EvidenceValidation(
        proposal_ref=created.ref,
        verdict=EvidenceVerdict.SUPPORTED,
        supported_refs=[evidence],
        verifier="test",
        explanation="supported",
    )
    created = await repositories.memories.record_validation(created.ref, validation)
    if status is MemoryStatus.ACTIVE:
        created = await repositories.memories.activate(created.ref, validation)
    elif status is MemoryStatus.TOMBSTONED:
        created = await repositories.memories.tombstone(created.ref, "test")
    return created.ref


def test_schema_application_reads_and_submits_entire_schema(tmp_path: Path) -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def query(self, source: str) -> None:
            self.queries.append(source)

    schema = tmp_path / "schema.surql"
    schema.write_text(
        "DEFINE TABLE OVERWRITE experience SCHEMAFULL;\n"
        "DEFINE INDEX OVERWRITE experience_embedding_hnsw "
        "ON TABLE experience FIELDS embedding HNSW DIMENSION 1024 DIST COSINE TYPE F32;\n",
        encoding="utf-8",
    )
    client = FakeClient()
    arun(apply_schema(client, schema))
    assert client.queries == [schema.read_text(encoding="utf-8")]


def test_repository_schema_declares_experience_readonly_and_hnsw() -> None:
    source = Path("db/FRED_SURREALDB_V1.surql").read_text(encoding="utf-8")
    assert "EXPERIENCE: immutable historical evidence" in source
    assert "DEFINE FIELD input ON TABLE experience TYPE object FLEXIBLE READONLY;" in source
    assert "experience_embedding_hnsw" in source
    assert "HNSW DIMENSION 1024 DIST COSINE" in source


def test_journal_to_experience_commit_and_duplicate_immutability() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        experience = await committed_experience(repos)
        events = await repos.journal.query("session")
        assert [event.event_type for event in events] == [
            "EXPERIENCE_STARTED",
            "EXPERIENCE_COMMITTED",
        ]
        assert experience.sequence_start == 1
        assert experience.sequence_end == 2
        assert "alpha evidence" in experience.search_text
        with pytest.raises(ValueError, match="already exists"):
            await repos.experiences.create(experience)

    arun(scenario())


def test_memory_proposal_parses_record_refs() -> None:
    item = MemoryProposal.model_validate(
        {
            "operation": "CREATE",
            "proposed_content": "remember",
            "evidence_refs": ["experience:e1"],
            "evidential_support": 0.9,
            "interpretive_confidence": 0.8,
            "salience_prior": 0.5,
            "episodicity": 0.4,
            "abstraction": 0.6,
            "procedurality": 0.1,
            "relationality": 0.2,
            "model_explanation": "parsed",
        }
    )
    assert str(item.evidence_refs[0]) == "experience:e1"


def test_relation_endpoint_validation_rejects_illegal_pair() -> None:
    with pytest.raises(ValueError, match="illegal"):
        validate_relation_endpoints(
            RelationKind.DERIVED_FROM,
            RecordRef(table=RecordTable.EXPERIENCE, key="e1"),
            RecordRef(table=RecordTable.MEMORY, key="m1"),
        )


def test_provenance_resolution_and_cycle_rejection() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        experience = await committed_experience(repos)
        m1 = await stored_memory(repos, experience.ref)
        m2 = await stored_memory(repos, m1)
        relations = await repos.relations.list_all()
        resolved = await resolve_experience_provenance(
            m2,
            memory_get=repos.memories.get,
            experience_get=repos.experiences.get,
            relations=relations,
        )
        assert resolved == {experience.ref}
        with pytest.raises(ValueError, match="cycle"):
            await repos.relations.create_validated(
                in_ref=m1,
                out_ref=m2,
                kind=RelationKind.DERIVED_FROM,
                source="cycle-test",
            )

    arun(scenario())


def test_provenance_resolution_rejects_missing_lineage() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        experience = await committed_experience(repos)
        orphan = await repos.memories.create_provisional(
            proposal("orphan", [experience.ref]),
            embedding=[1.0, 0.0, 0.0],
            embedding_model="fake",
            embedding_version="fake",
        )
        with pytest.raises(ProvenanceError, match="no Experience-resolving provenance"):
            await resolve_experience_provenance(
                orphan.ref,
                memory_get=repos.memories.get,
                experience_get=repos.experiences.get,
                relations=[],
            )

    arun(scenario())


def test_evidence_verdict_gates_activation() -> None:
    supported = EvidenceValidation(
        proposal_ref=RecordRef(table=RecordTable.MEMORY, key="m1"),
        verdict=EvidenceVerdict.SUPPORTED,
        verifier="v",
        explanation="ok",
    )
    unsupported = supported.model_copy(update={"verdict": EvidenceVerdict.UNSUPPORTED})
    assert evidence_allows_activation(supported)
    assert not evidence_allows_activation(unsupported)


def test_int02_unsupported_evidence_poisoning_stays_provisional() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        experience = await committed_experience(repos, text="I used Rust once for Project X.")
        item = await repos.memories.create_provisional(
            proposal("The Operator prefers Rust for all projects.", [experience.ref]),
            embedding=[1.0, 0.0, 0.0],
            embedding_model="fake",
            embedding_version="fake",
        )
        validation = EvidenceValidation(
            proposal_ref=item.ref,
            verdict=EvidenceVerdict.UNSUPPORTED,
            unsupported_refs=[experience.ref],
            verifier="independent-verifier",
            explanation="claim exceeds evidence",
        )
        await repos.memories.record_validation(item.ref, validation)
        with pytest.raises(ValueError, match="cannot activate"):
            await repos.memories.activate(item.ref, validation)
        assert (await repos.memories.get(item.ref)).status is MemoryStatus.PROVISIONAL

    arun(scenario())


def test_vector_bm25_structured_and_tombstone_exclusion() -> None:
    async def scenario() -> None:
        backend = InMemoryBackend()
        repos = Repositories.create(backend)
        experience = await committed_experience(repos, text="alpha project evidence")
        entity = await repos.entities.create_if_absent(
            kind="project", canonical_key="alpha-project", name="Alpha"
        )
        active = await stored_memory(
            repos,
            experience.ref,
            content="alpha procedure",
            status=MemoryStatus.ACTIVE,
        )
        await backend.update(active, {"metadata": {"entity_refs": [str(entity.ref)]}})
        tomb = await stored_memory(
            repos,
            experience.ref,
            content="alpha obsolete",
            status=MemoryStatus.TOMBSTONED,
        )

        vector = await backend.vector_search([1.0, 0.0, 0.0], {"MEMORY"}, 10)
        lexical = await backend.lexical_search("alpha procedure", {"MEMORY"}, 10)
        structured = await backend.structured_search([entity.ref], {"MEMORY"}, 10)
        assert active in vector and tomb not in vector
        assert active in lexical and tomb not in lexical
        assert structured == [active]

    arun(scenario())


def test_bounded_graph_expansion_excludes_tombstoned() -> None:
    async def scenario() -> None:
        backend = InMemoryBackend()
        repos = Repositories.create(backend)
        exp = await committed_experience(repos)
        m1 = await stored_memory(repos, exp.ref, status=MemoryStatus.ACTIVE)
        m2 = await stored_memory(repos, m1, status=MemoryStatus.ACTIVE)
        m3 = await stored_memory(repos, m2, status=MemoryStatus.TOMBSTONED)
        hits = await backend.graph_expand([exp.ref], {"MEMORY"}, 10, max_depth=2)
        assert m1 in hits
        assert m2 in hits
        assert m3 not in hits

    arun(scenario())


def test_rrf_fuses_and_deduplicates_candidates() -> None:
    ref = RecordRef(table=RecordTable.MEMORY, key="m1")
    other = RecordRef(table=RecordTable.EXPERIENCE, key="e1")
    fused = reciprocal_rank_fusion(
        {"vector": [ref, other], "lexical": [ref]},
        view_rankings={"procedural": [ref]},
    )
    assert [item.ref for item in fused].count(ref) == 1
    candidate = next(item for item in fused if item.ref == ref)
    assert candidate.discovered_by == {"vector", "lexical"}
    assert candidate.matched_views == {"procedural"}
    assert candidate.vector_rank == 1
    assert candidate.lexical_rank == 1
    assert candidate.view_ranks["procedural"] == 1


def test_int03_concurrent_views_preserve_both_labels_and_one_candidate() -> None:
    async def scenario() -> None:
        backend = InMemoryBackend()
        repos = Repositories.create(backend)
        exp = await committed_experience(repos)
        ref = await stored_memory(
            repos,
            exp.ref,
            status=MemoryStatus.ACTIVE,
            procedurality=0.95,
            relationality=0.9,
        )
        views = await run_views(backend, {"procedural", "relational"}, 10)
        fused = reciprocal_rank_fusion({}, view_rankings=views)
        assert len([item for item in fused if item.ref == ref]) == 1
        item = next(item for item in fused if item.ref == ref)
        assert item.matched_views == {"procedural", "relational"}
        assert set(item.view_ranks) == {"procedural", "relational"}

    arun(scenario())


def test_retrieval_no_match_is_explicit_and_traced() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        engine = RetrievalEngine(repos, FakeEmbedding(), FakeCognitive())
        result = await engine.retrieve(
            RetrievalQuery(query_id="q1", semantic_query="nothing here"),
            session_id="s1",
        )
        assert result.status is RetrievalStatus.NO_MATCH
        traces = await repos.traces.query("s1")
        assert len(traces) == 1
        assert traces[0].payload["status"] == "NO_MATCH"

    arun(scenario())


def test_retrieval_engine_emits_single_fused_trace_for_concurrent_views() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        exp = await committed_experience(repos)
        await stored_memory(
            repos,
            exp.ref,
            status=MemoryStatus.ACTIVE,
            procedurality=0.95,
            relationality=0.95,
        )
        engine = RetrievalEngine(repos, FakeEmbedding(), FakeCognitive())
        result = await engine.retrieve(
            RetrievalQuery(
                query_id="q2",
                semantic_query="alpha",
                views={"procedural", "relational"},
            ),
            session_id="s2",
        )
        assert result.status is RetrievalStatus.READY
        assert len({str(item.ref) for item in result.candidates}) == len(result.candidates)
        assert len(await repos.traces.query("s2")) == 1

    arun(scenario())


def test_sleep_keep_promotes_validated_provisional_to_active() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        exp = await committed_experience(repos)
        ref = await stored_memory(repos, exp.ref)
        decision = SleepDecision(
            operation=SleepOperation.KEEP,
            source_memory_refs=[ref],
            evidence_refs=[exp.ref],
            model_explanation="keep supported memory",
        )
        result = await SleepEngine(
            repos,
            FakeEmbedding(),
            FakeCognitive(sleep_decision=decision),
        ).run_once(session_id="sleep-keep")
        assert result.committed
        assert (await repos.memories.get(ref)).status is MemoryStatus.ACTIVE

    arun(scenario())


def test_sleep_tombstone_does_not_mutate_experience() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        exp = await committed_experience(repos)
        before = copy.deepcopy(await repos.backend.get(exp.ref))
        ref = await stored_memory(repos, exp.ref)
        decision = SleepDecision(
            operation=SleepOperation.TOMBSTONE,
            source_memory_refs=[ref],
            evidence_refs=[exp.ref],
            model_explanation="obsolete",
        )
        result = await SleepEngine(
            repos,
            FakeEmbedding(),
            FakeCognitive(sleep_decision=decision),
        ).run_once(session_id="sleep-tombstone")
        assert result.tombstoned == [ref]
        assert (await repos.memories.get(ref)).status is MemoryStatus.TOMBSTONED
        assert await repos.backend.get(exp.ref) == before

    arun(scenario())


def test_int01_sleep_merge_is_atomic_preserves_provenance_and_hides_sources() -> None:
    async def scenario() -> None:
        backend = InMemoryBackend()
        repos = Repositories.create(backend)
        exp = await committed_experience(repos)
        before_exp = copy.deepcopy(await backend.get(exp.ref))
        left = await stored_memory(repos, exp.ref, content="alpha rule one")
        right = await stored_memory(repos, exp.ref, content="alpha rule two")
        merged_proposal = proposal("alpha consolidated rule", [exp.ref])
        decision = SleepDecision(
            operation=SleepOperation.MERGE,
            source_memory_refs=[left, right],
            proposed_memory=merged_proposal,
            evidence_refs=[exp.ref],
            model_explanation="merge redundant memories",
        )
        result = await SleepEngine(
            repos,
            FakeEmbedding(),
            FakeCognitive(
                sleep_decision=decision,
                verdict=EvidenceVerdict.SUPPORTED,
            ),
        ).run_once(session_id="sleep-merge")
        assert result.committed
        assert len(result.created) == 1
        merged = await repos.memories.get(result.created[0])
        assert merged is not None and merged.status is MemoryStatus.ACTIVE
        assert str(exp.ref) in merged.provenance["evidence_refs"]
        assert str(left) in merged.provenance["evidence_refs"]
        assert str(right) in merged.provenance["evidence_refs"]
        assert (await repos.memories.get(left)).status is MemoryStatus.TOMBSTONED
        assert (await repos.memories.get(right)).status is MemoryStatus.TOMBSTONED
        assert await backend.get(exp.ref) == before_exp
        lexical = await backend.lexical_search("alpha rule", {"MEMORY"}, 10)
        assert left not in lexical and right not in lexical
        traces = await repos.traces.query("sleep-merge")
        assert traces[-1].payload["committed"] is True
        assert traces[-1].payload["memories_merged"] == [str(left), str(right)]

    arun(scenario())


def test_sleep_promote_creates_active_memory_without_tombstoning_source() -> None:
    async def scenario() -> None:
        repos = Repositories.create(InMemoryBackend())
        exp = await committed_experience(repos)
        source = await stored_memory(repos, exp.ref)
        promoted = proposal("general alpha principle", [exp.ref], abstraction=0.95)
        decision = SleepDecision(
            operation=SleepOperation.PROMOTE,
            source_memory_refs=[source],
            proposed_memory=promoted,
            evidence_refs=[exp.ref],
            model_explanation="promote abstraction",
        )
        result = await SleepEngine(
            repos,
            FakeEmbedding(),
            FakeCognitive(sleep_decision=decision),
        ).run_once(session_id="sleep-promote")
        assert result.committed and len(result.created) == 1
        assert (await repos.memories.get(result.created[0])).status is MemoryStatus.ACTIVE
        assert (await repos.memories.get(source)).status is MemoryStatus.PROVISIONAL

    arun(scenario())


def test_sleep_interruption_makes_no_mutation_and_backend_atomic_rolls_back() -> None:
    async def scenario() -> None:
        backend = InMemoryBackend()
        repos = Repositories.create(backend)
        exp = await committed_experience(repos)
        ref = await stored_memory(repos, exp.ref)
        decision = SleepDecision(
            operation=SleepOperation.TOMBSTONE,
            source_memory_refs=[ref],
            evidence_refs=[exp.ref],
            model_explanation="would tombstone",
        )
        result = await SleepEngine(
            repos,
            FakeEmbedding(),
            FakeCognitive(sleep_decision=decision),
        ).run_once(session_id="interrupt", interrupt_before_commit=True)
        assert result.interrupted and not result.committed
        assert (await repos.memories.get(ref)).status is MemoryStatus.PROVISIONAL

        with pytest.raises(RuntimeError):
            async with backend.atomic():
                await backend.update(ref, {"status": MemoryStatus.TOMBSTONED})
                raise RuntimeError("rollback")
        assert (await repos.memories.get(ref)).status is MemoryStatus.PROVISIONAL

    arun(scenario())


def test_observer_snapshot_is_read_only() -> None:
    async def scenario() -> None:
        backend = InMemoryBackend()
        repos = Repositories.create(backend)
        exp = await committed_experience(repos)
        await stored_memory(repos, exp.ref, status=MemoryStatus.ACTIVE)
        before = copy.deepcopy(backend._tables)
        snapshot = await MemoryObserver(repos).snapshot()
        assert snapshot["experience"]
        assert snapshot["memory"]["ACTIVE"]
        assert backend._tables == before

    arun(scenario())


def test_cross_run_database_isolation_and_context_reset_runtime() -> None:
    config = FredConfig()
    harness = ExperimentHarness(config)
    first = harness._run_config("EXP-01", "a" * 32)
    second = harness._run_config("EXP-01", "b" * 32)
    assert first.surreal_database != second.surreal_database
    assert first.surreal_database.startswith("fred_mem01_exp01_")

    repos = Repositories.create(InMemoryBackend())
    fresh_a = rebuild_cognitive_runtime(config, repos)
    fresh_b = rebuild_cognitive_runtime(config, repos)
    assert fresh_a is not fresh_b
    assert fresh_a.repositories is repos and fresh_b.repositories is repos
    assert fresh_a.cognitive is not fresh_b.cognitive
