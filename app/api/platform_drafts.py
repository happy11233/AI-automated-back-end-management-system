from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.operations_listing_amazon_service import confirm_and_prepare_amazon_listing_upload
from app.services.platform_action_executor_service import (
    execute_platform_draft_action,
    latest_platform_action_executions,
    publish_platform_draft_action,
    review_platform_draft,
)
from app.services.platform_draft_service import (
    get_platform_draft,
    list_platform_drafts,
)


router = APIRouter(
    prefix="/platform-drafts",
    tags=["platform-drafts"],
)


class PlatformDraftItem(BaseModel):
    id: str
    draft_type: str
    platform: str
    external_target: str
    title: str
    status: str
    position: str
    owner_user_id: str | None
    source_run_id: str | None
    source_resource_type: str | None
    source_resource_id: str | None
    content: dict
    writeback_status: str
    writeback_message: str | None
    metadata: dict
    created_at: str
    updated_at: str


class PlatformDraftsResponse(BaseModel):
    items: list[PlatformDraftItem]


class PlatformActionExecutionItem(BaseModel):
    id: str
    draft_id: str
    action_type: str
    executor_type: str
    target: str
    status: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    error_message: str | None
    run_id: str | None
    triggered_by: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str | None


class PlatformExecutionTaskItem(BaseModel):
    id: str
    draft_id: str
    latest_execution_id: str | None
    action_type: str
    target: str
    status: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    external_reference: str | None
    attempt_count: int
    max_attempts: int
    last_error: str | None
    requested_by: str | None
    next_attempt_at: str | None
    completed_at: str | None
    metadata: dict[str, Any]
    created_at: str | None
    updated_at: str | None
    draft_title: str | None = None
    draft_type: str | None = None
    draft_status: str | None = None
    draft_position: str | None = None
    draft_writeback_status: str | None = None


class PlatformDraftDetailResponse(BaseModel):
    item: PlatformDraftItem
    executions: list[PlatformActionExecutionItem]


class PlatformDraftExecuteResponse(BaseModel):
    draft: PlatformDraftItem
    execution: PlatformActionExecutionItem
    task: PlatformExecutionTaskItem | None = None
    run_id: str
    message: str


class PlatformDraftReviewRequest(BaseModel):
    decision: str
    comment: str | None = None


class PlatformDraftReviewResponse(BaseModel):
    item: PlatformDraftItem


class AmazonListingUploadRequest(BaseModel):
    confirmed: bool = False
    upload_mode: Literal["auto", "web_form", "batch_excel"] = "auto"
    target_marketplace: str | None = Field(default=None, max_length=20)
    price: float | None = None
    inventory: int | None = None


class AmazonListingUploadResponse(BaseModel):
    draft: PlatformDraftItem
    execution: PlatformActionExecutionItem
    task: PlatformExecutionTaskItem | None = None
    run_id: str
    message: str
    amazon_upload: dict[str, Any]


@router.get("", response_model=PlatformDraftsResponse)
def get_platform_drafts(
    draft_type: str | None = Query(default=None, pattern="^(listing|customer_reply)$"),
    status_value: str | None = Query(
        default=None,
        alias="status",
        pattern="^(pending_review|approved|published|rejected)$",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_platform_drafts(
            current_user=current_user,
            draft_type=draft_type,
            status_value=status_value,
            limit=limit,
        ),
    }


@router.get("/{draft_id}", response_model=PlatformDraftDetailResponse)
def get_platform_draft_detail(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    item = get_platform_draft(draft_id=draft_id, current_user=current_user)
    if item is None:
        raise HTTPException(status_code=404, detail="平台草稿不存在或无权查看")

    return {
        "item": item,
        "executions": latest_platform_action_executions(
            draft_id=draft_id,
            current_user=current_user,
        ),
    }


@router.post("/{draft_id}/execute", response_model=PlatformDraftExecuteResponse)
def execute_platform_draft(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    return execute_platform_draft_action(
        draft_id=draft_id,
        current_user=current_user,
    )


@router.post("/{draft_id}/review", response_model=PlatformDraftReviewResponse)
def review_platform_draft_endpoint(
    draft_id: str,
    request: PlatformDraftReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    return {
        "item": review_platform_draft(
            draft_id=draft_id,
            current_user=current_user,
            decision=request.decision,
            comment=request.comment,
        ),
    }


@router.post("/{draft_id}/publish", response_model=PlatformDraftExecuteResponse)
def publish_platform_draft(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    return publish_platform_draft_action(
        draft_id=draft_id,
        current_user=current_user,
    )


@router.post("/{draft_id}/amazon-upload", response_model=AmazonListingUploadResponse)
def prepare_amazon_listing_upload(
    draft_id: str,
    request: AmazonListingUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    return confirm_and_prepare_amazon_listing_upload(
        draft_id=draft_id,
        current_user=current_user,
        confirmed=request.confirmed,
        upload_mode=request.upload_mode,
        target_marketplace=request.target_marketplace,
        price=request.price,
        inventory=request.inventory,
    )
