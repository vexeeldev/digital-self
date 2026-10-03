-- =============================================================================
-- Digital Self — schema.sql
-- Version: V2.1 — Initial Technical Contract
-- Based on: PRD V1, PRD V2, PRD V2.1
-- =============================================================================
--
-- Scope: Three foundational tables only.
--   - experiences           : Immutable raw experience records (source of truth)
--   - nodes                 : Concepts/entities discovered from experiences
--   - associations          : Relationships between nodes, with provenance
--   - experience_associations : Provenance bridge (experiences ↔ associations)
--
-- Out of scope (not implemented until foundation is validated):
--   - patterns, beliefs, decisions, assemblies, internal_states
--   - reasoning engine, LLM pipeline, consolidation engine
--
-- PRD Principles enforced in this schema:
--   [P1] raw_text is immutable — never overwritten by AI interpretation.
--   [P2] Every association must trace back to at least one experience (provenance).
--   [P3] occurred_at (when it happened) ≠ created_at (when it was recorded).
--   [P4] Interpretation is not truth — all AI-derived fields carry confidence.
--   [P5] Contradictions are allowed — association stores positive AND negative evidence.
--   [P6] Default relationship type is co_occurs_with, not causes (PRD V2 §8).
--
-- =============================================================================


-- ---------------------------------------------------------------------------
-- ENUM: node_type
-- Defined in PRD V1 §5.8 and V2.1 §5
-- ---------------------------------------------------------------------------
CREATE TYPE node_type AS ENUM (
    'person',
    'place',
    'object',
    'event',
    'emotion',
    'action',
    'concept'
);

-- ---------------------------------------------------------------------------
-- ENUM: association_type
-- Relationship taxonomy from PRD V2 §7
-- Default for AI-inferred relationships: co_occurs_with
-- Causal relationships require stronger evidence (PRD V2 §8)
-- ---------------------------------------------------------------------------
CREATE TYPE association_type AS ENUM (
    -- Causal / correlational
    'causes',
    'correlates_with',
    'co_occurs_with',         -- DEFAULT: safest assumption without explicit evidence

    -- Temporal (PRD V2 §6 — Temporal Model)
    'before',
    'after',
    'during',
    'overlaps',

    -- Compositional
    'part_of',
    'contains',

    -- Taxonomic
    'instance_of',
    'is_a',
    'has_property',

    -- Situational
    'located_at',
    'involves',

    -- Epistemic
    'similar_to',
    'contradicts',
    'supports',
    'weakens',

    -- Fallback
    'associated_with'
);

-- ---------------------------------------------------------------------------
-- TABLE: experiences
-- PRD V1 §5.1, PRD V2 §5, PRD V2.1 §4
--
-- This is the most fundamental data layer.
-- raw_text is the source of truth and MUST NOT be modified after insertion.
-- metadata allows storing additional structured context (JSONB) without
-- requiring schema changes at this stage. Structure is intentionally
-- left flexible because PRD V2.1 does not specify metadata fields.
-- ---------------------------------------------------------------------------
CREATE TABLE experiences (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- [P1] Immutable raw experience text — source of truth.
    -- The exact words/sentences the user submitted.
    raw_text        TEXT        NOT NULL,

    -- [P3] When the experience actually happened (may differ from created_at).
    -- Example: User recalls something from yesterday → occurred_at = yesterday.
    -- NULL is allowed when the user does not specify when it happened.
    occurred_at     TIMESTAMPTZ NULL,

    -- [P3] When this record was written to the system.
    -- Set automatically at insert time.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Unstructured additional context (location, activity, participants snapshot, etc.)
    -- PRD V2.1 does not specify the exact structure of metadata.
    -- Using JSONB keeps it flexible for now. Structure will be formalized later.
    metadata        JSONB       NULL DEFAULT '{}'::jsonb,

    -- Constraint: raw_text must not be empty or blank
    CONSTRAINT experiences_raw_text_not_empty CHECK (char_length(trim(raw_text)) > 0)
);

