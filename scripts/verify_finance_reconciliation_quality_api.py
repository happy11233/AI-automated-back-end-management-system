"""Verify the real finance API, auth, PostgreSQL and XLSX artifacts in isolation.

Uses a disposable local Docker PostgreSQL instance; no existing database or
container is modified. No model, ERP or external marketplace is called.
"""
from contextlib import contextmanager
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@contextmanager
def disposable_database(scope="finance"):
    import psycopg

    name = "company-rag-" + scope + "-verify-" + uuid4().hex[:10]
    password = secrets.token_hex(24)
    try:
        print("Starting disposable PostgreSQL: " + name, flush=True)
        subprocess.run(
            ["docker", "run", "--rm", "--pull", "never", "-d", "--name", name,
             "--label", "company-rag.verification=" + scope + "-quality",
             "-e", "POSTGRES_PASSWORD", "-p", "127.0.0.1::5432", "pgvector/pgvector:pg16"],
            env={**os.environ, "POSTGRES_PASSWORD": password}, check=True, capture_output=True, text=True, timeout=60,
        )
        result = subprocess.run(["docker", "port", name, "5432/tcp"],
                                check=True, capture_output=True, text=True, timeout=10)
        port = int(result.stdout.strip().rsplit(":", 1)[1])
        url = f"postgresql://postgres:{password}@127.0.0.1:{port}/postgres"
        deadline = time.monotonic() + 180
        while True:
            try:
                with psycopg.connect(url, connect_timeout=2) as conn:
                    conn.execute("SELECT 1")
                break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    raise RuntimeError("Disposable verification PostgreSQL did not become ready.") from None
                time.sleep(0.25)
        print("Disposable PostgreSQL ready; running real API and file checks.", flush=True)
        yield url
    finally:
        cleanup = subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True, timeout=60)
        if cleanup.returncode and "No such container" not in cleanup.stderr:
            raise RuntimeError("Failed to remove disposable verification container: " + name)


@contextmanager
def isolated_database_on_local_server(scope="finance"):
    """Create/drop only a uniquely named database on the configured local server."""
    import psycopg
    from psycopg import sql
    from dotenv import dotenv_values

    server_url = os.environ.get("VERIFY_POSTGRES_URL") or dotenv_values(ROOT / ".env").get("DATABASE_URL")
    if not server_url:
        raise RuntimeError("Local verification requires DATABASE_URL or VERIFY_POSTGRES_URL")
    parts = urlsplit(server_url.replace("postgresql+psycopg://", "postgresql://"))
    if parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Verification may create databases only on an explicit local PostgreSQL server")
    name = "verify_" + scope + "_" + uuid4().hex
    with psycopg.connect(server_url, autocommit=True, connect_timeout=10) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    print("Created isolated local database: " + name, flush=True)
    try:
        yield urlunsplit(parts._replace(path="/" + name))
    finally:
        original_error = sys.exc_info()[1]
        for attempt in range(3):
            try:
                with psycopg.connect(server_url, autocommit=True, connect_timeout=5) as cleanup:
                    cleanup.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
                print("Removed isolated local database: " + name, flush=True)
                break
            except psycopg.OperationalError:
                if attempt == 2:
                    message = "Cannot clean isolated verification database while PostgreSQL is unavailable: " + name
                    if original_error is not None:
                        original_error.add_note(message)
                        break
                    raise RuntimeError(message) from None
                time.sleep(0.25)


