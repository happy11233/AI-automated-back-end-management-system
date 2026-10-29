CREATE TABLE IF NOT EXISTS email_send_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    artifacts JSONB NOT NULL CHECK (jsonb_typeof(artifacts) = 'array'),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'unknown')),
    run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '30 minutes'),
    sent_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_email_send_confirmations_user_status
    ON email_send_confirmations(user_id, status, expires_at);
ALTER TABLE email_send_confirmations ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL;
ALTER TABLE email_send_confirmations DROP CONSTRAINT IF EXISTS email_send_confirmations_status_check;
ALTER TABLE email_send_confirmations ADD CONSTRAINT email_send_confirmations_status_check
    CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'unknown'));
