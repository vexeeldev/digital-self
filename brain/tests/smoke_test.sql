-- =============================================================================
-- Digital Self V2.1 — Smoke Test
-- Tujuan: Memvalidasi bahwa schema bekerja secara fungsional di PostgreSQL nyata.
-- Dijalankan sekali, kemudian di-rollback — tidak meninggalkan data.
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 1: Insert satu experience
-- PRD V2.1 §4 — Experience Contract
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 1: Insert experience ---'

INSERT INTO experiences (id, raw_text, occurred_at, metadata)
VALUES (
    '11111111-0000-0000-0000-000000000001',
    'Tadi aku kesandung di kantor dan lumayan kesal.',
    '2026-10-01 10:00:00+07',   -- occurred_at: kapan kejadian terjadi
    '{"location": "office", "activity": "working"}'::jsonb
);

-- Verifikasi: baca kembali
SELECT
    id,
    raw_text,
    occurred_at,
    created_at,
    metadata
FROM experiences
WHERE id = '11111111-0000-0000-0000-000000000001';


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 2: occurred_at berbeda dari created_at
-- PRD V2.1 §4: "occurred_at ≠ created_at"
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 2: occurred_at ≠ created_at ---'

SELECT
    occurred_at,
    created_at,
    CASE
        WHEN occurred_at <> created_at THEN 'PASS: occurred_at different from created_at'
        ELSE 'FAIL: timestamps are identical'
    END AS check_result
FROM experiences
WHERE id = '11111111-0000-0000-0000-000000000001';


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 3: Insert beberapa node
-- PRD V2.1 §5 — Node Contract
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 3: Insert nodes ---'

INSERT INTO nodes (id, type, name, confidence, activation, first_seen, last_seen)
VALUES
    ('22222222-0000-0000-0000-000000000001', 'place',   'Office',    0.800, 0.540, now(), now()),
    ('22222222-0000-0000-0000-000000000002', 'event',   'Tripping',  0.900, 0.910, now(), now()),
    ('22222222-0000-0000-0000-000000000003', 'emotion', 'Annoyance', 0.850, 0.820, now(), now());

SELECT id, type, name, confidence, activation
FROM nodes
ORDER BY type;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 4: Insert association dengan source_experience_id (provenance)
-- PRD V2.1 §6 — Association Contract
-- Default type = co_occurs_with, bukan causes
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 4: Insert association dengan provenance ---'

INSERT INTO associations (
    id,
    source_node_id,
    target_node_id,
    type,
    strength,
    confidence,
    positive_evidence,
    negative_evidence,
    source_experience_id
)
VALUES (
    '33333333-0000-0000-0000-000000000001',
    '22222222-0000-0000-0000-000000000002',  -- Tripping
    '22222222-0000-0000-0000-000000000003',  -- Annoyance
    'co_occurs_with',                         -- Default type, bukan causes
    0.100,                                    -- Strength awal rendah
    0.500,                                    -- Confidence awal moderat
    1,
    0,
    '11111111-0000-0000-0000-000000000001'   -- Provenance ke experience #1
);

INSERT INTO associations (
    id,
    source_node_id,
    target_node_id,
    type,
    strength,
    confidence,
    positive_evidence,
    negative_evidence,
    source_experience_id
)
VALUES (
    '33333333-0000-0000-0000-000000000002',
    '22222222-0000-0000-0000-000000000001',  -- Office
    '22222222-0000-0000-0000-000000000002',  -- Tripping
    'co_occurs_with',
    0.100,
    0.500,
    1,
    0,
    '11111111-0000-0000-0000-000000000001'
);

SELECT
    a.id,
    sn.name AS source_node,
    a.type,
    tn.name AS target_node,
    a.strength,
    a.confidence,
    a.positive_evidence,
    a.negative_evidence,
    e.raw_text AS source_experience
FROM associations a
JOIN nodes sn ON a.source_node_id = sn.id
JOIN nodes tn ON a.target_node_id = tn.id
JOIN experiences e ON a.source_experience_id = e.id
ORDER BY a.created_at;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 5: Insert experience_association (provenance bridge)
-- PRD V2 §11 — source_experiences (plural)
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 5: Provenance bridge ---'

