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
    admin_token = login(*ACCOUNTS["admin"])
    operations_token = login(*ACCOUNTS["operations"])

    payload = get_json(admin_token, "/connectors")
    items = payload["items"]
    ids = {item["id"] for item in items}
    expected_ids = {
        "erpnext",
        "kingdee",
        "yonyou",
        "amazon_sp_api",
        "logistics",
        "amazon_ads",
        "feishu",
        "wechat_work",
        "email",
        "excel",
    }
    assert expected_ids <= ids, ids
    assert payload["summary"]["total"] == len(items), payload["summary"]

    erpnext = next(item for item in items if item["id"] == "erpnext")
    assert erpnext["supports_real_health_check"] is True
    assert erpnext["status"] == "healthy", erpnext
    assert erpnext["health_status"] == "ok", erpnext
    assert erpnext["resources"], "ERPNext should expose mapped resources"

    kingdee = next(item for item in items if item["id"] == "kingdee")
    assert kingdee["status"] in {"not_configured", "not_implemented", "degraded"}
    assert kingdee["supports_real_health_check"] is False

    excel = next(item for item in items if item["id"] == "excel")
    assert excel["status"] == "healthy"
    assert excel["configured"] is True

    detail = get_json(admin_token, "/connectors/erpnext")["item"]
    assert detail["id"] == "erpnext"
    assert any(resource["resource"] == "Sales Order" for resource in detail["resources"])

    forbidden = requests.get(
        f"{API_BASE_URL}/connectors",
        headers=auth_headers(operations_token),
        timeout=30,
    )
    assert forbidden.status_code == 403, forbidden.text

    raw_payload = json.dumps(payload, ensure_ascii=False)
    for secret_text in [
        "Bearer ",
        "api_secret",
        "password",
        "Authorization",
        "ERP_API_SECRET=",
        "app_secret=",
        "client_secret=",
    ]:
        assert secret_text not in raw_payload, secret_text

    secret_fields = [
        field
        for item in items
        for field in item["config_fields"]
        if field["secret"] and field["configured"]
    ]
    assert secret_fields, "expected at least one configured secret field from ERPNext"
    for field in secret_fields:
        preview = field["value_preview"] or ""
        assert "***" in preview or preview == "****", field

    print(json.dumps({
        "ok": True,
        "summary": payload["summary"],
        "erpnext_status": erpnext["health_status"],
        "employee_forbidden": forbidden.status_code,
        "note": "real API, real ERPNext health check, real auth; no mock/stub/fake",
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


if __name__ == "__main__":
    main()
