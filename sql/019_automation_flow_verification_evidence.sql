CREATE TABLE IF NOT EXISTS automation_flow_version_verification_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version_id UUID REFERENCES automation_flow_versions(id) ON DELETE CASCADE,
    flow_key TEXT NOT NULL,
    version TEXT NOT NULL,
    version_status TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    script TEXT NOT NULL,
    command TEXT NOT NULL,
    profile TEXT NOT NULL CHECK (profile IN ('api', 'release')),
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed')),
    report_id TEXT NOT NULL,
    report_url TEXT,
    summary TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (expires_at > verified_at)
);

CREATE INDEX IF NOT EXISTS idx_automation_flow_evidence_version_script
ON automation_flow_version_verification_evidence(version_id, script, status, verified_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_evidence_flow_snapshot
ON automation_flow_version_verification_evidence(flow_id, snapshot_hash, script, status, verified_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_evidence_report
ON automation_flow_version_verification_evidence(report_id, verified_at DESC);
