CREATE TABLE IF NOT EXISTS automation_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_key TEXT NOT NULL UNIQUE,
    app_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    position TEXT CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance')),
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'enabled' CHECK (status IN ('enabled', 'disabled', 'archived')),
    source TEXT NOT NULL DEFAULT 'code_defined' CHECK (source IN ('code_defined', 'db_defined', 'hybrid')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_flow_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'reviewing', 'approved', 'published', 'deprecated', 'rejected', 'rolled_back')),
    change_summary TEXT,
    trigger_type TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    input_schema JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_schema JSONB NOT NULL DEFAULT '[]'::jsonb,
    prompt_template TEXT,
    prompt_summary TEXT,
    model_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    allowed_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_erp_resources JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_rag_scopes JSONB NOT NULL DEFAULT '{}'::jsonb,
    permission_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    approval_policy TEXT NOT NULL,
    failure_strategy TEXT NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    publish_notes TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    published_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    UNIQUE (flow_id, version_number),
    UNIQUE (flow_id, version)
);

CREATE TABLE IF NOT EXISTS automation_flow_publications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES automation_flow_versions(id) ON DELETE RESTRICT,
    environment TEXT NOT NULL DEFAULT 'production' CHECK (environment IN ('dev', 'staging', 'production')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'rolled_back')),
    rollout_percent INTEGER NOT NULL DEFAULT 100 CHECK (rollout_percent BETWEEN 0 AND 100),
    published_by UUID REFERENCES users(id) ON DELETE SET NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rollback_from_version_id UUID REFERENCES automation_flow_versions(id) ON DELETE SET NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_automation_flows_position_status
ON automation_flows(position, status);

CREATE INDEX IF NOT EXISTS idx_automation_flow_versions_flow_status
ON automation_flow_versions(flow_id, status, version_number DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_versions_created_at
ON automation_flow_versions(created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_automation_flow_publications_active_unique
ON automation_flow_publications(flow_id, environment)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_automation_flow_publications_flow_created_at
ON automation_flow_publications(flow_id, created_at DESC);
