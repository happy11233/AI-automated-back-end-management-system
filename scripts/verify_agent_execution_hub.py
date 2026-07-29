from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.agent_execution_service import (  # noqa: E402
    PLAN_EXECUTE_WORKFLOW_ID,
    build_finance_monthly_package_plan,
    classify_agent_task,
)
from app.services.mcp_tool_registry_service import get_mcp_tool_definition  # noqa: E402


def main() -> None:
    finance_user = {
        "id": "finance-user",
        "username": "finance_demo",
        "role": "employee",
        "position": "finance",
        "allowed_ai_app_ids": [
            "automation-salary_summary",
            "automation-salary_wechat_send",
            "automation-report_analysis",
        ],
    }
    complex_message = "整理这个月财务报表和工资表，合并后通过个人微信发给张三"
    route = classify_agent_task(complex_message, finance_user)
    assert route.mode == "plan_execute", route
    assert route.workflow_id == PLAN_EXECUTE_WORKFLOW_ID, route
    assert route.estimated_step_count > 5, route

    user_report_message = "把这个月的财务报表和工资表整理好后通过微信发给屁焱"
    user_report_route = classify_agent_task(user_report_message, finance_user)
    assert user_report_route.mode == "plan_execute", user_report_route
    assert user_report_route.workflow_id == PLAN_EXECUTE_WORKFLOW_ID, user_report_route

    selected_workflow_message = f"请按「统计工资」能力处理：{user_report_message}"
    selected_workflow_route = classify_agent_task(selected_workflow_message, finance_user)
    assert selected_workflow_route.mode == "plan_execute", selected_workflow_route
    assert selected_workflow_route.workflow_id == PLAN_EXECUTE_WORKFLOW_ID, selected_workflow_route

    plan = build_finance_monthly_package_plan(complex_message)
    step_keys = {item["key"] for item in plan}
    assert {
        "intent",
        "permission",
        "salary_export",
        "finance_report",
        "merge_workbook",
        "save_files",
        "wechat_prepare",
        "final_result",
    }.issubset(step_keys), step_keys
    assert any(item["sensitive"] for item in plan), plan

    simple_salary = classify_agent_task("导出这个月工资表", finance_user)
    assert simple_salary.mode == "react", simple_salary

    simple_customer = classify_agent_task(
        "帮我根据客户说物流太慢生成客服回复草稿",
        {**finance_user, "position": "customer_service"},
    )
    assert simple_customer.mode == "react", simple_customer

    n8n_tool = get_mcp_tool_definition("n8n.dispatch_workflow")
    rpa_tool = get_mcp_tool_definition("desktop_rpa.prepare_wechat_attachment")
    assert n8n_tool.risk_level == "high"
    assert rpa_tool.risk_level == "high"
    assert n8n_tool.requires_approval is True
    assert rpa_tool.requires_approval is True

    print(json.dumps({
        "ok": True,
        "complex_route": route.workflow_id,
        "user_report_route_checked": True,
        "selected_workflow_prefix_checked": True,
        "plan_step_count": len(plan),
        "simple_react_checked": True,
        "high_risk_mcp_checked": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
