ALTER TABLE approval_requests
    ADD COLUMN IF NOT EXISTS payload_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_approval_requests_business_key
    ON approval_requests(thread_id, action_type, payload_hash)
    WHERE payload_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS approval_ticket_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id UUID NOT NULL UNIQUE REFERENCES approval_requests(id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'dispatching', 'succeeded', 'failed', 'uncertain')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    external_ticket_id TEXT,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_approval_ticket_outbox_due
    ON approval_ticket_outbox(next_attempt_at)
    WHERE status IN ('pending', 'failed', 'uncertain');
