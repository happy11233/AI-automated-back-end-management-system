ALTER TABLE documents
ADD COLUMN IF NOT EXISTS field_scope TEXT;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS sensitivity_level TEXT;

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_field_scope_check;

ALTER TABLE documents
ADD CONSTRAINT documents_field_scope_check
CHECK (
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
);

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_sensitivity_level_check;

ALTER TABLE documents
ADD CONSTRAINT documents_sensitivity_level_check
CHECK (
    sensitivity_level IS NULL
    OR sensitivity_level IN ('internal', 'confidential', 'restricted')
);

CREATE INDEX IF NOT EXISTS idx_documents_field_scope ON documents(field_scope);
CREATE INDEX IF NOT EXISTS idx_documents_sensitivity_level ON documents(sensitivity_level);
