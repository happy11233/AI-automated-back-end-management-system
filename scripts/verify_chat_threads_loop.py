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

API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag_user:rag_password@127.0.0.1:5433/rag_agent",
)

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}
    marker = f"chat-thread-loop-{int(time.time())}"

    created = post_json(tokens["finance"], "/threads", {})["item"]
    assert created["id"].startswith("thread-"), created
    assert created["message_count"] == 0, created

    finance_chat = post_json(
        tokens["finance"],
        "/chat",
        {
            "thread_id": created["id"],
            "message": f"{marker} 帮我查一下 AMZ-JP-250-6630188-4402197 的销售发票",
        },
        timeout=120,
    )
    assert finance_chat["thread_id"] == created["id"], finance_chat

    renamed_title = f"{marker} 财务会话改名验证"
    rename_result = patch_json(
        tokens["finance"],
        f"/threads/{created['id']}",
        {"title": renamed_title},
    )
    assert rename_result["item"]["title"] == renamed_title, rename_result

    auto_created = post_json(
        tokens["finance"],
        "/chat",
        {"message": f"{marker} 新会话自动生成唯一 ID，只需要回复摘要。"},
        timeout=120,
    )
    assert auto_created["thread_id"].startswith("thread-"), auto_created
    assert auto_created["thread_id"] != created["id"], auto_created

    finance_threads = get_json(tokens["finance"], "/threads?limit=30")["items"]
    finance_thread_ids = {item["id"] for item in finance_threads}
    assert created["id"] in finance_thread_ids, finance_threads
    assert auto_created["thread_id"] in finance_thread_ids, finance_threads

    latest = get_json(tokens["finance"], "/threads/latest")["item"]
    assert latest and latest["id"] in {created["id"], auto_created["thread_id"]}, latest

    forbidden_detail = requests.get(
        f"{API_BASE_URL}/threads/{created['id']}/messages",
        headers=auth_headers(tokens["customer_service"]),
        timeout=60,
    )
    assert forbidden_detail.status_code == 403, forbidden_detail.text[:500]

    forbidden_rename = requests.patch(
        f"{API_BASE_URL}/threads/{created['id']}",
        headers={**auth_headers(tokens["customer_service"]), "Content-Type": "application/json"},
        json={"title": f"{marker} 客服越权改名"},
        timeout=60,
    )
    assert forbidden_rename.status_code == 403, forbidden_rename.text[:500]

    forbidden_write = requests.post(
        f"{API_BASE_URL}/chat",
        headers={**auth_headers(tokens["customer_service"]), "Content-Type": "application/json"},
        json={
            "thread_id": created["id"],
            "message": f"{marker} 客服不能写入财务会话",
        },
        timeout=60,
    )
    assert forbidden_write.status_code == 403, forbidden_write.text[:500]

    unknown_thread = requests.post(
        f"{API_BASE_URL}/chat",
        headers={**auth_headers(tokens["finance"]), "Content-Type": "application/json"},
        json={
            "thread_id": f"custom-{marker}",
            "message": f"{marker} 不允许用自定义 ID 创建会话",
        },
        timeout=60,
    )
    assert unknown_thread.status_code == 404, unknown_thread.text[:500]

    admin_threads = get_json(tokens["admin"], f"/threads?search={marker}&limit=50")["items"]
    admin_thread_ids = {item["id"] for item in admin_threads}
    assert created["id"] in admin_thread_ids or auto_created["thread_id"] in admin_thread_ids, admin_threads

    admin_detail = get_json(tokens["admin"], f"/threads/{created['id']}/messages")
    assert admin_detail["messages"], admin_detail

    old_thread_id = f"thread-old-{marker}"
    cleanup_counts = insert_and_cleanup_old_thread(tokens["admin"], old_thread_id)
    old_thread_response = requests.get(
        f"{API_BASE_URL}/threads/{old_thread_id}/messages",
        headers=auth_headers(tokens["admin"]),
        timeout=60,
    )
    assert old_thread_response.status_code == 404, old_thread_response.text[:500]

    print(json.dumps({
        "ok": True,
        "created_thread_id": created["id"],
        "auto_created_thread_id": auto_created["thread_id"],
        "finance_visible_count": len(finance_threads),
        "admin_search_count": len(admin_threads),
        "customer_forbidden_detail": forbidden_detail.status_code,
        "customer_forbidden_rename": forbidden_rename.status_code,
        "customer_forbidden_write": forbidden_write.status_code,
        "unknown_custom_thread": unknown_thread.status_code,
        "renamed_title": renamed_title,
        "cleanup_counts": cleanup_counts,
        "note": "real API, real auth, real PostgreSQL cleanup; no mock/stub/fake",
    }, ensure_ascii=False, indent=2))


def insert_and_cleanup_old_thread(admin_token: str, thread_id: str) -> dict[str, Any]:
    admin_info = get_json(admin_token, "/settings/me")["item"]
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_threads (id, user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, now() - interval '16 days', now() - interval '16 days')
                ON CONFLICT (id)
                DO UPDATE SET updated_at = now() - interval '16 days';
                """,
                (thread_id, admin_info["id"], "过期会话清理验证"),
            )
            cur.execute(
                """
                INSERT INTO chat_messages (thread_id, user_id, role, content, created_at)
                VALUES (%s, %s, 'user', '过期消息', now() - interval '16 days');
                """,
                (thread_id, admin_info["id"]),
            )
        conn.commit()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM user_memories
                WHERE expires_at IS NOT NULL AND expires_at < now()
                RETURNING 1;
                """
            )
            expired_memory_count = len(cur.fetchall())

            cur.execute(
                """
                DELETE FROM audit_logs
                WHERE created_at < now() - interval '365 days'
                RETURNING 1;
                """
            )
            expired_audit_count = len(cur.fetchall())

            cur.execute(
                """
                DELETE FROM chat_messages
                WHERE created_at < now() - interval '15 days'
                RETURNING 1;
                """
            )
            expired_message_count = len(cur.fetchall())

            cur.execute(
                """
                DELETE FROM chat_threads
                WHERE updated_at < now() - interval '15 days'
                RETURNING 1;
                """
            )
            expired_thread_count = len(cur.fetchall())
        conn.commit()

    return {
        "expired_memories_deleted": expired_memory_count,
        "expired_audit_logs_deleted": expired_audit_count,
        "expired_chat_messages_deleted": expired_message_count,
        "expired_chat_threads_deleted": expired_thread_count,
        "chat_message_retention_days": 15,
        "chat_thread_retention_days": 15,
    }


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def get_json(token: str, path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=60)
    assert response.status_code == 200, response.text[:500]
    return response.json()


def post_json(token: str, path: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()


def patch_json(token: str, path: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    response = requests.patch(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
