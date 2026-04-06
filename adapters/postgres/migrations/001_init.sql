CREATE TABLE IF NOT EXISTS mgp_memories (
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    type TEXT NOT NULL,
    state TEXT NOT NULL,
    searchable_text TEXT NOT NULL,
    memory_json JSONB NOT NULL,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS mgp_memories_tenant_state_idx
    ON mgp_memories (tenant_id, state);

CREATE INDEX IF NOT EXISTS mgp_memories_subject_idx
    ON mgp_memories (subject_kind, subject_id);

CREATE INDEX IF NOT EXISTS mgp_memories_scope_type_idx
    ON mgp_memories (scope, type);

CREATE INDEX IF NOT EXISTS mgp_memories_created_idx
    ON mgp_memories (created_at DESC);

CREATE INDEX IF NOT EXISTS mgp_memories_memory_json_idx
    ON mgp_memories
    USING GIN (memory_json jsonb_path_ops);
