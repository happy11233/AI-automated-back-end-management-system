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
from app.rag.retriever import _filter_authorized_candidates, _load_keyword_corpus  # noqa: E402


DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)


def main() -> None:
    marker = f"RAG-USER-TEAM-{int(time.time())}-{uuid4().hex[:8]}"

    open_pool()
    try:
        ensure_rag_document_scope_schema()
        seeded = seed_authorization_records(marker)
        users = seeded["users"]
        documents = seeded["documents"]

        user_a_chunks = _load_keyword_corpus(
            role="employee",
            user_id=users["ops_a"],
            department="运营部",
            position="operations",
        )
        user_b_chunks = _load_keyword_corpus(
            role="employee",
            user_id=users["ops_b"],
            department="运营部",
            position="operations",
        )
        anonymous_employee_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
        )
        admin_chunks = _load_keyword_corpus(role="admin")

        assert has_source(user_a_chunks, source(marker, "open")), summarize_chunks(user_a_chunks)
        assert has_source(user_b_chunks, source(marker, "open")), summarize_chunks(user_b_chunks)
        assert has_source(anonymous_employee_chunks, source(marker, "open")), summarize_chunks(anonymous_employee_chunks)

        assert has_source(user_a_chunks, source(marker, "owner-only-a")), summarize_chunks(user_a_chunks)
        assert not has_source(user_b_chunks, source(marker, "owner-only-a")), summarize_chunks(user_b_chunks)
        assert not has_source(anonymous_employee_chunks, source(marker, "owner-only-a")), summarize_chunks(
            anonymous_employee_chunks
        )

        assert has_source(user_a_chunks, source(marker, "team-only-ops")), summarize_chunks(user_a_chunks)
        assert not has_source(user_b_chunks, source(marker, "team-only-ops")), summarize_chunks(user_b_chunks)

        assert has_source(user_b_chunks, source(marker, "explicit-user-b")), summarize_chunks(user_b_chunks)
        assert not has_source(user_a_chunks, source(marker, "explicit-user-b")), summarize_chunks(user_a_chunks)

        assert has_source(user_a_chunks, source(marker, "owner-and-grants")), summarize_chunks(user_a_chunks)
        assert has_source(user_b_chunks, source(marker, "owner-and-grants")), summarize_chunks(user_b_chunks)

        assert has_source(user_a_chunks, source(marker, "explicit-team-ops")), summarize_chunks(user_a_chunks)
        assert not has_source(user_b_chunks, source(marker, "explicit-team-ops")), summarize_chunks(user_b_chunks)

        assert not has_source(user_b_chunks, source(marker, "expired-grant-b")), summarize_chunks(user_b_chunks)
        assert not has_source(user_a_chunks, source(marker, "finance-granted-to-ops-a")), summarize_chunks(user_a_chunks)

        assert has_source(admin_chunks, source(marker, "owner-only-a")), summarize_chunks(admin_chunks)
        assert has_source(admin_chunks, source(marker, "team-only-ops")), summarize_chunks(admin_chunks)
        assert has_source(admin_chunks, source(marker, "finance-granted-to-ops-a")), summarize_chunks(admin_chunks)

        vector_candidates = build_vector_candidates(marker, documents)
        user_a_vector_chunks = _filter_authorized_candidates(
            vector_candidates,
            role="employee",
            user_id=users["ops_a"],
            department="运营部",
            position="operations",
            market_scope=None,
            store_scope=None,
            field_scope=None,
            max_sensitivity_level=None,
        )
        user_b_vector_chunks = _filter_authorized_candidates(
            vector_candidates,
            role="employee",
            user_id=users["ops_b"],
            department="运营部",
            position="operations",
            market_scope=None,
            store_scope=None,
            field_scope=None,
            max_sensitivity_level=None,
        )

        assert has_source(user_a_vector_chunks, source(marker, "owner-only-a")), summarize_chunks(user_a_vector_chunks)
        assert not has_source(user_b_vector_chunks, source(marker, "owner-only-a")), summarize_chunks(
            user_b_vector_chunks
        )
        assert has_source(user_a_vector_chunks, source(marker, "explicit-team-ops")), summarize_chunks(
            user_a_vector_chunks
        )
        assert not has_source(user_a_vector_chunks, source(marker, "finance-granted-to-ops-a")), summarize_chunks(
            user_a_vector_chunks
        )

        revoke_user_b_grant(documents["explicit-user-b"], users["ops_b"])
        user_b_after_revoke_chunks = _load_keyword_corpus(
            role="employee",
            user_id=users["ops_b"],
            department="运营部",
            position="operations",
        )
        assert not has_source(user_b_after_revoke_chunks, source(marker, "explicit-user-b")), summarize_chunks(
            user_b_after_revoke_chunks
        )

        print(
            json.dumps(
                {
                    "ok": True,
                    "marker": marker,
                    "users": users,
                    "documents": documents,
                    "user_a_sources": source_list(user_a_chunks, marker),
                    "user_b_sources": source_list(user_b_chunks, marker),
                    "user_b_after_revoke_sources": source_list(user_b_after_revoke_chunks, marker),
                    "admin_sources": source_list(admin_chunks, marker),
                    "vector_user_a_sources": source_list(user_a_vector_chunks, marker),
                    "vector_user_b_sources": source_list(user_b_vector_chunks, marker),
                    "note": "real PostgreSQL RAG user/team authorization filtering; no mock/stub/fake/monkeypatch",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup_authorization_records(marker)
        close_pool()


def seed_authorization_records(marker: str) -> dict[str, dict[str, str]]:
    import psycopg

    embedding = "[" + ",".join(["0.001"] * 1024) + "]"
    users: dict[str, str] = {}
    documents: dict[str, str] = {}

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for key, role, position, department in [
                ("admin", "admin", None, "管理部"),
                ("ops_a", "employee", "operations", "运营部"),
                ("ops_b", "employee", "operations", "运营部"),
            ]:
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
                    VALUES (%s, %s, %s, %s, %s, %s, 'verify-only')
                    RETURNING id;
                    """,
                    (
                        f"verify_{marker}_{key}",
                        role,
                        position,
                        department,
                        f"{marker} {key}",
                        f"verify-{marker}-{key}@example.com",
                    ),
                )
                users[key] = str(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO rag_teams (
                    team_key,
                    name,
                    description,
                    position_scope,
                    status,
                    created_by
                )
                VALUES (%s, %s, %s, 'operations', 'active', %s)
                RETURNING id;
                """,
                (
                    f"verify-{marker}-ops-team",
                    f"{marker} 运营项目组",
                    "RAG 用户/团队授权真实验证临时团队",
                    users["admin"],
                ),
            )
            team_id = str(cur.fetchone()[0])

            for user_key, membership_status in [("ops_a", "active"), ("ops_b", "paused")]:
                cur.execute(
                    """
                    INSERT INTO rag_team_memberships (
                        team_id,
                        user_id,
                        member_role,
                        status,
                        added_by
                    )
                    VALUES (%s, %s, 'member', %s, %s);
                    """,
                    (team_id, users[user_key], membership_status, users["admin"]),
                )

            docs = [
                {
                    "key": "open",
                    "title": "开放知识",
                    "access_mode": "open",
                    "department": None,
                    "position_scope": None,
                    "field_scope": None,
                    "sensitivity_level": None,
                    "owner_user_id": None,
                    "owner_team_id": None,
                },
                {
                    "key": "owner-only-a",
                    "title": "A 个人知识",
                    "access_mode": "owner_only",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
                    "owner_user_id": users["ops_a"],
                    "owner_team_id": None,
                },
                {
                    "key": "team-only-ops",
                    "title": "运营项目组知识",
                    "access_mode": "team_only",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
                    "owner_user_id": None,
                    "owner_team_id": team_id,
                },
                {
                    "key": "explicit-user-b",
                    "title": "显式授权给 B 的知识",
                    "access_mode": "explicit_grants",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
                    "owner_user_id": None,
                    "owner_team_id": None,
                    "grant_user": users["ops_b"],
                },
                {
                    "key": "owner-and-grants",
                    "title": "A 拥有且授权给 B 的知识",
                    "access_mode": "owner_and_grants",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
                    "owner_user_id": users["ops_a"],
                    "owner_team_id": None,
                    "grant_user": users["ops_b"],
                },
                {
                    "key": "explicit-team-ops",
                    "title": "显式授权给运营项目组的知识",
                    "access_mode": "explicit_grants",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
                    "owner_user_id": None,
                    "owner_team_id": None,
                    "grant_team": team_id,
                },
                {
                    "key": "expired-grant-b",
                    "title": "B 已过期授权知识",
                    "access_mode": "explicit_grants",
                    "department": "运营部",
                    "position_scope": "operations",
                    "field_scope": "operations_listing",
                    "sensitivity_level": "internal",
                    "owner_user_id": None,
                    "owner_team_id": None,
                    "grant_user": users["ops_b"],
                    "expires_sql": "now() - interval '1 day'",
                },
                {
                    "key": "finance-granted-to-ops-a",
                    "title": "错误授权给运营 A 的财务工资知识",
                    "access_mode": "explicit_grants",
                    "department": None,
                    "position_scope": "finance",
                    "field_scope": "finance_salary",
                    "sensitivity_level": "restricted",
                    "owner_user_id": None,
                    "owner_team_id": None,
                    "grant_user": users["ops_a"],
                },
            ]

            for item in docs:
                content = f"{marker} {item['title']}：这是用户团队级授权验证内容。"
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
                        owner_team_id,
                        access_mode,
                        content_hash,
                        version,
                        status
                    )
                    VALUES (
                        %s,
                        %s,
                        'employee',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
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
                        source(marker, item["key"]),
                        item["department"],
                        item["position_scope"],
                        item["field_scope"],
                        item["sensitivity_level"],
                        item["owner_user_id"],
                        item["owner_team_id"],
                        item["access_mode"],
                        f"verify-{marker}-{item['key']}",
                    ),
                )
                document_id = str(cur.fetchone()[0])
                documents[item["key"]] = document_id
                parent_id = str(uuid4())
                chunk_id = str(uuid4())
                metadata = {
                    "document_id": document_id,
                    "title": f"{marker} {item['title']}",
                    "source": source(marker, item["key"]),
                    "visibility": "employee",
                    "department": item["department"],
                    "position_scope": item["position_scope"],
                    "field_scope": item["field_scope"],
                    "sensitivity_level": item["sensitivity_level"],
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

                if item.get("grant_user"):
                    insert_grant(
                        cur=cur,
                        document_id=document_id,
                        subject_type="user",
                        subject_id=item["grant_user"],
                        granted_by=users["admin"],
                        expires_sql=item.get("expires_sql"),
                    )
                if item.get("grant_team"):
                    insert_grant(
                        cur=cur,
                        document_id=document_id,
                        subject_type="team",
                        subject_id=item["grant_team"],
                        granted_by=users["admin"],
                        expires_sql=item.get("expires_sql"),
                    )

        conn.commit()

    return {"users": users, "documents": documents}


def insert_grant(
    *,
    cur,
    document_id: str,
    subject_type: str,
    subject_id: str,
    granted_by: str,
    expires_sql: str | None,
) -> None:
    expires_expression = expires_sql or "NULL"
    cur.execute(
        f"""
        INSERT INTO rag_document_access_grants (
            document_id,
            subject_type,
            subject_id,
            access_level,
            status,
            granted_by,
            reason,
            expires_at
        )
        VALUES (%s, %s, %s, 'read', 'active', %s, 'verify-rag-user-team-authorization', {expires_expression});
        """,
        (document_id, subject_type, subject_id, granted_by),
    )


def revoke_user_b_grant(document_id: str, user_id: str) -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE rag_document_access_grants
                SET status = 'revoked',
                    updated_at = now()
                WHERE document_id = %s
                  AND subject_type = 'user'
                  AND subject_id = %s
                  AND status = 'active';
                """,
                (document_id, user_id),
            )
        conn.commit()


def cleanup_authorization_records(marker: str) -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE source LIKE %s;", (f"verify-rag-user-team/{marker}/%",))
            cur.execute("DELETE FROM rag_teams WHERE team_key = %s;", (f"verify-{marker}-ops-team",))
            cur.execute("DELETE FROM users WHERE username LIKE %s;", (f"verify_{marker}_%",))
        conn.commit()


def build_vector_candidates(marker: str, documents: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": f"vector-{key}",
            "parent_chunk_id": None,
            "document_id": document_id,
            "content": f"vector candidate {key}",
            "title": key,
            "source": source(marker, key),
            "visibility": "employee",
            "score": 1.0,
            "vector_score": 1.0,
            "keyword_score": 0.0,
            "rank": index,
            "retrieval_sources": ["vector"],
        }
        for index, (key, document_id) in enumerate(documents.items(), start=1)
    ]


def source(marker: str, key: str) -> str:
    return f"verify-rag-user-team/{marker}/{key}"


def has_source(chunks: list[dict[str, Any]], expected_source: str) -> bool:
    return any(chunk.get("source") == expected_source for chunk in chunks)


def source_list(chunks: list[dict[str, Any]], marker: str) -> list[str]:
    prefix = f"verify-rag-user-team/{marker}/"
    return [
        str(chunk.get("source") or "")
        for chunk in chunks
        if str(chunk.get("source") or "").startswith(prefix)
    ]


def summarize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source": chunk.get("source"),
            "position_scope": chunk.get("position_scope"),
            "field_scope": chunk.get("field_scope"),
            "sensitivity_level": chunk.get("sensitivity_level"),
            "access_mode": chunk.get("access_mode"),
            "owner_user_id": chunk.get("owner_user_id"),
            "owner_team_id": chunk.get("owner_team_id"),
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    main()
