CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'employee')),
    position TEXT CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance')),
    department TEXT,
    display_name TEXT,
    email TEXT,
    password_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_ai_app_permissions (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_id TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, app_id)
);

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

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    delivery_eta TIMESTAMPTZ,
    amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_cents >= 0),
    refundable BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT,
    visibility TEXT NOT NULL CHECK (visibility IN ('admin', 'employee')),
    department TEXT,
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
    field_scope TEXT CHECK (
        field_scope IS NULL
        OR field_scope IN (
            'operations_listing',
            'operations_inventory',
            'operations_sales',
            'customer_profile',
            'customer_logistics',
            'customer_after_sales',
            'finance_invoice',
            'finance_payment',
            'finance_profit',
            'finance_salary'
        )
    ),
    sensitivity_level TEXT CHECK (
        sensitivity_level IS NULL
        OR sensitivity_level IN ('internal', 'confidential', 'restricted')
    ),
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    owner_team_id UUID REFERENCES rag_teams(id) ON DELETE SET NULL,
    access_mode TEXT NOT NULL DEFAULT 'open' CHECK (
        access_mode IN ('open', 'owner_only', 'team_only', 'explicit_grants', 'owner_and_grants')
    ),
    content_hash TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deleted')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_parent_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parent_index INTEGER NOT NULL CHECK (parent_index >= 0),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, parent_index)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parent_chunk_id UUID REFERENCES document_parent_chunks(id) ON DELETE SET NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    embedding_model TEXT NOT NULL DEFAULT 'text-embedding-v4',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

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

CREATE TABLE IF NOT EXISTS chat_threads (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title TEXT,
    position TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_thread_summaries (
    thread_id TEXT PRIMARY KEY REFERENCES chat_threads(id) ON DELETE CASCADE,
    summary TEXT NOT NULL DEFAULT '',
    message_count INTEGER NOT NULL DEFAULT 0 CHECK (message_count >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_thread_state (
    thread_id TEXT PRIMARY KEY REFERENCES chat_threads(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    current_intent TEXT,
    order_no TEXT,
    risk_level TEXT,
    approval_id UUID,
    status TEXT NOT NULL DEFAULT 'active',
    slots JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.70 CHECK (confidence >= 0 AND confidence <= 1),
    source_thread_id TEXT REFERENCES chat_threads(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, memory_type, memory_key)
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread' CHECK (status IN ('unread', 'read')),
    resource_type TEXT,
    resource_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    position TEXT CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance')),
    category TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'completed')),
    admin_note TEXT,
    completed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    completed_by_username TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type TEXT NOT NULL,
    app_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed', 'blocked')),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    username TEXT,
    role TEXT,
    position TEXT,
    thread_id TEXT,
    resource_type TEXT,
    resource_id TEXT,
    flow_id UUID,
    flow_key TEXT,
    flow_version_id UUID,
    flow_version TEXT,
    publication_id UUID,
    execution_source TEXT,
    input_preview TEXT,
    input_hash TEXT,
    output_preview TEXT,
    error_message TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_run_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL DEFAULT 1 CHECK (step_order >= 1),
    step_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'blocked')),
    provider TEXT,
    resource_type TEXT,
    resource_id TEXT,
    input_preview TEXT,
    output_preview TEXT,
    error_message TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_run_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES automation_runs(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    name TEXT NOT NULL,
    mime_type TEXT,
    size_bytes INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    external_ref TEXT,
    storage_path TEXT,
    expires_at TIMESTAMPTZ,
    downloadable BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_flows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_key TEXT NOT NULL UNIQUE,
    app_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    position TEXT CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance')),
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'enabled' CHECK (status IN ('enabled', 'disabled', 'archived')),
    source TEXT NOT NULL DEFAULT 'code_defined' CHECK (source IN ('code_defined', 'db_defined', 'hybrid')),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_flow_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number >= 1),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'reviewing', 'approved', 'published', 'deprecated', 'rejected', 'rolled_back')),
    change_summary TEXT,
    trigger_type TEXT NOT NULL,
    entrypoint TEXT NOT NULL,
    input_schema JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_schema JSONB NOT NULL DEFAULT '[]'::jsonb,
    prompt_template TEXT,
    prompt_summary TEXT,
    model_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    allowed_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_erp_resources JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_rag_scopes JSONB NOT NULL DEFAULT '{}'::jsonb,
    permission_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    approval_policy TEXT NOT NULL,
    failure_strategy TEXT NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    publish_notes TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    published_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    UNIQUE (flow_id, version_number),
    UNIQUE (flow_id, version)
);

