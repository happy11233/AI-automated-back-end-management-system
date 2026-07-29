from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.permissions import erp_scopes_for_position  # noqa: E402
from app.skills.executor import MIN_REACT_EXECUTION_CONFIDENCE, validate_skill_access  # noqa: E402
from app.skills.registry import SkillDefinition, list_skills, skill_doc_absolute_path, skill_for_react_action  # noqa: E402


EXPECTED_SKILLS = {
    "operations_listing": {
        "position": "operations",
        "app_id": "automation-listing",
        "flow_key": "automation:operations:listing",
        "react_actions": {"operations_listing_draft"},
    },
    "customer_reply": {
        "position": "customer_service",
        "app_id": "customer-service-message-loop",
        "flow_key": "automation:customer_service:message-loop",
        "react_actions": {"customer_service_reply_draft"},
    },
    "finance_salary_export": {
        "position": "finance",
        "app_id": "automation-salary_summary",
        "flow_key": "automation:finance:salary-export",
        "react_actions": {"finance_salary_export"},
    },
    "finance_compound_report_generation": {
        "position": "finance",
        "app_id": "automation-report_analysis",
        "flow_key": "automation:finance:compound-report-generation",
        "react_actions": {"finance_compound_report_generation"},
    },
    "finance_salary_wechat_send": {
        "position": "finance",
        "app_id": "automation-salary_wechat_send",
        "flow_key": "automation:finance:salary-wechat-send",
        "react_actions": {"finance_salary_wechat_send"},
    },
    "finance_excel_settlement": {
        "position": "finance",
        "app_id": "finance-excel-transform",
        "flow_key": "automation:finance:excel-file-transform",
        "react_actions": set(),
    },
    "finance_reconciliation": {
        "position": "finance",
        "app_id": "finance-reconciliation",
        "flow_key": "automation:finance:reconciliation",
        "react_actions": set(),
    },
}

EXPECTED_DOC_PHRASES = {
    "operations_listing": ["运营", "Listing", "平台草稿", "automation-listing"],
    "customer_reply": ["客服", "回复草稿", "customer-service-message-loop", "审批"],
    "finance_salary_export": ["财务", "工资", "Salary Slip", "automation-salary_summary"],
    "finance_compound_report_generation": ["财务", "复合", "Salary Slip", "automation-report_analysis"],
    "finance_salary_wechat_send": ["财务", "微信", "Salary Slip", "automation-salary_wechat_send"],
    "finance_excel_settlement": ["财务", "Excel", "finance-excel-transform", "ERP"],
    "finance_reconciliation": ["财务", "对账", "finance-reconciliation", "不自动入账"],
}


def main() -> None:
    skills = list_skills()
    by_id = {skill.skill_id: skill for skill in skills}

    assert set(by_id) == set(EXPECTED_SKILLS), sorted(by_id)
    assert len(skills) == len(by_id), "skill_id must be unique"

    for skill_id, expected in EXPECTED_SKILLS.items():
        skill = by_id[skill_id]
        assert skill.position == expected["position"], skill
        assert skill.app_id == expected["app_id"], skill
        assert skill.flow_key == expected["flow_key"], skill
        assert set(skill.react_actions) == expected["react_actions"], skill
        assert skill.name and skill.description, skill
        assert skill.input_schema, skill
        assert skill.output_schema, skill
        assert skill.safety_rules, skill
        assert skill.verification_scripts, skill
        assert_executor_importable(skill)
        assert_skill_doc(skill)
        assert_erp_resources_do_not_exceed_position(skill)

    assert skill_for_react_action("operations_listing_draft").skill_id == "operations_listing"
    assert skill_for_react_action("customer_service_reply_draft").skill_id == "customer_reply"
    assert skill_for_react_action("finance_salary_export").skill_id == "finance_salary_export"
    assert skill_for_react_action("finance_compound_report_generation").skill_id == "finance_compound_report_generation"
    assert skill_for_react_action("finance_salary_wechat_send").skill_id == "finance_salary_wechat_send"
    assert skill_for_react_action("rag_query") is None

    assert_access_guards(by_id)
    assert_chat_dispatch_uses_skill_executor()
    assert_finance_apis_use_skill_executor()

    print(json.dumps({
        "ok": True,
        "skill_count": len(skills),
        "skill_ids": sorted(by_id),
        "react_actions": sorted(
            action
            for skill in skills
            for action in skill.react_actions
        ),
        "min_react_execution_confidence": MIN_REACT_EXECUTION_CONFIDENCE,
        "note": "static/import Skill Registry verification; no mock/stub/fake; business execution remains in existing real services",
    }, ensure_ascii=False, indent=2))


def assert_executor_importable(skill: SkillDefinition) -> None:
    module_name, function_name = skill.executor.split(":", 1)
    module = importlib.import_module(module_name)
    executor = getattr(module, function_name)
    assert callable(executor), skill.executor


