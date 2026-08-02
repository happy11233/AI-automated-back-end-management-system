from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

db_stub = types.ModuleType("app.db")
db_stub.execute = lambda *args, **kwargs: None
db_stub.fetch_all = lambda *args, **kwargs: []
db_stub.fetch_one = lambda *args, **kwargs: None
sys.modules.setdefault("app.db", db_stub)

config_stub = types.ModuleType("app.config")
config_stub.settings = types.SimpleNamespace(chat_thread_retention_days=30)
sys.modules.setdefault("app.config", config_stub)

json_utils_stub = types.ModuleType("app.json_utils")
json_utils_stub.dumps_json = lambda value: json.dumps(value, ensure_ascii=False)
sys.modules.setdefault("app.json_utils", json_utils_stub)

run_record_stub = types.ModuleType("app.services.run_record_service")
run_record_stub.sanitize_metadata = lambda value: value
sys.modules.setdefault("app.services.run_record_service", run_record_stub)

from app.services import logging_service  # noqa: E402


def main() -> None:
    if os.getenv("VERIFY_CHAT_THREAD_PRIVACY_LIVE") == "1":
        verify_live_api()
        return

    owner = {
        "id": "user-finance",
        "role": "employee",
        "position": "finance",
    }
    other_user = {
        "id": "user-operations",
        "role": "employee",
        "position": "operations",
    }
    admin = {
        "id": "user-admin",
        "role": "admin",
        "position": None,
    }

    thread = {
        "id": "thread-finance",
        "user_id": owner["id"],
        "position": "finance",
    }
    assert logging_service.thread_belongs_to_user(thread, owner) is True
    assert logging_service.thread_belongs_to_user(thread, other_user) is False
    assert logging_service.thread_belongs_to_user(thread, admin) is False

    original_get_thread = logging_service.get_thread
    original_fetch_all = logging_service.fetch_all
    captured: dict[str, object] = {}
    try:
        logging_service.get_thread = lambda thread_id: thread if thread_id == thread["id"] else None
        assert logging_service.get_thread_for_user(thread["id"], owner) == thread
        assert logging_service.get_thread_for_user(thread["id"], admin) is None

        def capture_fetch_all(query: str, params: tuple[object, ...]):
            captured["query"] = query
            captured["params"] = params
            return []

        logging_service.fetch_all = capture_fetch_all
        logging_service.list_chat_threads(admin, limit=10)
    finally:
        logging_service.get_thread = original_get_thread
        logging_service.fetch_all = original_fetch_all

    query = str(captured.get("query") or "")
    params = captured.get("params")
    assert "t.user_id = %s" in query, query
    assert isinstance(params, tuple), params
    assert params[0] == admin["id"], params
    assert "t.user_id = %s" in query and "updated_at" in query, query

    print(
        json.dumps(
            {
                "ok": True,
                "owner_can_read_own_thread": True,
                "employee_cross_user_blocked": True,
                "admin_cross_user_blocked": True,
                "thread_list_always_scoped_to_current_user": True,
                "note": "pure permission/query regression; no database mutation",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def verify_live_api() -> None:
    import requests

    api_base = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
    accounts = {
        "admin": ("admin_demo", "Admin123456"),
        "finance": ("finance_demo", "Finance123456"),
        "operations": ("operations_demo", "Operations123456"),
    }

    tokens: dict[str, str] = {}
    users: dict[str, dict] = {}
    for name, (username, password) in accounts.items():
        login_response = requests.post(
            f"{api_base}/auth/login",
            data={"username": username, "password": password},
            timeout=30,
        )
        assert login_response.status_code == 200, login_response.text[:500]
        tokens[name] = login_response.json()["access_token"]
        me_response = requests.get(
            f"{api_base}/auth/me",
            headers={"Authorization": f"Bearer {tokens[name]}"},
            timeout=30,
        )
        assert me_response.status_code == 200, me_response.text[:500]
        users[name] = me_response.json()

    def headers(name: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {tokens[name]}"}

    def get_json(name: str, path: str) -> dict:
        response = requests.get(f"{api_base}{path}", headers=headers(name), timeout=30)
        assert response.status_code == 200, response.text[:500]
        return response.json()

    finance_threads = get_json("finance", "/threads")["items"]
    assert finance_threads, "财务账号没有可用于隔离验证的会话"
    finance_thread_id = finance_threads[0]["id"]
    finance_thread_messages = requests.get(
        f"{api_base}/threads/{finance_thread_id}/messages",
        headers=headers("finance"),
        timeout=30,
    )
    assert finance_thread_messages.status_code == 200, finance_thread_messages.text[:500]

    admin_threads = get_json("admin", "/threads")["items"]
    operations_threads = get_json("operations", "/threads")["items"]
    finance_ids = {item["id"] for item in finance_threads}
    assert not finance_ids.intersection({item["id"] for item in admin_threads}), admin_threads
    assert not finance_ids.intersection({item["id"] for item in operations_threads}), operations_threads

    cross_messages = requests.get(
        f"{api_base}/threads/{finance_thread_id}/messages",
        headers=headers("admin"),
        timeout=30,
    )
    assert cross_messages.status_code == 404, cross_messages.text[:500]

    cross_operations_messages = requests.get(
        f"{api_base}/threads/{finance_thread_id}/messages",
        headers=headers("operations"),
        timeout=30,
    )
    assert cross_operations_messages.status_code == 404, cross_operations_messages.text[:500]

    cross_title = requests.patch(
        f"{api_base}/threads/{finance_thread_id}",
        headers={**headers("admin"), "Content-Type": "application/json"},
        json={"title": "越权标题测试"},
        timeout=30,
    )
    assert cross_title.status_code == 404, cross_title.text[:500]

    cross_chat = requests.post(
        f"{api_base}/chat",
        headers={**headers("admin"), "Content-Type": "application/json"},
        json={"message": "只做权限隔离测试，不执行任务", "thread_id": finance_thread_id},
        timeout=30,
    )
    assert cross_chat.status_code == 404, cross_chat.text[:500]

    cross_stream = requests.post(
        f"{api_base}/chat/stream",
        headers={**headers("admin"), "Content-Type": "application/json"},
        json={"message": "只做权限隔离测试，不执行任务", "thread_id": finance_thread_id},
        timeout=30,
    )
    assert cross_stream.status_code == 404, cross_stream.text[:500]

    admin_latest = get_json("admin", "/threads/latest")["item"]
    if admin_latest is not None:
        assert str(admin_latest["user_id"]) == str(users["admin"]["id"]), admin_latest

    records = get_json("admin", "/run-records?limit=1")
    assert "items" in records, records

    print(
        json.dumps(
            {
                "ok": True,
                "api_base": api_base,
                "finance_thread_checked": finance_thread_id,
                "admin_thread_list_is_private": True,
                "employee_cross_user_messages_status": cross_operations_messages.status_code,
                "admin_cross_user_messages_status": cross_messages.status_code,
                "admin_cross_user_title_status": cross_title.status_code,
                "admin_cross_user_chat_status": cross_chat.status_code,
                "admin_cross_user_stream_status": cross_stream.status_code,
                "admin_run_records_still_available": True,
                "note": "real API, real auth, existing PostgreSQL data; no test thread created",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