CREATE TABLE IF NOT EXISTS automation_flow_publications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES automation_flow_versions(id) ON DELETE RESTRICT,
    environment TEXT NOT NULL DEFAULT 'production' CHECK (environment IN ('dev', 'staging', 'production')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'rolled_back')),
    rollout_percent INTEGER NOT NULL DEFAULT 100 CHECK (rollout_percent BETWEEN 0 AND 100),
    published_by UUID REFERENCES users(id) ON DELETE SET NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rollback_from_version_id UUID REFERENCES automation_flow_versions(id) ON DELETE SET NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS automation_flow_version_preflight_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id UUID NOT NULL REFERENCES automation_flows(id) ON DELETE CASCADE,
    version_id UUID NOT NULL REFERENCES automation_flow_versions(id) ON DELETE CASCADE,
    flow_key TEXT NOT NULL,
    version TEXT NOT NULL,
    version_status TEXT NOT NULL,
    trigger_source TEXT NOT NULL DEFAULT 'manual'
        CHECK (trigger_source IN ('manual', 'publish')),
    ok BOOLEAN NOT NULL,
    blocking_failures INTEGER NOT NULL DEFAULT 0 CHECK (blocking_failures >= 0),
    checks JSONB NOT NULL DEFAULT '[]'::jsonb,
    failed_check_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_runs_flow_id'
    ) THEN
        ALTER TABLE automation_runs
        ADD CONSTRAINT fk_automation_runs_flow_id
        FOREIGN KEY (flow_id) REFERENCES automation_flows(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_runs_flow_version_id'
    ) THEN
        ALTER TABLE automation_runs
        ADD CONSTRAINT fk_automation_runs_flow_version_id
        FOREIGN KEY (flow_version_id) REFERENCES automation_flow_versions(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_automation_runs_publication_id'
    ) THEN
        ALTER TABLE automation_runs
        ADD CONSTRAINT fk_automation_runs_publication_id
        FOREIGN KEY (publication_id) REFERENCES automation_flow_publications(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS platform_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_type TEXT NOT NULL CHECK (draft_type IN ('listing', 'customer_reply')),
    platform TEXT NOT NULL DEFAULT 'amazon',
    external_target TEXT NOT NULL DEFAULT 'amazon_seller_central',
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (status IN ('pending_review', 'approved', 'published', 'rejected')),
    position TEXT NOT NULL CHECK (position IN ('operations', 'customer_service', 'finance')),
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    source_run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
    source_resource_type TEXT,
    source_resource_id TEXT,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    writeback_status TEXT NOT NULL DEFAULT 'draft_saved'
        CHECK (writeback_status IN ('draft_saved', 'rpa_ready', 'external_synced', 'failed')),
    writeback_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_drafts_position_created_at
ON platform_drafts(position, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_platform_drafts_owner_created_at
ON platform_drafts(owner_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS platform_action_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES platform_drafts(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('write_listing_draft', 'write_customer_reply', 'publish_listing', 'send_customer_reply')),
    executor_type TEXT NOT NULL CHECK (
        executor_type IN (
            'webhook',
            'amazon_sp_api',
            'n8n',
            'yingdao',
            'customer_service_system',
            'erp_writeback',
            'manual_waiting'
        )
    ),
    target TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('waiting_executor', 'running', 'succeeded', 'failed')),
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
    triggered_by UUID REFERENCES users(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_action_executions_draft_created_at
ON platform_action_executions(draft_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_platform_action_executions_status_created_at
ON platform_action_executions(status, created_at DESC);

CREATE TABLE IF NOT EXISTS platform_action_executors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    executor_type TEXT NOT NULL CHECK (
        executor_type IN ('webhook', 'amazon_sp_api', 'n8n', 'yingdao', 'customer_service_system', 'erp_writeback')
    ),
    action_types TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    webhook_url TEXT,
    api_key TEXT,
    timeout_seconds INTEGER NOT NULL DEFAULT 12 CHECK (timeout_seconds BETWEEN 1 AND 120),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    health_status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (health_status IN ('unknown', 'healthy', 'unhealthy', 'not_configured', 'disabled')),
    health_message TEXT,
    last_checked_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_action_executors_enabled_updated_at
ON platform_action_executors(enabled, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_platform_action_executors_action_types
ON platform_action_executors USING GIN(action_types);

CREATE TABLE IF NOT EXISTS platform_execution_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID NOT NULL REFERENCES platform_drafts(id) ON DELETE CASCADE,
    latest_execution_id UUID REFERENCES platform_action_executions(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('write_listing_draft', 'write_customer_reply', 'publish_listing', 'send_customer_reply')),
    target TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'dispatching', 'waiting_callback', 'succeeded', 'failed', 'cancelled')),
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    external_reference TEXT,
    callback_token TEXT NOT NULL DEFAULT encode(gen_random_bytes(24), 'hex'),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
    last_error TEXT,
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    next_attempt_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_execution_tasks_status_created_at
ON platform_execution_tasks(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_platform_execution_tasks_draft_created_at
ON platform_execution_tasks(draft_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_platform_execution_tasks_requested_by_created_at
ON platform_execution_tasks(requested_by, created_at DESC);

CREATE TABLE IF NOT EXISTS refund_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id UUID NOT NULL UNIQUE REFERENCES approval_requests(id),
    order_no TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_service_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel TEXT NOT NULL CHECK (channel IN ('manual', 'amazon', 'email', 'ticket', 'api')),
    external_id TEXT,
    buyer_name TEXT,
    buyer_email TEXT,
    buyer_language TEXT NOT NULL DEFAULT 'auto',
    marketplace TEXT,
    order_no TEXT,
    tracking_no TEXT,
    sku TEXT,
    subject TEXT,
    message TEXT NOT NULL,
    intent TEXT,
    risk_level TEXT NOT NULL DEFAULT 'unprocessed'
        CHECK (risk_level IN ('unprocessed', 'low', 'medium', 'high')),
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'processing', 'drafted', 'auto_reply_ready', 'human_handoff', 'closed', 'failed')),
    automation_decision TEXT,
    reply_draft TEXT,
    handoff_reason TEXT,
    erp_summary TEXT,
    rag_summary TEXT,
    erp_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    approval_id UUID REFERENCES approval_requests(id) ON DELETE SET NULL,
    run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    processed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    processed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customer_service_message_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES customer_service_messages(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    content TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_position ON users(position);
CREATE INDEX IF NOT EXISTS idx_user_ai_app_permissions_app ON user_ai_app_permissions(app_id, enabled);
CREATE INDEX IF NOT EXISTS idx_rag_teams_status ON rag_teams(status);
CREATE INDEX IF NOT EXISTS idx_rag_teams_position_scope ON rag_teams(position_scope);
CREATE INDEX IF NOT EXISTS idx_rag_team_memberships_user_status ON rag_team_memberships(user_id, status);
CREATE INDEX IF NOT EXISTS idx_rag_team_memberships_team_status ON rag_team_memberships(team_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_team_memberships_active_unique
ON rag_team_memberships(team_id, user_id)
WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_documents_visibility ON documents(visibility);
CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_documents_position_scope ON documents(position_scope);
CREATE INDEX IF NOT EXISTS idx_documents_market_scope ON documents(market_scope);
CREATE INDEX IF NOT EXISTS idx_documents_store_scope ON documents(store_scope);
CREATE INDEX IF NOT EXISTS idx_documents_field_scope ON documents(field_scope);
CREATE INDEX IF NOT EXISTS idx_documents_sensitivity_level ON documents(sensitivity_level);
CREATE INDEX IF NOT EXISTS idx_documents_owner_user ON documents(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_documents_owner_team ON documents(owner_team_id);
CREATE INDEX IF NOT EXISTS idx_documents_access_mode ON documents(access_mode);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_document_parent_chunks_document_id ON document_parent_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_parent_chunk_id ON document_chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_rag_document_access_grants_document_status
ON rag_document_access_grants(document_id, status);
CREATE INDEX IF NOT EXISTS idx_rag_document_access_grants_subject_status
ON rag_document_access_grants(subject_type, subject_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_document_access_grants_active_unique
ON rag_document_access_grants(document_id, subject_type, subject_id, access_level)
WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_id_created_at ON chat_messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_thread_state_user_id ON chat_thread_state(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_status_updated_at ON chat_threads(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_threads_user_updated_at ON chat_threads(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_threads_user_position_updated_at ON chat_threads(user_id, position, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_expires_at ON user_memories(expires_at);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id_created_at ON audit_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_user_status_created_at ON notifications(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_items_status_created_at ON feedback_items(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_items_submitted_created_at ON feedback_items(submitted_by, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_user_started_at ON automation_runs(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_status_started_at ON automation_runs(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_position_started_at ON automation_runs(position, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_run_type_started_at ON automation_runs(run_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_resource ON automation_runs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_automation_runs_flow_started_at ON automation_runs(flow_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_flow_key_started_at ON automation_runs(flow_key, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_flow_version_started_at ON automation_runs(flow_version_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_publication_started_at ON automation_runs(publication_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_run_steps_run_id ON automation_run_steps(run_id, step_order, started_at);
CREATE INDEX IF NOT EXISTS idx_automation_run_artifacts_run_id ON automation_run_artifacts(run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_automation_run_artifacts_downloadable_expires ON automation_run_artifacts(downloadable, expires_at, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_flows_position_status ON automation_flows(position, status);
CREATE INDEX IF NOT EXISTS idx_automation_flow_versions_flow_status ON automation_flow_versions(flow_id, status, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_automation_flow_versions_created_at ON automation_flow_versions(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_automation_flow_publications_active_unique
ON automation_flow_publications(flow_id, environment)
WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_automation_flow_publications_flow_created_at
ON automation_flow_publications(flow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_flow_preflight_runs_version_created
ON automation_flow_version_preflight_runs(version_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_flow_preflight_runs_flow_created
ON automation_flow_version_preflight_runs(flow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_flow_preflight_runs_ok_created
ON automation_flow_version_preflight_runs(ok, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_evidence_version_script
ON automation_flow_version_verification_evidence(version_id, script, status, verified_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_evidence_flow_snapshot
ON automation_flow_version_verification_evidence(flow_id, snapshot_hash, script, status, verified_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_flow_evidence_report
ON automation_flow_version_verification_evidence(report_id, verified_at DESC);
CREATE INDEX IF NOT EXISTS idx_refund_transactions_order_no ON refund_transactions(order_no);
CREATE INDEX IF NOT EXISTS idx_customer_service_messages_status_created_at ON customer_service_messages(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_service_messages_created_by_created_at ON customer_service_messages(created_by, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_customer_service_messages_order_no ON customer_service_messages(order_no);
CREATE INDEX IF NOT EXISTS idx_customer_service_messages_intent ON customer_service_messages(intent);
CREATE INDEX IF NOT EXISTS idx_customer_service_messages_risk ON customer_service_messages(risk_level);
CREATE INDEX IF NOT EXISTS idx_customer_service_message_events_message_created_at ON customer_service_message_events(message_id, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
