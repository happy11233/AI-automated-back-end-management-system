CREATE TABLE IF NOT EXISTS platform_execution_callback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES platform_execution_tasks(id) ON DELETE CASCADE,
    attempt_count INTEGER NOT NULL CHECK (attempt_count > 0),
    external_event_id TEXT NOT NULL,
    body_hash TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'received' CHECK (outcome IN ('received', 'applied', 'ignored')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_id, attempt_count, external_event_id)
);
CREATE INDEX IF NOT EXISTS idx_platform_callback_events_task_time
    ON platform_execution_callback_events(task_id, created_at DESC);
