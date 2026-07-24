from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import psycopg
import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
ADMIN_USERNAME = os.getenv("VERIFY_ADMIN_USERNAME", "admin_demo")
ADMIN_PASSWORD = os.getenv("VERIFY_ADMIN_PASSWORD", "Admin123456")
EMPLOYEE_USERNAME = os.getenv("VERIFY_OPERATIONS_USERNAME", "operations_demo")
EMPLOYEE_PASSWORD = os.getenv("VERIFY_OPERATIONS_PASSWORD", "Operations123456")
FLOW_KEY = "automation:operations:erp-query"
SECRET_MARKERS = ["Bearer ", "Authorization", "api_key", "api_secret", "callback_token", "database_url", "password"]


def main() -> None:
    marker = f"verify-run-flow-ref-{int(time.time())}-{uuid4().hex[:8]}"
    created_version_ids: list[str] = []
    created_publication_ids: list[str] = []
    created_run_ids: list[str] = []
    preserved_publications: list[dict[str, Any]] = []
    preserved_version_statuses: list[dict[str, Any]] = []

    ensure_schema()
    admin_token = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    employee_token = login(EMPLOYEE_USERNAME, EMPLOYEE_PASSWORD)
    flow_path = quote(FLOW_KEY, safe="")
    flow_db_id = ensure_flow_projection_for_cleanup(admin_token, FLOW_KEY)
    preserved_publications = load_active_publications(flow_db_id)
    preserved_version_statuses = load_version_statuses(flow_db_id)

    try:
        version = post_json(
            admin_token,
            f"/automation-flows/{flow_path}/versions",
            {
                "change_summary": f"{marker} 运行记录版本引用验证",
                "publish_notes": f"{marker} 发布后执行 ERP 查询",
            },
        )["item"]
        created_version_ids.append(version["id"])
        post_json(admin_token, f"/automation-flow-versions/{version['id']}/submit-review", {})
        post_json(admin_token, f"/automation-flow-versions/{version['id']}/approve", {})
        publication = post_json(
            admin_token,
            f"/automation-flow-versions/{version['id']}/publish",
            {"environment": "production", "reason": f"{marker} 发布运行记录验证版本"},
        )["item"]
        created_publication_ids.append(publication["id"])

        erp_response = post_json(
            employee_token,
            "/erp/query",
            {
                "resource": "Sales Order",
                "query": f"{marker} AMZ",
                "limit": 1,
            },
        )
        assert erp_response["resource"] == "Sales Order", erp_response

        run = find_run_record(admin_token, marker)
        created_run_ids.append(run["id"])
        assert_flow_reference(
            run,
            flow_db_id=flow_db_id,
            version_id=version["id"],
            version_label=version["version"],
            publication_id=publication["id"],
        )

        detail = get_json(admin_token, f"/run-records/{run['id']}")
        assert detail["steps"], detail
        assert_flow_reference(
            detail["run"],
            flow_db_id=flow_db_id,
            version_id=version["id"],
            version_label=version["version"],
            publication_id=publication["id"],
        )
        assert_forbidden(employee_token, f"/run-records/{run['id']}")

        payload = json.dumps({"run": run, "detail": detail}, ensure_ascii=False)
        for secret_text in SECRET_MARKERS:
            assert secret_text not in payload, f"run record response leaked {secret_text}"

        print(json.dumps({
            "ok": True,
            "flow_key": FLOW_KEY,
            "flow_id": flow_db_id,
            "version_id": version["id"],
            "publication_id": publication["id"],
            "run_id": run["id"],
            "execution_source": run["execution_source"],
            "note": "real API, real PostgreSQL, real auth, real ERP query; no mock/stub/fake/monkeypatch",
        }, ensure_ascii=False, indent=2))
    finally:
        cleanup_runs(created_run_ids)
        cleanup_versions(
            created_version_ids,
            created_publication_ids,
            preserved_publications,
            preserved_version_statuses,
        )


def ensure_schema() -> None:
    migration_sql = "\n".join(
        [
            (ROOT / "sql" / "016_automation_flow_versions.sql").read_text(encoding="utf-8"),
            (ROOT / "sql" / "017_automation_run_flow_references.sql").read_text(encoding="utf-8"),
        ]
    )
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)
        conn.commit()


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def get_json(token: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), params=params, timeout=60)
    assert response.status_code == 200, response.text
    return response.json()


def post_json(token: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{API_BASE_URL}{path}", headers=json_headers(token), json=payload, timeout=90)
    assert response.status_code == 200, response.text
    return response.json()


def assert_forbidden(token: str, path: str) -> None:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=60)
    assert response.status_code == 403, response.text


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def json_headers(token: str) -> dict[str, str]:
    return {**auth_headers(token), "Content-Type": "application/json"}


def ensure_flow_projection_for_cleanup(token: str, flow_key: str) -> str:
    flow_path = quote(flow_key, safe="")
    version = post_json(
        token,
        f"/automation-flows/{flow_path}/versions",
        {"change_summary": "verify-run-flow-ref-bootstrap"},
    )["item"]
    cleanup_versions([version["id"]], [], [], [])
    return version["flow_id"]


def find_run_record(token: str, marker: str) -> dict[str, Any]:
    response = get_json(
        token,
        "/run-records",
        params={
            "run_type": "erp_query",
            "flow_key": FLOW_KEY,
            "limit": 50,
        },
    )
    for item in response["items"]:
        text = json.dumps(item, ensure_ascii=False)
        if marker in text:
            return item
    raise AssertionError(f"missing run record for marker={marker}")


def assert_flow_reference(
    run: dict[str, Any],
    *,
    flow_db_id: str,
    version_id: str,
    version_label: str,
    publication_id: str,
) -> None:
    assert run["flow_id"] == flow_db_id, run
    assert run["flow_key"] == FLOW_KEY, run
    assert run["flow_version_id"] == version_id, run
    assert run["flow_version"] == version_label, run
    assert run["publication_id"] == publication_id, run
    assert run["execution_source"] == "manual_query", run


def load_active_publications(flow_id: str) -> list[dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status
                FROM automation_flow_publications
                WHERE flow_id = %s
                  AND status = 'active';
                """,
                (flow_id,),
            )
            return [{"id": str(row[0]), "status": row[1]} for row in cur.fetchall()]


def load_version_statuses(flow_id: str) -> list[dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status
                FROM automation_flow_versions
                WHERE flow_id = %s;
                """,
                (flow_id,),
            )
            return [{"id": str(row[0]), "status": row[1]} for row in cur.fetchall()]


def cleanup_runs(run_ids: list[str]) -> None:
    if not run_ids:
        return

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM automation_runs WHERE id = ANY(%s);",
                (run_ids,),
            )
        conn.commit()


def cleanup_versions(
    version_ids: list[str],
    publication_ids: list[str],
    preserved_publications: list[dict[str, Any]],
    preserved_version_statuses: list[dict[str, Any]],
) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            if publication_ids:
                cur.execute(
                    "DELETE FROM automation_flow_publications WHERE id = ANY(%s);",
                    (publication_ids,),
                )
            if version_ids:
                cur.execute(
                    "DELETE FROM automation_flow_versions WHERE id = ANY(%s);",
                    (version_ids,),
                )
            for item in preserved_version_statuses:
                cur.execute(
                    "UPDATE automation_flow_versions SET status = %s WHERE id = %s;",
                    (item["status"], item["id"]),
                )
            for item in preserved_publications:
                cur.execute(
                    "UPDATE automation_flow_publications SET status = %s WHERE id = %s;",
                    (item["status"], item["id"]),
                )
        conn.commit()


if __name__ == "__main__":
    main()
