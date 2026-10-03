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
