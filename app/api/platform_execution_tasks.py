from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.config import settings
from app.services.platform_action_executor_service import (
    get_platform_execution_task_item,
    handle_platform_execution_callback,
    list_platform_execution_task_items,
    retry_platform_execution_task,
)


router = APIRouter(
    prefix="/platform-execution-tasks",
    tags=["platform-execution-tasks"],
)


class PlatformExecutionTaskItem(BaseModel):
    id: str
    draft_id: str
    latest_execution_id: str | None
    action_type: str
    target: str
    status: str
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any] = Field(default_factory=dict)
    external_reference: str | None
    attempt_count: int
    max_attempts: int
    last_error: str | None
    requested_by: str | None
    next_attempt_at: str | None
    completed_at: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None
    updated_at: str | None
    draft_title: str | None = None
    draft_type: str | None = None
    draft_status: str | None = None
    draft_position: str | None = None
    draft_writeback_status: str | None = None


class PlatformExecutionTasksResponse(BaseModel):
    items: list[PlatformExecutionTaskItem]


class PlatformExecutionTaskResponse(BaseModel):
    item: PlatformExecutionTaskItem


class PlatformExecutionRetryResponse(BaseModel):
    draft: dict[str, Any]
    execution: dict[str, Any]
    task: PlatformExecutionTaskItem
    run_id: str
    message: str | None


class PlatformExecutionCallbackRequest(BaseModel):
    callback_token: str
    status: str
    response_payload: dict[str, Any] = Field(default_factory=dict)
    external_reference: str | None = None
    message: str | None = None


class PlatformExecutionCallbackResponse(BaseModel):
    draft: dict[str, Any]
    execution: dict[str, Any] | None = None
    task: PlatformExecutionTaskItem
    message: str | None


@router.get("", response_model=PlatformExecutionTasksResponse)
def get_platform_execution_tasks(
    status_value: str | None = Query(
        default=None,
        alias="status",
        pattern="^(queued|dispatching|waiting_callback|succeeded|failed|cancelled)$",
    ),
    limit: int = Query(default=80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_platform_execution_task_items(
            current_user=current_user,
            status_value=status_value,
            limit=limit,
        )
    }


@router.get("/{task_id}", response_model=PlatformExecutionTaskResponse)
def get_platform_execution_task_detail(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    item = get_platform_execution_task_item(task_id=task_id, current_user=current_user)
    if item is None:
        raise HTTPException(status_code=404, detail="执行任务不存在或无权查看")
    return {"item": item}


@router.post("/{task_id}/retry", response_model=PlatformExecutionRetryResponse)
def retry_platform_execution_task_endpoint(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    return retry_platform_execution_task(task_id=task_id, current_user=current_user)


@router.post("/{task_id}/callback", response_model=PlatformExecutionCallbackResponse)
async def platform_execution_task_callback(
    task_id: str,
    request: Request,
):
    raw_body = await request.body()
    try:
        payload = PlatformExecutionCallbackRequest.model_validate_json(raw_body)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors()) from error

    return handle_platform_execution_callback(
        task_id=task_id,
        callback_token=payload.callback_token,
        status_value=payload.status,
        response_payload=payload.response_payload,
        external_reference=payload.external_reference,
        message=payload.message,
        raw_body=raw_body,
        signature=request.headers.get(settings.platform_action_execution_callback_signature_header),
        timestamp=request.headers.get(settings.platform_action_execution_callback_timestamp_header),
        nonce=request.headers.get(settings.platform_action_execution_callback_nonce_header),
    )
