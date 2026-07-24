ALTER TABLE documents
ADD COLUMN IF NOT EXISTS position_scope TEXT;

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_position_scope_check;

ALTER TABLE documents
ADD CONSTRAINT documents_position_scope_check
CHECK (
    position_scope IS NULL
    OR position_scope IN ('operations', 'customer_service', 'finance')
);

CREATE INDEX IF NOT EXISTS idx_documents_position_scope ON documents(position_scope);
