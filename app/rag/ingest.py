from functools import lru_cache
from hashlib import sha256
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db import execute, fetch_all, fetch_one, transaction
from app.json_utils import dumps_json
from app.llm import embed_texts
from app.permissions import POSITION_LABELS
from app.rag.vector_store import vector_store

# 文档入库

ALLOWED_MARKET_SCOPES = {"us", "de", "jp"}
ALLOWED_STORE_SCOPES = {"us_store", "de_store", "jp_store"}
ALLOWED_FIELD_SCOPES = {
    "operations_listing",
    "operations_inventory",
    "operations_sales",
    "customer_profile",
    "customer_logistics",
    "customer_after_sales",
    "finance_invoice",
    "finance_payment",
    "finance_profit",
    "finance_salary",
}
ALLOWED_SENSITIVITY_LEVELS = {"internal", "confidential", "restricted"}
SENSITIVITY_LEVEL_ORDER = ("internal", "confidential", "restricted")
FIELD_SCOPE_POSITION_ALLOWLIST = {
    "operations_listing": {"operations"},
    "operations_inventory": {"operations"},
    "operations_sales": {"operations"},
    "customer_profile": {"customer_service"},
    "customer_logistics": {"customer_service"},
    "customer_after_sales": {"customer_service"},
    "finance_invoice": {"finance"},
    "finance_payment": {"finance"},
    "finance_profit": {"finance"},
    "finance_salary": {"finance"},
}
MAX_SENSITIVITY_LEVEL_BY_POSITION = {
    "operations": "confidential",
    "customer_service": "confidential",
    "finance": "restricted",
}

def vector_to_sql(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=[
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        "；",
        "，",
        " ",
        "",
    ],
)

parent_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1600,
    chunk_overlap=200,
    separators=[
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        "；",
        "，",
        " ",
        "",
    ],
)


def create_document(
    title: str,
    source: str,
    visibility: str,
    department: str | None = None,
    position_scope: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    sensitivity_level: str | None = None,
    owner_user_id: str | None = None,
    owner_team_id: str | None = None,
    access_mode: str = "open",
    content_hash: str | None = None,
) -> str:
    row = fetch_one(
        """
        INSERT INTO documents (
            title,
            source,
            visibility,
            department,
            position_scope,
            market_scope,
            store_scope,
            field_scope,
            sensitivity_level,
            owner_user_id,
            owner_team_id,
            access_mode,
            content_hash
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (
            title,
            source,
            visibility,
            department,
            position_scope,
            market_scope,
            store_scope,
            field_scope,
            sensitivity_level,
            owner_user_id,
            owner_team_id,
            access_mode,
            content_hash,
        ),
    )

    return str(row[0])


def create_parent_chunk(
    document_id: str,
    parent_index: int,
    content: str,
    metadata: dict,
) -> str:
    row = fetch_one(
        """
        INSERT INTO document_parent_chunks (
            document_id,
            parent_index,
            content,
            metadata
        )
        VALUES (%s, %s, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            document_id,
            parent_index,
            content,
            dumps_json(metadata),
        ),
    )

    return str(row[0])


