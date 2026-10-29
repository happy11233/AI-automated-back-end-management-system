-- Business tasks are distinct from execution attempts and platform receipts.
CREATE TABLE IF NOT EXISTS ecommerce_stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    external_store_id TEXT NOT NULL,
    marketplace TEXT NOT NULL,
    name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(platform, external_store_id, marketplace)
);

CREATE TABLE IF NOT EXISTS ecommerce_store_grants (
    store_id UUID NOT NULL REFERENCES ecommerce_stores(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position TEXT NOT NULL CHECK(position IN ('operations','finance','customer_service')),
    enabled BOOLEAN NOT NULL DEFAULT true,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(store_id, user_id, position)
);
CREATE INDEX IF NOT EXISTS idx_ecommerce_store_grants_user ON ecommerce_store_grants(user_id, position, enabled);

CREATE TABLE IF NOT EXISTS ecommerce_business_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES ecommerce_stores(id),
    object_type TEXT NOT NULL CHECK(object_type IN ('order','order_line','sku','refund','settlement',
        'bank_transaction','ticket','shipment','purchase','campaign','accounting_entry')),
    external_id TEXT NOT NULL,
    line_id TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(object_type <> 'order_line' OR line_id <> ''),
    UNIQUE(store_id, object_type, external_id, line_id)
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id UUID NOT NULL REFERENCES users(id),
    position TEXT NOT NULL CHECK(position IN ('operations','finance','customer_service')),
    workflow_id TEXT NOT NULL,
    app_id TEXT NOT NULL,
    title TEXT NOT NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','awaiting_input','queued','running',
        'awaiting_approval','awaiting_external','partially_completed','succeeded','failed','cancelled')),
    source TEXT NOT NULL CHECK(source IN ('manual','chat','event','schedule')),
    thread_id TEXT REFERENCES chat_threads(id) ON DELETE SET NULL,
    store_id UUID REFERENCES ecommerce_stores(id),
    expected_outputs JSONB NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(expected_outputs)='array'),
    completion_criteria JSONB NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_typeof(completion_criteria)='array'),
    policy_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    workflow_version TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    UNIQUE(owner_user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_owner_updated ON agent_tasks(owner_user_id, position, updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_store_status ON agent_tasks(store_id, status);

CREATE TABLE IF NOT EXISTS agent_task_objects (
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    object_id UUID NOT NULL REFERENCES ecommerce_business_objects(id),
    PRIMARY KEY(task_id, object_id)
);

CREATE TABLE IF NOT EXISTS agent_task_runs (
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    run_id UUID NOT NULL UNIQUE REFERENCES automation_runs(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK(attempt_number > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(task_id, run_id),
    UNIQUE(task_id, attempt_number)
);
