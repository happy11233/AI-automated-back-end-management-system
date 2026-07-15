from hashlib import sha256
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db import fetch_all, fetch_one, transaction
from app.json_utils import dumps_json
from app.llm import embed_texts
from app.rag.vector_store import vector_store

# 文档入库

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
    content_hash: str | None = None,
) -> str:
    row = fetch_one(
        """
        INSERT INTO documents (title, source, visibility, department, content_hash)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """,
        (title, source, visibility, department, content_hash),
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
        raw_documents=[document],
    )


def ingest_documents(
    title: str,
    source: str,
    visibility: str,
    raw_documents: list[Document],
    department: str | None = None,
) -> dict:
    return upsert_documents(
        title=title,
        source=source,
        visibility=visibility,
        raw_documents=raw_documents,
        department=department,
    )


def upsert_documents(
    title: str,
    source: str,
    visibility: str,
    raw_documents: list[Document],
    department: str | None = None,
) -> dict:
    content_hash = calculate_documents_hash(raw_documents)
    active_documents = find_active_documents_by_source(source)
    existing_document = active_documents[0] if active_documents else None
    duplicate_documents = active_documents[1:]

    if existing_document and existing_document["content_hash"] == content_hash:
        clear_duplicate_documents(duplicate_documents)
        return {
            "document_id": existing_document["id"],
            "content_hash": content_hash,
            "version": existing_document["version"],
            "status": existing_document["status"],
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
        }

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
        SELECT id, content_hash, version, status
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
        }
        for row in rows
    ]


def clear_duplicate_documents(documents: list[dict]) -> None:
    for document in documents:
        clear_document_vectors(document["id"])
        update_deleted_document(document["id"])


def update_document_metadata(
    document_id: str,
    title: str,
    visibility: str,
    department: str | None,
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
) -> list[dict]:
    where_parts = ["status = 'active'"]
    params = []

    if visibility is not None:
        where_parts.append("visibility = %s")
        params.append(visibility)

    if department is not None:
        where_parts.append("department IS NOT DISTINCT FROM %s")
        params.append(department)

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
