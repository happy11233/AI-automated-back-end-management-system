CREATE TABLE IF NOT EXISTS enterprise_wechat_settings (
    id TEXT PRIMARY KEY DEFAULT 'default' CHECK (id = 'default'),
    corp_id TEXT,
    agent_id TEXT,
    secret TEXT,
    real_send_enabled BOOLEAN,
    timeout_seconds INTEGER NOT NULL DEFAULT 12 CHECK (timeout_seconds BETWEEN 1 AND 120),
    last_health_status TEXT,
    last_health_message TEXT,
    last_sync_at TIMESTAMPTZ,
    last_sync_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO enterprise_wechat_settings (id)
VALUES ('default')
ON CONFLICT (id) DO NOTHING;
