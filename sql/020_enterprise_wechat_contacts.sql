CREATE TABLE IF NOT EXISTS enterprise_wechat_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type TEXT NOT NULL CHECK (object_type IN ('user', 'group', 'department')),
    name TEXT NOT NULL,
    alias TEXT,
    wechat_userid TEXT,
    chat_id TEXT,
    department_id TEXT,
    department TEXT,
    phone TEXT,
    avatar_url TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_enterprise_wechat_contacts_search
ON enterprise_wechat_contacts(active, object_type, name);

CREATE UNIQUE INDEX IF NOT EXISTS idx_enterprise_wechat_contacts_unique_target
ON enterprise_wechat_contacts(
    object_type,
    name,
    COALESCE(wechat_userid, ''),
    COALESCE(chat_id, ''),
    COALESCE(department_id, '')
);
