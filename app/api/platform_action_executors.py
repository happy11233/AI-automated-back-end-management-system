from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.platform_action_executor_config_service import (
    check_platform_action_executor_health,
    create_platform_action_executor,
    delete_platform_action_executor,
    get_platform_action_executor,
    list_platform_action_executors,
    update_platform_action_executor,
)


router = APIRouter(
    prefix="/platform-action-executors",
    tags=["platform-action-executors"],
)


class PlatformActionExecutorOption(BaseModel):
    value: str
    label: str


class PlatformActionExecutorSummary(BaseModel):
    total: int
    enabled: int
    configured: int
    healthy: int
    needs_config: int


class PlatformActionExecutorItem(BaseModel):
    id: str
    name: str
    executor_type: str
    executor_type_label: str
    action_types: list[str]
    action_type_labels: list[str]
    webhook_url: str | None
    webhook_url_preview: str | None
    api_key_configured: bool
    api_key_preview: str | None
    timeout_seconds: int
    enabled: bool
    configured: bool
    health_status: str
    health_message: str | None
    last_checked_at: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_environment_fallback: bool
    created_at: str | None
    updated_at: str | None


class PlatformActionExecutorsResponse(BaseModel):
    summary: PlatformActionExecutorSummary
    items: list[PlatformActionExecutorItem]
    action_types: list[PlatformActionExecutorOption]
    executor_types: list[PlatformActionExecutorOption]


class PlatformActionExecutorResponse(BaseModel):
    item: PlatformActionExecutorItem


class PlatformActionExecutorMutationRequest(BaseModel):
    name: str | None = None
    executor_type: str | None = None
    action_types: list[str] | None = None
    webhook_url: str | None = None
    api_key: str | None = None
    timeout_seconds: int | None = None
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None


class PlatformActionExecutorDeleteResponse(BaseModel):
    ok: bool
    id: str


@router.get("", response_model=PlatformActionExecutorsResponse)
def get_platform_action_executors(current_user: dict = Depends(require_admin)):
    return list_platform_action_executors()


@router.get("/{executor_id}", response_model=PlatformActionExecutorResponse)
def get_platform_action_executor_detail(
    executor_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": get_platform_action_executor(executor_id)}


@router.post("", response_model=PlatformActionExecutorResponse)
def create_platform_action_executor_endpoint(
    request: PlatformActionExecutorMutationRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": create_platform_action_executor(
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.put("/{executor_id}", response_model=PlatformActionExecutorResponse)
def update_platform_action_executor_endpoint(
    executor_id: str,
    request: PlatformActionExecutorMutationRequest,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": update_platform_action_executor(
            executor_id=executor_id,
            payload=request.model_dump(exclude_unset=True),
            current_user=current_user,
        )
    }


@router.post("/{executor_id}/health-check", response_model=PlatformActionExecutorResponse)
def check_platform_action_executor_health_endpoint(
    executor_id: str,
    current_user: dict = Depends(require_admin),
):
    return {
        "item": check_platform_action_executor_health(
            executor_id=executor_id,
            current_user=current_user,
        )
    }


@router.delete("/{executor_id}", response_model=PlatformActionExecutorDeleteResponse)
def delete_platform_action_executor_endpoint(
    executor_id: str,
    current_user: dict = Depends(require_admin),
):
    return delete_platform_action_executor(executor_id=executor_id, current_user=current_user)
