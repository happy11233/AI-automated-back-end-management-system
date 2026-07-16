from __future__ import annotations

import json
import os
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    admin_token = login(*ACCOUNTS["admin"])
    operations_token = login(*ACCOUNTS["operations"])
    finance_token = login(*ACCOUNTS["finance"])

    admin_payload = get_json(admin_token, "/effect-analytics?date_range=all")
    operations_payload = get_json(operations_token, "/effect-analytics?date_range=all&position=finance")
    finance_payload = get_json(finance_token, "/effect-analytics?date_range=all&position=operations")

    assert admin_payload["scope"]["role"] == "admin"
    assert admin_payload["summary"]["total_runs"] >= 4, admin_payload["summary"]
    assert admin_payload["status_distribution"], "admin should see status distribution from real runs"
    assert admin_payload["run_type_ranking"], "admin should see run type ranking from real runs"
    assert admin_payload["app_ranking"], "admin should see app ranking from real runs"
    assert admin_payload["audit_summary"]["total_events"] > 0, admin_payload["audit_summary"]

    assert operations_payload["scope"]["role"] == "employee"
    assert operations_payload["scope"]["position"] == "operations", operations_payload["scope"]
    assert all(
        item["position"] == "operations"
        for item in operations_payload["position_ranking"]
    ), operations_payload["position_ranking"]

    assert finance_payload["scope"]["role"] == "employee"
    assert finance_payload["scope"]["position"] == "finance", finance_payload["scope"]
    assert all(
        item["position"] == "finance"
        for item in finance_payload["position_ranking"]
    ), finance_payload["position_ranking"]

    for payload in [admin_payload, operations_payload, finance_payload]:
        raw_payload = json.dumps(payload, ensure_ascii=False)
        for sensitive_text in [
            "Bearer ",
            "api_secret",
            "password",
            "Authorization",
            "input_preview",
            "output_preview",
            "error_message",
            "resource_id",
            "external_ref",
        ]:
            assert sensitive_text not in raw_payload, sensitive_text

    print(json.dumps({
        "ok": True,
        "admin_total_runs": admin_payload["summary"]["total_runs"],
        "operations_total_runs": operations_payload["summary"]["total_runs"],
        "finance_total_runs": finance_payload["summary"]["total_runs"],
        "audit_events": admin_payload["audit_summary"]["total_events"],
        "note": "real API, real auth, real PostgreSQL run records/audit logs; no mock/stub/fake",
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