def create_document_chunk(
    chunk_id: str,
    document_id: str,
    parent_chunk_id: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    metadata: dict,
) -> str:
    embedding_sql = vector_to_sql(embedding)

    row = fetch_one(
        """
        INSERT INTO document_chunks (
            id,
            document_id,
            parent_chunk_id,
            chunk_index,
            content,
            embedding,
            embedding_model,
            metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            chunk_id,
            document_id,
            parent_chunk_id,
            chunk_index,
            content,
            embedding_sql,
            "text-embedding-v4",
            dumps_json(metadata),
        ),
    )

    return str(row[0])

def ingest_text_document(
    title: str,
    source: str,
    visibility: str,
    text: str,
    department: str | None = None,
    position_scope: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    sensitivity_level: str | None = None,
) -> dict:
    document = Document(
        page_content=text,
        metadata={
            "source": source,
        },
    )

    return ingest_documents(
        title=title,
        source=source,
        visibility=visibility,
        department=department,
        position_scope=position_scope,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        sensitivity_level=sensitivity_level,
        raw_documents=[document],
    )


def ingest_documents(
    title: str,
    source: str,
    visibility: str,
    raw_documents: list[Document],
    department: str | None = None,
    position_scope: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    sensitivity_level: str | None = None,
    owner_user_id: str | None = None,
    owner_team_id: str | None = None,
    access_mode: str = "open",
) -> dict:
    return upsert_documents(
        title=title,
        source=source,
        visibility=visibility,
        raw_documents=raw_documents,
        department=department,
        position_scope=position_scope,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        sensitivity_level=sensitivity_level,
        owner_user_id=owner_user_id,
        owner_team_id=owner_team_id,
        access_mode=access_mode,
    )


def upsert_documents(
    title: str,
    source: str,
    visibility: str,
    raw_documents: list[Document],
    department: str | None = None,
    position_scope: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    sensitivity_level: str | None = None,
    owner_user_id: str | None = None,
    owner_team_id: str | None = None,
    access_mode: str = "open",
) -> dict:
    ensure_rag_document_scope_schema()
    normalized_position_scope = normalize_position_scope(position_scope)
    normalized_market_scope = normalize_market_scope(market_scope)
    normalized_store_scope = normalize_store_scope(store_scope)
    normalized_field_scope = normalize_field_scope(field_scope)
    normalized_sensitivity_level = normalize_sensitivity_level(sensitivity_level)
    normalized_access_mode = access_mode or "open"
    content_hash = calculate_documents_hash(raw_documents)
    active_documents = find_active_documents_by_source(source)
    existing_document = active_documents[0] if active_documents else None
    duplicate_documents = active_documents[1:]

    if (
        existing_document
        and existing_document["content_hash"] == content_hash
        and document_metadata_matches(
            existing_document,
            visibility=visibility,
            department=department,
            position_scope=normalized_position_scope,
            market_scope=normalized_market_scope,
            store_scope=normalized_store_scope,
            field_scope=normalized_field_scope,
            sensitivity_level=normalized_sensitivity_level,
            owner_user_id=owner_user_id,
            owner_team_id=owner_team_id,
            access_mode=normalized_access_mode,
        )
    ):
        clear_duplicate_documents(duplicate_documents)
        return {
            "document_id": existing_document["id"],
            "content_hash": content_hash,
            "version": existing_document["version"],
            "status": existing_document["status"],
            "position_scope": normalized_position_scope,
            "market_scope": normalized_market_scope,
            "store_scope": normalized_store_scope,
            "field_scope": normalized_field_scope,
            "sensitivity_level": normalized_sensitivity_level,
            "owner_user_id": owner_user_id,
            "owner_team_id": owner_team_id,
            "access_mode": normalized_access_mode,
            "update_action": "skipped",
            "message": "文档内容未变化，跳过重新切分和向量化。",
            "parent_chunk_count": 0,
            "chunk_count": 0,
            "chunk_ids": [],
        }

    if existing_document:
        document_id = existing_document["id"]
        version = existing_document["version"] + 1
        clear_document_vectors(document_id)
        clear_duplicate_documents(duplicate_documents)
        update_document_metadata(
            document_id=document_id,
            title=title,
            visibility=visibility,
            department=department,
            position_scope=normalized_position_scope,
            market_scope=normalized_market_scope,
            store_scope=normalized_store_scope,
            field_scope=normalized_field_scope,
            sensitivity_level=normalized_sensitivity_level,
            owner_user_id=owner_user_id,
            owner_team_id=owner_team_id,
            access_mode=normalized_access_mode,
            content_hash=content_hash,
            version=version,
            status="active",
        )
        update_action = "updated"
    else:
        document_id = create_document(
            title=title,
            source=source,
            visibility=visibility,
            department=department,
            position_scope=normalized_position_scope,
            market_scope=normalized_market_scope,
            store_scope=normalized_store_scope,
            field_scope=normalized_field_scope,
            sensitivity_level=normalized_sensitivity_level,
            owner_user_id=owner_user_id,
            owner_team_id=owner_team_id,
            access_mode=normalized_access_mode,
            content_hash=content_hash,
        )
        version = 1
        update_action = "created"

    return build_and_store_chunks(
        document_id=document_id,
        title=title,
        source=source,
        visibility=visibility,
        raw_documents=raw_documents,
        department=department,
        position_scope=normalized_position_scope,
        market_scope=normalized_market_scope,
        store_scope=normalized_store_scope,
        field_scope=normalized_field_scope,
        sensitivity_level=normalized_sensitivity_level,
        owner_user_id=owner_user_id,
        owner_team_id=owner_team_id,
        access_mode=normalized_access_mode,
        content_hash=content_hash,
        version=version,
        update_action=update_action,
    )


def build_and_store_chunks(
    document_id: str,
    title: str,
    source: str,
    visibility: str,
    raw_documents: list[Document],
    department: str | None,
    position_scope: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    sensitivity_level: str | None,
    owner_user_id: str | None,
    owner_team_id: str | None,
    access_mode: str,
    content_hash: str,
    version: int,
    update_action: str,
) -> dict:
    parent_chunks = parent_text_splitter.split_documents(raw_documents)

    documents = []
    metadatas = []
    texts = []
    embeddings = []
    ids = []
    chunk_index = 0

    for parent_index, parent_chunk in enumerate(parent_chunks):
        parent_content = parent_chunk.page_content.strip()

        if not parent_content:
            continue

        parent_metadata = {
            **(parent_chunk.metadata or {}),
            "document_id": document_id,
            "title": title,
            "source": source,
            "visibility": visibility,
            "department": department,
            "status": "active",
            "parent_index": parent_index,
            "content_hash": content_hash,
            "version": version,
            "access_mode": access_mode,
        }
        if owner_user_id:
            parent_metadata["owner_user_id"] = owner_user_id
        if owner_team_id:
            parent_metadata["owner_team_id"] = owner_team_id
        if position_scope:
            parent_metadata["position_scope"] = position_scope
        if market_scope:
            parent_metadata["market_scope"] = market_scope
        if store_scope:
            parent_metadata["store_scope"] = store_scope
        if field_scope:
            parent_metadata["field_scope"] = field_scope
        if sensitivity_level:
            parent_metadata["sensitivity_level"] = sensitivity_level

        parent_chunk_id = create_parent_chunk(
            document_id=document_id,
            parent_index=parent_index,
            content=parent_content,
            metadata=parent_metadata,
        )

        child_chunks = text_splitter.split_documents([
            Document(
                page_content=parent_content,
                metadata=parent_metadata,
            )
        ])

        child_texts = [
            child_chunk.page_content.strip()
            for child_chunk in child_chunks
            if child_chunk.page_content.strip()
        ]

        if not child_texts:
            continue

        child_embeddings = embed_texts(child_texts)

        for child_text, child_embedding in zip(child_texts, child_embeddings):
            chunk_id = str(uuid4())
            metadata = {
                **parent_metadata,
                "chunk_id": chunk_id,
                "parent_chunk_id": parent_chunk_id,
                "chunk_index": chunk_index,
            }

            create_document_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                parent_chunk_id=parent_chunk_id,
                chunk_index=chunk_index,
                content=child_text,
                embedding=child_embedding,
                metadata=metadata,
            )

            documents.append(
                Document(
                    page_content=child_text,
                    metadata=metadata,
                )
            )
            texts.append(child_text)
            embeddings.append(child_embedding)
            metadatas.append(metadata)
            ids.append(chunk_id)
            chunk_index += 1

    if not documents:
        raise ValueError("文档切分后没有可入库的文本内容")

    vector_store.add_embeddings(
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    return {
        "document_id": document_id,
        "content_hash": content_hash,
        "version": version,
        "status": "active",
        "position_scope": position_scope,
        "market_scope": market_scope,
        "store_scope": store_scope,
        "field_scope": field_scope,
        "sensitivity_level": sensitivity_level,
        "owner_user_id": owner_user_id,
        "owner_team_id": owner_team_id,
        "access_mode": access_mode,
        "update_action": update_action,
        "parent_chunk_count": len(parent_chunks),
        "chunk_count": len(documents),
        "chunk_ids": ids,
    }


def calculate_documents_hash(raw_documents: list[Document]) -> str:
    hash_builder = sha256()

    for document in raw_documents:
        content = document.page_content.strip()
        if not content:
            continue

        hash_builder.update(content.encode("utf-8"))
        hash_builder.update(b"\n---document---\n")

    return hash_builder.hexdigest()


def find_active_documents_by_source(source: str) -> list[dict]:
    rows = fetch_all(
        """
        SELECT
            id,
            content_hash,
            version,
            status,
            visibility,
            department,
            position_scope,
            market_scope,
            store_scope,
            field_scope,
            sensitivity_level,
            owner_user_id,
            owner_team_id,
            access_mode
        FROM documents
        WHERE source = %s
          AND status = 'active'
        ORDER BY updated_at DESC, created_at DESC;
        """,
        (source,),
    )

    return [
        {
            "id": str(row[0]),
            "content_hash": row[1],
            "version": row[2],
            "status": row[3],
            "visibility": row[4],
            "department": row[5],
            "position_scope": row[6],
            "market_scope": row[7],
            "store_scope": row[8],
            "field_scope": row[9],
            "sensitivity_level": row[10],
            "owner_user_id": str(row[11]) if row[11] else None,
            "owner_team_id": str(row[12]) if row[12] else None,
            "access_mode": row[13] or "open",
        }
        for row in rows
    ]


@lru_cache(maxsize=1)
def ensure_rag_document_scope_schema() -> None:
    execute(
        """
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
        """
    )
    execute(
        """
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
        """
    )
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS position_scope TEXT;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS market_scope TEXT;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS store_scope TEXT;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS field_scope TEXT;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS sensitivity_level TEXT;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_user_id UUID;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS owner_team_id UUID;")
    execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS access_mode TEXT DEFAULT 'open';")
    execute("UPDATE documents SET access_mode = 'open' WHERE access_mode IS NULL;")
    execute("ALTER TABLE documents ALTER COLUMN access_mode SET DEFAULT 'open';")
    execute("ALTER TABLE documents ALTER COLUMN access_mode SET NOT NULL;")
    execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_access_mode_check;")
    execute(
        """
        ALTER TABLE documents
        ADD CONSTRAINT documents_access_mode_check
        CHECK (
            access_mode IN ('open', 'owner_only', 'team_only', 'explicit_grants', 'owner_and_grants')
        );
        """
    )
    execute(
        """
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
        """
    )
    execute(
        """
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
        """
    )
    execute(
        """
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
        """
    )
    execute("CREATE INDEX IF NOT EXISTS idx_documents_position_scope ON documents(position_scope);")
    execute("CREATE INDEX IF NOT EXISTS idx_documents_market_scope ON documents(market_scope);")
    execute("CREATE INDEX IF NOT EXISTS idx_documents_store_scope ON documents(store_scope);")
    execute("CREATE INDEX IF NOT EXISTS idx_documents_field_scope ON documents(field_scope);")
    execute("CREATE INDEX IF NOT EXISTS idx_documents_sensitivity_level ON documents(sensitivity_level);")
    execute("CREATE INDEX IF NOT EXISTS idx_rag_teams_status ON rag_teams(status);")
    execute("CREATE INDEX IF NOT EXISTS idx_rag_teams_position_scope ON rag_teams(position_scope);")
    execute("CREATE INDEX IF NOT EXISTS idx_rag_team_memberships_user_status ON rag_team_memberships(user_id, status);")
    execute("CREATE INDEX IF NOT EXISTS idx_rag_team_memberships_team_status ON rag_team_memberships(team_id, status);")
    execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_team_memberships_active_unique
        ON rag_team_memberships(team_id, user_id)
        WHERE status = 'active';
        """
    )
    execute("CREATE INDEX IF NOT EXISTS idx_documents_owner_user ON documents(owner_user_id);")
    execute("CREATE INDEX IF NOT EXISTS idx_documents_owner_team ON documents(owner_team_id);")
    execute("CREATE INDEX IF NOT EXISTS idx_documents_access_mode ON documents(access_mode);")
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rag_document_access_grants_document_status
        ON rag_document_access_grants(document_id, status);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rag_document_access_grants_subject_status
        ON rag_document_access_grants(subject_type, subject_id, status);
        """
    )
    execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_document_access_grants_active_unique
        ON rag_document_access_grants(document_id, subject_type, subject_id, access_level)
        WHERE status = 'active';
        """
    )


