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


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}

    admin_flows = get_json(tokens["admin"], "/automation-flows")["items"]
    employee_forbidden = {
        name: assert_forbidden(token, "/automation-flows")
        for name, token in tokens.items()
        if name != "admin"
    }

    assert_flow_names(admin_flows, ["生成 Listing", "退款售后话术", "财务 Excel 生成", "财务对账自动化", "知识库维护"])
    assert_positions(admin_flows, {"operations", "customer_service", "finance", None})

    finance_detail_path = flow_detail_path(admin_flows, "财务 Excel 生成")
    finance_detail = get_json(tokens["admin"], finance_detail_path)["item"]
    assert finance_detail["entrypoint"] == "/automation/finance/excel-transform"
    assert finance_detail["input_schema"], finance_detail
    assert finance_detail["output_schema"], finance_detail
    assert finance_detail["steps"], finance_detail

    reconciliation_detail = get_json(tokens["admin"], flow_detail_path(admin_flows, "财务对账自动化"))["item"]
    assert reconciliation_detail["entrypoint"] == "/automation/finance/reconciliation"
    assert any(step["id"] == "calculate_profit" for step in reconciliation_detail["steps"]), reconciliation_detail

    for name, token in tokens.items():
        if name != "admin":
            assert_forbidden(token, finance_detail_path)

    payload = json.dumps(admin_flows, ensure_ascii=False)
    for secret_text in ["Bearer ", "api_secret", "password", "Authorization", "api_key"]:
        assert secret_text not in payload, f"admin leaked {secret_text}"

    print(json.dumps({
        "ok": True,
        "counts": {
            "admin": len(admin_flows),
        },
        "employee_forbidden": employee_forbidden,
        "note": "real API, real auth tokens, flow config is admin-only; no mock/stub/fake",
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


def assert_forbidden(token: str, path: str) -> int:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=60)
    assert response.status_code == 403, response.text
    return response.status_code


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_positions(items: list[dict[str, Any]], allowed: set[str | None]) -> None:
    positions = {item["position"] for item in items}
    assert positions <= allowed, positions
    assert positions, "expected at least one visible flow"


def assert_flow_names(items: list[dict[str, Any]], expected: list[str]) -> None:
    names = {item["name"] for item in items}
    missing = [item for item in expected if item not in names]
    assert not missing, f"missing flows: {missing}; got={sorted(names)}"


def flow_detail_path(items: list[dict[str, Any]], name: str) -> str:
    for item in items:
        if item["name"] == name:
            return f"/automation-flows/{item['id']}"
    raise AssertionError(f"missing flow {name}")


if __name__ == "__main__":
    main()
