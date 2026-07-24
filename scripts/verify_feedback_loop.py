from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}
    marker = f"feedback-loop-{int(time.time())}"

    created = post_json(
        tokens["operations"],
        "/feedback",
        {
            "category": "自动化需求",
            "priority": "high",
            "title": f"{marker} 运营希望批量生成 Listing 草稿",
            "description": "运营每周要重复整理多个 SKU 的标题、五点描述和关键词，希望 AI 自动生成并保存到草稿中心。",
        },
    )["item"]
    assert created["status"] == "open", created
    assert created["position"] == "operations", created

    operations_feedback = get_json(tokens["operations"], "/feedback?status=all&limit=80")
    assert contains_feedback(operations_feedback["items"], created["id"]), operations_feedback
    assert operations_feedback["summary"]["open"] >= 1, operations_feedback

    finance_feedback = get_json(tokens["finance"], "/feedback?status=all&limit=120")
    assert not contains_feedback(finance_feedback["items"], created["id"]), finance_feedback

    admin_feedback = get_json(tokens["admin"], "/feedback?status=open&limit=120")
    assert contains_feedback(admin_feedback["items"], created["id"]), admin_feedback
    assert admin_feedback["summary"]["open"] >= 1, admin_feedback

    completed = post_json(
        tokens["admin"],
        f"/feedback/{created['id']}/complete",
        {"admin_note": "已加入下个运营自动化优化批次，并先开放草稿批量入口。"},
    )["item"]
    assert completed["status"] == "completed", completed
    assert completed["completed_by_username"] == "admin_demo", completed
    assert completed["admin_note"], completed

    operations_after = get_json(tokens["operations"], "/feedback?status=completed&limit=120")
    matched = next((item for item in operations_after["items"] if item["id"] == created["id"]), None)
    assert matched and matched["status"] == "completed", operations_after
    assert "优化批次" in matched["admin_note"], matched

    notifications = get_json(tokens["operations"], "/notifications?limit=120")
    assert any(item.get("resource_id") == created["id"] for item in notifications["items"]), notifications

    forbidden = requests.post(
        f"{API_BASE_URL}/feedback/{created['id']}/complete",
        headers={**auth_headers(tokens["finance"]), "Content-Type": "application/json"},
        json={"admin_note": "财务不能完成运营反馈"},
        timeout=30,
    )
    assert forbidden.status_code == 403, forbidden.text[:500]

    print(json.dumps({
        "ok": True,
        "created_feedback_id": created["id"],
        "employee_visible_status": matched["status"],
        "admin_open_count_before_complete": admin_feedback["summary"]["open"],
        "finance_cross_position_visible": contains_feedback(finance_feedback["items"], created["id"]),
        "employee_notification_count": len(notifications["items"]),
        "non_admin_complete_status": forbidden.status_code,
        "note": "real API, real PostgreSQL feedback lifecycle, real role isolation; no mock/stub/fake",
    }, ensure_ascii=False, indent=2))


def contains_feedback(items: list[dict[str, Any]], feedback_id: str) -> bool:
    return any(item.get("id") == feedback_id for item in items)


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def get_json(token: str, path: str) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
        timeout=30,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()


def post_json(token: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()


if __name__ == "__main__":
    main()
