ALTER TABLE background_jobs
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ;

UPDATE background_jobs
SET next_attempt_at = created_at
WHERE status = 'queued' AND next_attempt_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_background_jobs_due
    ON background_jobs(next_attempt_at) WHERE status = 'queued';