def normalize_position_scope(position_scope: str | None) -> str | None:
    if position_scope is None:
        return None

    normalized = position_scope.strip()
    if not normalized:
        return None

    if normalized not in POSITION_LABELS:
        raise ValueError("position_scope 只能是 operations、customer_service 或 finance")

    return normalized


def normalize_market_scope(market_scope: str | None) -> str | None:
    if market_scope is None:
        return None

    normalized = market_scope.strip().lower()
    if not normalized or normalized == "all":
        return None

    if normalized not in ALLOWED_MARKET_SCOPES:
        raise ValueError("market_scope 只能是 us、de 或 jp")

    return normalized


def normalize_store_scope(store_scope: str | None) -> str | None:
    if store_scope is None:
        return None

    normalized = store_scope.strip().lower()
    if not normalized or normalized == "all":
        return None

    if normalized not in ALLOWED_STORE_SCOPES:
        raise ValueError("store_scope 只能是 us_store、de_store 或 jp_store")

    return normalized


def normalize_field_scope(field_scope: str | None) -> str | None:
    if field_scope is None:
        return None

    normalized = field_scope.strip().lower()
    if not normalized or normalized == "all":
        return None

    if normalized not in ALLOWED_FIELD_SCOPES:
        raise ValueError(
            "field_scope 只能是 operations_listing、operations_inventory、operations_sales、"
            "customer_profile、customer_logistics、customer_after_sales、finance_invoice、"
            "finance_payment、finance_profit 或 finance_salary"
        )

    return normalized


