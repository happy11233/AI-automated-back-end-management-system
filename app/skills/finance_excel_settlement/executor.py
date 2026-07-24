from __future__ import annotations

from typing import Any

from app.services.finance_excel_service import transform_finance_excel
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
    content = payload.get("content")
    if not isinstance(content, bytes):
        raise ValueError("财务 Excel Skill 需要传入文件 bytes。")
    result = transform_finance_excel(
        source_filename=str(payload.get("source_filename") or "finance.xlsx"),
        content=content,
        instruction=str(payload.get("instruction") or ""),
        erp_context=payload.get("erp_context") if isinstance(payload.get("erp_context"), list) else [],
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
