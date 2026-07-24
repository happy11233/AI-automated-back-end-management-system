from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
EXECUTOR_PORT = int(os.getenv("VERIFY_EXECUTION_TASK_EXECUTOR_PORT", "18083"))
EXECUTOR_URL = f"http://host.docker.internal:{EXECUTOR_PORT}/execute"
CALLBACK_SECRET = os.getenv("PLATFORM_ACTION_EXECUTION_CALLBACK_SECRET", "local-platform-callback-secret")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "finance": ("finance_demo", "Finance123456"),
}

RECEIVED_PAYLOADS: list[dict[str, Any]] = []


class ExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length") or "0")
        payload = json.loads(self.rfile.read(size).decode("utf-8"))
        RECEIVED_PAYLOADS.append(payload)

        action_type = payload.get("action_type")
        payload_text = json.dumps(payload, ensure_ascii=False)
        is_retry = bool(payload.get("retry"))

        if action_type == "publish_listing" and "RETRY" in payload_text and not is_retry:
            body = json.dumps(
                {"ok": False, "status": "failed", "message": "intentional first failure"},
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if action_type == "publish_listing" and "ASYNC" in payload_text:
            body = json.dumps(
                {
                    "accepted": True,
                    "status": "queued",
                    "external_reference": f"async-job-{payload['draft_id'][:8]}",
                    "received_action_type": action_type,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(202)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = json.dumps(
            {
                "ok": True,
                "status": "succeeded",
                "external_reference": f"sync-{action_type}-{payload['draft_id'][:8]}",
                "received_action_type": action_type,
                "retry_attempt": payload.get("retry", {}).get("attempt"),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = HTTPServer(("0.0.0.0", EXECUTOR_PORT), ExecutorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        wait_for_api()
        tokens = {name: login(*account) for name, account in ACCOUNTS.items()}
        marker = f"execution-task-loop-{int(time.time())}"
        executor = create_executor(tokens["admin"], marker)

        async_draft = create_listing_draft(
            token=tokens["operations"],
            marker=f"{marker}-ASYNC",
            sku="OPS-ASYNC-001",
        )
        approve_draft(tokens["operations"], async_draft["id"])
        async_publish = post_json(tokens["operations"], f"/platform-drafts/{async_draft['id']}/publish", {})
        async_task = async_publish["task"]
        assert async_task["status"] == "waiting_callback", async_publish
        assert "callback_token" not in json.dumps(async_task, ensure_ascii=False), async_task
        assert async_publish["draft"]["status"] == "approved", async_publish

        async_payload = latest_payload_for_task(async_task["id"])
        callback_token = async_payload["execution_task"]["callback_token"]
        callback_body = {
            "callback_token": callback_token,
            "status": "succeeded",
            "response_payload": {
                "ok": True,
                "external_reference": f"callback-published-{async_draft['id'][:8]}",
                "platform_status": "published",
            },
        }
        unsigned_callback = requests.post(
            f"{API_BASE_URL}/platform-execution-tasks/{async_task['id']}/callback",
            json=callback_body,
            timeout=60,
        )
        assert unsigned_callback.status_code == 401, unsigned_callback.text[:500]
        unchanged_task = get_json(tokens["admin"], f"/platform-execution-tasks/{async_task['id']}")["item"]
        assert unchanged_task["status"] == "waiting_callback", unchanged_task

        bad_callback = signed_callback(
            task_id=async_task["id"],
            payload=callback_body,
            secret="wrong-secret",
        )
        assert bad_callback.status_code == 401, bad_callback.text[:500]
        unchanged_task = get_json(tokens["admin"], f"/platform-execution-tasks/{async_task['id']}")["item"]
        assert unchanged_task["status"] == "waiting_callback", unchanged_task

        callback_result = signed_callback(
            task_id=async_task["id"],
            payload=callback_body,
            secret=CALLBACK_SECRET,
            nonce="valid-callback-once",
        )
        assert callback_result.status_code == 200, callback_result.text[:500]
        callback_json = callback_result.json()
        assert callback_json["task"]["status"] == "succeeded", callback_json
        assert callback_json["draft"]["status"] == "published", callback_json
        replay_callback = signed_callback(
            task_id=async_task["id"],
            payload=callback_body,
            secret=CALLBACK_SECRET,
            nonce="valid-callback-once",
        )
        assert replay_callback.status_code in {400, 401}, replay_callback.text[:500]

        retry_draft = create_listing_draft(
            token=tokens["operations"],
            marker=f"{marker}-RETRY",
            sku="OPS-RETRY-001",
        )
        approve_draft(tokens["operations"], retry_draft["id"])
        failed_publish = post_json(tokens["operations"], f"/platform-drafts/{retry_draft['id']}/publish", {})
        failed_task = failed_publish["task"]
        assert failed_task["status"] == "failed", failed_publish
        assert failed_publish["draft"]["writeback_status"] == "failed", failed_publish

        retry_result = post_json(tokens["operations"], f"/platform-execution-tasks/{failed_task['id']}/retry", {})
        assert retry_result["task"]["status"] == "succeeded", retry_result
        assert retry_result["task"]["attempt_count"] >= 2, retry_result
        assert retry_result["draft"]["status"] == "published", retry_result

        operations_tasks = get_json(tokens["operations"], "/platform-execution-tasks?limit=20")["items"]
        assert any(item["id"] == async_task["id"] for item in operations_tasks), operations_tasks
        assert any(item["id"] == failed_task["id"] for item in operations_tasks), operations_tasks
        assert "callback_token" not in json.dumps(operations_tasks, ensure_ascii=False), operations_tasks

        finance_forbidden = requests.get(
            f"{API_BASE_URL}/platform-execution-tasks/{async_task['id']}",
            headers=auth_headers(tokens["finance"]),
            timeout=60,
        )
        assert finance_forbidden.status_code == 404, finance_forbidden.text[:500]

        admin_task_detail = get_json(tokens["admin"], f"/platform-execution-tasks/{async_task['id']}")["item"]
        assert admin_task_detail["id"] == async_task["id"], admin_task_detail

        owner_notifications = get_json(tokens["operations"], "/notifications?limit=80")
        admin_notifications = get_json(tokens["admin"], "/notifications?limit=80")
        finance_notifications = get_json(tokens["finance"], "/notifications?limit=80")
        assert has_resource(owner_notifications["items"], async_task["id"]), owner_notifications
        assert has_resource(admin_notifications["items"], async_task["id"]), admin_notifications
        assert not has_resource(finance_notifications["items"], async_task["id"]), finance_notifications

        unread_before = owner_notifications["unread_count"]
        if owner_notifications["items"]:
            read_result = post_json(tokens["operations"], f"/notifications/{owner_notifications['items'][0]['id']}/read", {})
            assert read_result["item"]["status"] == "read", read_result
        read_all = post_json(tokens["operations"], "/notifications/read-all", {})
        assert read_all["updated_count"] >= 0, read_all

        print(json.dumps({
            "ok": True,
            "executor_url": EXECUTOR_URL,
            "executor_id": executor["id"],
            "async_draft_id": async_draft["id"],
            "async_task_id": async_task["id"],
            "async_callback_status": callback_json["task"]["status"],
            "retry_draft_id": retry_draft["id"],
            "retry_task_id": failed_task["id"],
            "retry_final_status": retry_result["task"]["status"],
            "finance_forbidden_status": finance_forbidden.status_code,
            "owner_unread_before": unread_before,
            "received_action_types": [item.get("action_type") for item in RECEIVED_PAYLOADS],
            "note": "real API + real local HTTP executor + real callback endpoint + real database persistence; no production mock/stub/fake",
        }, ensure_ascii=False, indent=2))
    finally:
        try:
            token = login(*ACCOUNTS["admin"])
            if "executor" in locals():
                requests.delete(
                    f"{API_BASE_URL}/platform-action-executors/{executor['id']}",
                    headers=auth_headers(token),
                    timeout=30,
                )
        except Exception:
            pass
        server.shutdown()
        server.server_close()


def create_executor(token: str, marker: str) -> dict[str, Any]:
    response = post_json(
        token,
        "/platform-action-executors",
        {
            "name": f"{marker} callback executor",
            "executor_type": "amazon_sp_api",
            "action_types": ["write_listing_draft", "publish_listing"],
            "webhook_url": EXECUTOR_URL,
            "api_key": "callback-secret",
            "timeout_seconds": 12,
            "enabled": True,
        },
    )
    item = response["item"]
    assert item["api_key_configured"] is True, item
    return item


def create_listing_draft(*, token: str, marker: str, sku: str) -> dict[str, Any]:
    response = post_json(
        token,
        "/automation/generate",
        {
            "task_id": "listing",
            "input_text": (
                f"{marker} SKU {sku}，美国站，企业级桌面线缆收纳盒，ABS 材质，"
                "卖点是隐藏插线板、防尘、散热孔、适合办公室。请生成 Listing 并自动保存草稿。"
            ),
        },
        timeout=180,
    )
    draft = response["platform_draft"]
    assert draft["draft_type"] == "listing", draft
    assert draft["writeback_status"] == "external_synced", draft
    return draft


def approve_draft(token: str, draft_id: str) -> dict[str, Any]:
    return post_json(
        token,
        f"/platform-drafts/{draft_id}/review",
        {"decision": "approved", "comment": "真实执行任务验证通过"},
    )["item"]


def latest_payload_for_task(task_id: str) -> dict[str, Any]:
    for payload in reversed(RECEIVED_PAYLOADS):
        execution_task = payload.get("execution_task") or {}
        if execution_task.get("id") == task_id:
            return payload
    raise AssertionError(f"executor payload for task {task_id} not received")


def has_resource(items: list[dict[str, Any]], resource_id: str) -> bool:
    return any(item.get("resource_id") == resource_id for item in items)


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


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


def signed_callback(*, task_id: str, payload: dict[str, Any], secret: str, nonce: str | None = None) -> requests.Response:
    raw_body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    timestamp = str(int(time.time()))
    nonce = nonce or f"verify-{timestamp}-{task_id[:8]}"
    body_sha = hashlib.sha256(raw_body).hexdigest()
    signing_text = f"v1:{timestamp}:{nonce}:{task_id}:{body_sha}"
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), signing_text.encode("utf-8"), hashlib.sha256).hexdigest()
    return requests.post(
        f"{API_BASE_URL}/platform-execution-tasks/{task_id}/callback",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Callback-Signature": signature,
            "X-Platform-Callback-Timestamp": timestamp,
            "X-Platform-Callback-Nonce": nonce,
        },
        timeout=60,
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
