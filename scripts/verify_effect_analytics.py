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
    operations_forbidden = assert_forbidden(
        operations_token,
        "/effect-analytics?date_range=all&position=finance",
    )
    finance_forbidden = assert_forbidden(
        finance_token,
        "/effect-analytics?date_range=all&position=operations",
    )

    assert admin_payload["scope"]["role"] == "admin"
    assert admin_payload["summary"]["total_runs"] >= 4, admin_payload["summary"]
    assert admin_payload["status_distribution"], "admin should see status distribution from real runs"
    assert admin_payload["run_type_ranking"], "admin should see run type ranking from real runs"
    assert admin_payload["app_ranking"], "admin should see app ranking from real runs"
    assert admin_payload["audit_summary"]["total_events"] > 0, admin_payload["audit_summary"]

    raw_payload = json.dumps(admin_payload, ensure_ascii=False)
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
        "employee_forbidden": {
            "operations": operations_forbidden,
            "finance": finance_forbidden,
        },
        "audit_events": admin_payload["audit_summary"]["total_events"],
        "note": "real API, real auth, real PostgreSQL run records/audit logs; effect analytics is admin-only; no mock/stub/fake",
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


if __name__ == "__main__":
    main()