INSERT INTO experience_associations (experience_id, association_id, is_positive)
VALUES
    ('11111111-0000-0000-0000-000000000001', '33333333-0000-0000-0000-000000000001', true),
    ('11111111-0000-0000-0000-000000000001', '33333333-0000-0000-0000-000000000002', true);

-- Verifikasi: trace balik association ke experience
SELECT
    ea.association_id,
    sn.name AS source_node,
    a.type,
    tn.name AS target_node,
    ea.is_positive,
    e.raw_text AS from_experience
FROM experience_associations ea
JOIN associations a ON ea.association_id = a.id
JOIN nodes sn ON a.source_node_id = sn.id
JOIN nodes tn ON a.target_node_id = tn.id
JOIN experiences e ON ea.experience_id = e.id;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 6: Verifikasi UNIQUE constraint pada association
-- Tidak boleh ada dua association yang identik (source, target, type sama)
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 6: UNIQUE constraint pada association ---'

-- Ini harus gagal (duplicate directed association)
DO $$
BEGIN
    INSERT INTO associations (
        source_node_id, target_node_id, type, source_experience_id
    ) VALUES (
        '22222222-0000-0000-0000-000000000002',
        '22222222-0000-0000-0000-000000000003',
        'co_occurs_with',
        '11111111-0000-0000-0000-000000000001'
    );
    RAISE NOTICE 'FAIL: Duplicate association was accepted (should have been rejected)';
EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'PASS: Duplicate association correctly rejected by UNIQUE constraint';
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 7: Verifikasi self-loop constraint
-- Sebuah node tidak boleh berasosiasi dengan dirinya sendiri
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 7: Self-loop constraint ---'

DO $$
BEGIN
    INSERT INTO associations (
        source_node_id, target_node_id, type, source_experience_id
    ) VALUES (
        '22222222-0000-0000-0000-000000000001',
        '22222222-0000-0000-0000-000000000001',  -- self-loop
        'co_occurs_with',
        '11111111-0000-0000-0000-000000000001'
    );
    RAISE NOTICE 'FAIL: Self-loop was accepted (should have been rejected)';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: Self-loop correctly rejected by CHECK constraint';
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 8: ON DELETE RESTRICT pada source_experience_id
-- Tidak boleh menghapus experience yang menjadi provenance association
-- PRD V2 §2: "Every abstraction must be traceable"
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 8: ON DELETE RESTRICT (provenance protection) ---'

DO $$
BEGIN
    DELETE FROM experiences WHERE id = '11111111-0000-0000-0000-000000000001';
    RAISE NOTICE 'FAIL: Delete was accepted (provenance experience should be protected)';
EXCEPTION WHEN foreign_key_violation THEN
    RAISE NOTICE 'PASS: Delete correctly rejected by ON DELETE RESTRICT (provenance intact)';
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 9: Blank raw_text ditolak
-- PRD V2.1 §4: "raw_text harus dipertahankan" — tidak boleh kosong
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 9: Blank raw_text ditolak ---'

DO $$
BEGIN
    INSERT INTO experiences (raw_text) VALUES ('   ');
    RAISE NOTICE 'FAIL: Blank raw_text was accepted (should have been rejected)';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: Blank raw_text correctly rejected by CHECK constraint';
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 10: confidence di luar [0,1] ditolak
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 10: Confidence out-of-range ditolak ---'

DO $$
BEGIN
    INSERT INTO nodes (type, name, confidence)
    VALUES ('place', 'TestNode', 1.5);
    RAISE NOTICE 'FAIL: Out-of-range confidence was accepted';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'PASS: Out-of-range confidence correctly rejected';
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 11: Association tanpa source_experience_id ditolak (provenance wajib)
-- PRD V2.1 §6: "Association harus memiliki provenance"
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 11: Association tanpa provenance ditolak ---'

DO $$
BEGIN
    INSERT INTO associations (source_node_id, target_node_id, type, source_experience_id)
    VALUES (
        '22222222-0000-0000-0000-000000000001',
        '22222222-0000-0000-0000-000000000003',
        'co_occurs_with',
        NULL  -- tidak ada provenance
    );
    RAISE NOTICE 'FAIL: NULL source_experience_id was accepted';
EXCEPTION WHEN not_null_violation THEN
    RAISE NOTICE 'PASS: NULL source_experience_id correctly rejected (provenance required)';
END;
$$;


