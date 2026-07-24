from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
ADMIN_USERNAME = os.getenv("VERIFY_ADMIN_USERNAME", "admin_demo")
ADMIN_PASSWORD = os.getenv("VERIFY_ADMIN_PASSWORD", "Admin123456")


def main() -> None:
    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    marker = f"verify_admin_user_{int(time.time())}"
    username = f"{marker}_finance"
    password = "VerifyUser123456"
    created_id: str | None = None

    try:
        weak_password = post_json(
            admin_token,
            "/admin/users",
            {
                "username": f"{marker}_weak",
                "password": "123",
                "role": "employee",
                "position": "finance",
            },
            expected_status=422,
        )
        assert "password" in json.dumps(weak_password, ensure_ascii=False), weak_password

        invalid_position = post_json(
            admin_token,
            "/admin/users",
            {
                "username": f"{marker}_bad_position",
                "password": password,
                "role": "employee",
                "position": "sales",
            },
            expected_status=422,
        )
        assert "position" in json.dumps(invalid_position, ensure_ascii=False), invalid_position

        created = post_json(
            admin_token,
            "/admin/users",
            {
                "username": username,
                "password": password,
                "role": "employee",
                "position": "finance",
            },
        )["item"]
        created_id = created["id"]

        assert created["username"] == username, created
        assert created["role"] == "employee", created
        assert created["position"] == "finance", created
        assert created["department"] == "财务部", created
        assert "Salary Slip" in created["erp_scopes"], created
        assert "finance-excel-transform" in created["allowed_ai_app_ids"], created
        assert "password" not in json.dumps(created, ensure_ascii=False).lower(), created

        users = get_json(admin_token, "/admin/users")["items"]
        assert any(item["id"] == created_id for item in users), users[:3]

        employee_token = login(username, password)
        me = get_json(employee_token, "/auth/me")
        assert me["username"] == username, me
        assert me["role"] == "employee", me
        assert me["position"] == "finance", me
        assert "Salary Slip" in me["erp_scopes"], me

        employee_forbidden = get_raw(employee_token, "/admin/users")
        assert employee_forbidden.status_code == 403, employee_forbidden.text[:500]

        create_audit = find_audit_log(
            admin_token,
            action="admin.user.create",
            resource_id=created_id,
            username=username,
        )
        permission_audit = find_audit_log(
            admin_token,
            action="admin.user.permission_assignment",
            resource_id=created_id,
            username=username,
        )

        assert create_audit, "未找到 admin.user.create 审计记录"
        assert permission_audit, "未找到 admin.user.permission_assignment 审计记录"
        assert permission_audit["metadata"].get("position") == "finance", permission_audit
        assert "Salary Slip" in permission_audit["metadata"].get("erp_scopes", []), permission_audit

        delete_result = delete_json(admin_token, f"/admin/users/{created_id}")
        assert delete_result["ok"] is True, delete_result
        assert delete_result["deleted_user_id"] == created_id, delete_result
        created_id = None

        deleted_login = post_form(
            "/auth/login",
            {"username": username, "password": password},
            expected_status=401,
        )
        assert "用户名或密码错误" in json.dumps(deleted_login, ensure_ascii=False), deleted_login

        print(
            json.dumps(
                {
                    "ok": True,
                    "created_username": username,
                    "created_position": "finance",
                    "weak_password_status": 422,
                    "invalid_position_status": 422,
                    "employee_admin_access_status": employee_forbidden.status_code,
                    "create_audit_id": create_audit["id"],
                    "permission_audit_id": permission_audit["id"],
                    "cleanup": "deleted",
                    "note": "real API, real auth, real PostgreSQL user lifecycle and audit logs; no mock/stub/fake",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        if created_id:
            cleanup_response = requests.delete(
                f"{API_BASE_URL}/admin/users/{created_id}",
                headers=auth_headers(admin_token),
                timeout=30,
            )
            if cleanup_response.status_code not in {200, 404}:
                print(
                    json.dumps(
                        {
                            "cleanup_warning": True,
                            "user_id": created_id,
                            "status": cleanup_response.status_code,
                            "body": cleanup_response.text[:500],
                        },
                        ensure_ascii=False,
                    )
                )


def find_audit_log(
    token: str,
    *,
    action: str,
    resource_id: str,
    username: str,
) -> dict[str, Any] | None:
    payload = get_json(token, f"/admin/audit-logs?action={action}&resource_type=user&limit=80")
    for item in payload["items"]:
        if item.get("resource_id") != resource_id:
            continue
        metadata = item.get("metadata") or {}
        if metadata.get("created_username") == username:
            return item
    return None


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


def delete_json(token: str, path: str, *, expected_status: int = 200) -> dict[str, Any]:
    response = requests.delete(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
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
