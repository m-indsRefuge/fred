-- Fred Memory Complex V1
-- MEM-01 SurrealDB schema draft
-- Target: SurrealDB 3.3.x
-- Embedding baseline: qwen3-embedding:0.6b, 1024 dimensions, cosine distance
--
-- This schema intentionally keeps the physical model small:
-- experience, memory, entity, evaluation, state, journal_event,
-- cognitive_relation, trace_event.

DEFINE ANALYZER OVERWRITE fred_text
    TOKENIZERS class, punct
    FILTERS lowercase, ascii;

-- ---------------------------------------------------------------------------
-- EXPERIENCE: immutable historical evidence
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE experience SCHEMAFULL TYPE NORMAL
    COMMENT "Committed immutable evidence of what happened to Fred.";

DEFINE FIELD sequence_start ON TABLE experience TYPE int READONLY;
DEFINE FIELD sequence_end ON TABLE experience TYPE int READONLY
    ASSERT $value >= sequence_start;

DEFINE FIELD session_id ON TABLE experience TYPE string READONLY;
DEFINE FIELD turn_id ON TABLE experience TYPE option<string> READONLY;

DEFINE FIELD input ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD context ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD perception ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD decision ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD action ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD outcome ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD feedback ON TABLE experience TYPE option<object> FLEXIBLE READONLY;

DEFINE FIELD search_text ON TABLE experience TYPE string READONLY;

DEFINE FIELD entity_refs ON TABLE experience TYPE array<record<entity>> READONLY;

DEFINE FIELD started_at ON TABLE experience TYPE datetime READONLY;
DEFINE FIELD ended_at ON TABLE experience TYPE datetime READONLY;
DEFINE FIELD observed_at ON TABLE experience TYPE datetime READONLY;
DEFINE FIELD created_at ON TABLE experience TYPE datetime
    DEFAULT time::now() READONLY;

DEFINE FIELD embedding ON TABLE experience TYPE array<float, 1024> READONLY;
DEFINE FIELD embedding_model ON TABLE experience TYPE string READONLY;
DEFINE FIELD embedding_version ON TABLE experience TYPE string READONLY;

DEFINE FIELD provenance ON TABLE experience TYPE object FLEXIBLE READONLY;
DEFINE FIELD metadata ON TABLE experience TYPE object FLEXIBLE READONLY;

DEFINE INDEX OVERWRITE experience_embedding_hnsw
    ON TABLE experience FIELDS embedding
    HNSW DIMENSION 1024 DIST COSINE TYPE F32;

DEFINE INDEX OVERWRITE experience_text_ft
    ON TABLE experience FIELDS search_text
    FULLTEXT ANALYZER fred_text BM25;

DEFINE INDEX OVERWRITE experience_session_idx
    ON TABLE experience FIELDS session_id;

DEFINE INDEX OVERWRITE experience_ended_at_idx
    ON TABLE experience FIELDS ended_at;

-- ---------------------------------------------------------------------------
-- MEMORY: derived interpretation
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE memory SCHEMAFULL TYPE NORMAL
    COMMENT "Fred's derived interpretations over Experience evidence.";

DEFINE FIELD content ON TABLE memory TYPE string;

DEFINE FIELD status ON TABLE memory
    TYPE "PROVISIONAL" | "ACTIVE" | "TOMBSTONED"
    DEFAULT "PROVISIONAL";

DEFINE FIELD episodicity ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD abstraction ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD procedurality ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD relationality ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;

DEFINE FIELD evidential_support ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD interpretive_confidence ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD salience_prior ON TABLE memory TYPE number
    ASSERT $value >= 0 AND $value <= 1;

DEFINE FIELD valid_from ON TABLE memory TYPE option<datetime>;
DEFINE FIELD valid_until ON TABLE memory TYPE option<datetime>;

DEFINE FIELD created_at ON TABLE memory TYPE datetime
    DEFAULT time::now() READONLY;

DEFINE FIELD embedding ON TABLE memory TYPE array<float, 1024>;
DEFINE FIELD embedding_model ON TABLE memory TYPE string;
DEFINE FIELD embedding_version ON TABLE memory TYPE string;

