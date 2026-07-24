from __future__ import annotations

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
EXECUTOR_PORT = int(os.getenv("VERIFY_BUSINESS_LOOP_EXECUTOR_PORT", "18084"))
LEAK_PORT = int(os.getenv("VERIFY_BUSINESS_LOOP_LEAK_EXECUTOR_PORT", "18085"))
EXECUTOR_URL = f"http://host.docker.internal:{EXECUTOR_PORT}/execute"
LEAK_EXECUTOR_URL = f"http://host.docker.internal:{LEAK_PORT}/execute"

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "finance": ("finance_demo", "Finance123456"),
}

RECEIVED: list[dict[str, Any]] = []
LEAK_RECEIVED: list[dict[str, Any]] = []


class SuccessExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        payload = read_json_payload(self)
        RECEIVED.append(payload)
        body = json.dumps(
            {
                "ok": True,
                "status": "succeeded",
                "external_reference": f"business-loop-{payload['action_type']}-{payload['draft_id'][:8]}",
                "received_action_type": payload["action_type"],
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


class LeakingExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        payload = read_json_payload(self)
        LEAK_RECEIVED.append(payload)
        leaked_token = (payload.get("execution_task") or {}).get("callback_token", "")
        body = json.dumps(
            {
                "error": "executor failed and echoed payload",
                "callback_token": leaked_token,
                "message": f'callback_token: "{leaked_token}" Authorization: Bearer should-not-leak',
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    success_server = HTTPServer(("0.0.0.0", EXECUTOR_PORT), SuccessExecutorHandler)
    leak_server = HTTPServer(("0.0.0.0", LEAK_PORT), LeakingExecutorHandler)
    threading.Thread(target=success_server.serve_forever, daemon=True).start()
    threading.Thread(target=leak_server.serve_forever, daemon=True).start()

    created_executor_ids: list[str] = []
    try:
        wait_for_api()
        tokens = {name: login(*account) for name, account in ACCOUNTS.items()}
        marker = f"business-action-loop-{int(time.time())}"

        finance_forbidden = requests.get(
            f"{API_BASE_URL}/business-action-loop",
            headers=auth_headers(tokens["finance"]),
            timeout=30,
        )
        assert finance_forbidden.status_code == 403, finance_forbidden.text[:500]

        executor = post_json(
            tokens["admin"],
            "/platform-action-executors",
            {
                "name": f"{marker} success executor",
                "executor_type": "amazon_sp_api",
                "action_types": ["write_listing_draft", "publish_listing"],
                "webhook_url": EXECUTOR_URL,
                "api_key": "business-loop-secret",
                "timeout_seconds": 12,
                "enabled": True,
            },
        )["item"]
        created_executor_ids.append(executor["id"])

        chat_result = post_json(
            tokens["operations"],
            "/chat",
            {
                "message": (
                    f"{marker} 帮我上传这个商品的草稿：SKU OPS-BIZ-001，美国站，桌下走线盒，"
                    "卖点是隐藏线缆、防尘、安装简单、适合居家办公。请 AI 自动完成 Listing、标题、"
                    "五点描述、关键词、促销文案并保存到跨境平台草稿。"
                )
            },
            timeout=180,
        )
        draft = chat_result.get("platform_draft")
        assert chat_result["intent"] == "operations_listing_draft", chat_result
        assert draft, chat_result
        assert draft["draft_type"] == "listing", draft
        assert draft["position"] == "operations", draft
        assert draft["writeback_status"] == "external_synced", draft
        assert any(item.get("action_type") == "write_listing_draft" for item in RECEIVED), RECEIVED

        loop_after_write = get_json(tokens["operations"], "/business-action-loop?limit=80")
        loop_item = find_loop_item(loop_after_write, draft["id"])
        assert loop_item["stage"] == "needs_review", loop_item
        assert loop_item["latest_task_status"] == "succeeded", loop_item
        assert loop_item["latest_action_type"] == "write_listing_draft", loop_item
        assert "callback_token" not in json.dumps(loop_item, ensure_ascii=False), loop_item

        finance_hidden = get_json(tokens["admin"], "/business-action-loop?limit=120")
        assert find_loop_item(finance_hidden, draft["id"])["position"] == "operations"

        approved = post_json(
            tokens["operations"],
            f"/platform-drafts/{draft['id']}/review",
            {"decision": "approved", "comment": "业务动作闭环验证通过"},
        )["item"]
        assert approved["status"] == "approved", approved

        published = post_json(tokens["operations"], f"/platform-drafts/{draft['id']}/publish", {})
        assert published["draft"]["status"] == "published", published
        assert published["task"]["status"] == "succeeded", published
        assert published["task"]["request_payload"].get("redacted") is True, published
        assert published["task"]["target"] == "[REDACTED]", published
        assert "callback_token" not in json.dumps(published, ensure_ascii=False), published
        assert any(item.get("action_type") == "publish_listing" for item in RECEIVED), RECEIVED

        loop_after_publish = get_json(tokens["operations"], "/business-action-loop?limit=80")
        published_item = find_loop_item(loop_after_publish, draft["id"])
        assert published_item["stage"] == "done", published_item
        assert published_item["draft_status"] == "published", published_item
        assert published_item["latest_action_type"] == "publish_listing", published_item
        assert published_item["latest_task_status"] == "succeeded", published_item
        assert published_item["external_reference"], published_item

        delete_executor(tokens["admin"], executor["id"])
        created_executor_ids.remove(executor["id"])

        leak_executor = post_json(
            tokens["admin"],
            "/platform-action-executors",
            {
                "name": f"{marker} leaking executor",
                "executor_type": "amazon_sp_api",
                "action_types": ["write_listing_draft"],
                "webhook_url": LEAK_EXECUTOR_URL,
                "api_key": "business-loop-leak-secret",
                "timeout_seconds": 12,
                "enabled": True,
            },
        )["item"]
        created_executor_ids.append(leak_executor["id"])

        leaked_chat = post_json(
            tokens["operations"],
            "/chat",
            {
                "message": (
                    f"{marker} 泄露检查：SKU OPS-BIZ-LEAK，美国站，桌面收纳托盘，"
                    "卖点是可叠放、防滑、轻量。请生成 Listing 并写入草稿。"
                )
            },
            timeout=180,
        )
        leaked_draft = leaked_chat.get("platform_draft")
        assert leaked_draft, leaked_chat
        assert leaked_draft["writeback_status"] == "failed", leaked_draft
        leaked_token = (LEAK_RECEIVED[-1].get("execution_task") or {}).get("callback_token")
        assert leaked_token, LEAK_RECEIVED
        leaked_detail = get_json(tokens["operations"], f"/platform-drafts/{leaked_draft['id']}")
        leaked_tasks = get_json(tokens["operations"], "/platform-execution-tasks?status=failed&limit=80")["items"]
        leaked_task = next((item for item in leaked_tasks if item["draft_id"] == leaked_draft["id"]), None)
        assert leaked_task, leaked_tasks
        visible_payload = json.dumps([leaked_chat, leaked_draft, leaked_detail, leaked_task], ensure_ascii=False)
        assert leaked_token not in visible_payload, visible_payload
        assert "should-not-leak" not in visible_payload, visible_payload
        assert "[REDACTED]" in visible_payload, visible_payload

        print(json.dumps({
            "ok": True,
            "draft_id": draft["id"],
            "published_stage": published_item["stage"],
            "published_external_reference": published_item["external_reference"],
            "received_action_types": [item.get("action_type") for item in RECEIVED],
            "finance_forbidden_status": finance_forbidden.status_code,
            "leak_draft_id": leaked_draft["id"],
            "leak_token_redacted": True,
            "note": "real login + real /chat + real local HTTP executors + real database loop center; no production mock/stub/fake",
        }, ensure_ascii=False, indent=2))
    finally:
        for executor_id in created_executor_ids:
            try:
                token = login(*ACCOUNTS["admin"])
                delete_executor(token, executor_id)
            except Exception:
                pass
        success_server.shutdown()
        success_server.server_close()
        leak_server.shutdown()
        leak_server.server_close()


def read_json_payload(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    size = int(handler.headers.get("Content-Length") or "0")
    return json.loads(handler.rfile.read(size).decode("utf-8"))


def find_loop_item(payload: dict[str, Any], draft_id: str) -> dict[str, Any]:
    for item in payload["items"]:
        if item["draft_id"] == draft_id:
            return item
    raise AssertionError(f"business action loop item not found: {draft_id}")


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


def delete_executor(token: str, executor_id: str) -> None:
    response = requests.delete(
        f"{API_BASE_URL}/platform-action-executors/{executor_id}",
        headers=auth_headers(token),
        timeout=30,
    )
    assert response.status_code == 200, response.text[:500]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
