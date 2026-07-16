from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.security import require_admin
from app.services.connector_service import get_connector, list_connectors


router = APIRouter(
    prefix="/connectors",
    tags=["connectors"],
)


class ConnectorConfigField(BaseModel):
    name: str
    configured: bool
    secret: bool
    value_preview: str | None
    description: str


class ConnectorResourceItem(BaseModel):
    resource: str
    label: str
    provider_resource: str | None
    position_scopes: list[str]
    position_scope_labels: list[str]
    fields: list[str]


class ConnectorItem(BaseModel):
    id: str
    label: str
    category: str
    description: str
    active: bool
    configured: bool
    status: str
    health_status: str
    health_message: str
    auth_type: str
    admin_only: bool
    supports_real_health_check: bool
    managed_by: str
    capabilities: list[str]
    position_scopes: list[str]
    position_scope_labels: list[str]
    config_fields: list[ConnectorConfigField]
    resources: list[ConnectorResourceItem]
    next_steps: list[str]
    last_checked_at: str


class ConnectorsSummary(BaseModel):
    total: int
    configured: int
    healthy: int
    needs_config: int
    pending: int


class ConnectorsResponse(BaseModel):
    summary: ConnectorsSummary
    items: list[ConnectorItem]


class ConnectorDetailResponse(BaseModel):
    item: ConnectorItem


@router.get("", response_model=ConnectorsResponse)
def get_connectors(current_user: dict = Depends(require_admin)):
    return list_connectors()


@router.get("/{connector_id}", response_model=ConnectorDetailResponse)
def get_connector_detail(
    connector_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": get_connector(connector_id)}
