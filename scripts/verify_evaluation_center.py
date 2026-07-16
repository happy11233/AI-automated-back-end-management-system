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

    payload = get_json(admin_token, "/evaluation-center")
    assert payload["summary"]["dataset_count"] >= 2, payload["summary"]
    assert payload["summary"]["total_cases"] >= 900, payload["summary"]
    assert any(item["id"] == "rag_smoke" and item["case_count"] == 5 for item in payload["datasets"])
    assert any(item["id"] == "rag_rules_large" and item["case_count"] >= 900 for item in payload["datasets"])
    assert payload["reports"], "expected existing real RAG reports"
    assert payload["regression_suites"], "expected real regression suite catalog"

    employee_forbidden = requests.get(
        f"{API_BASE_URL}/evaluation-center",
        headers=auth_headers(operations_token),
        timeout=30,
    )
    assert employee_forbidden.status_code == 403, employee_forbidden.text

    run_payload = post_json(admin_token, "/evaluation-center/run-rag?dataset_id=rag_smoke&top_k=5")
    assert run_payload["dataset"]["id"] == "rag_smoke"
    assert run_payload["dataset"]["case_count"] == 5
    assert run_payload["report"]["counts"]["total_cases"] == 5
    assert run_payload["report"]["pass_rate"] >= 0.8, run_payload["report"]

    raw_payload = json.dumps({
        "center": payload,
        "run": run_payload,
    }, ensure_ascii=False)
    for sensitive_text in [
        "content_preview",
        "expected_evidence",
        "top_chunks",
        "chunk_id",
        "document_id",
        "Bearer ",
        "api_secret",
        "password",
        "Authorization",
    ]:
        assert sensitive_text not in raw_payload, sensitive_text

    print(json.dumps({
        "ok": True,
        "dataset_count": payload["summary"]["dataset_count"],
        "total_cases": payload["summary"]["total_cases"],
        "run_pass_rate": run_payload["report"]["pass_rate"],
        "employee_forbidden": employee_forbidden.status_code,
        "note": "real API, real auth, real RAG evaluation; no mock/stub/fake",
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


def post_json(token: str, path: str) -> dict[str, Any]:
    response = requests.post(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=180)
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    main()
