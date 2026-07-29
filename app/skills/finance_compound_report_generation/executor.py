from __future__ import annotations

from typing import Any

from app.services.finance_compound_generation_service import execute_finance_compound_generation
from app.services.finance_compound_intent_service import recognize_finance_compound_intent
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
    intent = payload.get("intent") or recognize_finance_compound_intent(message)
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    result = execute_finance_compound_generation(
        message=message,
        current_user=current_user,
        intent=intent,
        run_id=metadata.get("run_id"),
        source=source,
    )
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status="succeeded",
        answer=result.answer,
        attachments=[
            {
                "type": "excel_file",
                "filename": attachment.filename,
                "mime_type": attachment.mime_type,
                "content": attachment.content,
                "metadata": attachment.metadata,
            }
            for attachment in result.attachments
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
