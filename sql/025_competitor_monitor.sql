-- Mock monitoring is scoped to its owner; official API data must use a separate provider.
CREATE TABLE IF NOT EXISTS competitor_monitor_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    run_id UUID NOT NULL UNIQUE REFERENCES automation_runs(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('manual', 'schedule')),
    provider TEXT NOT NULL CHECK (provider IN ('mock', 'official')),
    scheduled_for TIMESTAMPTZ,
    captured_at TIMESTAMPTZ NOT NULL,
    result JSONB NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    CHECK ((trigger_type = 'schedule') = (scheduled_for IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_competitor_monitor_slot
    ON competitor_monitor_snapshots(owner_user_id, scheduled_for) WHERE scheduled_for IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_competitor_monitor_owner_time
    ON competitor_monitor_snapshots(owner_user_id, captured_at DESC, id DESC);
