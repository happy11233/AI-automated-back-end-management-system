from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.security import get_current_user
from app.services.automation_flow_service import get_flow_config, list_flow_configs


router = APIRouter(
    prefix="/automation-flows",
    tags=["automation-flows"],
)


class FlowResourceItem(BaseModel):
    resource: str
    label: str
    description: str
    provider_refs: dict[str, str]


class FlowStepItem(BaseModel):
    id: str
    name: str
    inputs: list[str]
    retryable: bool


class AutomationFlowItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    app_id: str
    name: str
    description: str
    category: str
    position: str | None
    position_label: str
    status: str
    version: str
    publish_status: str
    owner: str
    trigger_type: str
    entrypoint: str
    input_schema: list[dict[str, Any]]
    output_schema: list[dict[str, Any]]
    prompt_summary: str
    prompt_template_preview: str
    model_settings: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    allowed_tools: list[str]
    allowed_erp_resources: list[FlowResourceItem]
    permission_rules: list[str]
    approval_policy: str
    failure_strategy: str
    steps: list[FlowStepItem]
    source: str


class AutomationFlowsResponse(BaseModel):
    items: list[AutomationFlowItem]


class AutomationFlowDetailResponse(BaseModel):
    item: AutomationFlowItem


@router.get("", response_model=AutomationFlowsResponse)
def get_automation_flows(
    position: str | None = Query(default=None),
    category: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    flows = list_flow_configs(current_user)

    if position:
        flows = [item for item in flows if item["position"] == position]

    if category:
        flows = [item for item in flows if category.lower() in item["category"].lower()]

    return {"items": flows}


@router.get("/{flow_id}", response_model=AutomationFlowDetailResponse)
def get_automation_flow_detail(
    flow_id: str,
    current_user: dict = Depends(get_current_user),
):
    return {"item": get_flow_config(flow_id, current_user)}
