ALTER TABLE automation_runs
ADD COLUMN IF NOT EXISTS flow_id UUID;

ALTER TABLE automation_runs
ADD COLUMN IF NOT EXISTS flow_key TEXT;

ALTER TABLE automation_runs
ADD COLUMN IF NOT EXISTS flow_version_id UUID;

ALTER TABLE automation_runs
ADD COLUMN IF NOT EXISTS flow_version TEXT;

ALTER TABLE automation_runs
ADD COLUMN IF NOT EXISTS publication_id UUID;

ALTER TABLE automation_runs
ADD COLUMN IF NOT EXISTS execution_source TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_runs_flow_id'
    ) THEN
        ALTER TABLE automation_runs
        ADD CONSTRAINT fk_automation_runs_flow_id
        FOREIGN KEY (flow_id) REFERENCES automation_flows(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_runs_flow_version_id'
    ) THEN
        ALTER TABLE automation_runs
        ADD CONSTRAINT fk_automation_runs_flow_version_id
        FOREIGN KEY (flow_version_id) REFERENCES automation_flow_versions(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_runs_publication_id'
    ) THEN
        ALTER TABLE automation_runs
        ADD CONSTRAINT fk_automation_runs_publication_id
        FOREIGN KEY (publication_id) REFERENCES automation_flow_publications(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_automation_runs_flow_started_at
ON automation_runs(flow_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_flow_key_started_at
ON automation_runs(flow_key, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_flow_version_started_at
ON automation_runs(flow_version_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_runs_publication_started_at
ON automation_runs(publication_id, started_at DESC);
