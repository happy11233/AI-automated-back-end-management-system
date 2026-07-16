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
    operations_flows = get_json(tokens["operations"], "/automation-flows")["items"]
    customer_flows = get_json(tokens["customer_service"], "/automation-flows")["items"]
    finance_flows = get_json(tokens["finance"], "/automation-flows")["items"]

    assert_flow_names(admin_flows, ["生成 Listing", "退款售后话术", "财务 Excel 生成", "知识库维护"])
    assert_positions(admin_flows, {"operations", "customer_service", "finance", None})

    assert_positions(operations_flows, {"operations"})
    assert_flow_names(operations_flows, ["生成 Listing", "竞品分析", "运营 ERP 查询"])
    assert_not_flow_names(operations_flows, ["退款售后话术", "分析财务报表", "财务 Excel 生成"])

    assert_positions(customer_flows, {"customer_service"})
    assert_flow_names(customer_flows, ["智能客服", "退款售后话术", "客服 ERP 查询"])
    assert_not_flow_names(customer_flows, ["生成 Listing", "财务 Excel 生成", "分析财务报表"])

    assert_positions(finance_flows, {"finance"})
    assert_flow_names(finance_flows, ["分析财务报表", "统计工资", "财务 Excel 生成", "财务 ERP 查询"])
    assert_not_flow_names(finance_flows, ["生成 Listing", "退款售后话术"])

    finance_detail = get_json(tokens["finance"], flow_detail_path(finance_flows, "财务 Excel 生成"))["item"]
    assert finance_detail["entrypoint"] == "/automation/finance/excel-transform"
    assert finance_detail["input_schema"], finance_detail
    assert finance_detail["output_schema"], finance_detail
    assert finance_detail["steps"], finance_detail

    operation_finance_detail = requests.get(
        f"{API_BASE_URL}{flow_detail_path(finance_flows, '财务 Excel 生成')}",
        headers=auth_headers(tokens["operations"]),
        timeout=30,
    )
    assert operation_finance_detail.status_code == 404, operation_finance_detail.text

    for account, flows in {
        "admin": admin_flows,
        "operations": operations_flows,
        "customer_service": customer_flows,
        "finance": finance_flows,
    }.items():
        payload = json.dumps(flows, ensure_ascii=False)
        for secret_text in ["Bearer ", "api_secret", "password", "Authorization", "api_key"]:
            assert secret_text not in payload, f"{account} leaked {secret_text}"

    verify_erp_resource_alignment(tokens["operations"], operations_flows)
    verify_erp_resource_alignment(tokens["customer_service"], customer_flows)
    verify_erp_resource_alignment(tokens["finance"], finance_flows)

    print(json.dumps({
        "ok": True,
        "counts": {
            "admin": len(admin_flows),
            "operations": len(operations_flows),
            "customer_service": len(customer_flows),
            "finance": len(finance_flows),
        },
        "note": "real API, real auth tokens, real permission checks; no mock/stub/fake",
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


def assert_not_flow_names(items: list[dict[str, Any]], hidden: list[str]) -> None:
    names = {item["name"] for item in items}
    leaked = [item for item in hidden if item in names]
    assert not leaked, f"unexpected visible flows: {leaked}"


def flow_detail_path(items: list[dict[str, Any]], name: str) -> str:
    for item in items:
        if item["name"] == name:
            return f"/automation-flows/{item['id']}"
    raise AssertionError(f"missing flow {name}")


def verify_erp_resource_alignment(token: str, flows: list[dict[str, Any]]) -> None:
    scope_resources = {
        item["resource"]
        for item in get_json(token, "/erp/scopes")["resources"]
    }
    for flow in flows:
        resources = {item["resource"] for item in flow["allowed_erp_resources"]}
        assert resources <= scope_resources, {
            "flow": flow["name"],
            "resources": sorted(resources),
            "scopes": sorted(scope_resources),
        }


if __name__ == "__main__":
    main()
