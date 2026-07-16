CREATE TABLE IF NOT EXISTS automation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type TEXT NOT NULL,
    app_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed', 'blocked')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    username TEXT,
    role TEXT,
    position TEXT,
    thread_id TEXT,
    resource_type TEXT,
    resource_id TEXT,
    input_preview TEXT,
    input_hash TEXT,
    output_preview TEXT,
    error_message TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_run_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL DEFAULT 1 CHECK (step_order >= 1),
    step_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'blocked')),
    provider TEXT,
    resource_type TEXT,
    resource_id TEXT,
    input_preview TEXT,
    output_preview TEXT,
    error_message TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_run_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    name TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    external_ref TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_automation_runs_user_started_at
ON automation_runs(user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_status_started_at
ON automation_runs(status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_position_started_at
ON automation_runs(position, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_run_type_started_at
ON automation_runs(run_type, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_resource
ON automation_runs(resource_type, resource_id);

CREATE INDEX IF NOT EXISTS idx_automation_run_steps_run_id
ON automation_run_steps(run_id, step_order, started_at);

CREATE INDEX IF NOT EXISTS idx_automation_run_artifacts_run_id
ON automation_run_artifacts(run_id, created_at);
