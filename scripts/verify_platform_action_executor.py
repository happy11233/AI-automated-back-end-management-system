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
EXECUTOR_PORT = int(os.getenv("VERIFY_EXECUTOR_PORT", "18081"))
EXECUTOR_URL = f"http://host.docker.internal:{EXECUTOR_PORT}/execute"

ACCOUNTS = {
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
}

RECEIVED_PAYLOADS: list[dict[str, Any]] = []


class ExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length") or "0")
        payload = json.loads(self.rfile.read(size).decode("utf-8"))
        RECEIVED_PAYLOADS.append(payload)
        response = {
            "ok": True,
            "external_reference": f"external-{payload['action_type']}-{payload['draft_id'][:8]}",
            "received_action_type": payload["action_type"],
            "received_draft_type": payload["draft_type"],
        }
        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
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
        marker = f"platform-executor-loop-{int(time.time())}"

        listing_result = post_json(
            tokens["operations"],
            "/automation/generate",
            {
                "task_id": "listing",
                "input_text": (
                    f"{marker} SKU OPS-EXEC-001，美国站，桌面理线盒，ABS 材质，"
                    "卖点是隐藏插线板、防尘、散热孔、适合办公室。请生成 Listing 并自动保存草稿。"
                ),
            },
            timeout=180,
        )
        listing_draft = listing_result["platform_draft"]
        assert listing_draft["writeback_status"] == "external_synced", listing_draft
        assert listing_draft["metadata"].get("latest_execution_status") == "succeeded", listing_draft

        listing_detail = get_json(tokens["operations"], f"/platform-drafts/{listing_draft['id']}")
        assert listing_detail["executions"], listing_detail
        assert listing_detail["executions"][0]["status"] == "succeeded", listing_detail
        assert listing_detail["executions"][0]["response_payload"]["received_action_type"] == "write_listing_draft", listing_detail

        customer_response = post_json(
            tokens["customer_service"],
            "/chat",
            {
                "message": (
                    f"{marker} 客户说：Where is my order? order AMZ-US-250-1000001-000001，"
                    "tracking TRK000001。请 AI 自动查物流并生成客服回复草稿。"
                )
            },
            timeout=180,
        )
        reply_draft = customer_response["platform_draft"]
        assert reply_draft["draft_type"] == "customer_reply", reply_draft
        assert reply_draft["writeback_status"] == "external_synced", reply_draft
        assert reply_draft["metadata"].get("latest_execution_status") == "succeeded", reply_draft

        reply_detail = get_json(tokens["customer_service"], f"/platform-drafts/{reply_draft['id']}")
        assert reply_detail["executions"], reply_detail
        assert reply_detail["executions"][0]["response_payload"]["received_action_type"] == "write_customer_reply", reply_detail

        assert any(item["action_type"] == "write_listing_draft" for item in RECEIVED_PAYLOADS), RECEIVED_PAYLOADS
        assert any(item["action_type"] == "write_customer_reply" for item in RECEIVED_PAYLOADS), RECEIVED_PAYLOADS

        print(json.dumps({
            "ok": True,
            "executor_url": EXECUTOR_URL,
            "listing_draft_id": listing_draft["id"],
            "listing_writeback_status": listing_draft["writeback_status"],
            "listing_execution_id": listing_detail["executions"][0]["id"],
            "customer_reply_draft_id": reply_draft["id"],
            "customer_reply_writeback_status": reply_draft["writeback_status"],
            "customer_execution_id": reply_detail["executions"][0]["id"],
            "received_action_types": [item["action_type"] for item in RECEIVED_PAYLOADS],
            "note": "real API + real local HTTP executor + real database persistence; no production mock/stub/fake",
        }, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()
        server.server_close()


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


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
