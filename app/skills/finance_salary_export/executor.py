from __future__ import annotations

from typing import Any

from app.services.finance_salary_service import (
    export_salary_workbook_from_erp,
    recognize_salary_export_intent,
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
        intent = recognize_salary_export_intent(message)
    result = export_salary_workbook_from_erp(
        message=message,
        current_user=current_user,
        intent=intent,
    )
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status="succeeded",
        answer=f"已生成 {result.filename}",
        attachments=[
            {
                "filename": result.filename,
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "content": result.content,
            }
        ],
        metadata={
            "source": source,
            "skill_id": skill.skill_id,
            "skill_name": skill.name,
            "app_id": skill.app_id,
            "flow_key": execution_context["flow_key"],
            **result.metadata,
        },
    )
