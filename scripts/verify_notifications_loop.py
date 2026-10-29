"""Verify notification pagination and isolation using temporary PostgreSQL fixtures."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
import requests

from app.auth.security import hash_password
from app.config import settings

API = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def prepare(state_path: Path) -> None:
    if state_path.exists():
        raise FileExistsError(f"Cleanup the existing verification state first: {state_path}")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    marker = f"notification-ui-{uuid4().hex[:12]}"
    state = {"marker": marker, "accounts": {}, "feedback_ids": []}
    password = uuid4().hex
    with psycopg.connect(settings.database_url) as conn:
        for name, role in (("admin", "admin"), ("employee", "employee")):
            username = f"{marker}-{name}"
            user_id = str(uuid4())
            conn.execute(
                "INSERT INTO users (id, username, role, position, password_hash) VALUES (%s, %s, %s, %s, %s)",
                (user_id, username, role, "operations" if role == "employee" else None, hash_password(password)),
            )
            state["accounts"][name] = {"id": user_id, "username": username, "password": password}
            count = 95 if name == "admin" else 3
            for index in range(count):
                conn.execute(
                    """INSERT INTO notifications (user_id, type, title, body, status, resource_type, resource_id, metadata, read_at, created_at)
                    VALUES (%s, 'verification', %s, %s, %s, %s, %s, %s::jsonb,
                        CASE WHEN %s = 'read' THEN now() ELSE NULL END, now() - %s * interval '1 second')""",
                    (user_id, f"{marker}-{name}-{index:03d}", "通知筛选、分页和已读交互验收数据",
                     "unread" if index < 21 else "read", "feedback" if index % 2 == 0 else None,
                     f"{marker}-resource-{index}" if index % 2 == 0 else None,
                     json.dumps({"verification_index": index}), "unread" if index < 21 else "read", index),
                )
        for status in ("open", "completed"):
            feedback_id = str(uuid4())
            state["feedback_ids"].append(feedback_id)
            employee = state["accounts"]["employee"]
            conn.execute(
                """INSERT INTO feedback_items (id, submitted_by, username, position, category, priority, title, description, status)
                VALUES (%s, %s, %s, 'operations', '体验问题', 'normal', %s, %s, %s)""",
                (feedback_id, employee["id"], employee["username"], f"{marker}-{status}", "状态切换自动加载的验收反馈", status),
            )
        # Save cleanup identifiers before committing the fixture transaction.
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        state_path.chmod(0o600)
    try:
        for account in state["accounts"].values():
            response = requests.post(f"{API}/auth/login", data={"username": account["username"], "password": password}, timeout=30)
            response.raise_for_status()
            account["session"] = response.json()
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        cleanup(state_path)
        raise
    print(json.dumps({"ok": True, "temporary_accounts": 2, "notification_count": 98}))


def check_api(state_path: Path) -> None:
    state = json.loads(state_path.read_text())
    admin = state["accounts"]["admin"]
    employee = state["accounts"]["employee"]

    def request(account: dict, method: str, path: str, expected=200):
        response = requests.request(method, f"{API}{path}", headers={"Authorization": f"Bearer {account['session']['access_token']}"}, timeout=30)
        assert response.status_code == expected, (path, response.status_code, response.text[:300])
        return response.json()

    expected = dict(unread_count=21, read_count=74, total_count=95, resource_count=48)
    try:
        all_items = request(admin, "GET", "/notifications?limit=200")
        assert {key: all_items[key] for key in expected} == expected, {key: all_items.get(key) for key in expected}
        assert len(all_items["items"]) == 95
        for status in ("unread", "read"):
            data = request(admin, "GET", f"/notifications?status={status}&limit=10")
            assert {key: data[key] for key in expected} == expected
            assert all(item["status"] == status for item in data["items"])
        page = request(admin, "GET", "/notifications?limit=10&offset=80")
        assert [item["id"] for item in page["items"]] == [item["id"] for item in all_items["items"][80:90]]
        assert not request(admin, "GET", "/notifications?limit=10&offset=1000")["items"]
        for query in ("status=invalid", "offset=-1", "limit=0", "limit=201"):
            request(admin, "GET", f"/notifications?{query}", 422)
        other = request(employee, "GET", "/notifications?limit=200")
        assert other["total_count"] == 3 and other["unread_count"] == 3
        assert all(item["user_id"] == employee["id"] for item in other["items"])
        request(admin, "POST", f"/notifications/{other['items'][0]['id']}/read", 404)
        notification_id = all_items["items"][0]["id"]
        marked = request(admin, "POST", f"/notifications/{notification_id}/read")["item"]
        repeated = request(admin, "POST", f"/notifications/{notification_id}/read")["item"]
        assert marked["status"] == "read" and marked["read_at"] == repeated["read_at"]
        assert request(admin, "GET", "/notifications")["unread_count"] == 20
        assert request(admin, "POST", "/notifications/read-all")["updated_count"] == 20
        after = request(admin, "GET", "/notifications?status=unread")
        assert after["items"] == [] and after["unread_count"] == 0 and after["read_count"] == 95
        assert request(employee, "GET", "/notifications")["unread_count"] == 3
        assert requests.get(f"{API}/notifications", timeout=30).status_code == 401
        print(json.dumps({"ok": True, "checks": ["global_summary", "status_filters", "pagination_past_80", "query_validation", "user_isolation", "idempotent_mark_read", "mark_all", "authentication"]}))
    finally:
        with psycopg.connect(settings.database_url) as conn:
            conn.execute(
                """UPDATE notifications SET status = CASE WHEN (metadata->>'verification_index')::int < 21 THEN 'unread' ELSE 'read' END,
                read_at = CASE WHEN (metadata->>'verification_index')::int < 21 THEN NULL ELSE created_at END WHERE user_id = %s""",
                (admin["id"],),
            )


def cleanup(state_path: Path) -> None:
    if not state_path.exists():
        return
    state = json.loads(state_path.read_text())
    with psycopg.connect(settings.database_url) as conn:
        for feedback_id in state["feedback_ids"]:
            conn.execute("DELETE FROM feedback_items WHERE id = %s AND title LIKE %s", (feedback_id, state["marker"] + "%"))
        for account in state["accounts"].values():
            conn.execute("DELETE FROM users WHERE id = %s AND username = %s", (account["id"], account["username"]))
    state_path.unlink()
    print(json.dumps({"ok": True, "cleaned_temporary_accounts": len(state["accounts"])}))


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "run":
        state_path = ROOT / ".codex" / "verification" / f"notifications-{uuid4().hex}.json"
        try:
            prepare(state_path)
            check_api(state_path)
            subprocess.run(["node", str(ROOT / "scripts" / "verify_notifications_loop_frontend.mjs"), str(state_path)], cwd=ROOT, check=True)
        finally:
            cleanup(state_path)
    else:
        action, filename = sys.argv[1:]
        {"prepare": prepare, "check-api": check_api, "cleanup": cleanup}[action](Path(filename))
