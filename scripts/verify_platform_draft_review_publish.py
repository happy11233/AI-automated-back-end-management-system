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
EXECUTOR_PORT = int(os.getenv("VERIFY_REVIEW_EXECUTOR_PORT", "18082"))
EXECUTOR_URL = f"http://host.docker.internal:{EXECUTOR_PORT}/execute"

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}

RECEIVED_PAYLOADS: list[dict[str, Any]] = []


class ExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        size = int(self.headers.get("Content-Length") or "0")
        payload = json.loads(self.rfile.read(size).decode("utf-8"))
        RECEIVED_PAYLOADS.append(payload)
        body = json.dumps(
            {
                "ok": True,
                "external_reference": f"published-{payload['action_type']}-{payload['draft_id'][:8]}",
                "received_action_type": payload["action_type"],
                "received_phase": payload.get("action_phase"),
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
        marker = f"platform-review-loop-{int(time.time())}"

        listing_result = post_json(
            tokens["operations"],
            "/automation/generate",
            {
                "task_id": "listing",
                "input_text": (
                    f"{marker} SKU OPS-REVIEW-001，美国站，厨房硅胶收纳垫，"
                    "卖点是耐热、防滑、易清洁、适合小厨房。请生成 Listing 并保存草稿。"
                ),
            },
            timeout=180,
        )
        listing_draft = listing_result["platform_draft"]
        assert listing_draft["status"] == "pending_review", listing_draft

        publish_before_review = requests.post(
            f"{API_BASE_URL}/platform-drafts/{listing_draft['id']}/publish",
            headers=auth_headers(tokens["operations"]),
            timeout=60,
        )
        assert publish_before_review.status_code == 400, publish_before_review.text

        finance_detail = requests.get(
            f"{API_BASE_URL}/platform-drafts/{listing_draft['id']}",
            headers=auth_headers(tokens["finance"]),
            timeout=60,
        )
        assert finance_detail.status_code == 404, finance_detail.text

        approved_listing = post_json(
            tokens["operations"],
            f"/platform-drafts/{listing_draft['id']}/review",
            {"decision": "approved", "comment": "Listing 内容符合发布要求"},
        )["item"]
        assert approved_listing["status"] == "approved", approved_listing
        assert approved_listing["metadata"]["review_decision"] == "approved", approved_listing

        listing_publish = post_json(tokens["operations"], f"/platform-drafts/{listing_draft['id']}/publish", {})
        assert listing_publish["draft"]["status"] == "published", listing_publish
        assert listing_publish["draft"]["metadata"]["latest_publication_status"] == "succeeded", listing_publish
        assert listing_publish["execution"]["action_type"] == "publish_listing", listing_publish
        assert listing_publish["execution"]["status"] == "succeeded", listing_publish

        customer_message = post_json(
            tokens["customer_service"],
            "/customer-service/messages",
            {
                "channel": "amazon",
                "external_id": f"{marker}-reply",
                "buyer_name": "Evan",
                "buyer_email": "evan@example.com",
                "buyer_language": "en",
                "marketplace": "US",
                "order_no": "AMZ-US-250-1000001-000001",
                "tracking_no": "TRK000001",
                "subject": "Where is my order?",
                "message": "Where is my order? Please check my tracking.",
            },
        )["item"]
        process_result = post_json(
            tokens["customer_service"],
            f"/customer-service/messages/{customer_message['id']}/process",
            {},
            timeout=180,
        )
        reply_draft_id = process_result["item"]["metadata"]["platform_draft_id"]
        reply_rejected = post_json(
            tokens["customer_service"],
            f"/platform-drafts/{reply_draft_id}/review",
            {"decision": "rejected", "comment": "回复语气需要修改"},
        )["item"]
        assert reply_rejected["status"] == "rejected", reply_rejected

        rejected_publish = requests.post(
            f"{API_BASE_URL}/platform-drafts/{reply_draft_id}/publish",
            headers=auth_headers(tokens["customer_service"]),
            timeout=60,
        )
        assert rejected_publish.status_code == 400, rejected_publish.text

        reply_approved = post_json(
            tokens["customer_service"],
            f"/platform-drafts/{reply_draft_id}/review",
            {"decision": "approved", "comment": "修改后可发送"},
        )["item"]
        assert reply_approved["status"] == "approved", reply_approved

        reply_publish = post_json(tokens["customer_service"], f"/platform-drafts/{reply_draft_id}/publish", {})
        assert reply_publish["draft"]["status"] == "published", reply_publish
        assert reply_publish["execution"]["action_type"] == "send_customer_reply", reply_publish
        assert reply_publish["execution"]["status"] == "succeeded", reply_publish

        admin_drafts = get_json(tokens["admin"], "/platform-drafts?limit=10")["items"]
        assert any(item["id"] == listing_draft["id"] for item in admin_drafts), admin_drafts

        received_action_types = [item["action_type"] for item in RECEIVED_PAYLOADS]
        assert "publish_listing" in received_action_types, RECEIVED_PAYLOADS
        assert "send_customer_reply" in received_action_types, RECEIVED_PAYLOADS

        print(json.dumps({
            "ok": True,
            "executor_url": EXECUTOR_URL,
            "listing_draft_id": listing_draft["id"],
            "listing_final_status": listing_publish["draft"]["status"],
            "customer_reply_draft_id": reply_draft_id,
            "customer_reply_final_status": reply_publish["draft"]["status"],
            "received_action_types": received_action_types,
            "forbidden_finance_detail_status": finance_detail.status_code,
            "publish_before_review_status": publish_before_review.status_code,
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