-- Index: retrieval by time of occurrence (temporal queries: "what happened yesterday?")
CREATE INDEX idx_experiences_occurred_at ON experiences (occurred_at);

-- Index: retrieval by time of recording
CREATE INDEX idx_experiences_created_at  ON experiences (created_at DESC);


-- ---------------------------------------------------------------------------
-- TABLE: nodes
-- PRD V1 §5.8, PRD V2 §10, PRD V2.1 §5
--
-- Nodes represent concepts/entities found in experiences.
-- They are NOT permanent facts about the user.
-- They can be corrected, merged, or split by the user (PRD V2 §19).
--
-- INTENTIONALLY EXCLUDED from V2.1:
--   - aliases (entity resolution — PRD V2 §9/§10) — out of scope for V2.1
--   - embedding (vector search — PRD V2 §10) — added in Phase 2 with pgvector
-- ---------------------------------------------------------------------------
CREATE TABLE nodes (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Semantic type of this node (person, place, emotion, etc.)
    type            node_type    NOT NULL,

    -- Canonical display name of this node.
    -- Example: "Office", "Annoyance", "Friend"
    name            TEXT         NOT NULL,

    -- How confident the system is that this node is correctly identified.
    -- Range: 0.0 to 1.0
    -- Newly created nodes start at a moderate confidence (0.5).
    confidence      NUMERIC(4,3) NOT NULL DEFAULT 0.500
                    CHECK (confidence >= 0.0 AND confidence <= 1.0),

    -- Current activation level of this node.
    -- Range: 0.0 to 1.0
    -- High activation = currently relevant to the active context.
    -- Decays over time per params.yaml decay_lambda (PRD V2 §21).
    activation      NUMERIC(4,3) NOT NULL DEFAULT 0.000
                    CHECK (activation >= 0.0 AND activation <= 1.0),

    -- When this node was first observed across any experience.
    first_seen      TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- When this node was most recently referenced by any experience.
    last_seen       TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- Constraint: name must not be blank
    CONSTRAINT nodes_name_not_empty CHECK (char_length(trim(name)) > 0),

    -- Constraint: last_seen cannot be before first_seen
    CONSTRAINT nodes_last_seen_gte_first_seen CHECK (last_seen >= first_seen)
);

-- Index: filter/group by node type
CREATE INDEX idx_nodes_type        ON nodes (type);

-- Index: case-insensitive name search (replaced by unique index below for resolution)
-- CREATE INDEX idx_nodes_name_lower  ON nodes (lower(name));

-- UNIQUE Index: Prevent duplicate canonical names for the same type
CREATE UNIQUE INDEX idx_nodes_unique_name_type ON nodes (lower(name), type);

-- Index: hot-path retrieval — most active nodes first
CREATE INDEX idx_nodes_activation  ON nodes (activation DESC);

-- Index: recency-based retrieval
CREATE INDEX idx_nodes_last_seen   ON nodes (last_seen DESC);


-- ---------------------------------------------------------------------------
-- TABLE: node_aliases
-- PRD V2 §9 Entity Resolution, §10 Node Identity
--
-- Records aliases for canonical nodes to support Entity Resolution.
-- ---------------------------------------------------------------------------
CREATE TABLE node_aliases (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id         UUID        NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    alias_name      TEXT        NOT NULL,
    
    -- Redundant node_type to allow database-level uniqueness across type
    node_type       node_type   NOT NULL,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT node_aliases_alias_name_not_empty CHECK (char_length(trim(alias_name)) > 0)
);

-- Case-insensitive unique constraint for alias + type
CREATE UNIQUE INDEX idx_node_aliases_unique_name_type ON node_aliases (lower(alias_name), node_type);

-- Index: fast lookup of aliases by node
CREATE INDEX idx_node_aliases_node_id ON node_aliases (node_id);


