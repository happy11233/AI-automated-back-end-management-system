from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.agent_execution_service import CHAT_PLAN_EXECUTE_WORKFLOW_ID, classify_agent_task
from app.services import chat_plan_execute_service as chat_planner
from app.services.chat_plan_execute_service import build_chat_plan_execute_plan
from app.services.external_action_gateway_service import recognize_external_action_intent


FINANCE_USER = {
    "id": "finance-user",
    "role": "employee",
    "position": "finance",
    "allowed_ai_app_ids": [
        "automation-salary_summary",
        "automation-salary_wechat_send",
        "finance-chat-agent",
    ],
}

OPERATIONS_USER = {
    "id": "ops-user",
    "role": "employee",
    "position": "operations",
    "allowed_ai_app_ids": ["automation-listing"],
}


chat_planner.is_ai_app_allowed = lambda user, app_id: app_id in user.get("allowed_ai_app_ids", [])


def test_salary_wechat_uses_external_action_gateway() -> None:
    message = "把2026年07月工资表发到企业微信给向鑫"
    intent = recognize_external_action_intent(message)
    assert intent is not None
    assert intent.target_channel == "enterprise_wechat"
    assert intent.business_object == "salary_table"

    route = classify_agent_task(message, FINANCE_USER)
    assert route.requires_plan_execute is True
    assert route.workflow_id == CHAT_PLAN_EXECUTE_WORKFLOW_ID
    assert route.intent == "external_action_gateway"

    plan = build_chat_plan_execute_plan(message=message, current_user=FINANCE_USER)
    assert plan["kind"] == "external_action"
    assert plan["target_channel"] == "enterprise_wechat"
    assert plan["business_object"] == "salary_table"
    assert plan["requires_confirmation"] is True


def test_employee_table_send_uses_gateway_instead_of_salary_route() -> None:
    message = "把员工表发到企业微信给张三"
    plan = build_chat_plan_execute_plan(message=message, current_user=FINANCE_USER)
    assert plan["kind"] == "external_action"
    assert plan["target_channel"] == "enterprise_wechat"
    assert plan["business_object"] == "employee_table"


def test_latest_file_email_uses_recent_generated_file() -> None:
    message = "把刚刚生成的文件发到邮箱给 demo@example.com"
    plan = build_chat_plan_execute_plan(message=message, current_user=FINANCE_USER)
    assert plan["kind"] == "external_action"
    assert plan["target_channel"] == "email"
    assert plan["business_object"] == "latest_file"
    assert plan["data_source"] == "latest_generated_file"


def test_external_action_followup_keeps_pending_context() -> None:
    thread_id = "thread-finance-pending"
    pending = {
        "active": True,
        "source_message": "将这个月工资表发给向鑫",
        "recipient_name": "向鑫",
        "target_channel": "unknown_message_channel",
        "business_object": "salary_table",
        "data_source": "latest_generated_file",
        "external_action_type": "send_file",
        "matched_actions": ["发给"],
        "matched_targets": ["接收人"],
    }
    from app.services import external_action_gateway_service as gateway

    original_get_pending_external_action = gateway.get_pending_external_action
    gateway.get_pending_external_action = lambda _: pending
    try:
        intent = gateway.resolve_external_action_followup_intent("企业微信", thread_id, [])
        assert intent is not None
        assert intent.target_channel == "enterprise_wechat"
        assert intent.business_object == "salary_table"
        assert intent.recipient_name == "向鑫"

        route = classify_agent_task("企业微信", FINANCE_USER, thread_id=thread_id)
        assert route.requires_plan_execute is True
        assert route.workflow_id == CHAT_PLAN_EXECUTE_WORKFLOW_ID
        assert route.intent == "external_action_gateway"

        plan = build_chat_plan_execute_plan(message="企业微信", current_user=FINANCE_USER, thread_id=thread_id)
        assert plan["kind"] == "external_action"
        assert plan["target_channel"] == "enterprise_wechat"
        assert plan["business_object"] == "salary_table"
        assert plan["recipient_name"] == "向鑫"
        assert plan["source_message"] == "将这个月工资表发给向鑫"
    finally:
        gateway.get_pending_external_action = original_get_pending_external_action


