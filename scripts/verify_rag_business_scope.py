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
    marker = f"RAG-BIZ-SCOPE-{int(time.time())}-{uuid4().hex[:8]}"

    open_pool()
    try:
        ensure_rag_document_scope_schema()
        document_ids = seed_scope_documents(marker)

        common_source = f"verify-rag-business-scope/{marker}/common"
        us_store_source = f"verify-rag-business-scope/{marker}/us-store"
        de_store_source = f"verify-rag-business-scope/{marker}/de-store"

        default_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
        )
        us_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
            market_scope="us",
            store_scope="us_store",
        )
        de_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
            market_scope="de",
            store_scope="de_store",
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
            market_scope="de",
            store_scope="de_store",
        )

        assert has_source(default_chunks, common_source), summarize_chunks(default_chunks)
        assert not has_source(default_chunks, us_store_source), summarize_chunks(default_chunks)
        assert not has_source(default_chunks, de_store_source), summarize_chunks(default_chunks)

        assert has_source(us_chunks, common_source), summarize_chunks(us_chunks)
        assert has_source(us_chunks, us_store_source), summarize_chunks(us_chunks)
        assert not has_source(us_chunks, de_store_source), summarize_chunks(us_chunks)

        assert has_source(de_chunks, common_source), summarize_chunks(de_chunks)
        assert has_source(de_chunks, de_store_source), summarize_chunks(de_chunks)
        assert not has_source(de_chunks, us_store_source), summarize_chunks(de_chunks)

        assert has_source(admin_chunks, us_store_source), summarize_chunks(admin_chunks)
        assert has_source(admin_chunks, de_store_source), summarize_chunks(admin_chunks)

        vector_filter_text = json.dumps(vector_filter, ensure_ascii=False)
        assert "market_scope" in vector_filter_text, vector_filter
        assert "store_scope" in vector_filter_text, vector_filter
        assert "de_store" in vector_filter_text, vector_filter

        print(
            json.dumps(
                {
                    "ok": True,
                    "marker": marker,
                    "seeded_document_ids": document_ids,
                    "default_sources": source_list(default_chunks),
                    "us_sources": source_list(us_chunks),
                    "de_sources": source_list(de_chunks),
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
            "title": f"{marker} 运营通用 Listing 规则",
            "source": f"verify-rag-business-scope/{marker}/common",
            "market_scope": None,
            "store_scope": None,
            "content": f"{marker} 运营通用 Listing 规则：标题必须包含品牌和核心关键词。",
        },
        {
            "title": f"{marker} 美国站 US Store Listing 规则",
            "source": f"verify-rag-business-scope/{marker}/us-store",
            "market_scope": "us",
            "store_scope": "us_store",
            "content": f"{marker} 美国站 US Store 专属规则：标题必须包含 FDA 合规提示。",
        },
        {
            "title": f"{marker} 德国站 DE Store Listing 规则",
            "source": f"verify-rag-business-scope/{marker}/de-store",
            "market_scope": "de",
            "store_scope": "de_store",
            "content": f"{marker} 德国站 DE Store 专属规则：标题必须包含德语合规关键词。",
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
                        market_scope,
                        store_scope,
                        content_hash,
                        version,
                        status
                    )
                    VALUES (%s, %s, 'employee', '运营部', 'operations', %s, %s, %s, 1, 'active')
                    RETURNING id;
                    """,
                    (
                        item["title"],
                        item["source"],
                        item["market_scope"],
                        item["store_scope"],
                        f"verify-{marker}-{item['source']}",
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
                    "department": "运营部",
                    "position_scope": "operations",
                    "status": "active",
                    "parent_index": 0,
                    "chunk_id": chunk_id,
                    "parent_chunk_id": parent_id,
                    "chunk_index": 0,
                }
                if item["market_scope"]:
                    metadata["market_scope"] = item["market_scope"]
                if item["store_scope"]:
                    metadata["store_scope"] = item["store_scope"]

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
                (f"verify-rag-business-scope/{marker}/%",),
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
            "market_scope": chunk.get("market_scope"),
            "store_scope": chunk.get("store_scope"),
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    main()
