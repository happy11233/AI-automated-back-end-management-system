from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import close_pool, open_pool  # noqa: E402
from app.rag.ingest import ensure_rag_document_scope_schema  # noqa: E402


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
ADMIN_USERNAME = os.getenv("VERIFY_ADMIN_USERNAME", "admin_demo")
ADMIN_PASSWORD = os.getenv("VERIFY_ADMIN_PASSWORD", "Admin123456")
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)


def main() -> None:
    marker = f"verify-rag-auth-{int(time.time())}-{uuid4().hex[:8]}"
    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    password = "VerifyRagAuth123456"
    created_user_ids: list[str] = []
    document_ids: dict[str, str] = {}

    ensure_schema()

    try:
        ops_user = post_json(
            admin_token,
            "/admin/users",
            {
                "username": f"{marker}_ops",
                "password": password,
                "role": "employee",
                "position": "operations",
            },
        )["item"]
        finance_user = post_json(
            admin_token,
            "/admin/users",
            {
                "username": f"{marker}_finance",
                "password": password,
                "role": "employee",
                "position": "finance",
            },
        )["item"]
        created_user_ids.extend([ops_user["id"], finance_user["id"]])

        employee_token = login(ops_user["username"], password)
        employee_forbidden = get_raw(employee_token, "/rag-teams")
        assert employee_forbidden.status_code == 403, employee_forbidden.text[:500]
        employee_documents_forbidden = get_raw(employee_token, "/documents")
        assert employee_documents_forbidden.status_code == 403, employee_documents_forbidden.text[:500]

        team = post_json(
            admin_token,
            "/rag-teams",
            {
                "team_key": marker,
                "name": f"{marker} 运营授权组",
                "description": "RAG 授权管理 API 真实验证临时团队",
                "position_scope": "operations",
                "market_scope": "de",
                "store_scope": "de_store",
            },
        )["item"]
        team_id = team["id"]
        assert team["team_key"] == marker, team
        assert team["position_scope"] == "operations", team

        listed_teams = get_json(admin_token, "/rag-teams")["items"]
        assert any(item["id"] == team_id for item in listed_teams), listed_teams[:5]

        member = post_json(
            admin_token,
            f"/rag-teams/{team_id}/members",
            {
                "user_id": ops_user["id"],
                "member_role": "member",
                "expires_at": future_iso(days=7),
            },
        )["item"]
        assert member["team_id"] == team_id, member
        assert member["user_id"] == ops_user["id"], member
        assert member["status"] == "active", member

        idempotent_member = post_json(
            admin_token,
            f"/rag-teams/{team_id}/members",
            {
                "user_id": ops_user["id"],
                "member_role": "supervisor",
                "expires_at": future_iso(days=10),
            },
        )["item"]
        assert idempotent_member["id"] == member["id"], idempotent_member
        assert idempotent_member["member_role"] == "supervisor", idempotent_member

        bad_member = post_json(
            admin_token,
            f"/rag-teams/{team_id}/members",
            {
                "user_id": finance_user["id"],
                "member_role": "member",
            },
            expected_status=400,
        )
        assert "岗位" in json.dumps(bad_member, ensure_ascii=False), bad_member

        members = get_json(admin_token, f"/rag-teams/{team_id}/members")["items"]
        assert any(item["user_id"] == ops_user["id"] and item["status"] == "active" for item in members), members

        updated_team = patch_json(
            admin_token,
            f"/rag-teams/{team_id}",
            {
                "description": "已通过 RAG 授权管理 API 更新",
                "market_scope": "us",
                "store_scope": "us_store",
                "status": "active",
            },
        )["item"]
        assert updated_team["market_scope"] == "us", updated_team
        assert updated_team["store_scope"] == "us_store", updated_team

        document_ids["ops"] = seed_document(
            marker=marker,
            key="ops",
            title="运营授权验证文档",
            position_scope="operations",
            field_scope="operations_listing",
            sensitivity_level="internal",
        )
        document_ids["finance"] = seed_document(
            marker=marker,
            key="finance",
            title="财务越权验证文档",
            position_scope="finance",
            field_scope="finance_salary",
            sensitivity_level="restricted",
        )

        document_list = get_json(admin_token, f"/documents?search={quote(marker)}&limit=20")
        listed_document_ids = {item["id"] for item in document_list["items"]}
        assert document_ids["ops"] in listed_document_ids, document_list
        assert document_ids["finance"] in listed_document_ids, document_list
        assert_no_document_body_payload(document_list["items"])
        assert_document_list_fields(document_list["items"])

        ops_title_search = get_json(admin_token, f"/documents?search={quote('运营授权验证文档')}&limit=20")["items"]
        assert any(item["id"] == document_ids["ops"] for item in ops_title_search), ops_title_search

        ops_id_search = get_json(admin_token, f"/documents?search={quote(document_ids['ops'])}&limit=20")["items"]
        assert any(item["id"] == document_ids["ops"] for item in ops_id_search), ops_id_search

        missing_owner_upload = upload_file(
            admin_token,
            filename=f"{marker}-missing-owner.txt",
            content=f"{marker} missing owner upload should be rejected",
            data={
                "visibility": "employee",
                "position_scope": "operations",
                "field_scope": "operations_listing",
                "sensitivity_level": "internal",
                "access_mode": "owner_only",
            },
            expected_status=400,
        )
        assert "owner_user_id" in json.dumps(missing_owner_upload, ensure_ascii=False), missing_owner_upload

        uploaded = upload_file(
            admin_token,
            filename=f"{marker}-owner-upload.txt",
            content=(
                f"{marker} 上传 owner-only 授权验证文档。\n"
                "该文档用于验证管理员上传时可以直接设置 owner 用户和访问模式。"
            ),
            data={
                "visibility": "employee",
                "position_scope": "operations",
                "field_scope": "operations_listing",
                "sensitivity_level": "internal",
                "access_mode": "owner_only",
                "owner_user_id": ops_user["id"],
            },
        )
        uploaded_document_id = uploaded["document_id"]
        assert uploaded["access_mode"] == "owner_only", uploaded
        assert uploaded["owner_user_id"] == ops_user["id"], uploaded
        uploaded_access = get_json(admin_token, f"/documents/{uploaded_document_id}/access")["item"]
        assert uploaded_access["access_mode"] == "owner_only", uploaded_access
        assert uploaded_access["owner_user_id"] == ops_user["id"], uploaded_access
        upload_search = get_json(admin_token, f"/documents?search={quote(marker + '-owner-upload')}&limit=20")["items"]
        assert any(item["id"] == uploaded_document_id for item in upload_search), upload_search

        uploaded_with_grant = upload_file(
            admin_token,
            filename=f"{marker}-grant-upload.txt",
            content=(
                f"{marker} 上传时直接创建初始 grant 验证文档。\n"
                "该文档用于验证上传接口可以在入库后创建有效用户授权。"
            ),
            data={
                "visibility": "employee",
                "position_scope": "operations",
                "field_scope": "operations_listing",
                "sensitivity_level": "internal",
                "access_mode": "explicit_grants",
                "grant_subject_type": "user",
                "grant_subject_id": ops_user["id"],
                "grant_access_level": "read",
                "grant_reason": "verify-rag-upload-initial-grant",
                "grant_expires_at": future_iso(days=7),
            },
        )
        uploaded_grant_document_id = uploaded_with_grant["document_id"]
        initial_grant = uploaded_with_grant["initial_grant"]
        assert initial_grant["document_id"] == uploaded_grant_document_id, initial_grant
        assert initial_grant["subject_type"] == "user", initial_grant
        assert initial_grant["subject_id"] == ops_user["id"], initial_grant
        upload_grants = get_json(admin_token, f"/documents/{uploaded_grant_document_id}/grants")["items"]
        assert any(item["id"] == initial_grant["id"] for item in upload_grants), upload_grants

        cross_position_upload_grant = upload_file(
            admin_token,
            filename=f"{marker}-cross-grant-upload.txt",
            content=f"{marker} cross position upload grant should be rejected",
            data={
                "visibility": "employee",
                "position_scope": "finance",
                "field_scope": "finance_salary",
                "sensitivity_level": "restricted",
                "access_mode": "explicit_grants",
                "grant_subject_type": "user",
                "grant_subject_id": ops_user["id"],
                "grant_access_level": "read",
            },
            expected_status=400,
        )
        assert "岗位" in json.dumps(cross_position_upload_grant, ensure_ascii=False), cross_position_upload_grant

        access = patch_json(
            admin_token,
            f"/documents/{document_ids['ops']}/access",
            {
                "access_mode": "owner_and_grants",
                "owner_user_id": ops_user["id"],
                "owner_team_id": team_id,
            },
        )["item"]
        assert access["id"] == document_ids["ops"], access
        assert access["access_mode"] == "owner_and_grants", access
        assert access["owner_user_id"] == ops_user["id"], access
        assert access["owner_team_id"] == team_id, access

        access_detail = get_json(admin_token, f"/documents/{document_ids['ops']}/access")["item"]
        assert access_detail["access_mode"] == "owner_and_grants", access_detail

        user_grant = post_json(
            admin_token,
            f"/documents/{document_ids['ops']}/grants",
            {
                "subject_type": "user",
                "subject_id": ops_user["id"],
                "access_level": "read",
                "reason": "verify-rag-authorization-admin-api",
                "expires_at": future_iso(days=14),
            },
        )["item"]
        assert user_grant["document_id"] == document_ids["ops"], user_grant
        assert user_grant["subject_type"] == "user", user_grant
        assert user_grant["status"] == "active", user_grant

        team_grant = post_json(
            admin_token,
            f"/documents/{document_ids['ops']}/grants",
            {
                "subject_type": "team",
                "subject_id": team_id,
                "access_level": "manage",
                "reason": "verify-rag-authorization-admin-api-team",
                "expires_at": future_iso(days=14),
            },
        )["item"]
        assert team_grant["subject_type"] == "team", team_grant
        assert team_grant["subject_id"] == team_id, team_grant

        cross_position_grant = post_json(
            admin_token,
            f"/documents/{document_ids['finance']}/grants",
            {
                "subject_type": "user",
                "subject_id": ops_user["id"],
                "access_level": "read",
                "reason": "should-be-rejected",
                "expires_at": future_iso(days=1),
            },
            expected_status=400,
        )
        assert "岗位" in json.dumps(cross_position_grant, ensure_ascii=False), cross_position_grant

        grants = get_json(admin_token, f"/documents/{document_ids['ops']}/grants")["items"]
        assert any(item["id"] == user_grant["id"] for item in grants), grants
        assert any(item["id"] == team_grant["id"] for item in grants), grants

        revoked = delete_json(admin_token, f"/documents/{document_ids['ops']}/grants/{user_grant['id']}")
        assert revoked["ok"] is True, revoked
        assert revoked["item"]["status"] == "revoked", revoked

        removed = delete_json(admin_token, f"/rag-teams/{team_id}/members/{ops_user['id']}")
        assert removed["ok"] is True, removed

        audits = {
            "team_create": find_audit(
                admin_token,
                action="admin.rag_team.create",
                resource_type="rag_team",
                resource_id=team_id,
                marker=marker,
            ),
            "team_update": find_audit(
                admin_token,
                action="admin.rag_team.update",
                resource_type="rag_team",
                resource_id=team_id,
                marker=marker,
            ),
            "member_add": find_audit(
                admin_token,
                action="admin.rag_team.member_add",
                resource_type="rag_team",
                resource_id=team_id,
                marker=marker,
            ),
            "member_remove": find_audit(
                admin_token,
                action="admin.rag_team.member_remove",
                resource_type="rag_team",
                resource_id=team_id,
                marker=marker,
            ),
            "access_update": find_audit(
                admin_token,
                action="admin.rag_document.access_update",
                resource_type="rag_document",
                resource_id=document_ids["ops"],
                marker=marker,
            ),
            "grant_create": find_audit(
                admin_token,
                action="admin.rag_document.grant_create",
                resource_type="rag_document_grant",
                resource_id=user_grant["id"],
                marker=marker,
            ),
            "grant_revoke": find_audit(
                admin_token,
                action="admin.rag_document.grant_revoke",
                resource_type="rag_document_grant",
                resource_id=user_grant["id"],
                marker=marker,
            ),
        }
        missing = [name for name, item in audits.items() if not item]
        assert not missing, f"缺少审计记录：{missing}"
        assert_no_sensitive_audit_payloads(audits)

        print(
            json.dumps(
                {
                    "ok": True,
                    "marker": marker,
                    "team_id": team_id,
                    "ops_user_id": ops_user["id"],
                    "document_id": document_ids["ops"],
                    "uploaded_document_id": uploaded_document_id,
                    "uploaded_grant_document_id": uploaded_grant_document_id,
                    "initial_upload_grant_id": initial_grant["id"],
                    "employee_admin_access_status": employee_forbidden.status_code,
                    "employee_document_list_status": employee_documents_forbidden.status_code,
                    "document_list_count": document_list["total"],
                    "member_id": member["id"],
                    "idempotent_member_role": idempotent_member["member_role"],
                    "user_grant_id": user_grant["id"],
                    "team_grant_id": team_grant["id"],
                    "audit_ids": {name: item["id"] for name, item in audits.items() if item},
                    "note": "real API, real auth, real PostgreSQL RAG authorization admin API and audit; no mock/stub/fake/monkeypatch",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup_records(marker)


def ensure_schema() -> None:
    open_pool()
    try:
        ensure_rag_document_scope_schema()
    finally:
        close_pool()


def seed_document(
    *,
    marker: str,
    key: str,
    title: str,
    position_scope: str,
    field_scope: str,
    sensitivity_level: str,
) -> str:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
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
                    access_mode,
                    content_hash,
                    version,
                    status
                )
                VALUES (
                    %s,
                    %s,
                    'employee',
                    NULL,
                    %s,
                    %s,
                    %s,
                    'open',
                    %s,
                    1,
                    'active'
                )
                RETURNING id;
                """,
                (
                    f"{marker} {title}",
                    f"verify-rag-authorization-admin-api/{marker}/{key}",
                    position_scope,
                    field_scope,
                    sensitivity_level,
                    f"verify-rag-authorization-admin-api-{marker}-{key}",
                ),
            )
            document_id = str(cur.fetchone()[0])
        conn.commit()

    return document_id


def cleanup_records(marker: str) -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM documents WHERE source LIKE %s OR source LIKE %s;",
                (
                    f"verify-rag-authorization-admin-api/{marker}/%",
                    f"upload/{marker}%",
                ),
            )
            cur.execute("DELETE FROM rag_teams WHERE team_key = %s;", (marker,))
            cur.execute("DELETE FROM users WHERE username LIKE %s;", (f"{marker}_%",))
        conn.commit()


def find_audit(
    token: str,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    marker: str,
) -> dict[str, Any] | None:
    payload = get_json(token, f"/admin/audit-logs?action={action}&resource_type={resource_type}&limit=200")
    for item in payload["items"]:
        if item.get("resource_id") != resource_id:
            continue
        metadata = item.get("metadata") or {}
        serialized = json.dumps(metadata, ensure_ascii=False)
        if marker in serialized or metadata.get("document_id") == resource_id or item.get("resource_id") == resource_id:
            return item
    return None


def assert_no_sensitive_audit_payloads(audits: dict[str, dict[str, Any] | None]) -> None:
    forbidden_fragments = [
        "Bearer ",
        "database_url",
        "api_key",
        "jwt",
        "password",
        "运营授权验证文档正文",
    ]
    serialized = json.dumps(audits, ensure_ascii=False).lower()
    for fragment in forbidden_fragments:
        assert fragment.lower() not in serialized, f"审计记录泄露敏感片段：{fragment}"


def assert_no_document_body_payload(items: list[dict[str, Any]]) -> None:
    forbidden_keys = {"content", "body", "text", "chunks", "metadata", "content_hash"}
    for item in items:
        leaked_keys = sorted(forbidden_keys.intersection(item.keys()))
        assert not leaked_keys, f"文档列表泄露正文或索引字段：{leaked_keys}"


def assert_document_list_fields(items: list[dict[str, Any]]) -> None:
    required_keys = {
        "id",
        "title",
        "source",
        "visibility",
        "position_scope",
        "field_scope",
        "sensitivity_level",
        "access_mode",
        "status",
        "updated_at",
    }
    for item in items:
        missing = sorted(required_keys.difference(item.keys()))
        assert not missing, f"文档列表缺少字段：{missing}"


def future_iso(*, days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def login(username: str, password: str) -> str:
    payload = post_form("/auth/login", {"username": username, "password": password})
    token = payload.get("access_token")
    if not token:
        raise AssertionError(f"登录响应缺少 access_token：{username}, payload={payload}")
    return str(token)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def get_json(token: str, path: str, *, expected_status: int = 200) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
        timeout=30,
    )
    return parse_response(response, expected_status=expected_status)


def get_raw(token: str, path: str) -> requests.Response:
    return requests.get(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
        timeout=30,
    )


def post_json(
    token: str,
    path: str,
    payload: dict[str, Any],
    *,
    expected_status: int = 200,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    return parse_response(response, expected_status=expected_status)


def patch_json(
    token: str,
    path: str,
    payload: dict[str, Any],
    *,
    expected_status: int = 200,
) -> dict[str, Any]:
    response = requests.patch(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    return parse_response(response, expected_status=expected_status)


def delete_json(token: str, path: str, *, expected_status: int = 200) -> dict[str, Any]:
    response = requests.delete(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
        timeout=30,
    )
    return parse_response(response, expected_status=expected_status)


def upload_file(
    token: str,
    *,
    filename: str,
    content: str,
    data: dict[str, str],
    expected_status: int = 200,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/admin/documents/upload",
        headers=auth_headers(token),
        data=data,
        files={
            "file": (
                filename,
                content.encode("utf-8"),
                "text/plain",
            )
        },
        timeout=60,
    )
    return parse_response(response, expected_status=expected_status)


def post_form(
    path: str,
    payload: dict[str, str],
    *,
    expected_status: int = 200,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        data=payload,
        timeout=30,
    )
    return parse_response(response, expected_status=expected_status)


def parse_response(response: requests.Response, *, expected_status: int) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = {"detail": response.text}

    if response.status_code != expected_status:
        raise AssertionError(
            f"请求状态不符合预期：expected={expected_status}, actual={response.status_code}, payload={payload}"
        )

    return payload


if __name__ == "__main__":
    main()
