CREATE TABLE IF NOT EXISTS rag_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    position_scope TEXT CHECK (
        position_scope IS NULL
        OR position_scope IN ('operations', 'customer_service', 'finance')
    ),
    market_scope TEXT CHECK (
        market_scope IS NULL
        OR market_scope IN ('us', 'de', 'jp')
    ),
    store_scope TEXT CHECK (
        store_scope IS NULL
        OR store_scope IN ('us_store', 'de_store', 'jp_store')
    ),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rag_team_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES rag_teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    member_role TEXT NOT NULL DEFAULT 'member' CHECK (member_role IN ('member', 'supervisor', 'auditor')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'removed')),
    added_by UUID REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS owner_user_id UUID;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS owner_team_id UUID;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS access_mode TEXT DEFAULT 'open';

UPDATE documents
SET access_mode = 'open'
WHERE access_mode IS NULL;

ALTER TABLE documents
ALTER COLUMN access_mode SET DEFAULT 'open';

ALTER TABLE documents
ALTER COLUMN access_mode SET NOT NULL;

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_access_mode_check;

ALTER TABLE documents
ADD CONSTRAINT documents_access_mode_check
CHECK (
    access_mode IN ('open', 'owner_only', 'team_only', 'explicit_grants', 'owner_and_grants')
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'documents_owner_user_id_fkey'
    ) THEN
        ALTER TABLE documents
        ADD CONSTRAINT documents_owner_user_id_fkey
        FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'documents_owner_team_id_fkey'
    ) THEN
        ALTER TABLE documents
        ADD CONSTRAINT documents_owner_team_id_fkey
        FOREIGN KEY (owner_team_id) REFERENCES rag_teams(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS rag_document_access_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('user', 'team')),
    subject_id UUID NOT NULL,
    access_level TEXT NOT NULL DEFAULT 'read' CHECK (access_level IN ('read', 'manage')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired')),
    granted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rag_teams_status ON rag_teams(status);
CREATE INDEX IF NOT EXISTS idx_rag_teams_position_scope ON rag_teams(position_scope);
CREATE INDEX IF NOT EXISTS idx_rag_team_memberships_user_status ON rag_team_memberships(user_id, status);
CREATE INDEX IF NOT EXISTS idx_rag_team_memberships_team_status ON rag_team_memberships(team_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_team_memberships_active_unique
ON rag_team_memberships(team_id, user_id)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_documents_owner_user ON documents(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_documents_owner_team ON documents(owner_team_id);
CREATE INDEX IF NOT EXISTS idx_documents_access_mode ON documents(access_mode);

CREATE INDEX IF NOT EXISTS idx_rag_document_access_grants_document_status
ON rag_document_access_grants(document_id, status);
CREATE INDEX IF NOT EXISTS idx_rag_document_access_grants_subject_status
ON rag_document_access_grants(subject_type, subject_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_document_access_grants_active_unique
ON rag_document_access_grants(document_id, subject_type, subject_id, access_level)
WHERE status = 'active';