def normalize_sensitivity_level(sensitivity_level: str | None) -> str | None:
    if sensitivity_level is None:
        return None

    normalized = sensitivity_level.strip().lower()
    if not normalized or normalized == "all":
        return None

    if normalized not in ALLOWED_SENSITIVITY_LEVELS:
        raise ValueError("sensitivity_level 只能是 internal、confidential 或 restricted")

    return normalized


def field_scopes_for_position(
    position: str | None,
    requested_field_scope: str | None = None,
) -> list[str]:
    normalized_requested = normalize_field_scope(requested_field_scope)
    if not position:
        return []

    allowed = sorted(
        field_scope
        for field_scope, positions in FIELD_SCOPE_POSITION_ALLOWLIST.items()
        if position in positions
    )

    if normalized_requested:
        return [normalized_requested] if normalized_requested in allowed else []

    return allowed


def sensitivity_levels_for_position(
    position: str | None,
    requested_max_sensitivity_level: str | None = None,
) -> list[str]:
    requested = normalize_sensitivity_level(requested_max_sensitivity_level)
    position_max = MAX_SENSITIVITY_LEVEL_BY_POSITION.get(position or "", "internal")
    max_level = requested or position_max
    max_rank = SENSITIVITY_LEVEL_ORDER.index(max_level)
    position_max_rank = SENSITIVITY_LEVEL_ORDER.index(position_max)
    allowed_rank = min(max_rank, position_max_rank)

    return list(SENSITIVITY_LEVEL_ORDER[: allowed_rank + 1])


