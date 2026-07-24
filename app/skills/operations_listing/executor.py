from __future__ import annotations

from typing import Any

from app.services.ai_workflow_service import run_ai_workflow
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
    result = run_ai_workflow(
        workflow_id="operations_listing_launch",
        input_text=message,
        current_user=current_user,
    )
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status=str(result.get("status") or "succeeded"),
        run_id=result.get("run_id"),
        answer=result.get("answer"),
        platform_draft=result.get("platform_draft") if isinstance(result.get("platform_draft"), dict) else None,
        erp_references=result.get("erp_references") or [],
        metadata={
            "source": source,
            "legacy_workflow_id": "operations_listing_launch",
            "flow_key": execution_context["flow_key"],
            "risk_level": skill.risk_level,
            "step_count": len(result.get("steps") or []),
        },
    )
