CREATE TABLE IF NOT EXISTS facility_material_rules (
    facility_id TEXT NOT NULL,
    material TEXT NOT NULL,
    route TEXT NOT NULL CHECK (route IN ('recyclable', 'reusable', 'refuse_processing', 'needs_review')),
    reason TEXT NOT NULL,
    needs_review BOOLEAN NOT NULL DEFAULT TRUE,
    possible_outputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    reuse_ideas JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_title TEXT NOT NULL,
    policy_url TEXT,
    reviewed_at TIMESTAMPTZ,
    is_example BOOLEAN NOT NULL DEFAULT TRUE,
    policy_version TEXT NOT NULL,
    PRIMARY KEY (facility_id, material)
);

CREATE INDEX IF NOT EXISTS ix_facility_material_rules_material
    ON facility_material_rules (material);
