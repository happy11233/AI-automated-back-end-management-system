ALTER TABLE documents
ADD COLUMN IF NOT EXISTS department TEXT;

CREATE TABLE IF NOT EXISTS document_parent_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parent_index INTEGER NOT NULL CHECK (parent_index >= 0),
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, parent_index)
);

ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS parent_chunk_id UUID REFERENCES document_parent_chunks(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department);
CREATE INDEX IF NOT EXISTS idx_document_parent_chunks_document_id ON document_parent_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_parent_chunk_id ON document_chunks(parent_chunk_id);

INSERT INTO document_parent_chunks (document_id, parent_index, content, metadata)
SELECT
    d.id,
    0,
    string_agg(c.content, E'\n\n' ORDER BY c.chunk_index),
    jsonb_build_object('migrated_from', 'document_chunks')
FROM documents d
JOIN document_chunks c ON c.document_id = d.id
WHERE NOT EXISTS (
    SELECT 1
    FROM document_parent_chunks p
    WHERE p.document_id = d.id
)
GROUP BY d.id;

UPDATE document_chunks c
SET parent_chunk_id = p.id
FROM document_parent_chunks p
WHERE p.document_id = c.document_id
  AND p.parent_index = 0
  AND c.parent_chunk_id IS NULL;