def assert_skill_doc(skill: SkillDefinition) -> None:
    doc_path = skill_doc_absolute_path(skill)
    assert doc_path.exists(), doc_path
    text = doc_path.read_text(encoding="utf-8")
    assert len(text) >= 400, f"{doc_path} is too short"
    assert "## 权限规则" in text, doc_path
    assert "## 执行步骤" in text, doc_path
    assert "## 输出格式" in text, doc_path
    assert "## 安全边界" in text, doc_path
    for phrase in EXPECTED_DOC_PHRASES[skill.skill_id]:
        assert phrase in text, f"{doc_path} missing {phrase}"


def assert_erp_resources_do_not_exceed_position(skill: SkillDefinition) -> None:
    allowed_by_position = set(erp_scopes_for_position(skill.position))
    unknown = [resource for resource in skill.allowed_erp_resources if resource not in allowed_by_position]
    assert not unknown, f"{skill.skill_id} ERP resource exceeds position scope: {unknown}"


def assert_access_guards(by_id: dict[str, SkillDefinition]) -> None:
    operations_user = user("operations", allowed_apps=["automation-listing"])
    finance_user = user(
        "finance",
        allowed_apps=[
            "automation-salary_summary",
            "automation-report_analysis",
            "automation-salary_wechat_send",
            "finance-excel-transform",
            "finance-reconciliation",
        ],
    )
    customer_user = user("customer_service", allowed_apps=["customer-service-message-loop"])
    admin_user = {"id": "admin", "username": "admin", "role": "admin", "position": None}

    context = validate_skill_access(skill=by_id["operations_listing"], current_user=operations_user)
    assert context["execution_user"]["position"] == "operations", context

    admin_context = validate_skill_access(skill=by_id["customer_reply"], current_user=admin_user)
    assert admin_context["execution_user"]["position"] == "customer_service", admin_context

    expect_http_error(
        lambda: validate_skill_access(skill=by_id["operations_listing"], current_user=finance_user),
        403,
    )
    expect_http_error(
        lambda: validate_skill_access(skill=by_id["finance_salary_export"], current_user=customer_user),
        403,
    )
    expect_http_error(
        lambda: validate_skill_access(
            skill=by_id["finance_salary_export"],
            current_user=finance_user,
            react_decision={"confidence": 0.5, "requested_position": "finance"},
        ),
        400,
    )
    expect_http_error(
        lambda: validate_skill_access(
            skill=by_id["finance_salary_wechat_send"],
            current_user=user("finance", allowed_apps=["automation-salary_summary"]),
        ),
        403,
    )
    expect_http_error(
        lambda: validate_skill_access(
            skill=by_id["finance_compound_report_generation"],
            current_user=user("finance", allowed_apps=["automation-salary_summary"]),
        ),
        403,
    )
    expect_http_error(
        lambda: validate_skill_access(
            skill=by_id["finance_excel_settlement"],
            current_user=finance_user,
            requested_erp_resources=["Customer"],
        ),
        403,
    )


def assert_chat_dispatch_uses_skill_executor() -> None:
    dispatcher = (ROOT / "app/services/chat_automation_dispatcher.py").read_text(encoding="utf-8")
    main_py = (ROOT / "app/main.py").read_text(encoding="utf-8")

    assert "execute_skill(" in dispatcher, "chat automation must call Skill Executor"
    assert "skill_for_react_action(" in dispatcher, "chat automation must map ReAct actions through Skill Registry"
    assert "from app.services.ai_workflow_service import run_ai_workflow" not in dispatcher, "chat dispatcher must not call workflow directly"
    assert "from app.services.customer_service_automation_service" not in dispatcher, "chat dispatcher must not call customer service automation directly"
    assert "react_decision=chat_react_decision_dict(react_decision)" in main_py, "chat route must pass ReAct decision into Skill Executor"
    assert "skill_for_react_action(decision.action)" in main_py, "chat route must build Skill candidate from Registry"


def assert_finance_apis_use_skill_executor() -> None:
    automation_api = (ROOT / "app/api/automation.py").read_text(encoding="utf-8")

    for skill_id in [
        "finance_salary_export",
        "finance_salary_wechat_send",
        "finance_excel_settlement",
        "finance_reconciliation",
    ]:
        assert f'skill_id="{skill_id}"' in automation_api, f"finance API must call Skill Executor for {skill_id}"

    forbidden_direct_calls = [
        "export_salary_workbook_from_erp(",
        "transform_finance_excel(",
        "reconcile_finance_workbooks(",
    ]
    for text in forbidden_direct_calls:
        assert text not in automation_api, f"finance API must not call service directly: {text}"

    assert "from app.skills.executor import SkillExecutionResult, execute_skill" in automation_api
    assert "selected_erp_resources" in automation_api and '"erp_resources": selected_erp_resources' in automation_api


def user(position: str, *, allowed_apps: list[str]) -> dict[str, Any]:
    return {
        "id": f"{position}-user",
        "username": f"{position}_demo",
        "role": "employee",
        "position": position,
        "allowed_ai_app_ids": allowed_apps,
    }


def expect_http_error(callback, status_code: int) -> None:
    try:
        callback()
    except HTTPException as error:
        assert error.status_code == status_code, error.detail
        return
    raise AssertionError(f"expected HTTPException {status_code}")


if __name__ == "__main__":
    main()
