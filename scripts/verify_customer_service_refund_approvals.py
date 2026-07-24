from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import psycopg
import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.json_utils import dumps_json


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DATABASE_URL = os.getenv(
    "VERIFY_DATABASE_URL",
    "postgresql://rag_user:rag_password@127.0.0.1:5433/rag_agent",
)


def main() -> None:
    admin = login("admin_demo", "Admin123456")
    customer_service = login("employee_demo", "Employee123456")
    finance = login("finance_demo", "Finance123456")

    marker = f"cs-refund-approval-{int(time.time())}"
    order_no = f"CS-REFUND-{int(time.time())}"
    approval_id = create_refund_approval(
        customer_user_id=customer_service["id"],
        marker=marker,
        order_no=order_no,
    )

    customer_approvals = get_json(customer_service["access_token"], "/approvals")["items"]
    approval = next((item for item in customer_approvals if item["id"] == approval_id), None)
    assert approval, customer_approvals[:5]
    summary = str(approval.get("summary_cn") or "")
    assert "客服" in summary, approval
    assert "管理员确认" not in summary and "管理员审批" not in summary, approval

    admin_approvals = get_json(admin["access_token"], "/admin/approvals")["items"]
    assert not any(item["id"] == approval_id for item in admin_approvals), admin_approvals[:5]

    admin_review = requests.post(
        f"{API_BASE_URL}/admin/approvals/{approval_id}/review",
        headers={**auth_headers(admin["access_token"]), "Content-Type": "application/json"},
        json={"approved": True},
        timeout=30,
    )
    assert admin_review.status_code == 403, admin_review.text[:500]

    finance_list = requests.get(
        f"{API_BASE_URL}/approvals",
        headers=auth_headers(finance["access_token"]),
        timeout=30,
    )
    assert finance_list.status_code == 403, finance_list.text[:500]

    reviewed = post_json(
        customer_service["access_token"],
        f"/approvals/{approval_id}/review",
        {"approved": True},
    )
    assert reviewed["status"] == "approved", reviewed
    assert reviewed["refund_result"]["success"] is True, reviewed

    after_customer_approvals = get_json(customer_service["access_token"], "/approvals")["items"]
    assert not any(item["id"] == approval_id for item in after_customer_approvals), after_customer_approvals[:5]

    refund_row = read_refund_transaction(approval_id)
    assert refund_row and refund_row["status"] == "succeeded", refund_row
    order_row = read_order(order_no)
    assert order_row and order_row["status"] == "refunded", order_row

    print(json.dumps({
        "ok": True,
        "approval_id": approval_id,
        "order_no": order_no,
        "summary_cn": summary,
        "admin_review_status": admin_review.status_code,
        "finance_list_status": finance_list.status_code,
        "customer_review_status": reviewed["status"],
        "refund_status": refund_row["status"],
        "order_status": order_row["status"],
        "note": "real API, real customer-service approval permission, real PostgreSQL refund transaction; no mock/stub/fake",
    }, ensure_ascii=False, indent=2))


def create_refund_approval(*, customer_user_id: str, marker: str, order_no: str) -> str:
    thread_id = f"thread-{marker}"
    payload: dict[str, Any] = {
        "order_no": order_no,
        "user_input": f"{marker} 客户收到商品损坏，要求订单 {order_no} 退款，需要客服审批。",
        "order_result": {
            "order_no": order_no,
            "status": "shipping",
            "amount_cents": 29900,
            "refundable": True,
        },
        "summary_cn": f"退款审批：需要管理员确认是否允许继续处理。订单：{order_no}。金额：299.00 元。",
        "summary_source": "legacy_cached",
    }

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (order_no, status, amount_cents, refundable)
                VALUES (%s, 'shipping', 29900, true)
                ON CONFLICT (order_no)
                DO UPDATE SET status = 'shipping', amount_cents = 29900, refundable = true, updated_at = now();
                """,
                (order_no,),
            )
            cur.execute(
                """
                INSERT INTO chat_threads (id, user_id, title, position)
                VALUES (%s, %s, %s, 'customer_service')
                ON CONFLICT (id)
                DO UPDATE SET updated_at = now(), position = 'customer_service'
                RETURNING id;
                """,
                (thread_id, customer_user_id, "客服退款审批验证"),
            )
            cur.execute(
                """
                INSERT INTO approval_requests (thread_id, requested_by, action_type, payload)
                VALUES (%s, %s, 'refund', %s::jsonb)
                RETURNING id;
                """,
                (thread_id, customer_user_id, dumps_json(payload)),
            )
            row = cur.fetchone()
        conn.commit()

    return str(row[0])


def login(username: str, password: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text[:500]
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def get_json(token: str, path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=30)
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


def read_refund_transaction(approval_id: str) -> dict[str, Any] | None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, order_no, amount_cents, status
                FROM refund_transactions
                WHERE approval_id = %s;
                """,
                (approval_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": str(row[0]),
        "order_no": row[1],
        "amount_cents": row[2],
        "status": row[3],
    }


def read_order(order_no: str) -> dict[str, Any] | None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_no, status, amount_cents, refundable
                FROM orders
                WHERE order_no = %s;
                """,
                (order_no,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "order_no": row[0],
        "status": row[1],
        "amount_cents": row[2],
        "refundable": row[3],
    }


if __name__ == "__main__":
    main()
