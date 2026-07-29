from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.security import require_admin
from app.services.connector_service import get_connector, list_connectors
from app.services.enterprise_wechat_service import (
    get_enterprise_wechat_admin_state,
    get_enterprise_wechat_contact,
    get_enterprise_wechat_settings_public,
    list_enterprise_wechat_contacts,
    recipient_from_candidate,
    send_enterprise_wechat_test_file,
    sync_enterprise_wechat_departments_and_users,
    update_enterprise_wechat_settings,
    upsert_enterprise_wechat_manual_group,
)
from app.services.logging_service import write_audit_log


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


class EnterpriseWechatSettingsUpdateRequest(BaseModel):
    corp_id: str | None = None
    agent_id: str | None = None
    secret: str | None = None
    real_send_enabled: bool | None = None
    timeout_seconds: int | None = None
    clear_secret: bool = False


class EnterpriseWechatManualGroupRequest(BaseModel):
    name: str
    chat_id: str


class EnterpriseWechatTestSendRequest(BaseModel):
    recipient_id: str


@router.get("", response_model=ConnectorsResponse)
def get_connectors(current_user: dict = Depends(require_admin)):
    return list_connectors()


@router.get("/wechat-work/management")
def get_enterprise_wechat_management(current_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return get_enterprise_wechat_admin_state()


@router.put("/wechat-work/settings")
def update_enterprise_wechat_management_settings(
    request: EnterpriseWechatSettingsUpdateRequest,
    current_user: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        payload = update_enterprise_wechat_settings(
            corp_id=request.corp_id,
            agent_id=request.agent_id,
            secret=request.secret,
            real_send_enabled=request.real_send_enabled,
            timeout_seconds=request.timeout_seconds,
            clear_secret=request.clear_secret,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    write_audit_log(
        current_user.get("id"),
        "admin.enterprise_wechat.settings_update",
        resource_type="connector",
        resource_id="wechat_work",
        metadata={
            "corp_id_configured": bool(request.corp_id),
            "agent_id_configured": bool(request.agent_id),
            "secret_updated": bool(request.secret),
            "clear_secret": request.clear_secret,
            "real_send_enabled": request.real_send_enabled,
            "timeout_seconds": request.timeout_seconds,
        },
    )
    return {"settings": payload}


@router.post("/wechat-work/sync")
def sync_enterprise_wechat_contacts(current_user: dict = Depends(require_admin)) -> dict[str, Any]:
    result = sync_enterprise_wechat_departments_and_users()
    write_audit_log(
        current_user.get("id"),
        "admin.enterprise_wechat.sync",
        resource_type="connector",
        resource_id="wechat_work",
        metadata={
            "status": result.get("status"),
            "synced_count": result.get("synced_count"),
            "department_count": result.get("department_count"),
            "user_count": result.get("user_count"),
            "group_count": result.get("group_count"),
            "errors": result.get("errors"),
        },
    )
    return result


@router.get("/wechat-work/contacts")
def list_enterprise_wechat_management_contacts(
    query: str = Query("", max_length=80),
    object_type: str = Query("all", max_length=32),
    current_user: dict = Depends(require_admin),
) -> dict[str, Any]:
    return list_enterprise_wechat_contacts(query=query, object_type=object_type, limit=50)


@router.post("/wechat-work/groups")
def upsert_enterprise_wechat_group(
    request: EnterpriseWechatManualGroupRequest,
    current_user: dict = Depends(require_admin),
) -> dict[str, Any]:
    try:
        item = upsert_enterprise_wechat_manual_group(name=request.name, chat_id=request.chat_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    write_audit_log(
        current_user.get("id"),
        "admin.enterprise_wechat.group_upsert",
        resource_type="enterprise_wechat_group",
        resource_id=str(item.get("id") or ""),
        metadata={
            "name": item.get("name"),
            "chat_id_configured": bool(item.get("chat_id")),
        },
    )
    return {"item": item, "contacts": list_enterprise_wechat_contacts(object_type="group", limit=50)}


@router.post("/wechat-work/test-send")
def test_enterprise_wechat_send(
    request: EnterpriseWechatTestSendRequest,
    current_user: dict = Depends(require_admin),
) -> dict[str, Any]:
    contact = get_enterprise_wechat_contact(request.recipient_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业微信接收对象不存在")
    result = send_enterprise_wechat_test_file(recipient=recipient_from_candidate(contact))
    write_audit_log(
        current_user.get("id"),
        "admin.enterprise_wechat.test_send",
        resource_type="enterprise_wechat_contact",
        resource_id=request.recipient_id,
        metadata={
            "status": result.get("status"),
            "sent": result.get("sent"),
            "recipient": {
                "id": contact.get("id"),
                "object_type": contact.get("object_type"),
                "name": contact.get("name"),
                "department": contact.get("department"),
                "phone_last4": contact.get("phone_last4"),
            },
        },
    )
    return result


@router.get("/wechat-work/settings")
def get_enterprise_wechat_management_settings(current_user: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"settings": get_enterprise_wechat_settings_public()}


@router.get("/{connector_id}", response_model=ConnectorDetailResponse)
def get_connector_detail(
    connector_id: str,
    current_user: dict = Depends(require_admin),
):
    return {"item": get_connector(connector_id)}
