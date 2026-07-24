from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import close_pool, open_pool  # noqa: E402
from app.rag.ingest import ensure_rag_document_scope_schema  # noqa: E402
from app.rag.retriever import _load_keyword_corpus, build_metadata_filter  # noqa: E402


DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)


def main() -> None:
    marker = f"RAG-SCOPE-{int(time.time())}-{uuid4().hex[:8]}"

    open_pool()
    try:
        ensure_rag_document_scope_schema()
        document_ids = seed_scope_documents(marker)

        operations_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
        )
        customer_service_chunks = _load_keyword_corpus(
            role="employee",
            department="客服部",
            position="customer_service",
        )
        finance_chunks = _load_keyword_corpus(
            role="employee",
            department="财务部",
            position="finance",
        )
        admin_chunks = _load_keyword_corpus(
            role="admin",
            department="管理部",
            position=None,
        )
        vector_filter = build_metadata_filter(
            role="employee",
            department="运营部",
            position="operations",
        )

        assert has_source(operations_chunks, f"verify-rag-position-scope/{marker}/operations"), operations_chunks
        assert not has_source(customer_service_chunks, f"verify-rag-position-scope/{marker}/operations"), customer_service_chunks
        assert not has_source(finance_chunks, f"verify-rag-position-scope/{marker}/operations"), finance_chunks
        assert has_source(admin_chunks, f"verify-rag-position-scope/{marker}/operations"), admin_chunks
        assert "position_scope" in json.dumps(vector_filter, ensure_ascii=False), vector_filter

        assert all(
            chunk.get("position_scope") in {None, "", "operations"}
            for chunk in operations_chunks
        ), summarize_chunks(operations_chunks)
        assert all(
            chunk.get("position_scope") in {None, "", "customer_service"}
            for chunk in customer_service_chunks
        ), summarize_chunks(customer_service_chunks)
        assert all(
            chunk.get("position_scope") in {None, "", "finance"}
            for chunk in finance_chunks
        ), summarize_chunks(finance_chunks)

        print(
            json.dumps(
                {
                    "ok": True,
                    "marker": marker,
                    "seeded_document_ids": document_ids,
                    "operations_sources": source_list(operations_chunks),
                    "customer_service_sources": source_list(customer_service_chunks),
                    "finance_sources": source_list(finance_chunks),
                    "admin_sources": source_list(admin_chunks),
                    "vector_filter": vector_filter,
                    "note": "real PostgreSQL RAG keyword filtering plus vector metadata filter inspection; no mock/stub/fake/monkeypatch",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup_scope_documents(marker)
        close_pool()


def seed_scope_documents(marker: str) -> list[str]:
    import psycopg

    embedding = "[" + ",".join(["0.001"] * 1024) + "]"
    documents = [
        {
            "title": f"{marker} 运营专属 Listing 规则",
            "source": f"verify-rag-position-scope/{marker}/operations",
            "department": "运营部",
            "position_scope": "operations",
            "content": f"{marker} 运营专属 Listing 审核规则：标题必须包含品牌、核心关键词和站点差异。",
        },
        {
            "title": f"{marker} 客服专属售后规则",
            "source": f"verify-rag-position-scope/{marker}/customer-service",
            "department": "客服部",
            "position_scope": "customer_service",
            "content": f"{marker} 客服专属售后规则：退款前必须确认物流节点和客户沟通记录。",
        },
        {
            "title": f"{marker} 财务专属对账规则",
            "source": f"verify-rag-position-scope/{marker}/finance",
            "department": "财务部",
            "position_scope": "finance",
            "content": f"{marker} 财务专属对账规则：付款流水必须和销售发票、总账分录逐笔核对。",
        },
    ]

    document_ids: list[str] = []
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for item in documents:
                cur.execute(
                    """
                    INSERT INTO documents (
                        title,
                        source,
                        visibility,
                        department,
                        position_scope,
                        content_hash,
                        version,
                        status
                    )
                    VALUES (%s, %s, 'employee', %s, %s, %s, 1, 'active')
                    RETURNING id;
                    """,
                    (
                        item["title"],
                        item["source"],
                        item["department"],
                        item["position_scope"],
                        f"verify-{marker}-{item['position_scope']}",
                    ),
                )
                document_id = str(cur.fetchone()[0])
                document_ids.append(document_id)
                parent_id = str(uuid4())
                chunk_id = str(uuid4())
                metadata = {
                    "document_id": document_id,
                    "title": item["title"],
                    "source": item["source"],
                    "visibility": "employee",
                    "department": item["department"],
                    "position_scope": item["position_scope"],
                    "status": "active",
                    "parent_index": 0,
                    "chunk_id": chunk_id,
                    "parent_chunk_id": parent_id,
                    "chunk_index": 0,
                }
                cur.execute(
                    """
                    INSERT INTO document_parent_chunks (
                        id,
                        document_id,
                        parent_index,
                        content,
                        metadata
                    )
                    VALUES (%s, %s, 0, %s, %s::jsonb);
                    """,
                    (
                        parent_id,
                        document_id,
                        item["content"],
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
                cur.execute(
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
                    VALUES (
                        %s,
                        %s,
                        %s,
                        0,
                        %s,
                        %s::vector,
                        'text-embedding-v4',
                        %s::jsonb
                    );
                    """,
                    (
                        chunk_id,
                        document_id,
                        parent_id,
                        item["content"],
                        embedding,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
        conn.commit()

    return document_ids


def cleanup_scope_documents(marker: str) -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM documents
                WHERE source LIKE %s;
                """,
                (f"verify-rag-position-scope/{marker}/%",),
            )
        conn.commit()


def has_source(chunks: list[dict[str, Any]], source: str) -> bool:
    return any(chunk.get("source") == source for chunk in chunks)


def source_list(chunks: list[dict[str, Any]]) -> list[str]:
    return [str(chunk.get("source") or "") for chunk in chunks if chunk.get("source")]


def summarize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source": chunk.get("source"),
            "department": chunk.get("department"),
            "position_scope": chunk.get("position_scope"),
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    main()
