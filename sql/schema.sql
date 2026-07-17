CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'employee')),
    position TEXT CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance')),
    department TEXT,
    password_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
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

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT,
    visibility TEXT NOT NULL CHECK (visibility IN ('admin', 'employee')),
    department TEXT,
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

CREATE TABLE IF NOT EXISTS chat_threads (
    id TEXT PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title TEXT,
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
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
CREATE INDEX IF NOT EXISTS idx_documents_visibility ON documents(visibility);
CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_document_parent_chunks_document_id ON document_parent_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_parent_chunk_id ON document_chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread_id_created_at ON chat_messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_thread_state_user_id ON chat_thread_state(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_threads_status_updated_at ON chat_threads(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_expires_at ON user_memories(expires_at);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id_created_at ON audit_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_automation_runs_user_started_at ON automation_runs(user_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_status_started_at ON automation_runs(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_position_started_at ON automation_runs(position, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_run_type_started_at ON automation_runs(run_type, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_runs_resource ON automation_runs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_automation_run_steps_run_id ON automation_run_steps(run_id, step_order, started_at);
CREATE INDEX IF NOT EXISTS idx_automation_run_artifacts_run_id ON automation_run_artifacts(run_id, created_at);
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
