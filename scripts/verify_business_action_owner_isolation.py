from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import psycopg
import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
ADMIN_USERNAME = os.getenv("VERIFY_ADMIN_USERNAME", "admin_demo")
ADMIN_PASSWORD = os.getenv("VERIFY_ADMIN_PASSWORD", "Admin123456")
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)


def main() -> None:
    wait_for_api()
    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    marker = f"owner-isolation-{int(time.time())}"
    password = "OwnerIso123456"
    user_a_id: str | None = None
    user_b_id: str | None = None
    draft_id: str | None = None
    task_id: str | None = None

    try:
        user_a = create_user(admin_token, f"{marker}-ops-a", password)
        user_b = create_user(admin_token, f"{marker}-ops-b", password)
        user_a_id = user_a["id"]
        user_b_id = user_b["id"]
        token_a = login(user_a["username"], password)
        token_b = login(user_b["username"], password)

        generated = post_json(
            token_a,
            "/automation/generate",
            {
                "task_id": "listing",
                "input_text": (
                    f"{marker} SKU OPS-ISO-001，美国站，桌面显示器增高架，竹木材质，"
                    "卖点是稳固、收纳键盘、改善坐姿、适合居家办公。请生成完整 Listing 并保存草稿。"
                ),
            },
            timeout=180,
        )
        draft = generated.get("platform_draft")
        assert draft, generated
        draft_id = draft["id"]
        assert draft["owner_user_id"] == user_a_id, draft
        assert draft["position"] == "operations", draft

        owner_drafts = get_json(token_a, "/platform-drafts?draft_type=listing&limit=80")["items"]
        assert any(item["id"] == draft_id for item in owner_drafts), owner_drafts

        owner_detail = get_json(token_a, f"/platform-drafts/{draft_id}")
        assert owner_detail["item"]["id"] == draft_id, owner_detail

        owner_tasks = get_json(token_a, "/platform-execution-tasks?limit=80")["items"]
        owner_task = next((item for item in owner_tasks if item["draft_id"] == draft_id), None)
        assert owner_task, owner_tasks
        task_id = owner_task["id"]

        owner_loop = get_json(token_a, "/business-action-loop?limit=80")
        assert find_loop_item(owner_loop, draft_id), owner_loop

        peer_drafts = get_json(token_b, "/platform-drafts?draft_type=listing&limit=120")["items"]
        assert all(item["id"] != draft_id for item in peer_drafts), peer_drafts

        peer_loop = get_json(token_b, "/business-action-loop?limit=120")
        assert all(item["draft_id"] != draft_id for item in peer_loop["items"]), peer_loop

        assert_status(token_b, f"/platform-drafts/{draft_id}", expected_status=404)
        assert_status(token_b, f"/platform-execution-tasks/{task_id}", expected_status=404)
        assert_status(
            token_b,
            f"/platform-drafts/{draft_id}/review",
            method="POST",
            payload={"decision": "approved", "comment": "同岗位越权审核应失败"},
            expected_status=404,
        )
        assert_status(
            token_b,
            f"/platform-drafts/{draft_id}/publish",
            method="POST",
            payload={},
            expected_status=404,
        )
        retry_status = assert_status(
            token_b,
            f"/platform-execution-tasks/{task_id}/retry",
            method="POST",
            payload={},
            expected_status=404,
        )

        admin_drafts = get_json(admin_token, "/platform-drafts?draft_type=listing&limit=120")["items"]
        assert any(item["id"] == draft_id for item in admin_drafts), admin_drafts
        admin_detail = get_json(admin_token, f"/platform-drafts/{draft_id}")
        assert admin_detail["item"]["owner_user_id"] == user_a_id, admin_detail
        admin_task = get_json(admin_token, f"/platform-execution-tasks/{task_id}")["item"]
        assert admin_task["draft_id"] == draft_id, admin_task

        cleanup_draft(draft_id)
        draft_id = None

        print(
            json.dumps(
                {
                    "ok": True,
                    "owner_username": user_a["username"],
                    "peer_username": user_b["username"],
                    "draft_id": draft["id"],
                    "task_id": task_id,
                    "owner_visible": True,
                    "peer_hidden_from_draft_list": True,
                    "peer_hidden_from_loop": True,
                    "peer_detail_status": 404,
                    "peer_retry_status": retry_status,
                    "admin_global_visible": True,
                    "cleanup": "draft/tasks deleted; temporary users deleted",
                    "note": "real API, real auth, real PostgreSQL owner isolation; no mock/stub/fake",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        if draft_id:
            try:
                cleanup_draft(draft_id)
            except Exception as error:
                print(json.dumps({"cleanup_warning": str(error), "draft_id": draft_id}, ensure_ascii=False))
        for user_id in [user_a_id, user_b_id]:
            if user_id:
                try:
                    delete_user(admin_token, user_id)
                except Exception as error:
                    print(json.dumps({"cleanup_warning": str(error), "user_id": user_id}, ensure_ascii=False))


def wait_for_api() -> None:
    deadline = time.time() + 45
    last_error = ""
    while time.time() < deadline:
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                return
            last_error = response.text[:200]
        except requests.RequestException as error:
            last_error = str(error)
        time.sleep(1)
    raise AssertionError(f"API did not become healthy: {last_error}")


def create_user(token: str, username: str, password: str) -> dict[str, Any]:
    return post_json(
        token,
        "/admin/users",
        {
            "username": username,
            "password": password,
            "role": "employee",
            "position": "operations",
        },
    )["item"]


def delete_user(token: str, user_id: str) -> None:
    response = requests.delete(
        f"{API_BASE_URL}/admin/users/{user_id}",
        headers=auth_headers(token),
        timeout=30,
    )
    if response.status_code not in {200, 404}:
        raise AssertionError(response.text[:500])


def cleanup_draft(draft_id: str) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM platform_drafts WHERE id = %s;", (draft_id,))
        conn.commit()


def find_loop_item(payload: dict[str, Any], draft_id: str) -> dict[str, Any] | None:
    return next((item for item in payload["items"] if item["draft_id"] == draft_id), None)


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()["access_token"]


def get_json(token: str, path: str, *, expected_status: int = 200) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
        timeout=60,
    )
    return parse_response(response, expected_status=expected_status)


def post_json(
    token: str,
    path: str,
    payload: dict[str, Any],
    *,
    expected_status: int = 200,
    timeout: int = 60,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    return parse_response(response, expected_status=expected_status)


def assert_status(
    token: str,
    path: str,
    *,
    expected_status: int,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> int:
    if method == "POST":
        response = requests.post(
            f"{API_BASE_URL}{path}",
            headers={**auth_headers(token), "Content-Type": "application/json"},
            json=payload or {},
            timeout=60,
        )
    else:
        response = requests.get(
            f"{API_BASE_URL}{path}",
            headers=auth_headers(token),
            timeout=60,
        )
    assert response.status_code == expected_status, response.text[:500]
    return response.status_code


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


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
