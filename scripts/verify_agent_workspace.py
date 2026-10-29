"""Real PostgreSQL/API contracts with isolated users; external calls are explicitly stubbed."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import sys
from threading import Event
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.ai_workflows import router
from app.auth.security import create_access_token, hash_password
from app.db import close_pool, execute, fetch_one, open_pool, pool
from app.services.agent_business_event_service import ensure_agent_event_schema
from app.services.run_record_service import finish_run, start_run


def main():
    open_pool()
    marker = "agent-loop-" + uuid4().hex[:10]
    user_ids, run_ids = [], []
    app = FastAPI()
    app.include_router(router)
    accounts = {}
    try:
        ensure_agent_event_schema()
        for position in ("admin", "operations", "customer_service", "finance", "other_operations"):
            uid = str(uuid4())
            user_ids.append(uid)
            role = "admin" if position == "admin" else "employee"
            actual_position = "operations" if position == "other_operations" else None if role == "admin" else position
            execute("INSERT INTO users(id,username,role,position,password_hash) VALUES (%s,%s,%s,%s,%s)", (uid, marker+position, role, actual_position, hash_password(uuid4().hex)))
            accounts[position] = {"id": uid, "username": marker+position, "role": role, "position": actual_position}
            accounts[position]["headers"] = {"Authorization": "Bearer " + create_access_token({**accounts[position], "sub": uid})}
        for name, status in (("operations", "succeeded"), ("operations", "failed"), ("other_operations", "succeeded"), ("finance", "succeeded")):
            user = accounts[name]
            app_id = "finance_report_analysis" if name == "finance" else "operations_competitor_analysis"
            run_id = start_run(run_type="ai_workflow", app_id=app_id, app_name=marker, entrypoint="verification", current_user=user)
            run_ids.append(run_id)
            finish_run(run_id, status_value=status, output_text=marker+" result")
        with TestClient(app) as client:
            def request(name, method, path, expected=200, **kwargs):
                response = client.request(method, path, headers=accounts[name]["headers"], **kwargs)
                assert response.status_code == expected, (path, response.status_code, response.text[:300])
                return response.json()
            data = request("operations", "GET", "/ai-workflows/activity")
            assert data["summary"] == dict(total=2, running=0, succeeded=1, failed=1, blocked=0), data["summary"]
            assert len(data["recent"]) == 2
            assert sum(item["total"] for item in data["trend"]) == 2
            filtered = request("operations", "GET", "/ai-workflows/activity?status=failed")
            assert filtered["summary"] == data["summary"] and len(filtered["recent"]) == 1
            assert filtered["recent"][0]["status"] == "failed"
            request("operations", "GET", "/ai-workflows/activity?workflow_id=finance_report_analysis", 404)
            request("operations", "GET", "/ai-workflows/activity?status=invalid", 422)
            assert client.get("/ai-workflows/activity").status_code == 401
            execute("INSERT INTO user_ai_app_permissions (user_id,app_id,enabled) VALUES (%s,'automation-competitor_analysis',false)", (accounts["operations"]["id"],))
            denied = request("operations", "GET", "/ai-workflows/activity")
            assert denied["summary"]["total"] == 0
            request("operations", "GET", "/ai-workflows/activity?workflow_id=operations_competitor_analysis", 404)
            execute("DELETE FROM user_ai_app_permissions WHERE user_id=%s", (accounts["operations"]["id"],))
            workflow = "operations_competitor_analysis"
            path = "/ai-workflows/" + workflow + "/events"
            event = {"event_id": marker, "event_type": "competitor.snapshot", "data": {"marketplace": "test", "product_name": "verification item", "competitors": [{"name": "test competitor", "price": "10"}]}}
            request("finance", "POST", path, 404, json=event)
            request("operations", "POST", path, 422, json={**event, "data": {}})
            calls = []
            def isolated_model(prompt):
                calls.append(prompt)
                return "Isolated verification result. No external model or platform was called."
            with patch("app.services.ai_workflow_service.chat", isolated_model):
                response = request("operations", "POST", path, json=event)
                run_ids.append(response["run_id"])
                assert not response["reused"] and response["status"] == "succeeded"
                repeated = request("operations", "POST", path, json=event)
                assert repeated["reused"] and repeated["run_id"] == response["run_id"] and len(calls) == 1
                request("operations", "POST", path, 409, json={**event, "data": {**event["data"], "product_name": "changed"}})
                status = request("operations", "GET", path+"/"+marker)
                assert status["run_status"] == "succeeded" and not status["automatic_retry"]
                request("other_operations", "GET", path+"/"+marker, 404)
            assert fetch_one("SELECT count(*) FROM notifications WHERE user_id=%s AND type='agent_event'", (accounts["operations"]["id"],))[0] == 1
            entered, release = Event(), Event()
            concurrent = {**event, "event_id": marker+"-parallel"}
            def slow_model(prompt):
                entered.set()
                assert release.wait(10)
                return "Concurrent isolated result"
            with patch("app.services.ai_workflow_service.chat", slow_model), ThreadPoolExecutor(1) as executor:
                pending = executor.submit(request, "operations", "POST", path, json=concurrent)
                assert entered.wait(10)
                try:
                    request("operations", "POST", path, 409, json=concurrent)
                finally:
                    release.set()
                run_ids.append(pending.result()["run_id"])
            failure = {**event, "event_id": marker+"-failure"}
            with patch("app.services.ai_workflow_service.chat", side_effect=RuntimeError("test failure")):
                request("operations", "POST", path, 502, json=failure)
            failed = request("operations", "POST", path, json=failure)
            assert failed["status"] == "failed" and failed["reused"]
            assert fetch_one("SELECT status,run_id FROM agent_business_events WHERE event_id=%s", (failure["event_id"],))[0] == "failed"
            with patch("app.services.ai_workflow_service.chat", isolated_model), patch("app.services.ai_workflow_service.chat_fast", isolated_model):
                report = request("finance", "POST", "/ai-workflows/finance_report_analysis/events", json={"event_id": marker+"-report", "event_type": "finance.report.ready", "data": {"period": "2026-10", "currency": "CNY", "metrics": {"revenue": 100, "expense": 40}}})
                assert report["status"] == "succeeded"
                listing = request("operations", "POST", "/ai-workflows/operations_listing_launch/events", json={"event_id": marker+"-product", "event_type": "product.updated", "data": {"sku": marker, "name": "Isolated product", "marketplace": "test", "attributes": {"material": "test"}, "compliance_requirements": "verification only"}})
                draft = fetch_one("SELECT status FROM platform_drafts WHERE source_run_id=%s", (listing["run_id"],))
                assert draft and draft[0] == "pending_review"
            # Customer webhook persistence and dedup are real; only the expensive
            # downstream processor is isolated to avoid any platform side effects.
            from app.services.customer_service_automation_service import ingest_and_process_external_message
            processor_calls = []
            def isolated_processor(*, message_id, current_user):
                processor_calls.append(message_id)
                execute("UPDATE customer_service_messages SET status='drafted',reply_draft='Isolated verification draft' WHERE id=%s", (message_id,))
                from app.services.customer_service_automation_service import get_customer_message_detail
                return {**get_customer_message_detail(message_id=message_id, current_user=current_user), "run_id": None, "steps": []}
            with patch("app.services.customer_service_automation_service.process_customer_message", isolated_processor):
                kwargs = dict(service_user=accounts["customer_service"], channel="api", external_id=marker, message="Isolated customer event", auto_process=True)
                first = ingest_and_process_external_message(**kwargs)
                second = ingest_and_process_external_message(**kwargs)
                assert first["processed"] and not second["processed"] and len(processor_calls) == 1
                assert first["item"]["id"] == second["item"]["id"]
        print(json.dumps({"ok": True, "checks": ["authenticated_api", "user_and_position_isolation", "app_permission_revocation", "all_record_aggregation", "instant_filter_consistency", "event_field_validation", "event_result_and_notification", "repeat_delivery", "concurrent_delivery", "failed_event_no_reexecution", "customer_webhook_dedup"], "external_model_and_processor": "stubbed deliberately", "database": "real PostgreSQL"}))
    finally:
        with pool.connection() as conn:
            conn.execute("DELETE FROM customer_service_messages WHERE external_id=%s", (marker,))
            conn.execute("DELETE FROM agent_business_events WHERE user_id=ANY(%s::uuid[])", (user_ids,))
            conn.execute("DELETE FROM audit_logs WHERE user_id=ANY(%s::uuid[])", (user_ids,))
            conn.execute("DELETE FROM platform_drafts WHERE owner_user_id=ANY(%s::uuid[])", (user_ids,))
            conn.execute("DELETE FROM automation_runs WHERE user_id=ANY(%s::uuid[])", (user_ids,))
            conn.execute("DELETE FROM users WHERE id=ANY(%s::uuid[])", (user_ids,))
            conn.commit()
        close_pool()


if __name__ == "__main__":
    main()