def verify_http(url, storage_dir):
    os.environ.update({
        "DATABASE_URL": url, "VECTOR_DATABASE_URL": url,
        "APP_ENVIRONMENT": "development", "JWT_SECRET_KEY": secrets.token_hex(32),
        "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
        "LANGSMITH_API_KEY": "", "BACKGROUND_JOBS_ENABLED": "true",
        "ARTIFACT_STORAGE_BACKEND": "local", "GENERATED_FILE_STORAGE_DIR": str(storage_dir),
        "RATE_LIMIT_ENABLED": "false", "DASHSCOPE_API_KEY": "unused-file-verification",
        "BAILIAN_BASE_URL": "http://127.0.0.1:9/v1",
    })
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openpyxl import load_workbook
    from app.api.auth import router as auth_router
    from app.api.automation import router as automation_router
    from app.api.files import router as files_router
    from app.api.jobs import router as jobs_router
    from app.auth.security import hash_password
    from app.db import close_pool, open_pool, pool
    from scripts.verify_finance_reconciliation_quality import fixtures, input_file

    open_pool()
    try:
        accounts = {}
        password = secrets.token_hex(16)
        with pool.connection() as conn:
            conn.execute((ROOT / "sql/schema.sql").read_text())
            for position in ("finance", "other_finance", "operations", "customer_service"):
                user_id = str(uuid4())
                username = "finance-quality-" + uuid4().hex[:12]
                conn.execute(
                    "INSERT INTO users(id,username,role,position,password_hash) VALUES (%s,%s,'employee',%s,%s)",
                    (user_id, username, "finance" if position == "other_finance" else position, hash_password(password)),
                )
                accounts[position] = {"id": user_id, "username": username}
            conn.commit()
        app = FastAPI()
        for router in (auth_router, automation_router, files_router, jobs_router):
            app.include_router(router)
        with TestClient(app) as client:
            for account in accounts.values():
                response = client.post("/auth/login", data={"username": account["username"], "password": password})
                assert response.status_code == 200, response.text[:500]
                account["headers"] = {"Authorization": "Bearer " + response.json()["access_token"]}

            def upload(files, headers=None):
                return client.post("/automation/finance/reconciliation", headers=headers,
                                   files=[("files", (f.filename, f.content,
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) for f in files],
                                   data={"instruction": "隔离验证：订单贡献利润与缺资料边界", "base_currency": "CNY"})

            assert upload(fixtures()).status_code == 401
            for position in ("operations", "customer_service"):
                assert upload(fixtures(), accounts[position]["headers"]).status_code == 403

            response = upload(fixtures(purchase=False), accounts["finance"]["headers"])
            assert response.status_code == 200, response.text[:500]
            workbook = load_workbook(BytesIO(response.content), data_only=True)
            summary = dict(list(workbook["对账摘要"].values)[1:])
            assert summary["复核状态"] == "待补成本资料" and summary["利润合计"] is None
            with pool.connection() as conn:
                run = conn.execute("SELECT id,status,metadata,output_preview FROM automation_runs WHERE user_id=%s ORDER BY started_at DESC LIMIT 1",
                                   (accounts["finance"]["id"],)).fetchone()
                artifact = conn.execute("SELECT id,metadata FROM automation_run_artifacts WHERE run_id=%s", (run[0],)).fetchone()
            assert run[1] == "succeeded"  # File generation succeeded; business review is still required.
            assert run[2]["review_status"] == "requires_input" and run[2]["total_profit"] is None
            assert "未提供整体利润合计" in run[3] and "银行到账" in run[3]
            assert artifact[1]["incomplete_line_count"] == 1
            download = client.get(f"/files/{artifact[0]}/download", headers=accounts["finance"]["headers"])
            assert download.status_code == 200 and download.content == response.content
            assert client.get(f"/files/{artifact[0]}/download", headers=accounts["other_finance"]["headers"]).status_code == 403

            for files in (fixtures(rate=None), fixtures() + [
                input_file(
                    "conflicting_rate.xlsx", ["币种", "汇率"], [["USD", 8]])
            ]):
                response = upload(files, accounts["finance"]["headers"])
                assert response.status_code == 400 and "汇率" in response.json()["detail"], response.text[:500]
            response = upload(fixtures(), accounts["finance"]["headers"])
            assert response.status_code == 200
            with pool.connection() as conn:
                rows = conn.execute("SELECT status,metadata FROM automation_runs WHERE user_id=%s ORDER BY started_at",
                                    (accounts["finance"]["id"],)).fetchall()
                artifact_count = conn.execute("SELECT count(*) FROM automation_run_artifacts").fetchone()[0]
            assert [r[0] for r in rows] == ["succeeded", "failed", "failed", "succeeded"]
            assert rows[-1][1]["review_status"] == "pending_review" and rows[-1][1]["total_profit"] == 400
            assert artifact_count == 2

            from app.tasks import execute_job

            response = client.post("/jobs/finance-reconciliation",
                                   headers={**accounts["finance"]["headers"], "Idempotency-Key": uuid4().hex},
                                   files=[("files", (f.filename, f.content,
                                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
                                          for f in fixtures(purchase=False)],
                                   data={"instruction": "隔离验证后台结果", "base_currency": "CNY"})
            assert response.status_code == 202, response.text[:500]
            job_id = response.json()["id"]
            # Run the actual Celery handler; broker delivery is outside this check.
            execute_job.run(job_id)
            response = client.get(f"/jobs/{job_id}", headers=accounts["finance"]["headers"])
            assert response.status_code == 200
            job = response.json()
            assert job["status"] == "succeeded" and job["result"]["review_status"] == "requires_input"
            assert job["result"]["total_profit"] is None
            artifact_id = job["result"]["artifact_id"]
            assert client.get(f"/files/{artifact_id}/download", headers=accounts["finance"]["headers"]).status_code == 200
            with pool.connection() as conn:
                count_before = conn.execute("SELECT count(*) FROM automation_run_artifacts").fetchone()[0]
                conn.execute("UPDATE background_jobs SET status='queued',result='{}'::jsonb WHERE id=%s", (job_id,))
                conn.commit()
            execute_job.run(job_id)
            recovered = client.get(f"/jobs/{job_id}", headers=accounts["finance"]["headers"]).json()
            assert recovered["result"]["artifact_id"] == artifact_id
            assert recovered["result"]["review_status"] == "requires_input"
            assert recovered["result"]["total_profit"] is None
            with pool.connection() as conn:
                assert conn.execute("SELECT count(*) FROM automation_run_artifacts").fetchone()[0] == count_before
            print(json.dumps({"ok": True, "database_isolated": True, "real_login_accounts": 4,
                              "checks": ["xlsx_upload_download", "skill_executor", "missing_cost_review",
                                         "missing_fx_400", "conflicting_fx_400", "run_and_artifact_metadata",
                                         "file_ownership", "role_boundaries", "complete_contribution_profit",
                                         "worker_handler_metadata", "artifact_recovery_without_recalculation"],
                              "broker_delivery_tested": False,
                              "model_calls": 0, "platform_actions": 0}, ensure_ascii=False), flush=True)
    finally:
        close_pool()


def main():
    database = isolated_database_on_local_server() if "--local-postgres" in sys.argv else disposable_database()
    with database as url, tempfile.TemporaryDirectory(prefix="finance-quality-") as directory:
        verify_http(url, Path(directory))
    print("Removed isolated verification database and generated files.", flush=True)


if __name__ == "__main__":
    main()
