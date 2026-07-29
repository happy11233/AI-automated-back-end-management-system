from __future__ import annotations

from typing import Any

from app.services.finance_salary_service import export_salary_workbook_from_erp
from app.services.finance_salary_wechat_service import (
    ensure_salary_wechat_intent_ready,
    prepare_salary_wechat_dispatch,
    recognize_salary_wechat_send_intent,
)
from app.skills.executor import SkillExecutionResult
from app.skills.registry import SkillDefinition


def execute(
    *,
    payload: dict[str, Any],
    current_user: dict,
    source: str,
    skill: SkillDefinition,
    execution_context: dict[str, Any],
) -> SkillExecutionResult:
    message = str(payload.get("message") or payload.get("input_text") or "").strip()
    intent = payload.get("intent")
    if not intent:
        intent = recognize_salary_wechat_send_intent(message)
    ensure_salary_wechat_intent_ready(intent)

    salary_result = export_salary_workbook_from_erp(
        message=message,
        current_user=current_user,
        intent=intent.salary_intent,
    )
    dispatch = prepare_salary_wechat_dispatch(
        intent=intent,
        salary_result=salary_result,
        current_user=current_user,
        source=source,
    )

    answer = (
        f"已生成 {salary_result.intent.period_label} 员工工资表，并创建企业微信文件发送确认任务。\n"
        f"接收人：{intent.recipient_name}\n"
        f"文件：{salary_result.filename}\n"
        f"状态：等待确认接收对象和敏感数据。\n"
        "确认后由后端发送文件，不附带正文说明。"
    )
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status="waiting_manual_send",
        answer=answer,
        attachments=[
            {
                "filename": salary_result.filename,
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "content": salary_result.content,
            }
        ],
        metadata={
            "source": source,
            "skill_id": skill.skill_id,
            "skill_name": skill.name,
            "app_id": skill.app_id,
            "flow_key": execution_context["flow_key"],
            "risk_level": skill.risk_level,
            "salary": salary_result.metadata,
            "wechat_send": dispatch,
        },
    )
