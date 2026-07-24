from __future__ import annotations

from typing import Any

from app.services.customer_service_automation_service import (
    create_customer_message,
    process_customer_message,
)
from app.services.platform_draft_service import get_platform_draft
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
    customer_message = create_customer_message(
        current_user=current_user,
        channel=str(payload.get("channel") or "manual"),
        buyer_name=payload.get("buyer_name"),
        buyer_email=payload.get("buyer_email"),
        buyer_language=str(payload.get("buyer_language") or "auto"),
        marketplace=payload.get("marketplace"),
        order_no=payload.get("order_no"),
        tracking_no=payload.get("tracking_no"),
        sku=payload.get("sku"),
        subject=str(payload.get("subject") or "Skill 触发客服回复草稿"),
        message=message,
        metadata={
            "source": source,
            "skill_id": skill.skill_id,
            "flow_key": execution_context["flow_key"],
            **(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}),
        },
    )
    result = process_customer_message(message_id=customer_message["id"], current_user=current_user)
    item = result["item"]
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    draft_id = metadata.get("platform_draft_id")
    draft = get_platform_draft(draft_id=str(draft_id), current_user=current_user) if draft_id else None
    return SkillExecutionResult(
        skill_id=skill.skill_id,
        status=str(item.get("status") or "succeeded"),
        run_id=result.get("run_id"),
        answer=item.get("reply_draft"),
        platform_draft=draft,
        approval_result={"approval_id": item.get("approval_id")} if item.get("approval_id") else None,
        erp_references=item.get("erp_references") or [],
        metadata={
            "source": source,
            "message_id": item["id"],
            "intent": item.get("intent"),
            "status": item.get("status"),
            "risk_level": item.get("risk_level"),
            "platform_draft_id": draft_id,
            "writeback_status": metadata.get("writeback_status"),
            "automation_decision": item.get("automation_decision"),
            "flow_key": execution_context["flow_key"],
            "step_count": len(result.get("steps") or []),
        },
    )