-- ---------------------------------------------------------------------------
-- TABLE: associations
-- PRD V1 §5.9, PRD V2 §7, §11, §12, PRD V2.1 §6
--
-- Associations represent typed, weighted relationships between two nodes.
-- Every association MUST have provenance to at least one source experience.
-- This enforces PRD principle: "Every abstraction must be traceable." (V2 §2)
--
-- NOTE on positive/negative_evidence:
--   PRD V2 §11 explicitly includes these fields in the Association Data Model.
--   PRD V2.1 §6 does not repeat them, but they are required by the Contradiction
--   Model (PRD V2 §15) and PRD V1 §4.4 ("Contradictions Are Allowed").
--   Including them here is justified and not scope creep.
--
-- NOTE on source_experience_id:
--   PRD V2.1 §6 uses "source_experience" (singular) for the initial contract.
--   This field records the FIRST experience that created this association.
--   All subsequent evidence is tracked via experience_associations (below).
-- ---------------------------------------------------------------------------
CREATE TABLE associations (
    id                   UUID             PRIMARY KEY DEFAULT gen_random_uuid(),

    -- The "from" node in the directed relationship.
    source_node_id       UUID             NOT NULL
                         REFERENCES nodes(id) ON DELETE CASCADE,

    -- The "to" node in the directed relationship.
    target_node_id       UUID             NOT NULL
                         REFERENCES nodes(id) ON DELETE CASCADE,

    -- Relationship type from taxonomy (PRD V2 §7).
    -- [P6] Default is co_occurs_with — the safest inference.
    -- 'causes' requires strong/explicit evidence (PRD V2 §8).
    type                 association_type NOT NULL DEFAULT 'co_occurs_with',

    -- How strong this relationship is believed to be.
    -- Range: 0.0 to 1.0
    -- Updated via learning rules: s_new = s_old + α × w × (1 - s_old) (PRD V2.1 §8)
    strength             NUMERIC(4,3)     NOT NULL DEFAULT 0.100
                         CHECK (strength >= 0.0 AND strength <= 1.0),

    -- How confident the system is in this association.
    -- [P4] Distinct from strength: a weak-but-consistent link can have high confidence.
    -- A strong-but-contested link can have low confidence. (PRD V2 §14)
    confidence           NUMERIC(4,3)     NOT NULL DEFAULT 0.500
                         CHECK (confidence >= 0.0 AND confidence <= 1.0),

    -- [P5] Count of experiences that SUPPORTED (strengthened) this relationship.
    positive_evidence    INTEGER          NOT NULL DEFAULT 1
                         CHECK (positive_evidence >= 0),

    -- [P5] Count of experiences that CONTRADICTED (weakened) this relationship.
    -- Contradictions are not resolved into a single conclusion (PRD V1 §4.4).
    negative_evidence    INTEGER          NOT NULL DEFAULT 0
                         CHECK (negative_evidence >= 0),

    -- [P2] PROVENANCE: The first experience that created this association.
    -- Cannot be null — associations must have a traceable origin.
    -- ON DELETE RESTRICT prevents deleting an experience that created an association.
    source_experience_id UUID             NOT NULL
                         REFERENCES experiences(id) ON DELETE RESTRICT,

    -- When this association was first created.
    created_at           TIMESTAMPTZ      NOT NULL DEFAULT now(),

    -- When this association was last updated (e.g., strength recalculated).
    updated_at           TIMESTAMPTZ      NOT NULL DEFAULT now(),

    -- A node cannot be associated with itself.
    CONSTRAINT associations_no_self_loop CHECK (source_node_id <> target_node_id),

    -- Prevent exact duplicate directed associations of the same type.
    -- Different relationship types between the same nodes are allowed.
    -- Example: A --causes--> B and A --co_occurs_with--> B can coexist.
    CONSTRAINT associations_unique_directed
        UNIQUE (source_node_id, target_node_id, type)
);

-- Index: find all associations FROM a node (outgoing edges)
CREATE INDEX idx_associations_source_node ON associations (source_node_id);

