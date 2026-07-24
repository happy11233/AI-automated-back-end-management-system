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
LISTING_PORT = int(os.getenv("VERIFY_LISTING_EXECUTOR_PORT", "18084"))
REPLY_PORT = int(os.getenv("VERIFY_REPLY_EXECUTOR_PORT", "18085"))
LISTING_EXECUTOR_URL = f"http://host.docker.internal:{LISTING_PORT}/execute"
REPLY_EXECUTOR_URL = f"http://host.docker.internal:{REPLY_PORT}/execute"

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
}

RECEIVED: dict[str, list[dict[str, Any]]] = {"listing": [], "reply": []}


def make_handler(kind: str):
    class ExecutorHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            RECEIVED[kind].append(payload)

            if payload.get("health_check"):
                body = json.dumps(
                    {"ok": True, "status": "healthy", "message": f"{kind} executor healthy"},
                    ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            body = json.dumps(
                {
                    "ok": True,
                    "status": "succeeded",
                    "executor_kind": kind,
                    "external_reference": f"{kind}-{payload['action_type']}-{payload['draft_id'][:8]}",
                    "received_action_type": payload["action_type"],
                    "received_executor_id": (payload.get("executor") or {}).get("id"),
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

    return ExecutorHandler


def main() -> None:
    listing_server = HTTPServer(("0.0.0.0", LISTING_PORT), make_handler("listing"))
    reply_server = HTTPServer(("0.0.0.0", REPLY_PORT), make_handler("reply"))
    threading.Thread(target=listing_server.serve_forever, daemon=True).start()
    threading.Thread(target=reply_server.serve_forever, daemon=True).start()

    created_executor_ids: list[str] = []
    try:
        wait_for_api()
        tokens = {name: login(*account) for name, account in ACCOUNTS.items()}

        employee_forbidden = requests.get(
            f"{API_BASE_URL}/platform-action-executors",
            headers=auth_headers(tokens["operations"]),
            timeout=30,
        )
        assert employee_forbidden.status_code == 403, employee_forbidden.text[:500]

        marker = f"executor-routing-loop-{int(time.time())}"
        blocked_urls = [
            "http://127.0.0.1:18084/execute",
            "http://localhost:18084/execute",
            "http://[::1]:18084/execute",
            "http://10.0.0.1/execute",
            "http://172.16.0.1/execute",
            "http://192.168.0.1/execute",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
        ]
        for index, blocked_url in enumerate(blocked_urls):
            blocked_response = requests.post(
                f"{API_BASE_URL}/platform-action-executors",
                headers={**auth_headers(tokens["admin"]), "Content-Type": "application/json"},
                json={
                    "name": f"{marker} blocked {index}",
                    "executor_type": "webhook",
                    "action_types": ["write_listing_draft"],
                    "webhook_url": blocked_url,
                    "timeout_seconds": 2,
                    "enabled": True,
                },
                timeout=30,
            )
            assert blocked_response.status_code == 400, blocked_response.text[:500]

        listing_executor = post_json(
            tokens["admin"],
            "/platform-action-executors",
            {
                "name": f"{marker} Listing executor",
                "executor_type": "amazon_sp_api",
                "action_types": ["write_listing_draft", "publish_listing"],
                "webhook_url": LISTING_EXECUTOR_URL,
                "api_key": "listing-secret",
                "timeout_seconds": 12,
                "enabled": True,
            },
        )["item"]
        created_executor_ids.append(listing_executor["id"])

        reply_executor = post_json(
            tokens["admin"],
            "/platform-action-executors",
            {
                "name": f"{marker} Reply executor",
                "executor_type": "customer_service_system",
                "action_types": ["write_customer_reply", "send_customer_reply"],
                "webhook_url": REPLY_EXECUTOR_URL,
                "api_key": "reply-secret",
                "timeout_seconds": 12,
                "enabled": True,
            },
        )["item"]
        created_executor_ids.append(reply_executor["id"])

        assert listing_executor["api_key_configured"] is True, listing_executor
        assert "listing-secret" not in json.dumps(listing_executor, ensure_ascii=False), listing_executor
        assert listing_executor["webhook_url"] is None, listing_executor
        assert LISTING_EXECUTOR_URL not in json.dumps(listing_executor, ensure_ascii=False), listing_executor

        listing_health = post_json(tokens["admin"], f"/platform-action-executors/{listing_executor['id']}/health-check", {})["item"]
        reply_health = post_json(tokens["admin"], f"/platform-action-executors/{reply_executor['id']}/health-check", {})["item"]
        assert listing_health["health_status"] == "healthy", listing_health
        assert reply_health["health_status"] == "healthy", reply_health

        updated_listing = put_json(
            tokens["admin"],
            f"/platform-action-executors/{listing_executor['id']}",
            {
                "name": f"{marker} Listing executor updated",
                "executor_type": "amazon_sp_api",
                "action_types": ["write_listing_draft", "publish_listing"],
                "webhook_url": "__UNCHANGED__",
                "timeout_seconds": 12,
                "enabled": True,
            },
        )["item"]
        assert updated_listing["webhook_url"] is None, updated_listing

        configs = get_json(tokens["admin"], "/platform-action-executors")
        assert LISTING_EXECUTOR_URL not in json.dumps(configs, ensure_ascii=False), configs
        assert REPLY_EXECUTOR_URL not in json.dumps(configs, ensure_ascii=False), configs
        assert not any(str(item.get("name", "")).startswith(f"{marker} blocked") for item in configs["items"]), configs
        assert any(item["id"] == listing_executor["id"] for item in configs["items"]), configs
        assert any(item["id"] == reply_executor["id"] for item in configs["items"]), configs

        listing_result = post_json(
            tokens["operations"],
            "/automation/generate",
            {
                "task_id": "listing",
                "input_text": (
                    f"{marker} SKU OPS-ROUTE-001，美国站，桌面支架，铝合金，"
                    "卖点是可折叠、稳定、防滑、适合居家办公。请生成 Listing 并自动写入草稿。"
                ),
            },
            timeout=180,
        )
        listing_draft = listing_result["platform_draft"]
        assert listing_draft["writeback_status"] == "external_synced", listing_draft
        assert listing_draft["metadata"]["executor_id"] == listing_executor["id"], listing_draft

        approved = post_json(
            tokens["operations"],
            f"/platform-drafts/{listing_draft['id']}/review",
            {"decision": "approved", "comment": "路由验证通过"},
        )["item"]
        assert approved["status"] == "approved", approved
        published = post_json(tokens["operations"], f"/platform-drafts/{listing_draft['id']}/publish", {})
        assert published["draft"]["status"] == "published", published
        assert published["task"]["target"] == "[REDACTED]", published
        assert published["task"]["request_payload"].get("redacted") is True, published

        admin_listing_detail = get_json(tokens["admin"], f"/platform-drafts/{listing_draft['id']}")
        listing_executions = admin_listing_detail["executions"]
        assert any(item["executor_type"] == "amazon_sp_api" for item in listing_executions), listing_executions
        assert any(item["target"] == LISTING_EXECUTOR_URL for item in listing_executions), listing_executions

        message_item = post_json(
            tokens["customer_service"],
            "/customer-service/messages",
            {
                "channel": "amazon",
                "external_id": f"{marker}-msg",
                "buyer_name": "Routing Buyer",
                "buyer_email": "routing@example.com",
                "buyer_language": "en",
                "marketplace": "US",
                "order_no": "AMZ-US-250-1000001-000001",
                "tracking_no": "TRK000001",
                "subject": "Where is my order?",
                "message": "Where is my order? Please check my package.",
            },
        )["item"]
        processed = post_json(
            tokens["customer_service"],
            f"/customer-service/messages/{message_item['id']}/process",
            {},
            timeout=180,
        )
        reply_draft_id = processed["item"]["metadata"]["platform_draft_id"]
        reply_draft = get_json(tokens["customer_service"], f"/platform-drafts/{reply_draft_id}")["item"]
        assert reply_draft["writeback_status"] == "external_synced", reply_draft
        assert reply_draft["metadata"]["executor_id"] == reply_executor["id"], reply_draft
        reply_detail = get_json(tokens["customer_service"], f"/platform-drafts/{reply_draft_id}")
        assert all(item["target"] == "[REDACTED]" for item in reply_detail["executions"]), reply_detail

        assert any(item.get("action_type") == "write_listing_draft" for item in RECEIVED["listing"]), RECEIVED
        assert any(item.get("action_type") == "publish_listing" for item in RECEIVED["listing"]), RECEIVED
        assert any(item.get("action_type") == "write_customer_reply" for item in RECEIVED["reply"]), RECEIVED
        assert not any(item.get("action_type") == "write_customer_reply" for item in RECEIVED["listing"]), RECEIVED

        print(json.dumps({
            "ok": True,
            "listing_executor_id": listing_executor["id"],
            "reply_executor_id": reply_executor["id"],
            "listing_draft_id": listing_draft["id"],
            "reply_draft_id": reply_draft_id,
            "employee_forbidden_status": employee_forbidden.status_code,
            "listing_received_actions": [item.get("action_type") for item in RECEIVED["listing"]],
            "reply_received_actions": [item.get("action_type") for item in RECEIVED["reply"]],
            "note": "real API + real local HTTP executors + real database routing; no production mock/stub/fake",
        }, ensure_ascii=False, indent=2))
    finally:
        for executor_id in created_executor_ids:
            try:
                token = login(*ACCOUNTS["admin"])
                requests.delete(
                    f"{API_BASE_URL}/platform-action-executors/{executor_id}",
                    headers=auth_headers(token),
                    timeout=30,
                )
            except Exception:
                pass
        listing_server.shutdown()
        reply_server.shutdown()
        listing_server.server_close()
        reply_server.server_close()


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


def put_json(token: str, path: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    response = requests.put(
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
