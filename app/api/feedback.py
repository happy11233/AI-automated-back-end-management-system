from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.security import get_current_user, require_admin
from app.services.feedback_service import (
    complete_feedback,
    create_feedback,
    list_feedback,
)


router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
)


class FeedbackItem(BaseModel):
    id: str
    submitted_by: str | None
    username: str
    display_name: str | None
    position: str | None
    category: str
    priority: str
    title: str
    description: str
    status: str
    admin_note: str | None
    completed_by: str | None
    completed_by_username: str | None
    completed_at: str | None
    created_at: str | None
    updated_at: str | None


class FeedbackSummary(BaseModel):
    total: int
    open: int
    completed: int


class FeedbackListResponse(BaseModel):
    items: list[FeedbackItem]
    summary: FeedbackSummary


class FeedbackCreateRequest(BaseModel):
    category: Literal["功能建议", "体验问题", "数据问题", "自动化需求", "权限流程", "其他"] = "功能建议"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=4, max_length=3000)


class FeedbackCompleteRequest(BaseModel):
    admin_note: str | None = Field(default=None, max_length=1000)


class FeedbackItemResponse(BaseModel):
    item: FeedbackItem


@router.get("", response_model=FeedbackListResponse)
def read_feedback(
    status_value: Literal["all", "open", "completed"] = Query(default="all", alias="status"),
    limit: int = Query(default=80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return list_feedback(
        current_user=current_user,
        status_value=status_value,
        limit=limit,
    )


@router.post("", response_model=FeedbackItemResponse)
def submit_feedback(
    request: FeedbackCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    return {
        "item": create_feedback(
            current_user=current_user,
            category=request.category,
            priority=request.priority,
            title=request.title,
            description=request.description,
        )
    }


@router.post("/{feedback_id}/complete", response_model=FeedbackItemResponse)
def mark_feedback_completed(
    feedback_id: str,
    request: FeedbackCompleteRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": complete_feedback(
            feedback_id=feedback_id,
            admin_note=request.admin_note,
            current_user=current_user,
        )
    }
