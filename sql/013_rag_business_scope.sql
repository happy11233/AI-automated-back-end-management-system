ALTER TABLE documents
ADD COLUMN IF NOT EXISTS market_scope TEXT;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS store_scope TEXT;

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_market_scope_check;

ALTER TABLE documents
ADD CONSTRAINT documents_market_scope_check
CHECK (
    market_scope IS NULL
    OR market_scope IN ('us', 'de', 'jp')
);

ALTER TABLE documents
DROP CONSTRAINT IF EXISTS documents_store_scope_check;

ALTER TABLE documents
ADD CONSTRAINT documents_store_scope_check
CHECK (
    store_scope IS NULL
    OR store_scope IN ('us_store', 'de_store', 'jp_store')
);

CREATE INDEX IF NOT EXISTS idx_documents_market_scope ON documents(market_scope);
CREATE INDEX IF NOT EXISTS idx_documents_store_scope ON documents(store_scope);
