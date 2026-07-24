from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth.security import get_current_user
from app.services.notification_service import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


class NotificationItem(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    body: str
    status: str
    resource_type: str | None
    resource_id: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    read_at: str | None
    created_at: str | None


class NotificationsResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int


class NotificationResponse(BaseModel):
    item: NotificationItem


class NotificationReadAllResponse(BaseModel):
    updated_count: int


@router.get("", response_model=NotificationsResponse)
def get_notifications(
    status_value: str | None = Query(default=None, alias="status", pattern="^(unread|read)$"),
    limit: int = Query(default=80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return list_notifications(
        current_user=current_user,
        status_value=status_value,
        limit=limit,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    return {
        "item": mark_notification_read(
            notification_id=notification_id,
            current_user=current_user,
        )
    }


@router.post("/read-all", response_model=NotificationReadAllResponse)
def read_all_notifications(current_user: dict = Depends(get_current_user)):
    return {"updated_count": mark_all_notifications_read(current_user=current_user)}