-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 12: Verifikasi raw_text masih utuh (immutability check)
-- PRD V1 §4.1: "Raw Experience Is Ground Truth"
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 12: Raw experience masih tersimpan utuh ---'

SELECT
    raw_text,
    CASE
        WHEN raw_text = 'Tadi aku kesandung di kantor dan lumayan kesal.'
        THEN 'PASS: raw_text preserved exactly as inserted'
        ELSE 'FAIL: raw_text was modified'
    END AS check_result
FROM experiences
WHERE id = '11111111-0000-0000-0000-000000000001';

-- ─────────────────────────────────────────────────────────────────────────────
-- SMOKE TEST 13: Entity Resolution (Aliases)
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 13: Entity Resolution (Aliases) ---'
INSERT INTO node_aliases (node_id, alias_name, node_type)
VALUES ('22222222-0000-0000-0000-000000000001', 'tempat kerja', 'place');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM node_aliases WHERE alias_name = 'tempat kerja') THEN
        RAISE EXCEPTION 'FAIL: node alias not inserted';
    END IF;
    
    -- Coba insert ulang dengan alias yang sama (harus gagal unique constraint)
    BEGIN
        INSERT INTO node_aliases (node_id, alias_name, node_type)
        VALUES ('22222222-0000-0000-0000-000000000001', 'tempat kerja', 'place');
        RAISE EXCEPTION 'FAIL: Duplicate alias not rejected';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: Duplicate alias correctly rejected by UNIQUE constraint';
    END;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SMOKE TEST 14: Assembly Extraction (Idempotent Replace, Unique Member) ---'
DO $$
DECLARE
    exp_id UUID;
    node_id1 UUID;
    node_id2 UUID;
    asm_id UUID;
BEGIN
    SELECT id INTO exp_id FROM experiences WHERE raw_text = 'Tadi aku kesandung di kantor dan lumayan kesal.';
    SELECT id INTO node_id1 FROM nodes WHERE name = 'Office' LIMIT 1;
    SELECT id INTO node_id2 FROM nodes WHERE name = 'Tripping' LIMIT 1;
    
    INSERT INTO assemblies (experience_id, context_summary, confidence)
    VALUES (exp_id, 'Kesandung di kantor', 0.900)
    RETURNING id INTO asm_id;
    
    INSERT INTO assembly_members (assembly_id, node_id, role, weight)
    VALUES 
        (asm_id, node_id1, 'location', 0.8),
        (asm_id, node_id2, 'event', 1.0);
        
    -- Test Duplicate assembly (Should fail due to UNIQUE(experience_id))
    BEGIN
        INSERT INTO assemblies (experience_id, context_summary, confidence)
        VALUES (exp_id, 'Duplicate context', 0.500);
        RAISE EXCEPTION 'FAIL: Duplicate assembly allowed!';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: Duplicate assembly correctly rejected by UNIQUE constraint';
    END;
    
    -- Test Duplicate member (Should fail due to UNIQUE(assembly_id, node_id))
    BEGIN
        INSERT INTO assembly_members (assembly_id, node_id, role, weight)
        VALUES (asm_id, node_id1, 'another_role', 0.5);
        RAISE EXCEPTION 'FAIL: Duplicate assembly member allowed!';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'PASS: Duplicate member correctly rejected by UNIQUE constraint';
    END;
END $$;
SELECT 'PASS: Assembly constraints validated' AS check_result;

-- ─────────────────────────────────────────────────────────────────────────────
-- Summary: Jumlah data yang berhasil masuk
-- ─────────────────────────────────────────────────────────────────────────────
\echo '--- SUMMARY: Row counts ---'

SELECT 'experiences' AS table_name, COUNT(*) AS rows FROM experiences
UNION ALL
SELECT 'nodes',                COUNT(*) FROM nodes
UNION ALL
SELECT 'associations',         COUNT(*) FROM associations
UNION ALL
SELECT 'experience_associations', COUNT(*) FROM experience_associations
UNION ALL
SELECT 'assemblies',           COUNT(*) FROM assemblies
UNION ALL
SELECT 'assembly_members',     COUNT(*) FROM assembly_members;


-- Rollback — tidak meninggalkan data di database
ROLLBACK;

\echo '--- ROLLBACK: Semua data test di-rollback, database tetap bersih ---'
