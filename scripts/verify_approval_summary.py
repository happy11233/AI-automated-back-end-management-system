from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import psycopg
import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.json_utils import dumps_json
from app.services.approval_summary_service import summarize_approval


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DATABASE_URL = os.getenv(
    "VERIFY_DATABASE_URL",
    "postgresql://rag_user:rag_password@127.0.0.1:5433/rag_agent",
)


def main() -> None:
    wait_for_api()
    admin_login = login("admin_demo", "Admin123456")
    customer_login = login("employee_demo", "Employee123456")

    approval_id = create_real_pending_approval(customer_login["id"])
    approvals = get_json(customer_login["access_token"], "/approvals")["items"]
    admin_approvals = get_json(admin_login["access_token"], "/admin/approvals")["items"]

    first = next((item for item in approvals if item["id"] == approval_id), None)
    assert first, approvals[:3]
    assert not any(item["id"] == approval_id for item in admin_approvals), admin_approvals[:3]
    summary = str(first.get("summary_cn") or "")
    assert summary, first
    assert re.search(r"[\u4e00-\u9fff]", summary), first
    assert "客服" in summary, first
    assert "管理员确认" not in summary, first
    assert "customer_service_refund" not in summary, first
    assert "callback_token" not in json.dumps(first, ensure_ascii=False), first
    assert "Authorization" not in json.dumps(first, ensure_ascii=False), first

    print(json.dumps({
        "ok": True,
        "approval_id": first["id"],
        "action_type": first["action_type"],
        "summary_cn": summary,
        "summary_source": first.get("summary_source"),
        "admin_refund_visible": False,
    }, ensure_ascii=False, indent=2))


def create_real_pending_approval(customer_user_id: str) -> str:
    marker = f"approval-summary-{int(time.time())}"
    thread_id = f"approval-summary-script-{int(time.time())}"
    payload: dict[str, Any] = {
        "order_no": "10086",
        "user_input": f"{marker} 客户要求给订单 10086 退款，商品收到后损坏，需要客服审批。",
        "order_result": {
            "order_no": "10086",
            "status": "shipping",
            "amount_cents": 29900,
            "refundable": True,
        },
    }
    summary = summarize_approval("refund", payload)
    payload = {
        **payload,
        "summary_cn": summary["summary"],
        "summary_source": summary["source"],
    }

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_threads (id, user_id, title)
                VALUES (%s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET updated_at = now()
                RETURNING id;
                """,
                (thread_id, customer_user_id, "审批中文摘要验证"),
            )
            cur.execute(
                """
                INSERT INTO approval_requests (thread_id, requested_by, action_type, payload)
                VALUES (%s, %s, %s, %s::jsonb)
                RETURNING id;
                """,
                (thread_id, customer_user_id, "refund", dumps_json(payload)),
            )
            row = cur.fetchone()
        conn.commit()

    return str(row[0])


def wait_for_api() -> None:
    for _ in range(30):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"API 不可用：{API_BASE_URL}")


def login(username: str, password: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_json(token: str, path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=30)
    response.raise_for_status()
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
