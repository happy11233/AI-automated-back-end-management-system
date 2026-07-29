from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import finance_salary_wechat_service as service  # noqa: E402
from app.services.finance_salary_wechat_service import (  # noqa: E402
    build_salary_wechat_plan,
    build_wechat_prepare_confirmation_task,
    dispatch_enterprise_wechat_file_send_task,
    dispatch_salary_wechat_send_task,
    recognize_salary_wechat_send_intent,
    run_record_status_for_salary_wechat,
)
from app.config import settings  # noqa: E402
from app.db import close_pool, open_pool  # noqa: E402
from app.skills.executor import validate_skill_access  # noqa: E402
from app.skills.registry import get_skill  # noqa: E402


def main() -> None:
    message = "生成这个月员工工资表，准备通过企业微信发给张三"
    intent = recognize_salary_wechat_send_intent(message)
    assert intent.intent == "finance_salary_wechat_send", intent
    assert intent.recipient_name == "张三", intent
    assert intent.salary_intent.intent == "finance_salary_export", intent

    missing_contact = recognize_salary_wechat_send_intent(
        "生成这个月员工工资表，准备通过企业微信发送"
    )
    assert "微信联系人" in missing_contact.missing_fields, missing_contact

    plan = build_salary_wechat_plan(intent)
    assert plan["requires_recipient_confirmation"] is True
    assert plan["requires_sensitive_confirmation"] is True
    assert plan["manual_final_send_required"] is False
    assert any(step["key"] == "enterprise_wechat_send" for step in plan["steps"])
    assert "不附带正文说明" in plan["steps"][-1]["description"]
    assert any(item["status"] == "waiting_wechat_confirmation" for item in plan["status_flow"])
    assert any(item["status"] == "completed" for item in plan["status_flow"])

    skill = get_skill("finance_salary_wechat_send")
    finance_user = {
        "id": "finance-user",
        "username": "finance_demo",
        "role": "employee",
        "position": "finance",
        "allowed_ai_app_ids": ["automation-salary_wechat_send"],
    }
    context = validate_skill_access(skill=skill, current_user=finance_user)
    assert context["execution_user"]["position"] == "finance", context

    try:
        validate_skill_access(
            skill=skill,
            current_user={
                **finance_user,
                "allowed_ai_app_ids": [],
            },
        )
    except HTTPException as error:
        assert error.status_code == 403, error.detail
    else:
        raise AssertionError("未启用工资表微信应用时必须被阻断")

    original_mode = settings.finance_wechat_executor_mode
    original_webhook_url = settings.finance_wechat_n8n_webhook_url
    open_pool()
    try:
        selected_recipient = {
            "id": "wechat-user-demo",
            "object_type": "user",
            "object_type_label": "成员",
            "name": "张三",
            "wechat_userid": "zhangsan",
            "department": "财务部",
            "phone_last4": "1234",
            "avatar_text": "张",
            "send_target": {"kind": "user", "value": "zhangsan"},
        }
        dispatch = {
            "recipient_name": "张三",
            "recipient": selected_recipient,
            "recipient_search": {
                "query": "张三",
                "items": [selected_recipient],
                "matched_count": 1,
                "needs_selection": False,
                "selected_item": selected_recipient,
            },
            "requires_recipient_selection": False,
            "manual_final_send_required": False,
            "payload": {
                "recipient_name": "张三",
                "recipient": selected_recipient,
                "period_label": intent.salary_intent.period_label,
                "source": "verify_script",
                "message_body": "",
            },
            "logs": [],
            "plan": plan,
        }
        settings.finance_wechat_executor_mode = "manual_final_click"
        settings.finance_wechat_n8n_webhook_url = None
        confirmation_execution = build_wechat_prepare_confirmation_task(
            dispatch=dispatch,
            artifact_id="artifact-demo",
            artifact_filename="salary-demo.xlsx",
            current_user=finance_user,
        )
        assert confirmation_execution["status"] == "waiting_wechat_confirmation", confirmation_execution
        assert confirmation_execution["requires_sensitive_confirmation"] is True, confirmation_execution
        assert confirmation_execution["message_body"] == "", confirmation_execution
        confirmation_card = confirmation_execution["confirmation_card"]
        assert confirmation_card["type"] == "enterprise_wechat_file_send_confirmation", confirmation_card
        assert confirmation_card["message_body"] == "", confirmation_card
        assert confirmation_card["artifact"]["artifact_id"] == "artifact-demo", confirmation_card
        assert confirmation_card["recipient_search"]["items"][0]["phone_last4"] == "1234", confirmation_card
        assert any(
            item["tool_id"] == "file_center.get_generated_file_download_path"
            for item in confirmation_execution["mcp_tool_calls"]
        ), confirmation_execution

        manual_execution = dispatch_salary_wechat_send_task(
            dispatch=dispatch,
            artifact_id="artifact-demo",
            artifact_filename="salary-demo.xlsx",
            current_user=finance_user,
        )
        assert manual_execution["status"] == "waiting_manual_send", manual_execution
        assert manual_execution["download_path"] == "/files/artifact-demo/download", manual_execution
        assert manual_execution["payload"]["safety"]["auto_click_send_allowed"] is False
        assert any(
            item["tool_id"] == "file_center.get_generated_file_download_path"
            for item in manual_execution["mcp_tool_calls"]
        ), manual_execution
        assert run_record_status_for_salary_wechat(manual_execution["status"]) == "blocked"

        original_real_send_enabled = settings.message_sender_real_send_enabled
        original_storage_lookup = service.get_generated_file_storage_reference
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as temp_file:
            temp_file.write(b"demo")
            temp_file.flush()
            service.get_generated_file_storage_reference = lambda artifact_id, current_user: {
                "storage_path": temp_file.name,
                "filename": "salary-demo.xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            settings.message_sender_real_send_enabled = False
            enterprise_execution = dispatch_enterprise_wechat_file_send_task(
                artifact_id="artifact-demo",
                recipient_candidate_id=selected_recipient["id"],
                recipient=selected_recipient,
                recipient_name="张三",
                current_user=finance_user,
            )
            assert enterprise_execution["status"] == "waiting_executor", enterprise_execution
            assert enterprise_execution["message_body"] == "", enterprise_execution
            assert enterprise_execution["send_result"]["sent"] is False, enterprise_execution
            assert enterprise_execution["recipient"]["phone_last4"] == "1234", enterprise_execution
        service.get_generated_file_storage_reference = original_storage_lookup
        settings.message_sender_real_send_enabled = original_real_send_enabled

    finally:
        settings.finance_wechat_executor_mode = original_mode
        settings.finance_wechat_n8n_webhook_url = original_webhook_url
        if "original_storage_lookup" in locals():
            service.get_generated_file_storage_reference = original_storage_lookup
        if "original_real_send_enabled" in locals():
            settings.message_sender_real_send_enabled = original_real_send_enabled
        close_pool()

    print(json.dumps({
        "ok": True,
        "intent": intent.intent,
        "recipient_name": intent.recipient_name,
        "plan_step_count": len(plan["steps"]),
        "manual_final_send_required": plan["manual_final_send_required"],
        "permission_guard_checked": True,
        "enterprise_wechat_waiting_executor_checked": True,
        "post_file_confirmation_checked": True,
        "confirmation_card_checked": True,
        "message_body_empty_checked": True,
        "mcp_file_center_trace_checked": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
