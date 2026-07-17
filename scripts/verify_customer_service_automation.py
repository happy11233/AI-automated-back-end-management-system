from __future__ import annotations

import json
import os
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}

    low_risk_detail = post_json(
        tokens["customer_service"],
        "/customer-service/messages",
        {
            "channel": "manual",
            "buyer_name": "John Buyer",
            "buyer_language": "English",
            "marketplace": "Amazon US",
            "order_no": "AMZ-US-001",
            "subject": "Where is my order?",
            "message": "Where is my order? My order number is AMZ-US-001.",
        },
    )
    low_risk_id = low_risk_detail["item"]["id"]
    assert low_risk_detail["item"]["status"] == "new", low_risk_detail

    low_risk_result = post_json(
        tokens["customer_service"],
        f"/customer-service/messages/{low_risk_id}/process",
        {},
        timeout=180,
    )
    low_risk_item = low_risk_result["item"]
    assert low_risk_item["intent"] in {"logistics", "general_question"}, low_risk_item
    assert low_risk_item["risk_level"] == "low", low_risk_item
    assert low_risk_item["status"] in {"auto_reply_ready", "drafted"}, low_risk_item
    assert low_risk_item["reply_draft"], low_risk_item
    assert low_risk_result["run_id"], low_risk_result
    assert [step["step_order"] for step in low_risk_result["steps"]] == [1, 2, 3, 4], low_risk_result["steps"]

    high_risk_detail = post_json(
        tokens["customer_service"],
        "/customer-service/messages",
        {
            "channel": "manual",
            "buyer_name": "Mary Buyer",
            "buyer_language": "English",
            "marketplace": "Amazon US",
            "order_no": "AMZ-US-001",
            "subject": "Refund complaint",
            "message": "I want a refund now, otherwise I will leave a bad review.",
        },
    )
    high_risk_id = high_risk_detail["item"]["id"]
    high_risk_result = post_json(
        tokens["customer_service"],
        f"/customer-service/messages/{high_risk_id}/process",
        {},
        timeout=180,
    )
    high_risk_item = high_risk_result["item"]
    assert high_risk_item["risk_level"] == "high", high_risk_item
    assert high_risk_item["status"] == "human_handoff", high_risk_item
    assert high_risk_item["approval_id"], high_risk_item
    assert high_risk_item["handoff_reason"], high_risk_item

    listing = get_json(tokens["customer_service"], "/customer-service/messages?limit=20")
    ids = {item["id"] for item in listing["items"]}
    assert low_risk_id in ids and high_risk_id in ids, listing

    run_detail = get_json(tokens["customer_service"], f"/run-records/{low_risk_result['run_id']}")
    assert run_detail["run"]["run_type"] == "customer_service_automation", run_detail["run"]
    assert run_detail["run"]["resource_type"] == "customer_service_message", run_detail["run"]
    assert len(run_detail["steps"]) >= 4, run_detail["steps"]

    approvals = get_json(tokens["admin"], "/admin/approvals")
    assert any(item["id"] == high_risk_item["approval_id"] for item in approvals["items"]), approvals

    forbidden_create = requests.post(
        f"{API_BASE_URL}/customer-service/messages",
        headers={**auth_headers(tokens["finance"]), "Content-Type": "application/json"},
        json={"channel": "manual", "message": "Where is my order?"},
        timeout=30,
    )
    assert forbidden_create.status_code == 403, forbidden_create.text

    webhook_result = post_json(
        tokens["customer_service"],
        "/customer-service/webhooks/messages",
        {
            "channel": "email",
            "external_id": "verify-email-auto-001",
            "buyer_name": "Webhook Buyer",
            "buyer_language": "English",
            "marketplace": "Amazon US",
            "order_no": "AMZ-US-001",
            "subject": "Package tracking",
            "message": "Where is my order? Please check AMZ-US-001.",
            "auto_process": True,
        },
        timeout=180,
    )
    webhook_item = webhook_result["item"]
    assert webhook_result["processed"] is True, webhook_result
    assert webhook_result["webhook_auth"] == "bearer_token", webhook_result
    assert webhook_item["channel"] == "email", webhook_item
    assert webhook_item["status"] in {"auto_reply_ready", "drafted"}, webhook_item
    assert webhook_item["reply_draft"], webhook_item
    assert webhook_result["run_id"], webhook_result

    forbidden_webhook = requests.post(
        f"{API_BASE_URL}/customer-service/webhooks/messages",
        headers={**auth_headers(tokens["finance"]), "Content-Type": "application/json"},
        json={"channel": "email", "message": "Where is my order?"},
        timeout=30,
    )
    assert forbidden_webhook.status_code == 403, forbidden_webhook.text

    workflow_items = get_json(tokens["customer_service"], "/ai-workflows")["items"]
    assert any(item["id"] == "customer_service_message_loop" for item in workflow_items), workflow_items

    flow_items = get_json(tokens["customer_service"], "/automation-flows")["items"]
    assert any(item["app_id"] == "customer-service-message-loop" for item in flow_items), flow_items

    raw_outputs = json.dumps([low_risk_result, high_risk_result, run_detail, webhook_result], ensure_ascii=False)
    for sensitive_text in ["Bearer ", "api_key", "password", "Authorization"]:
        assert sensitive_text not in raw_outputs, f"leaked {sensitive_text}"

    print(json.dumps({
        "ok": True,
        "low_risk": {
            "id": low_risk_id,
            "intent": low_risk_item["intent"],
            "risk_level": low_risk_item["risk_level"],
            "status": low_risk_item["status"],
            "run_id": low_risk_result["run_id"],
        },
        "high_risk": {
            "id": high_risk_id,
            "intent": high_risk_item["intent"],
            "risk_level": high_risk_item["risk_level"],
            "status": high_risk_item["status"],
            "approval_id": high_risk_item["approval_id"],
        },
        "webhook": {
            "id": webhook_item["id"],
            "intent": webhook_item["intent"],
            "risk_level": webhook_item["risk_level"],
            "status": webhook_item["status"],
            "run_id": webhook_result["run_id"],
        },
        "note": "real API, real auth, real DB, real ERP/RAG/LLM path; no mock/stub/fake",
    }, ensure_ascii=False))


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
    assert response.status_code == 200, response.text
    return response.json()


def post_json(token: str, path: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
