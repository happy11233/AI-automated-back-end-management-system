from __future__ import annotations

from typing import Any

from app.services.operations_listing_amazon_service import generate_operations_listing_draft
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
    return generate_operations_listing_draft(
        payload=payload,
        current_user=current_user,
        source=source,
        skill=skill,
        execution_context=execution_context,
    )
