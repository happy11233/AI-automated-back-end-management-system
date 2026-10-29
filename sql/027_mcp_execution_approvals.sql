CREATE TABLE IF NOT EXISTS mcp_execution_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    arguments_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'issued' CHECK (status IN ('issued', 'used')),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '5 minutes'),
    used_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_mcp_execution_approvals_user_status
    ON mcp_execution_approvals(user_id, status, expires_at);
