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
    incomplete_count = result.metadata["incomplete_line_count"]
    review_message = (
        f"其中 {incomplete_count} 条订单缺少成本资料，需补充后重跑；未提供整体利润合计。"
        if incomplete_count
        else "按已提供费用计算，待财务复核。"
    )
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status="succeeded",
        answer=f"已生成 {result.filename}。{review_message}此文件为订单贡献利润复核表，不代表银行到账已对平或已入账。",
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