def document_metadata_matches(
    document: dict,
    *,
    visibility: str,
    department: str | None,
    position_scope: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    sensitivity_level: str | None,
    owner_user_id: str | None,
    owner_team_id: str | None,
    access_mode: str,
) -> bool:
    return (
        document.get("visibility") == visibility
        and (document.get("department") or None) == (department or None)
        and (document.get("position_scope") or None) == (position_scope or None)
        and (document.get("market_scope") or None) == (market_scope or None)
        and (document.get("store_scope") or None) == (store_scope or None)
        and (document.get("field_scope") or None) == (field_scope or None)
        and (document.get("sensitivity_level") or None) == (sensitivity_level or None)
        and (document.get("owner_user_id") or None) == (owner_user_id or None)
        and (document.get("owner_team_id") or None) == (owner_team_id or None)
        and (document.get("access_mode") or "open") == (access_mode or "open")
    )


def clear_duplicate_documents(documents: list[dict]) -> None:
    for document in documents:
        clear_document_vectors(document["id"])
        update_deleted_document(document["id"])


def update_document_metadata(
    document_id: str,
    title: str,
    visibility: str,
    department: str | None,
    position_scope: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    sensitivity_level: str | None,
    owner_user_id: str | None,
    owner_team_id: str | None,
    access_mode: str,
    content_hash: str,
    version: int,
    status: str,
) -> None:
    fetch_one(
        """
        UPDATE documents
        SET title = %s,
            visibility = %s,
            department = %s,
            position_scope = %s,
            market_scope = %s,
            store_scope = %s,
            field_scope = %s,
            sensitivity_level = %s,
            owner_user_id = %s,
            owner_team_id = %s,
            access_mode = %s,
            content_hash = %s,
            version = %s,
            status = %s,
            updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (
            title,
            visibility,
            department,
            position_scope,
            market_scope,
            store_scope,
            field_scope,
            sensitivity_level,
            owner_user_id,
            owner_team_id,
            access_mode,
            content_hash,
            version,
            status,
            document_id,
        ),
    )


def clear_document_vectors(document_id: str) -> list[str]:
    rows = fetch_all(
        """
        SELECT id
        FROM document_chunks
        WHERE document_id = %s;
        """,
        (document_id,),
    )
    chunk_ids = [str(row[0]) for row in rows]

    if chunk_ids:
        vector_store.delete(ids=chunk_ids)

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM document_chunks
                WHERE document_id = %s;
                """,
                (document_id,),
            )
            cur.execute(
                """
                DELETE FROM document_parent_chunks
                WHERE document_id = %s;
                """,
                (document_id,),
            )

    return chunk_ids


