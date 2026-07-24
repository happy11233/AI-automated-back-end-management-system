from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
}


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}
    marker = f"platform-draft-loop-{int(time.time())}"

    listing_result = post_json(
        tokens["operations"],
        "/automation/generate",
        {
            "task_id": "listing",
            "input_text": (
                f"{marker} SKU OPS-BOTTLE-001，美国站，保温水杯，316 不锈钢，24oz，"
                "卖点是保温 24 小时、防漏、车载杯架适配、户外健身人群。请直接生成完整 Listing 并保存草稿。"
            ),
        },
        timeout=120,
    )
    listing_draft = listing_result.get("platform_draft")
    assert listing_draft, listing_result
    assert listing_draft["draft_type"] == "listing", listing_draft
    assert listing_draft["status"] == "pending_review", listing_draft
    assert listing_draft["writeback_status"] == "rpa_ready", listing_draft

    listing_drafts = get_json(tokens["operations"], "/platform-drafts?draft_type=listing&limit=20")["items"]
    assert any(item["id"] == listing_draft["id"] for item in listing_drafts), listing_drafts

    customer_message = post_json(
        tokens["customer_service"],
        "/customer-service/messages",
        {
            "channel": "amazon",
            "external_id": f"{marker}-msg",
            "buyer_name": "Alice",
            "buyer_email": "alice@example.com",
            "buyer_language": "en",
            "marketplace": "US",
            "order_no": "AMZ-US-250-1000001-000001",
            "subject": "Where is my order?",
            "message": "Where is my order? Please check the shipping status.",
        },
    )["item"]
    process_result = post_json(
        tokens["customer_service"],
        f"/customer-service/messages/{customer_message['id']}/process",
        {},
        timeout=120,
    )
    processed_item = process_result["item"]
    assert processed_item["reply_draft"], processed_item
    assert processed_item["metadata"].get("platform_draft_id"), processed_item
    assert processed_item["metadata"].get("writeback_status") in {"rpa_ready", "draft_saved"}, processed_item

    reply_drafts = get_json(tokens["customer_service"], "/platform-drafts?draft_type=customer_reply&limit=20")["items"]
    assert any(item["id"] == processed_item["metadata"]["platform_draft_id"] for item in reply_drafts), reply_drafts

    print(json.dumps({
        "ok": True,
        "listing_draft_id": listing_draft["id"],
        "listing_writeback_status": listing_draft["writeback_status"],
        "customer_reply_draft_id": processed_item["metadata"]["platform_draft_id"],
        "customer_reply_writeback_status": processed_item["metadata"]["writeback_status"],
        "customer_steps": [step["step_name"] for step in process_result["steps"]],
        "note": "real API, real LLM/ERP/RAG where configured, real PostgreSQL drafts; no mock/stub/fake",
    }, ensure_ascii=False, indent=2))


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


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
