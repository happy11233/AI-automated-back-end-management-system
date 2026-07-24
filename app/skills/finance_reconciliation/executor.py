from __future__ import annotations

from typing import Any

from app.services.finance_reconciliation_service import (
    FinanceReconciliationInputFile,
    reconcile_finance_workbooks,
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
    raw_files = payload.get("files")
    if not isinstance(raw_files, list):
        raise ValueError("财务对账 Skill 需要传入文件列表。")
    files = [
        FinanceReconciliationInputFile(
            filename=str(item["filename"]),
            content=item["content"],
        )
        for item in raw_files
        if isinstance(item, dict) and isinstance(item.get("content"), bytes)
    ]
    result = reconcile_finance_workbooks(
        files=files,
        instruction=str(payload.get("instruction") or ""),
        base_currency=str(payload.get("base_currency") or "CNY"),
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