def mark_missing_documents_deleted(
    active_sources: set[str],
    source_prefixes: list[str],
    visibility: str | None = None,
    department: str | None = None,
    position_scope: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    sensitivity_level: str | None = None,
) -> list[dict]:
    ensure_rag_document_scope_schema()
    where_parts = ["status = 'active'"]
    params = []

    if visibility is not None:
        where_parts.append("visibility = %s")
        params.append(visibility)

    if department is not None:
        where_parts.append("department IS NOT DISTINCT FROM %s")
        params.append(department)

    if position_scope is not None:
        where_parts.append("position_scope IS NOT DISTINCT FROM %s")
        params.append(normalize_position_scope(position_scope))

    if market_scope is not None:
        where_parts.append("market_scope IS NOT DISTINCT FROM %s")
        params.append(normalize_market_scope(market_scope))

    if store_scope is not None:
        where_parts.append("store_scope IS NOT DISTINCT FROM %s")
        params.append(normalize_store_scope(store_scope))

    if field_scope is not None:
        where_parts.append("field_scope IS NOT DISTINCT FROM %s")
        params.append(normalize_field_scope(field_scope))

    if sensitivity_level is not None:
        where_parts.append("sensitivity_level IS NOT DISTINCT FROM %s")
        params.append(normalize_sensitivity_level(sensitivity_level))

    rows = fetch_all(
        f"""
        SELECT id, title, source, version
        FROM documents
        WHERE {" AND ".join(where_parts)};
        """,
        tuple(params),
    )
    deleted_items = []

    for row in rows:
        document_id = str(row[0])
        title = row[1]
        source = row[2]
        version = row[3]

        if not source or not any(source.startswith(prefix) for prefix in source_prefixes):
            continue

        if source in active_sources:
            continue

        removed_chunk_ids = clear_document_vectors(document_id)
        update_deleted_document(document_id)
        deleted_items.append(
            {
                "document_id": document_id,
                "title": title,
                "source": source,
                "version": version,
                "status": "deleted",
                "update_action": "deleted",
                "removed_chunk_count": len(removed_chunk_ids),
            }
        )

    return deleted_items


def update_deleted_document(document_id: str) -> None:
    fetch_one(
        """
        UPDATE documents
        SET status = 'deleted',
            updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (document_id,),
    )
