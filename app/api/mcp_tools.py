from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.security import require_admin
from app.services.mcp_tool_registry_service import (
    check_mcp_tool_health,
    get_mcp_tool,
    list_mcp_tools,
    update_mcp_tool,
)


router = APIRouter(
    prefix="/admin/mcp-tools",
    tags=["admin-mcp-tools"],
)


class McpToolItem(BaseModel):
    id: str
    tool_id: str
    server_name: str
    tool_name: str
    label: str
    category: str
    description: str
    risk_level: str
    risk_label: str
    position_scopes: list[str]
    position_scope_labels: list[str]
    execution_mode: str
    enabled: bool
    status: str
    status_label: str
    requires_approval: bool
    supports_real_health_check: bool
    health_status: str
    health_message: str
    last_checked_at: str | None = None
    input_schema: list[dict[str, Any]] = Field(default_factory=list)
    output_schema: list[dict[str, Any]] = Field(default_factory=list)
    safety_rules: list[str] = Field(default_factory=list)
    example: str
    admin_note: str = ""


class McpToolsSummary(BaseModel):
    total: int
    enabled: int
    paused: int
    high_risk: int
    servers: int
    healthy: int


class McpToolsResponse(BaseModel):
    summary: McpToolsSummary
    items: list[McpToolItem]


class McpToolDetailResponse(BaseModel):
    item: McpToolItem


class McpToolUpdateRequest(BaseModel):
    enabled: bool
    admin_note: str | None = Field(default=None, max_length=1000)


class McpToolHealthResponse(BaseModel):
    item: McpToolItem
    health: dict[str, Any]


@router.get("", response_model=McpToolsResponse)
def get_mcp_tools(current_user: dict = Depends(require_admin)):
    return list_mcp_tools()


@router.get("/{tool_id}", response_model=McpToolDetailResponse)
def get_mcp_tool_detail(
    tool_id: str,
    current_user: dict = Depends(require_admin),
):
    return get_mcp_tool(tool_id)


@router.patch("/{tool_id}", response_model=McpToolDetailResponse)
def update_mcp_tool_item(
    tool_id: str,
    request: McpToolUpdateRequest,
    current_user: dict = Depends(require_admin),
):
    return update_mcp_tool(
        tool_id=tool_id,
        enabled=request.enabled,
        admin_note=request.admin_note,
        current_user=current_user,
    )


@router.post("/{tool_id}/health-check", response_model=McpToolHealthResponse)
def check_mcp_tool_health_item(
    tool_id: str,
    current_user: dict = Depends(require_admin),
):
    return check_mcp_tool_health(tool_id=tool_id, current_user=current_user)
