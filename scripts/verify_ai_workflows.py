from __future__ import annotations

import json
import os
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}

SENSITIVE_TEXTS = [
    "Bearer abc.def.ghi",
    "api_key=secret-value",
    "buyer@example.com",
    "13812345678",
    "Authorization",
    "api_secret",
    "password",
    "JWT_SECRET",
    "DATABASE_URL",
]


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}

    admin_items = get_json(tokens["admin"], "/ai-workflows")["items"]
    operations_items = get_json(tokens["operations"], "/ai-workflows")["items"]
    customer_items = get_json(tokens["customer_service"], "/ai-workflows")["items"]
    finance_items = get_json(tokens["finance"], "/ai-workflows")["items"]

    assert len(admin_items) == 9, admin_items
    assert_positions(admin_items, {"operations", "customer_service", "finance"})
    assert_positions(operations_items, {"operations"})
    assert_positions(customer_items, {"customer_service"})
    assert_positions(finance_items, {"finance"})

    assert_workflows(operations_items, ["operations_listing_launch", "operations_competitor_analysis"])
    assert_workflows(customer_items, [
        "customer_service_refund_reply",
        "customer_service_logistics_reply",
        "customer_service_message_loop",
    ])
    assert_workflows(finance_items, [
        "finance_report_analysis",
        "finance_salary_summary",
        "finance_excel_settlement",
        "finance_reconciliation",
    ])

    cross_detail = requests.get(
        f"{API_BASE_URL}/ai-workflows/finance_salary_summary",
        headers=auth_headers(tokens["operations"]),
        timeout=30,
    )
    assert cross_detail.status_code == 404, cross_detail.text

    cross_run = requests.post(
        f"{API_BASE_URL}/ai-workflows/finance_salary_summary/run",
        headers=auth_headers(tokens["operations"]),
        json={"input_text": "尝试查询工资"},
        timeout=30,
    )
    assert cross_run.status_code == 403, cross_run.text

    external_run = requests.post(
        f"{API_BASE_URL}/ai-workflows/finance_excel_settlement/run",
        headers=auth_headers(tokens["finance"]),
        json={"input_text": "请上传 Excel 后生成结算表"},
        timeout=30,
    )
    assert external_run.status_code == 400, external_run.text

    run_input = (
        "竞品 A 标题：Stainless Steel Bottle，价格 19.99 USD，差评集中在漏水和涂层掉漆。"
        "我们的产品有防漏盖、双层保温、可替换吸管。"
        "敏感串用于脱敏验证：Bearer abc.def.ghi api_key=secret-value buyer@example.com 13812345678。"
    )
    run_payload = post_json(
        tokens["operations"],
        "/ai-workflows/operations_competitor_analysis/run",
        {"input_text": run_input},
        timeout=180,
    )
    assert run_payload["status"] == "succeeded", run_payload
    assert run_payload["run_id"], run_payload
    assert run_payload["answer"], run_payload
    assert run_payload["workflow"]["id"] == "operations_competitor_analysis", run_payload
    assert [step["step_order"] for step in run_payload["steps"]] == [1, 2, 3], run_payload["steps"]
    assert all(step["status"] == "succeeded" for step in run_payload["steps"]), run_payload["steps"]

    detail = get_json(tokens["admin"], f"/run-records/{run_payload['run_id']}")
    assert detail["run"]["run_type"] == "ai_workflow", detail["run"]
    assert detail["run"]["app_id"] == "operations_competitor_analysis", detail["run"]
    assert detail["run"]["entrypoint"] == "/ai-workflows/operations_competitor_analysis/run", detail["run"]
    assert detail["run"]["resource_type"] == "ai_workflow", detail["run"]
    assert len(detail["steps"]) >= 3, detail["steps"]

    audit_payload = get_json(tokens["admin"], "/admin/audit-logs?action=ai_workflow.run&limit=20")
    assert any(item["resource_id"] == "operations_competitor_analysis" for item in audit_payload["items"]), audit_payload

    erp_payload = post_json(
        tokens["customer_service"],
        "/ai-workflows/customer_service_logistics_reply/run",
        {
            "input_text": (
                "买家询问物流，订单 AMZ-US-001，需要查 Delivery Note 或物流出库单。"
                "敏感串：Bearer abc.def.ghi api_key=secret-value buyer@example.com 13812345678。"
            )
        },
        timeout=180,
    )
    assert erp_payload["status"] == "succeeded", erp_payload
    assert any(step["step_name"] == "erp_permission_query" for step in erp_payload["steps"]), erp_payload["steps"]
    assert any(
        step["status"] in {"succeeded", "blocked", "failed"}
        for step in erp_payload["steps"]
        if step["step_name"] == "erp_permission_query"
    ), erp_payload["steps"]

    raw_outputs = json.dumps([run_payload, detail, audit_payload, erp_payload], ensure_ascii=False)
    for sensitive_text in SENSITIVE_TEXTS:
        assert sensitive_text not in raw_outputs, f"leaked {sensitive_text}"

    latest_runs = get_json(tokens["admin"], "/run-records?run_type=ai_workflow&limit=20")["items"]
    assert any(item["id"] == run_payload["run_id"] for item in latest_runs), latest_runs

    print(json.dumps({
        "ok": True,
        "counts": {
            "admin": len(admin_items),
            "operations": len(operations_items),
            "customer_service": len(customer_items),
            "finance": len(finance_items),
        },
        "run_id": run_payload["run_id"],
        "erp_workflow_run_id": erp_payload["run_id"],
        "note": "real API, real auth, real LLM/ERP path, real run records/audit logs; no mock/stub/fake",
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


def assert_positions(items: list[dict[str, Any]], allowed: set[str]) -> None:
    positions = {item["position"] for item in items}
    assert positions <= allowed, positions
    assert positions, "expected visible workflows"


def assert_workflows(items: list[dict[str, Any]], expected: list[str]) -> None:
    ids = {item["id"] for item in items}
    missing = [item for item in expected if item not in ids]
    assert not missing, f"missing workflows: {missing}; got={sorted(ids)}"


if __name__ == "__main__":
    main()
