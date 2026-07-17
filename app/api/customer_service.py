import secrets
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.auth.security import decode_access_token, get_current_user, get_user_by_id
from app.config import settings
from app.services.customer_service_automation_service import (
    create_customer_message,
    get_customer_message_detail,
    ingest_and_process_external_message,
    list_customer_messages,
    process_customer_message,
)


router = APIRouter(
    prefix="/customer-service",
    tags=["customer-service"],
)


class CustomerServiceMessageItem(BaseModel):
    id: str
    channel: str
    external_id: str | None
    buyer_name: str | None
    buyer_email: str | None
    buyer_language: str
    marketplace: str | None
    order_no: str | None
    tracking_no: str | None
    sku: str | None
    subject: str | None
    message: str
    intent: str | None
    risk_level: str
    status: str
    automation_decision: str | None
    reply_draft: str | None
    handoff_reason: str | None
    erp_summary: str | None
    rag_summary: str | None
    erp_references: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    approval_id: str | None
    run_id: str | None
    assigned_to: str | None
    created_by: str | None
    processed_by: str | None
    processed_at: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None
    updated_at: str | None


class CustomerServiceMessageEventItem(BaseModel):
    id: str
    message_id: str
    event_type: str
    actor_id: str | None
    content: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None


class CustomerServiceMessagesResponse(BaseModel):
    items: list[CustomerServiceMessageItem]


class CustomerServiceMessageDetailResponse(BaseModel):
    item: CustomerServiceMessageItem
    events: list[CustomerServiceMessageEventItem]


class CustomerServiceMessageCreateRequest(BaseModel):
    channel: Literal["manual", "amazon", "email", "ticket", "api"] = "manual"
    external_id: str | None = Field(default=None, max_length=160)
    buyer_name: str | None = Field(default=None, max_length=120)
    buyer_email: str | None = Field(default=None, max_length=180)
    buyer_language: str = Field(default="auto", max_length=40)
    marketplace: str | None = Field(default=None, max_length=80)
    order_no: str | None = Field(default=None, max_length=120)
    tracking_no: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, max_length=120)
    subject: str | None = Field(default=None, max_length=180)
    message: str = Field(min_length=1, max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomerServiceProcessStep(BaseModel):
    step_order: int
    step_name: str
    status: str
    duration_ms: int


class CustomerServiceProcessResponse(BaseModel):
    item: CustomerServiceMessageItem
    run_id: str
    steps: list[CustomerServiceProcessStep]
    events: list[CustomerServiceMessageEventItem]


class CustomerServiceWebhookMessageRequest(CustomerServiceMessageCreateRequest):
    auto_process: bool = True


class CustomerServiceWebhookMessageResponse(BaseModel):
    item: CustomerServiceMessageItem
    processed: bool
    run_id: str | None
    steps: list[CustomerServiceProcessStep] = Field(default_factory=list)
    events: list[CustomerServiceMessageEventItem] = Field(default_factory=list)
    webhook_auth: str


@router.get("/messages", response_model=CustomerServiceMessagesResponse)
def get_customer_service_messages(
    status_filter: str | None = Query(default=None, alias="status"),
    risk_level: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    return {
        "items": list_customer_messages(
            current_user=current_user,
            status_filter=status_filter,
            risk_level=risk_level,
            limit=limit,
        )
    }


@router.post("/messages", response_model=CustomerServiceMessageDetailResponse)
def create_customer_service_message(
    request: CustomerServiceMessageCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    item = create_customer_message(
        current_user=current_user,
        channel=request.channel,
        external_id=request.external_id,
        buyer_name=request.buyer_name,
        buyer_email=request.buyer_email,
        buyer_language=request.buyer_language,
        marketplace=request.marketplace,
        order_no=request.order_no,
        tracking_no=request.tracking_no,
        sku=request.sku,
        subject=request.subject,
        message=request.message,
        metadata=request.metadata,
    )
    return get_customer_message_detail(message_id=item["id"], current_user=current_user)


@router.get("/messages/{message_id}", response_model=CustomerServiceMessageDetailResponse)
def get_customer_service_message_detail(
    message_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_customer_message_detail(message_id=message_id, current_user=current_user)


@router.post("/messages/{message_id}/process", response_model=CustomerServiceProcessResponse)
def post_process_customer_service_message(
    message_id: str,
    current_user: dict = Depends(get_current_user),
):
    return process_customer_message(message_id=message_id, current_user=current_user)


@router.post("/webhooks/messages", response_model=CustomerServiceWebhookMessageResponse)
def receive_external_customer_service_message(
    request: CustomerServiceWebhookMessageRequest,
    raw_request: Request,
    authorization: str | None = Header(default=None),
    current_secret: str | None = Header(default=None, alias="X-Customer-Service-Webhook-Secret"),
):
    service_user, auth_type = _resolve_webhook_user(
        authorization=authorization,
        configured_secret_header=raw_request.headers.get(settings.customer_service_webhook_secret_header),
        default_secret_header=current_secret,
    )
    result = ingest_and_process_external_message(
        service_user=service_user,
        channel=request.channel,
        external_id=request.external_id,
        buyer_name=request.buyer_name,
        buyer_email=request.buyer_email,
        buyer_language=request.buyer_language,
        marketplace=request.marketplace,
        order_no=request.order_no,
        tracking_no=request.tracking_no,
        sku=request.sku,
        subject=request.subject,
        message=request.message,
        metadata=request.metadata,
        auto_process=request.auto_process,
    )
    return {
        **result,
        "webhook_auth": auth_type,
    }


def _resolve_webhook_user(
    *,
    authorization: str | None,
    configured_secret_header: str | None,
    default_secret_header: str | None,
) -> tuple[dict[str, Any], str]:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        user = get_user_by_id(str(user_id)) if user_id else None
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="webhook token 对应用户不存在",
            )
        if user.get("role") != "admin" and user.get("position") != "customer_service":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有客服岗位或管理员 token 可以接入外部客服消息。",
            )
        return user, "bearer_token"

    configured_secret = settings.customer_service_webhook_secret
    provided_secret = configured_secret_header or default_secret_header
    if configured_secret:
        if provided_secret and secrets.compare_digest(provided_secret, configured_secret):
            return {
                "id": None,
                "username": "external_customer_service_webhook",
                "role": "employee",
                "position": "customer_service",
                "department": "客服部",
            }, "webhook_secret"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="客服外部消息 webhook 密钥无效。",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="请使用客服岗位 Bearer token，或在 .env 配置 CUSTOMER_SERVICE_WEBHOOK_SECRET 后使用 webhook 密钥。",
    )
