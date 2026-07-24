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
from app.db import close_pool, fetch_all, open_pool  # noqa: E402
from app.rag.ingest import ensure_rag_document_scope_schema  # noqa: E402
from app.rag.retriever import (  # noqa: E402
    _new_authorization_audit_collector,
    _retrieve_keyword_candidates,
    _write_rag_authorization_audit,
)


DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)


def main() -> None:
    marker = f"RAG-AUTH-AUDIT-{int(time.time())}-{uuid4().hex[:8]}"
    query = f"ragAuditToken{uuid4().hex[:10]} authorization audit"
    seeded: dict[str, Any] | None = None

    open_pool()
    try:
        ensure_rag_document_scope_schema()
        seeded = seed_records(marker=marker, query_token=query)
        user_a = seeded["users"]["ops_a"]
        user_b = seeded["users"]["ops_b"]
        documents = seeded["documents"]

        collector_a = _new_authorization_audit_collector()
        user_a_chunks = _retrieve_keyword_candidates(
            query=query,
            role="employee",
            user_id=user_a,
            department="运营部",
            position="operations",
            market_scope=None,
            store_scope=None,
            field_scope=None,
            max_sensitivity_level=None,
            candidate_k=10,
            audit_collector=collector_a,
        )
        assert has_document(user_a_chunks, documents["owner_only"]), summarize_chunks(user_a_chunks)
        assert has_document(user_a_chunks, documents["user_grant"]), summarize_chunks(user_a_chunks)
        _write_rag_authorization_audit(
            query=query,
            role="employee",
            user_id=user_a,
            department="运营部",
            position="operations",
            market_scope=None,
            store_scope=None,
            field_scope=None,
            max_sensitivity_level=None,
            chunks=user_a_chunks,
            audit_collector=collector_a,
        )

        collector_b = _new_authorization_audit_collector()
        user_b_chunks = _retrieve_keyword_candidates(
            query=query,
            role="employee",
            user_id=user_b,
            department="运营部",
            position="operations",
            market_scope=None,
            store_scope=None,
            field_scope=None,
            max_sensitivity_level=None,
            candidate_k=10,
            audit_collector=collector_b,
        )
        assert not has_document(user_b_chunks, documents["owner_only"]), summarize_chunks(user_b_chunks)
        assert not has_document(user_b_chunks, documents["user_grant"]), summarize_chunks(user_b_chunks)
        _write_rag_authorization_audit(
            query=query,
            role="employee",
            user_id=user_b,
            department="运营部",
            position="operations",
            market_scope=None,
            store_scope=None,
            field_scope=None,
            max_sensitivity_level=None,
            chunks=user_b_chunks,
            audit_collector=collector_b,
        )

        owner_hit = find_audit(
            action="rag.authorization.hit",
            user_id=user_a,
            document_id=documents["owner_only"],
        )
        grant_hit = find_audit(
            action="rag.authorization.hit",
            user_id=user_a,
            document_id=documents["user_grant"],
        )
        owner_deny = find_audit(
            action="rag.authorization.deny",
            user_id=user_b,
            document_id=documents["owner_only"],
        )
        grant_deny = find_audit(
            action="rag.authorization.deny",
            user_id=user_b,
            document_id=documents["user_grant"],
        )

        assert owner_hit, "未找到 owner_user 命中审计"
        assert grant_hit, "未找到 user_grant 命中审计"
        assert owner_deny, "未找到 owner_only 拒绝审计"
        assert grant_deny, "未找到 user_grant 拒绝审计"
        assert owner_hit["metadata"].get("rag_access_reason") == "owner_user", owner_hit
        assert grant_hit["metadata"].get("rag_access_reason") == "user_grant", grant_hit
        assert owner_deny["metadata"].get("rag_access_reason") == "not_owner_or_grant", owner_deny
        assert grant_deny["metadata"].get("rag_access_reason") == "not_owner_or_grant", grant_deny
        assert owner_hit["metadata"].get("rag_access_result") == "hit", owner_hit
        assert owner_deny["metadata"].get("rag_access_result") == "deny", owner_deny
        assert "query_hash" in owner_hit["metadata"], owner_hit
        assert "query_hash" in owner_deny["metadata"], owner_deny
        assert_no_sensitive_payloads(
            marker=marker,
            query=query,
            audits=[owner_hit, grant_hit, owner_deny, grant_deny],
        )

        print(
            json.dumps(
                {
                    "ok": True,
                    "marker": marker,
                    "owner_document_id": documents["owner_only"],
                    "grant_document_id": documents["user_grant"],
                    "user_a_chunk_documents": source_documents(user_a_chunks),
                    "user_b_chunk_documents": source_documents(user_b_chunks),
                    "audit_ids": {
                        "owner_hit": owner_hit["id"],
                        "grant_hit": grant_hit["id"],
                        "owner_deny": owner_deny["id"],
                        "grant_deny": grant_deny["id"],
                    },
                    "note": "real PostgreSQL keyword retrieval authorization hit/deny audit; no mock/stub/fake/monkeypatch",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup_records(marker)
        close_pool()


def seed_records(*, marker: str, query_token: str) -> dict[str, Any]:
    import psycopg

    embedding = "[" + ",".join(["0.001"] * 1024) + "]"
    users: dict[str, str] = {}
    documents: dict[str, str] = {}

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for key in ["ops_a", "ops_b"]:
                cur.execute(
                    """
                    INSERT INTO users (
                        username,
                        role,
                        position,
                        department,
                        display_name,
                        email,
                        password_hash
                    )
                    VALUES (%s, 'employee', 'operations', '运营部', %s, %s, 'verify-only')
                    RETURNING id;
                    """,
                    (
                        f"verify_{marker}_{key}",
                        f"{marker} {key}",
                        f"verify-{marker}-{key}@example.com",
                    ),
                )
                users[key] = str(cur.fetchone()[0])

            docs = [
                {
                    "key": "owner_only",
                    "title": "owner 命中与拒绝审计文档",
                    "access_mode": "owner_only",
                    "owner_user_id": users["ops_a"],
                    "grant_user": None,
                },
                {
                    "key": "user_grant",
                    "title": "user grant 命中与拒绝审计文档",
                    "access_mode": "explicit_grants",
                    "owner_user_id": None,
                    "grant_user": users["ops_a"],
                },
            ]

            for item in docs:
                cur.execute(
                    """
                    INSERT INTO documents (
                        title,
                        source,
                        visibility,
                        department,
                        position_scope,
                        field_scope,
                        sensitivity_level,
                        owner_user_id,
                        access_mode,
                        content_hash,
                        version,
                        status
                    )
                    VALUES (
                        %s,
                        %s,
                        'employee',
                        '运营部',
                        'operations',
                        'operations_listing',
                        'internal',
                        %s,
                        %s,
                        %s,
                        1,
                        'active'
                    )
                    RETURNING id;
                    """,
                    (
                        f"{marker} {item['title']}",
                        f"verify-rag-authorization-audit/{marker}/{item['key']}",
                        item["owner_user_id"],
                        item["access_mode"],
                        f"verify-rag-authorization-audit-{marker}-{item['key']}",
                    ),
                )
                document_id = str(cur.fetchone()[0])
                documents[item["key"]] = document_id
                parent_id = str(uuid4())
                chunk_id = str(uuid4())
                content = (
                    f"{query_token} {marker} {item['title']}。"
                    "这段内容只用于 RAG 授权审计真实验证。"
                )
                metadata = {
                    "document_id": document_id,
                    "title": f"{marker} {item['title']}",
                    "source": f"verify-rag-authorization-audit/{marker}/{item['key']}",
                    "visibility": "employee",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
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
                    (parent_id, document_id, content, json.dumps(metadata, ensure_ascii=False)),
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
                    VALUES (%s, %s, %s, 0, %s, %s::vector, 'text-embedding-v4', %s::jsonb);
                    """,
                    (
                        chunk_id,
                        document_id,
                        parent_id,
                        content,
                        embedding,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )

                if item["grant_user"]:
                    cur.execute(
                        """
                        INSERT INTO rag_document_access_grants (
                            document_id,
                            subject_type,
                            subject_id,
                            access_level,
                            status,
                            granted_by,
                            reason
                        )
                        VALUES (%s, 'user', %s, 'read', 'active', NULL, 'verify-rag-authorization-audit');
                        """,
                        (document_id, item["grant_user"]),
                    )

        conn.commit()

    return {"users": users, "documents": documents}


def cleanup_records(marker: str) -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE source LIKE %s;", (f"verify-rag-authorization-audit/{marker}/%",))
            cur.execute("DELETE FROM users WHERE username LIKE %s;", (f"verify_{marker}_%",))
        conn.commit()


def find_audit(*, action: str, user_id: str, document_id: str) -> dict[str, Any] | None:
    rows = fetch_all(
        """
        SELECT id, user_id, action, resource_type, resource_id, metadata, created_at
        FROM audit_logs
        WHERE action = %s
          AND resource_type = 'rag_document'
          AND resource_id = %s
          AND user_id = %s
        ORDER BY created_at DESC
        LIMIT 5;
        """,
        (action, document_id, user_id),
    )
    for row in rows:
        metadata = row[5] or {}
        if metadata.get("document_id") == document_id:
            return {
                "id": str(row[0]),
                "user_id": str(row[1]) if row[1] else None,
                "action": row[2],
                "resource_type": row[3],
                "resource_id": row[4],
                "metadata": metadata,
                "created_at": row[6],
            }
    return None


def assert_no_sensitive_payloads(*, marker: str, query: str, audits: list[dict[str, Any]]) -> None:
    serialized = json.dumps(audits, ensure_ascii=False, default=str)
    forbidden = [
        marker,
        query,
        "这段内容只用于",
        "Bearer ",
        "database_url",
        "api_key",
        "jwt",
        "password",
    ]
    for item in forbidden:
        assert item not in serialized, f"审计 payload 泄露敏感片段：{item}"


def has_document(chunks: list[dict[str, Any]], document_id: str) -> bool:
    return any(str(chunk.get("document_id")) == document_id for chunk in chunks)


def source_documents(chunks: list[dict[str, Any]]) -> list[str]:
    return sorted({str(chunk.get("document_id")) for chunk in chunks if chunk.get("document_id")})


def summarize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": chunk.get("document_id"),
            "source": chunk.get("source"),
            "access_mode": chunk.get("access_mode"),
            "authorization_reason": chunk.get("authorization_reason"),
            "retrieval_sources": chunk.get("retrieval_sources"),
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    main()
