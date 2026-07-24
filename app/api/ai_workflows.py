from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.ai_workflow_service import (
    get_ai_workflow,
    list_ai_workflows,
    run_ai_workflow,
)


router = APIRouter(
    prefix="/ai-workflows",
    tags=["ai-workflows"],
)


class AiWorkflowStage(BaseModel):
    key: str
    label: str
    description: str
    automated: bool


class AiWorkflowItem(BaseModel):
    id: str
    name: str
    position: str
    position_label: str
    category: str
    scenario: str
    business_value: str
    trigger_type: str
    automation_level: str
    execution_mode: str
    entry_view: str
    entry_label: str
    source_task_id: str
    input_placeholder: str
    output_contract: str
    requires_approval: bool
    approval_policy: str
    tools: list[str]
    erp_resources: list[str]
    writeback_target: str
    notification_target: str
    saved_minutes: int
    version: str
    executable: bool
    stages: list[AiWorkflowStage]


class AiWorkflowsResponse(BaseModel):
    items: list[AiWorkflowItem]


class AiWorkflowDetailResponse(BaseModel):
    item: AiWorkflowItem


class AiWorkflowRunRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=10000)


class AiWorkflowRunStep(BaseModel):
    step_order: int
    step_name: str
    status: str
    duration_ms: int


class AiWorkflowRunResponse(BaseModel):
    run_id: str
    workflow: AiWorkflowItem
    status: str
    answer: str
    erp_references: list[dict[str, Any]] = Field(default_factory=list)
    platform_draft: dict[str, Any] | None = None
    steps: list[AiWorkflowRunStep]
    created_at: str


@router.get("", response_model=AiWorkflowsResponse)
def get_ai_workflows(current_user: dict = Depends(get_current_user)):
    return {"items": list_ai_workflows(current_user)}


@router.get("/{workflow_id}", response_model=AiWorkflowDetailResponse)
def get_ai_workflow_detail(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    return {"item": get_ai_workflow(workflow_id, current_user)}


@router.post("/{workflow_id}/run", response_model=AiWorkflowRunResponse)
def post_run_ai_workflow(
    workflow_id: str,
    request: AiWorkflowRunRequest,
    current_user: dict = Depends(get_current_user),
):
    return run_ai_workflow(
        workflow_id=workflow_id,
        input_text=request.input_text,
        current_user=current_user,
    )
