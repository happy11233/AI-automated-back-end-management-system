CREATE TABLE IF NOT EXISTS automation_flow_version_preflight_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES automation_flow_versions(id) ON DELETE CASCADE,
    flow_key TEXT NOT NULL,
    version TEXT NOT NULL,
    version_status TEXT NOT NULL,
    trigger_source TEXT NOT NULL DEFAULT 'manual'
        CHECK (trigger_source IN ('manual', 'publish')),
    ok BOOLEAN NOT NULL,
    blocking_failures INTEGER NOT NULL DEFAULT 0 CHECK (blocking_failures >= 0),
    checks JSONB NOT NULL DEFAULT '[]'::jsonb,
    failed_check_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_automation_flow_preflight_runs_version_created
ON automation_flow_version_preflight_runs(version_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_preflight_runs_flow_created
ON automation_flow_version_preflight_runs(flow_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_preflight_runs_ok_created
ON automation_flow_version_preflight_runs(ok, created_at DESC);