-- Index: find all associations TO a node (incoming edges)
CREATE INDEX idx_associations_target_node ON associations (target_node_id);

-- Index: filter by relationship type
CREATE INDEX idx_associations_type        ON associations (type);

-- Index: retrieve strongest associations first
CREATE INDEX idx_associations_strength    ON associations (strength DESC);

-- Index: provenance lookup — find associations originating from an experience
CREATE INDEX idx_associations_source_exp  ON associations (source_experience_id);


-- ---------------------------------------------------------------------------
-- TABLE: experience_nodes (Provenance Bridge / Join Table)
--
-- This table records which experiences a specific node was extracted from.
-- This ensures full provenance for nodes, even if they don't have associations yet.
-- ---------------------------------------------------------------------------
CREATE TABLE experience_nodes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    experience_id   UUID        NOT NULL
                    REFERENCES experiences(id) ON DELETE CASCADE,

    node_id         UUID        NOT NULL
                    REFERENCES nodes(id) ON DELETE CASCADE,

    -- When this extraction/provenance link was created.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A node is extracted at most once per experience.
    CONSTRAINT experience_nodes_unique UNIQUE (experience_id, node_id)
);

-- Index: find all nodes extracted from an experience
CREATE INDEX idx_exp_nodes_experience ON experience_nodes (experience_id);

-- Index: find all experiences that contain a given node
CREATE INDEX idx_exp_nodes_node       ON experience_nodes (node_id);


-- ---------------------------------------------------------------------------
-- TABLE: experience_associations (Provenance Bridge / Join Table)
-- PRD V2 §11: source_experiences (plural) in Association Data Model
-- PRD V1 §4.3: Memory Has Provenance — every abstraction traceable to experiences
-- PRD V2 §50: Audit Trail
--
-- This table records EVERY experience that contributed evidence to an association.
-- Required because an association accumulates evidence from many experiences over time.
--
-- This enables:
--   - Full provenance: Association → all contributing Experiences
--   - Evidence counting (positive vs negative, per PRD V2 §15)
--   - Future audit trail (PRD V2 §50)
--
-- This is not a feature table — it is a provenance infrastructure table.
-- Without it, provenance would be limited to only the first experience.
-- ---------------------------------------------------------------------------
CREATE TABLE experience_associations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    experience_id   UUID        NOT NULL
                    REFERENCES experiences(id) ON DELETE CASCADE,

    association_id  UUID        NOT NULL
                    REFERENCES associations(id) ON DELETE CASCADE,

    -- Whether this experience provided positive or negative evidence.
    -- true  = this experience strengthened the association
    -- false = this experience contradicted or weakened the association
    is_positive     BOOLEAN     NOT NULL DEFAULT true,

    -- When this evidence link was created.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Each experience contributes at most once per association.
    CONSTRAINT experience_associations_unique UNIQUE (experience_id, association_id)
);

-- Index: find all experiences that contributed to a given association (provenance lookup)
CREATE INDEX idx_exp_assoc_association ON experience_associations (association_id);

-- Index: find all associations an experience contributed to
CREATE INDEX idx_exp_assoc_experience  ON experience_associations (experience_id);


-- ---------------------------------------------------------------------------
-- TABLE: assemblies
-- PRD V1 §5.10, PRD V2 §60: Assembly / Episodic Memory
-- ---------------------------------------------------------------------------
CREATE TABLE assemblies (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    experience_id   UUID        NOT NULL REFERENCES experiences(id) ON DELETE RESTRICT,
    context_summary TEXT        NOT NULL,
    confidence      NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT assemblies_context_not_empty CHECK (char_length(trim(context_summary)) > 0),
    CONSTRAINT assemblies_experience_unique UNIQUE (experience_id)
);

CREATE INDEX idx_assemblies_experience ON assemblies (experience_id);

