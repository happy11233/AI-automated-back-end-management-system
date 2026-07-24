from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.business_action_loop_service import build_business_action_loop


router = APIRouter(
    prefix="/business-action-loop",
    tags=["business-action-loop"],
)


class BusinessActionLoopSummary(BaseModel):
    total: int
    pending_review: int
    waiting_external: int
    succeeded: int
    failed: int
    unread_notifications: int


class BusinessActionLoopItem(BaseModel):
    draft_id: str
    draft_type: str
    platform: str
    external_target: str
    title: str
    draft_status: str
    draft_status_label: str
    position: str
    owner_user_id: str | None
    source_run_id: str | None
    source_resource_type: str | None
    source_resource_id: str | None
    writeback_status: str
    writeback_status_label: str
    writeback_message: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None
    updated_at: str | None
    latest_task_id: str | None
    latest_action_type: str | None
    latest_action_label: str | None
    latest_task_status: str | None
    latest_task_status_label: str | None
    external_reference: str | None
    attempt_count: int
    max_attempts: int
    last_error: str | None
    completed_at: str | None
    task_updated_at: str | None
    stage: str
    stage_label: str
    next_action: str


class BusinessActionLoopResponse(BaseModel):
    summary: BusinessActionLoopSummary
    items: list[BusinessActionLoopItem]


@router.get("", response_model=BusinessActionLoopResponse)
def get_business_action_loop(
    limit: int = Query(default=80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "admin" and current_user.get("position") not in {"operations", "customer_service"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前岗位无权查看业务动作闭环")
    return build_business_action_loop(current_user=current_user, limit=limit)
