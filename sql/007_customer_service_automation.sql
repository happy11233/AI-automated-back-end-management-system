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

CREATE INDEX IF NOT EXISTS idx_customer_service_messages_status_created_at
ON customer_service_messages(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_service_messages_created_by_created_at
ON customer_service_messages(created_by, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_service_messages_order_no
ON customer_service_messages(order_no);

CREATE INDEX IF NOT EXISTS idx_customer_service_messages_intent
ON customer_service_messages(intent);

CREATE INDEX IF NOT EXISTS idx_customer_service_messages_risk
ON customer_service_messages(risk_level);

CREATE TABLE IF NOT EXISTS customer_service_message_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES customer_service_messages(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    content TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_customer_service_message_events_message_created_at
ON customer_service_message_events(message_id, created_at ASC);