DEFINE FIELD provenance ON TABLE memory TYPE object FLEXIBLE;
DEFINE FIELD metadata ON TABLE memory TYPE object FLEXIBLE;

DEFINE INDEX OVERWRITE memory_embedding_hnsw
    ON TABLE memory FIELDS embedding
    HNSW DIMENSION 1024 DIST COSINE TYPE F32;

DEFINE INDEX OVERWRITE memory_content_ft
    ON TABLE memory FIELDS content
    FULLTEXT ANALYZER fred_text BM25;

DEFINE INDEX OVERWRITE memory_status_idx
    ON TABLE memory FIELDS status;

DEFINE INDEX OVERWRITE memory_valid_from_idx
    ON TABLE memory FIELDS valid_from;

DEFINE INDEX OVERWRITE memory_valid_until_idx
    ON TABLE memory FIELDS valid_until;

-- ---------------------------------------------------------------------------
-- ENTITY
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE entity SCHEMAFULL TYPE NORMAL
    COMMENT "Stable identity used across Experiences and Memories.";

DEFINE FIELD kind ON TABLE entity TYPE string;
DEFINE FIELD canonical_key ON TABLE entity TYPE string;
DEFINE FIELD name ON TABLE entity TYPE string;
DEFINE FIELD aliases ON TABLE entity TYPE array<string> DEFAULT [];
DEFINE FIELD created_at ON TABLE entity TYPE datetime
    DEFAULT time::now() READONLY;
DEFINE FIELD metadata ON TABLE entity TYPE object FLEXIBLE;

DEFINE INDEX OVERWRITE entity_canonical_key_unique
    ON TABLE entity FIELDS canonical_key UNIQUE;

-- ---------------------------------------------------------------------------
-- EVALUATION
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE evaluation SCHEMAFULL TYPE NORMAL
    COMMENT "Outcome evidence about an Experience or Memory.";

DEFINE FIELD target_ref ON TABLE evaluation TYPE record;
DEFINE FIELD kind ON TABLE evaluation
    TYPE "SUCCESS" | "FAILURE" | "CORRECTION" | "UNEXPECTED"
       | "USEFUL" | "NOT_USEFUL" | "PARTIAL";
DEFINE FIELD value ON TABLE evaluation TYPE option<number>;
DEFINE FIELD source ON TABLE evaluation TYPE string;
DEFINE FIELD created_at ON TABLE evaluation TYPE datetime
    DEFAULT time::now() READONLY;
DEFINE FIELD evidence_refs ON TABLE evaluation TYPE array<record> DEFAULT [];
DEFINE FIELD metadata ON TABLE evaluation TYPE object FLEXIBLE;

-- ---------------------------------------------------------------------------
-- STATE
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE state SCHEMAFULL TYPE NORMAL
    COMMENT "Exact current state; direct lookup, not semantic reconstruction.";

DEFINE FIELD key ON TABLE state TYPE string;
DEFINE FIELD value ON TABLE state TYPE object FLEXIBLE;
DEFINE FIELD authority ON TABLE state TYPE string;
DEFINE FIELD updated_at ON TABLE state TYPE datetime
    DEFAULT time::now();
DEFINE FIELD metadata ON TABLE state TYPE object FLEXIBLE;

DEFINE INDEX OVERWRITE state_key_unique
    ON TABLE state FIELDS key UNIQUE;

-- ---------------------------------------------------------------------------
-- JOURNAL EVENT: operational append-only history
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE journal_event SCHEMAFULL TYPE NORMAL
    COMMENT "Append-only operational events used to construct and replay Experiences.";

DEFINE FIELD sequence ON TABLE journal_event TYPE int READONLY;
DEFINE FIELD event_type ON TABLE journal_event TYPE string READONLY;
DEFINE FIELD session_id ON TABLE journal_event TYPE string READONLY;
DEFINE FIELD turn_id ON TABLE journal_event TYPE option<string> READONLY;
DEFINE FIELD occurred_at ON TABLE journal_event TYPE datetime READONLY;
DEFINE FIELD payload ON TABLE journal_event TYPE object FLEXIBLE READONLY;

