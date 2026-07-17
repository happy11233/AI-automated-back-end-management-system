from __future__ import annotations

from io import BytesIO
import json
import os
import time
from typing import Any

import pandas as pd
import psycopg
import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag_user:rag_password@127.0.0.1:5433/rag_agent",
)

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    test_run_id = f"pl2-{int(time.time())}"
    print(f"[run-records] test_run_id={test_run_id}")

    admin_token = login(*ACCOUNTS["admin"])
    operations_token = login(*ACCOUNTS["operations"])
    customer_token = login(*ACCOUNTS["customer_service"])
    finance_token = login(*ACCOUNTS["finance"])

    diagnostics = get_json(admin_token, "/erp/diagnostics")
    print(
        "[run-records] erp_diagnostics="
        f"{diagnostics['active_provider_label']}:{diagnostics['active_health']['status']}"
    )

    erp_response = post_json(
        operations_token,
        "/erp/query",
        {
            "resource": "Sales Order",
            "query": f"{test_run_id} AMZ",
            "limit": 1,
        },
    )
    assert erp_response["resource"] == "Sales Order"

    forbidden = requests.post(
        f"{API_BASE_URL}/erp/query",
        headers=auth_headers(customer_token),
        json={
            "resource": "GL Entry",
            "query": f"{test_run_id} blocked finance check",
            "limit": 1,
        },
        timeout=30,
    )
    assert forbidden.status_code == 403, forbidden.text

    excel_bytes = build_excel()
    excel_response = requests.post(
        f"{API_BASE_URL}/automation/finance/excel-transform",
        headers=auth_headers(finance_token),
        files={
            "file": (
                f"{test_run_id}_finance.xlsx",
                excel_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "instruction": f"{test_run_id} 请生成财务复核汇总，只保存摘要。",
        },
        timeout=180,
    )
    assert excel_response.status_code == 200, excel_response.text[:500]
    assert excel_response.content[:2] == b"PK"

    reconciliation_response = requests.post(
        f"{API_BASE_URL}/automation/finance/reconciliation",
        headers=auth_headers(finance_token),
        files=[
            (
                "files",
                (
                    f"{test_run_id}_{filename}",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            )
            for filename, content in build_reconciliation_excels().items()
        ],
        data={
            "instruction": f"{test_run_id} 请生成订单利润表和异常账单，只保存摘要。",
            "base_currency": "CNY",
        },
        timeout=180,
    )
    assert reconciliation_response.status_code == 200, reconciliation_response.text[:500]
    assert reconciliation_response.content[:2] == b"PK"

    chat_thread_id = f"thread-{test_run_id}"
    chat_response = post_json(
        finance_token,
        "/chat",
        {
            "thread_id": chat_thread_id,
            "message": f"{test_run_id} 帮我查看销售发票相关信息，只需要摘要。",
        },
        timeout=180,
    )
    assert chat_response["thread_id"] == chat_thread_id
    assert "answer" in chat_response

    admin_runs = get_json(admin_token, "/run-records?limit=120")["items"]
    assert_has_run(admin_runs, "erp_query", "operations", "succeeded")
    assert_has_run(admin_runs, "erp_query", "customer_service", "blocked")
    assert_has_run(admin_runs, "finance_excel_transform", "finance", "succeeded")
    assert_has_run(admin_runs, "finance_reconciliation", "finance", "succeeded")
    assert_has_run(admin_runs, "chat", "finance", "succeeded")

    finance_runs = get_json(finance_token, "/run-records?limit=120")["items"]
    assert finance_runs, "finance account should see its own runs"
    assert all(item["position"] == "finance" for item in finance_runs), finance_runs[:3]
    assert all(item["username"] == ACCOUNTS["finance"][0] for item in finance_runs), finance_runs[:3]

    other_finance_run = next(item for item in finance_runs if item["run_type"] == "finance_excel_transform")
    forbidden_detail = requests.get(
        f"{API_BASE_URL}/run-records/{other_finance_run['id']}",
        headers=auth_headers(customer_token),
        timeout=30,
    )
    assert forbidden_detail.status_code == 403, forbidden_detail.text

    detail = get_json(admin_token, f"/run-records/{other_finance_run['id']}")
    assert detail["steps"], "finance excel run should have steps"
    assert detail["artifacts"], "finance excel run should have artifact metadata"

    db_counts = query_db_counts(test_run_id)
    assert db_counts["runs"] >= 4, db_counts
    assert db_counts["steps"] >= 4, db_counts
    assert db_counts["artifacts"] >= 2, db_counts

    admin_payload = json.dumps(admin_runs, ensure_ascii=False)
    for secret_text in ["Bearer ", "api_secret", "password", "Authorization"]:
        assert secret_text not in admin_payload, secret_text

    print(json.dumps({
        "ok": True,
        "test_run_id": test_run_id,
        "db_counts": db_counts,
        "finance_run_id": other_finance_run["id"],
        "note": "real API, real PostgreSQL, real ERP/LLM paths; no mock/stub/fake",
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


def build_excel() -> bytes:
    output = BytesIO()
    frame = pd.DataFrame(
        [
            {"订单号": "AMZ-US-001", "金额": 126.5, "币种": "USD", "状态": "paid"},
            {"订单号": "AMZ-DE-002", "金额": 89.9, "币种": "EUR", "状态": "review"},
        ]
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Finance")
    return output.getvalue()


def build_reconciliation_excels() -> dict[str, bytes]:
    return {
        "amazon_settlement.xlsx": dataframe_to_excel(
            "Amazon结算",
            [
                {"订单号": "AMZ-RUN-001", "SKU": "SKU-RUN-01", "数量": 2, "币种": "USD", "销售额": 100, "退款": 0, "平台手续费": 15},
                {"订单号": "AMZ-RUN-002", "SKU": "SKU-RUN-02", "数量": 1, "币种": "USD", "销售额": 30, "退款": 0, "平台手续费": 6},
            ],
        ),
        "logistics.xlsx": dataframe_to_excel(
            "物流账单",
            [
                {"订单号": "AMZ-RUN-001", "物流费": 70, "币种": "CNY"},
                {"订单号": "AMZ-RUN-002", "物流费": 20, "币种": "CNY"},
            ],
        ),
        "purchase.xlsx": dataframe_to_excel(
            "采购成本",
            [
                {"SKU": "SKU-RUN-01", "采购成本": 120, "币种": "CNY"},
                {"SKU": "SKU-RUN-02", "采购成本": 180, "币种": "CNY"},
            ],
        ),
        "rates.xlsx": dataframe_to_excel(
            "汇率",
            [
                {"币种": "USD", "汇率": 7.2},
                {"币种": "CNY", "汇率": 1},
            ],
        ),
    }


def dataframe_to_excel(sheet_name: str, rows: list[dict[str, Any]]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def assert_has_run(items: list[dict[str, Any]], run_type: str, position: str, status: str) -> None:
    found = [
        item for item in items
        if item["run_type"] == run_type
        and item["position"] == position
        and item["status"] == status
    ]
    assert found, f"missing run type={run_type} position={position} status={status}"


def query_db_counts(test_run_id: str) -> dict[str, int]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    count(*) FILTER (WHERE input_preview ILIKE %s OR output_preview ILIKE %s) AS runs,
                    (
                        SELECT count(*)
                        FROM automation_run_steps
                        WHERE input_preview ILIKE %s OR output_preview ILIKE %s
                    ) AS steps,
                    (
                        SELECT count(*)
                        FROM automation_run_artifacts
                        WHERE name ILIKE %s OR external_ref ILIKE %s OR metadata::text ILIKE %s
                    ) AS artifacts
                FROM automation_runs;
                """,
                tuple([f"%{test_run_id}%"] * 7),
            )
            row = cur.fetchone()

    return {
        "runs": int(row[0]),
        "steps": int(row[1]),
        "artifacts": int(row[2]),
    }


if __name__ == "__main__":
    main()
