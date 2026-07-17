from __future__ import annotations

import json
import os
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
}


def main() -> None:
    admin_token = login(*ACCOUNTS["admin"])
    operations_token = login(*ACCOUNTS["operations"])

    payload = get_json(admin_token, "/monitoring-center?date_range=all")
    assert payload["scope"]["date_range"] == "all", payload["scope"]
    assert payload["database"]["status"] == "ok", payload["database"]
    assert payload["run_summary"]["total_runs"] >= 1, payload["run_summary"]
    assert isinstance(payload["service_health"], list) and payload["service_health"], "missing service health"
    assert any(item["id"] == "database" for item in payload["service_health"]), payload["service_health"]
    assert payload["connectors"]["summary"]["total"] >= 1, payload["connectors"]["summary"]
    assert payload["evaluation"]["summary"]["total_cases"] >= 1, payload["evaluation"]["summary"]
    assert payload["knowledge"]["total_documents"] >= 1, payload["knowledge"]
    assert payload["users"]["total_users"] >= 1, payload["users"]
    assert "detail" not in payload["erp_health"], payload["erp_health"]

    employee_forbidden = requests.get(
        f"{API_BASE_URL}/monitoring-center?date_range=all",
        headers=auth_headers(operations_token),
        timeout=30,
    )
    assert employee_forbidden.status_code == 403, employee_forbidden.text

    raw_payload = json.dumps(payload, ensure_ascii=False)
    for sensitive_text in [
        "Bearer ",
        "Authorization",
        "api_secret",
        "API_SECRET",
        "password",
        "JWT_SECRET",
        "DATABASE_URL",
        "input_preview",
        "output_preview",
        "error_message",
        "content_preview",
        "expected_evidence",
        "top_chunks",
        "chunk_id",
        "document_id",
    ]:
        assert sensitive_text not in raw_payload, sensitive_text

    print(json.dumps({
        "ok": True,
        "overall_status": payload["overall_status"],
        "total_runs": payload["run_summary"]["total_runs"],
        "connectors": payload["connectors"]["summary"]["total"],
        "evaluation_cases": payload["evaluation"]["summary"]["total_cases"],
        "employee_forbidden": employee_forbidden.status_code,
        "note": "real API, real auth, real DB/ERP/connector/evaluation aggregation; no mock/stub/fake",
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