def test_salary_wechat_followup_keeps_channel_period_and_recipient() -> None:
    thread_id = "thread-finance-followup-window"
    pending = {
        "active": True,
        "source_message": "将工资表发给向鑫",
        "effective_message": "将工资表发给向鑫 企业微信 生成上个月的工资表",
        "recipient_name": "向鑫",
        "target_channel": "enterprise_wechat",
        "business_object": "salary_table",
        "data_source": "erp_resource",
        "external_action_type": "send_file",
        "matched_actions": ["发给"],
        "matched_targets": ["接收人", "企业微信"],
    }
    from app.services import external_action_gateway_service as gateway

    original_get_pending_external_action = gateway.get_pending_external_action
    gateway.get_pending_external_action = lambda _: pending
    try:
        channel_plan = build_chat_plan_execute_plan(
            message="企业微信",
            current_user=FINANCE_USER,
            thread_id=thread_id,
        )
        assert channel_plan["target_channel"] == "enterprise_wechat"
        assert channel_plan["recipient_name"] == "向鑫"
        assert channel_plan["business_object"] == "salary_table"

        period_plan = build_chat_plan_execute_plan(
            message="生成上个月的工资表",
            current_user=FINANCE_USER,
            thread_id=thread_id,
        )
        assert period_plan["target_channel"] == "enterprise_wechat"
        assert period_plan["recipient_name"] == "向鑫"
        assert "上个月" in period_plan["effective_message"] or "上月" in period_plan["effective_message"]

        recipient_plan = build_chat_plan_execute_plan(
            message="发给向鑫",
            current_user=FINANCE_USER,
            thread_id=thread_id,
        )
        assert recipient_plan["target_channel"] == "enterprise_wechat"
        assert recipient_plan["recipient_name"] == "向鑫"
        assert recipient_plan["business_object"] == "salary_table"
    finally:
        gateway.get_pending_external_action = original_get_pending_external_action


def test_finance_clarification_does_not_expose_amazon_terms() -> None:
    plan = build_chat_plan_execute_plan(message="发工资表", current_user=FINANCE_USER)
    question = str(plan.get("question") or plan.get("clarification_question") or "")
    assert "Amazon" not in question
    assert "amazon" not in question.lower()


def test_amazon_fill_stops_before_publish() -> None:
    message = "把 SKU ABC 的商品信息填到 Amazon Seller Central 草稿"
    plan = build_chat_plan_execute_plan(message=message, current_user=OPERATIONS_USER)
    assert plan["kind"] == "external_action"
    assert plan["target_channel"] == "amazon_seller_central"
    assert plan["business_object"] == "listing_draft"
    assert any(step["ref"] == "playwright_amazon.prepare_seller_central_listing" for step in plan["steps"])
    assert plan["requires_confirmation"] is True


def test_pending_send_does_not_capture_new_questions() -> None:
    from app.services import external_action_gateway_service as gateway
    from app.services.chat_react_decision_service import decide_chat_action
    from unittest.mock import patch

    pending = {
        "active": True, "status": "waiting_clarification", "target_channel": "email",
        "source_message": "把工资表发到邮箱", "business_object": "salary_table",
        "external_action_type": "send_file", "data_source": "erp_resource",
    }
    with patch.object(gateway, "get_pending_external_action", return_value=pending):
        for message in ["请假找谁请", "请假流程是什么？", "工资表应该发给谁？", "你好", "谢谢"]:
            assert gateway.should_resume_external_action_with_message(message, pending) is False, message
            assert gateway.resolve_external_action_followup_intent(message, "pending-thread") is None, message
            assert classify_agent_task(message, FINANCE_USER, thread_id="pending-thread").requires_plan_execute is False, message
        assert decide_chat_action("请假找谁请", FINANCE_USER).action == "rag_query"


def test_information_questions_do_not_trigger_external_actions() -> None:
    for message in [
        "工资表应该发送给谁？", "这个文件怎么发送到企业微信？", "请假申请需要发邮件吗？",
        "如何填写 Amazon Seller Central 草稿？", "帮我看看工资表应该发给谁？",
    ]:
        assert recognize_external_action_intent(message) is None, message
        assert classify_agent_task(message, FINANCE_USER).requires_plan_execute is False, message
    for message in ["把工资表发送到邮箱 demo@example.com", "请问把文件发送到企业微信给张三可以吗？"]:
        assert recognize_external_action_intent(message) is not None, message


def test_email_recipient_is_an_address_and_followup_is_current_message_only() -> None:
    from app.services import external_action_gateway_service as gateway
    from unittest.mock import patch

    pending = {
        "active": True, "status": "waiting_clarification", "target_channel": "email",
        "source_message": "把工资表发到邮箱", "business_object": "salary_table",
        "external_action_type": "send_file", "data_source": "erp_resource",
    }
    assert recognize_external_action_intent("把工资表发到邮箱给张三").recipient_name is None
    with patch.object(gateway, "get_pending_external_action", return_value=pending):
        intent = gateway.resolve_external_action_followup_intent("demo@example.com", "pending-thread")
        assert intent is not None and intent.recipient_name == "demo@example.com"
        assert gateway.resolve_external_action_followup_intent("张三", "pending-thread") is None


def main() -> None:
    test_salary_wechat_uses_external_action_gateway()
    test_employee_table_send_uses_gateway_instead_of_salary_route()
    test_latest_file_email_uses_recent_generated_file()
    test_external_action_followup_keeps_pending_context()
    test_salary_wechat_followup_keeps_channel_period_and_recipient()
    test_finance_clarification_does_not_expose_amazon_terms()
    test_amazon_fill_stops_before_publish()
    test_pending_send_does_not_capture_new_questions()
    test_information_questions_do_not_trigger_external_actions()
    test_email_recipient_is_an_address_and_followup_is_current_message_only()
    print("external_action_gateway_spec: ok")


if __name__ == "__main__":
    main()
