"""Real authenticated HTTP, PostgreSQL, ERP/RAG/model and optional browser checks.

Uses a disposable database and actual configured model/ERP reads. External
write executors stay unconfigured; no customer channel is contacted. Explicit
seeded boundary cases test persistence/dispatch, not model-generated results.
"""
from pathlib import Path
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_finance_reconciliation_quality_api import disposable_database, isolated_database_on_local_server


def verify(url, browser=False):
    import psycopg
    import requests
    from dotenv import dotenv_values
    config = dotenv_values(ROOT / ".env")
    erp_url = os.environ.get("ERP_BASE_URL", config.get("ERP_BASE_URL", "")) or ""
    os.environ.update({
        "DATABASE_URL": url, "VECTOR_DATABASE_URL": url, "REDIS_URL": "",
        "APP_ENVIRONMENT": "development", "JWT_SECRET_KEY": secrets.token_hex(32),
        "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false", "LANGSMITH_API_KEY": "",
        "RATE_LIMIT_ENABLED": "false", "CONTEXT_CLEANUP_SCHEDULER": "celery",
        "PLATFORM_ACTION_EXECUTOR_WEBHOOK_URL": "", "PLATFORM_ACTION_EXECUTOR_API_KEY": "",
        "ERP_BASE_URL": erp_url.replace("host.docker.internal", "127.0.0.1"),
    })
    from app.auth.security import hash_password
    marker = "reply-quality-" + uuid4().hex[:10]
    password = secrets.token_hex(16)
    accounts = {}
    with psycopg.connect(url) as conn:
        conn.execute((ROOT / "sql/schema.sql").read_text())
        for name in ("admin", "customer_service", "finance"):
            uid = str(uuid4())
            username = marker + "-" + name
            conn.execute("INSERT INTO users(id,username,role,position,password_hash) VALUES (%s,%s,%s,%s,%s)",
                         (uid, username, "admin" if name == "admin" else "employee",
                          None if name == "admin" else name, hash_password(password)))
            accounts[name] = {"id": uid, "username": username}
    from app.main import app
    import uvicorn
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 45
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Isolated HTTP server failed to start")
            time.sleep(0.1)
        session = requests.Session()
        for account in accounts.values():
            r = session.post(base + "/auth/login", data={"username": account["username"], "password": password}, timeout=30)
            assert r.status_code == 200, r.text[:300]
            account["headers"] = {"Authorization": "Bearer " + r.json()["access_token"]}

        def call(method, path, *, name="customer_service", expected=200, **kwargs):
            r = session.request(method, base + path, headers=accounts[name]["headers"], timeout=180, **kwargs)
            assert r.status_code == expected, (path, r.status_code, r.text[:500])
            return r.json()

        diagnostics = call("GET", "/erp/diagnostics", name="admin")
        assert diagnostics["active_provider"] == "erpnext" and diagnostics["active_health"]["ok"], diagnostics["active_health"]
        print("Real ERPNext diagnosis passed; uploading isolated RAG policy and running real model.", flush=True)
        call("POST", "/admin/documents/upload", name="admin",
             files={"file": (marker + ".txt",
                    "隔离验证规则，仅用于测试：客户询问物流但没有匹配订单或物流记录时，不得编造物流进度；请求客户补充订单号并由客服核实。退款和投诉必须转人工。内部建议使用中文，客户正文使用客户语言。".encode(), "text/plain")},
             data={"visibility": "employee", "department": "客服部", "position_scope": "customer_service", "field_scope": "customer_logistics"})
        assert session.get(base + "/customer-service/messages", timeout=10).status_code == 401
        call("POST", "/customer-service/messages", name="finance", expected=403, json={"message": "Verification message"})
        results = []
        for case, message in (("missing-order", "Where is my order? Please check the delivery status."),
                              ("refund", "I want a refund now, otherwise I will leave a bad review.")):
            detail = call("POST", "/customer-service/messages", json={
                "channel": "manual", "subject": marker + "-" + case,
                "buyer_language": "English", "order_no": marker + "-unknown-order", "message": message})
            mid = detail["item"]["id"]
            result = call("POST", f"/customer-service/messages/{mid}/process", json={})
            item = result["item"]
            assert item["reply_parse_status"] == "validated", item
            assert item["reply_draft"] and item["internal_note"] and item["needs_human_review"]
            assert item["status"] == ("drafted" if case == "missing-order" else "human_handoff"), item
            if case == "refund":
                assert item["approval_id"]
            assert not item["metadata"].get("latest_execution_id")
            assert [s["step_order"] for s in result["steps"]] == [1, 2, 3, 4, 5]
            reloaded = call("GET", f"/customer-service/messages/{mid}")["item"]
            for key in ("reply_draft", "internal_note", "needs_human_review", "reply_parse_status"):
                assert reloaded[key] == item[key], key
            draft = call("GET", "/platform-drafts/" + item["metadata"]["platform_draft_id"])["item"]
            assert draft["writeback_status"] == "draft_saved" and draft["status"] == "pending_review"
            assert "internal_note" not in draft["content"]
            call("POST", f"/customer-service/messages/{mid}/process", expected=409, json={})
            with psycopg.connect(url) as conn:
                assert conn.execute("SELECT count(*) FROM platform_execution_tasks WHERE draft_id=%s", (draft["id"],)).fetchone()[0] == 0
            results.append(item)
            print("Real model and persistence case passed: " + case, flush=True)

        # Explicit verification seed: long text and internal metadata are not model output.
        from app.services.platform_draft_service import create_platform_draft, create_platform_execution_task
        from app.services.customer_reply_contract import parse_customer_reply
        from app.services.customer_service_automation_service import _finish_message_processing, decide_customer_action
        private_note = "ISOLATED-STAFF-ONLY-" + marker
        body = "Isolated verification customer text. " * 40
        seed_content = {"customer_message_id": results[0]["id"], "reply_draft": body,
                        "reply_parse_status": "validated", "internal_note": private_note,
                        "handoff_reason": private_note, "reply_unparsed_output": private_note}
        def seed_draft(content):
            return create_platform_draft(
                draft_type="customer_reply", platform="manual", external_target="isolated-verification-only",
                title=private_note, position="customer_service", owner_user_id=accounts["customer_service"]["id"],
                source_run_id=None, source_resource_type="verification_seed", source_resource_id=marker,
                content=content, metadata={"internal_note": private_note})
        draft = seed_draft(seed_content)
        call("POST", f"/platform-drafts/{draft['id']}/publish", expected=400, json={})
        dispatched = call("POST", f"/platform-drafts/{draft['id']}/execute", json={})
        assert dispatched["execution"]["status"] == "waiting_executor"
        task = dispatched["task"]
        assert task["request_payload"].get("redacted") is True
        stored = call("GET", f"/platform-execution-tasks/{task['id']}", name="admin")["item"]
        assert stored["request_payload"]["content"]["reply_draft"] == body
        assert private_note not in json.dumps(stored["request_payload"])
        call("POST", f"/platform-execution-tasks/{task['id']}/retry", json={})
        retried = call("GET", f"/platform-execution-tasks/{task['id']}", name="admin")["item"]
        assert retried["request_payload"]["content"]["reply_draft"] == body
        assert private_note not in json.dumps(retried["request_payload"])
        legacy = seed_draft({"reply_draft": "Legacy customer text and internal suggestions"})
        call("POST", f"/platform-drafts/{legacy['id']}/execute", expected=400, json={})
        legacy_task = create_platform_execution_task(draft_id=legacy["id"], action_type="write_customer_reply",
            target="isolated-verification-only", requested_by=accounts["customer_service"]["id"],
            request_payload={"draft_type": "customer_reply", "content": legacy["content"]})
        call("POST", f"/platform-execution-tasks/{legacy_task['id']}/retry", expected=400, json={})
        invalid = call("POST", "/customer-service/messages", json={"message": "Isolated invalid-output persistence boundary"})["item"]
        _finish_message_processing(message_id=invalid["id"], current_user=accounts["customer_service"], run_id=None,
            classification={"intent": "general_question", "risk_level": "low", "reason": "verification seed"},
            decision={"status": "drafted", "decision": "draft_only", "handoff_reason": "invalid structure"},
            reply=parse_customer_reply("Unstructured isolated verification output"), erp_result={}, erp_summary="",
            rag_result={}, rag_summary="", approval_result=None, duration_ms=0)
        invalid_item = call("GET", f"/customer-service/messages/{invalid['id']}")["item"]
        assert not invalid_item["reply_draft"] and invalid_item["reply_parse_status"] == "invalid"
        assert invalid_item["needs_human_review"] and invalid_item["metadata"]["reply_unparsed_output"]
        for erp in ({"ok": False, "items": [{"id": "seed"}]}, {"ok": True, "items": []}):
            assert decide_customer_action({"risk_level": "low", "intent": "logistics"}, erp, {})["status"] == "drafted"

        if browser:
            subprocess.run(["node", "scripts/verify_customer_reply_browser.mjs"], cwd=ROOT, check=True, timeout=150, env={
                **os.environ, "VERIFY_API_BASE_URL": base, "VERIFY_REPLY_USERNAME": accounts["customer_service"]["username"],
                "VERIFY_REPLY_PASSWORD": password, "VERIFY_REPLY_SUBJECT": marker + "-missing-order",
            })
        print(json.dumps({"ok": True, "database_isolated": True, "real_model_cases": 2,
            "real_erp": "erpnext", "real_rag_upload": True, "browser_tested": browser,
            "checks": ["customer_staff_separation", "missing_order_no_auto_writeback", "high_risk_approval",
                       "refresh_persistence", "duplicate_processing_409", "role_boundaries",
                       "dispatch_allowlist", "long_body_retry", "legacy_dispatch_and_retry_blocked",
                       "invalid_output_internal_only"],
            "external_channel_configured": False, "external_send_tested": False}, ensure_ascii=False), flush=True)
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        if thread.is_alive():
            raise RuntimeError("Isolated HTTP server did not stop")


if __name__ == "__main__":
    database = isolated_database_on_local_server("customer") if "--local-postgres" in sys.argv else disposable_database("customer")
    with database as url:
        verify(url, browser="--browser" in sys.argv)
    print("Removed isolated customer verification database.", flush=True)