DEFINE INDEX OVERWRITE journal_session_idx
    ON TABLE journal_event FIELDS session_id;
DEFINE INDEX OVERWRITE journal_turn_idx
    ON TABLE journal_event FIELDS turn_id;
DEFINE INDEX OVERWRITE journal_time_idx
    ON TABLE journal_event FIELDS occurred_at;
DEFINE INDEX OVERWRITE journal_type_idx
    ON TABLE journal_event FIELDS event_type;

-- ---------------------------------------------------------------------------
-- COGNITIVE RELATION: one typed graph edge substrate
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE cognitive_relation
    SCHEMAFULL
    TYPE RELATION
        IN experience|memory|evaluation
        OUT experience|memory|entity|evaluation
        ENFORCED
    COMMENT "Controlled graph relation vocabulary for the Memory Complex.";

DEFINE FIELD kind ON TABLE cognitive_relation
    TYPE "DERIVED_FROM" | "PART_OF" | "ABOUT" | "CAUSED_BY"
       | "RESULTED_IN" | "SUPPORTS" | "CONTRADICTS" | "SUPERSEDES"
       | "REINFORCES" | "SIMILAR_TO" | "RECALLED_WITH";

DEFINE FIELD confidence ON TABLE cognitive_relation TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD strength ON TABLE cognitive_relation TYPE number
    ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD source ON TABLE cognitive_relation TYPE string;
DEFINE FIELD created_at ON TABLE cognitive_relation TYPE datetime
    DEFAULT time::now() READONLY;
DEFINE FIELD provenance ON TABLE cognitive_relation TYPE array<record> DEFAULT [];
DEFINE FIELD metadata ON TABLE cognitive_relation TYPE object FLEXIBLE;

DEFINE INDEX OVERWRITE relation_kind_idx
    ON TABLE cognitive_relation FIELDS kind;

-- ---------------------------------------------------------------------------
-- TRACE EVENT: read-only observer/research instrumentation stream
-- ---------------------------------------------------------------------------

DEFINE TABLE OVERWRITE trace_event SCHEMAFULL TYPE NORMAL
    COMMENT "Machine-readable research instrumentation; not cognitive state.";

DEFINE FIELD trace_type ON TABLE trace_event
    TYPE "RETRIEVAL" | "COGNITIVE_SELECTION" | "MEMORY_PROPOSAL"
       | "MEMORY_VALIDATION" | "SLEEP" | "MODEL_CALL"
       | "EXPERIMENT_CHECKPOINT" | "ERROR";
DEFINE FIELD session_id ON TABLE trace_event TYPE string;
DEFINE FIELD turn_id ON TABLE trace_event TYPE option<string>;
DEFINE FIELD experience_ref ON TABLE trace_event TYPE option<record<experience>>;
DEFINE FIELD occurred_at ON TABLE trace_event TYPE datetime
    DEFAULT time::now() READONLY;
DEFINE FIELD payload ON TABLE trace_event TYPE object FLEXIBLE;

DEFINE INDEX OVERWRITE trace_session_idx
    ON TABLE trace_event FIELDS session_id;
DEFINE INDEX OVERWRITE trace_turn_idx
    ON TABLE trace_event FIELDS turn_id;
DEFINE INDEX OVERWRITE trace_time_idx
    ON TABLE trace_event FIELDS occurred_at;
DEFINE INDEX OVERWRITE trace_type_idx
    ON TABLE trace_event FIELDS trace_type;

-- ---------------------------------------------------------------------------
-- IMPORTANT APPLICATION-LEVEL INVARIANTS
-- ---------------------------------------------------------------------------
-- 1. ExperienceRepository exposes create/read/search only.
-- 2. Journal events are append-only.
-- 3. Memory mutations only enter through validated operations.
-- 4. RelationValidator enforces legal endpoint combinations per relation kind.
-- 5. Fred never emits executable SurrealQL.
-- 6. Proposer and evidence verifier are separate model calls.
-- 7. Normal retrieval excludes memory.status = "TOMBSTONED".