-- ---------------------------------------------------------------------------
-- TABLE: assembly_members
-- ---------------------------------------------------------------------------
CREATE TABLE assembly_members (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    assembly_id     UUID        NOT NULL REFERENCES assemblies(id) ON DELETE CASCADE,
    node_id         UUID        NOT NULL REFERENCES nodes(id) ON DELETE RESTRICT,
    role            TEXT        NOT NULL,
    weight          NUMERIC(4,3) NOT NULL DEFAULT 1.000 CHECK (weight >= 0.0 AND weight <= 1.0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT assembly_members_role_not_empty CHECK (char_length(trim(role)) > 0),
    CONSTRAINT assembly_members_unique_node UNIQUE (assembly_id, node_id)
);

CREATE INDEX idx_assembly_members_assembly ON assembly_members (assembly_id);
CREATE INDEX idx_assembly_members_node     ON assembly_members (node_id);

-- =============================================================================
-- STAGE 18: Human Correction Layer
-- =============================================================================
CREATE TYPE correction_operation AS ENUM ('ADD', 'REJECT', 'RESTORE');

CREATE TABLE experience_node_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experience_node_id UUID NOT NULL REFERENCES experience_nodes(id) ON DELETE RESTRICT,
    operation correction_operation NOT NULL,
    event_sequence SERIAL,
    actor TEXT NOT NULL DEFAULT 'human',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE experience_association_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experience_association_id UUID NOT NULL REFERENCES experience_associations(id) ON DELETE RESTRICT,
    operation correction_operation NOT NULL,
    event_sequence SERIAL,
    actor TEXT NOT NULL DEFAULT 'human',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE assembly_member_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assembly_member_id UUID NOT NULL REFERENCES assembly_members(id) ON DELETE RESTRICT,
    operation correction_operation NOT NULL,
    event_sequence SERIAL,
    actor TEXT NOT NULL DEFAULT 'human',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE VIEW vw_active_experience_nodes AS
SELECT en.*
FROM experience_nodes en
LEFT JOIN (
    SELECT experience_node_id, operation
    FROM (
        SELECT experience_node_id, operation,
               ROW_NUMBER() OVER(PARTITION BY experience_node_id ORDER BY event_sequence DESC) as rn
        FROM experience_node_corrections
    ) sub
    WHERE rn = 1
) latest_corr ON en.id = latest_corr.experience_node_id
WHERE latest_corr.operation IS NULL OR latest_corr.operation IN ('ADD', 'RESTORE');

CREATE VIEW vw_active_experience_associations AS
SELECT ea.*
FROM experience_associations ea
LEFT JOIN (
    SELECT experience_association_id, operation
    FROM (
        SELECT experience_association_id, operation,
               ROW_NUMBER() OVER(PARTITION BY experience_association_id ORDER BY event_sequence DESC) as rn
        FROM experience_association_corrections
    ) sub
    WHERE rn = 1
) latest_corr ON ea.id = latest_corr.experience_association_id
WHERE latest_corr.operation IS NULL OR latest_corr.operation IN ('ADD', 'RESTORE');

CREATE VIEW vw_active_assembly_members AS
SELECT am.*
FROM assembly_members am
LEFT JOIN (
    SELECT assembly_member_id, operation
    FROM (
        SELECT assembly_member_id, operation,
               ROW_NUMBER() OVER(PARTITION BY assembly_member_id ORDER BY event_sequence DESC) as rn
        FROM assembly_member_corrections
    ) sub
    WHERE rn = 1
) latest_corr ON am.id = latest_corr.assembly_member_id
WHERE latest_corr.operation IS NULL OR latest_corr.operation IN ('ADD', 'RESTORE');

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================

-- What is NOT in this schema (out of V2.1 scope):
--   - patterns, beliefs, decisions
--   - assemblies, internal_states (note assemblies were added in 15, but this is a note)
--   - node aliases (entity resolution)
--   - node embeddings (pgvector / Phase 2)
--   - audit/versioning tables
--   - user/session tables
-- =============================================================================
