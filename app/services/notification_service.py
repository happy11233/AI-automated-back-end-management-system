from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json
from app.services.run_record_service import sanitize_metadata


NOTIFICATION_STATUSES = {"unread", "read"}


def ensure_notification_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'unread' CHECK (status IN ('unread', 'read')),
            resource_type TEXT,
            resource_id TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            read_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notifications_user_status_created_at
        ON notifications(user_id, status, created_at DESC);
        """
    )


def create_notification(
    *,
    user_id: str | None,
    type_value: str,
    title: str,
    body: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not user_id:
        return None

    row = fetch_one(
        """
        INSERT INTO notifications (
            user_id, type, title, body, resource_type, resource_id, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING
            id, user_id, type, title, body, status, resource_type,
            resource_id, metadata, read_at, created_at;
        """,
        (
            user_id,
            type_value[:80],
            title[:180],
            body[:1000],
            resource_type,
            resource_id,
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    return _map_notification_row(row)


def notify_user_and_admins(
    *,
    user_id: str | None,
    type_value: str,
    title: str,
    body: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    target_ids: list[str] = []
    if user_id:
        target_ids.append(user_id)

    rows = fetch_all("SELECT id FROM users WHERE role = 'admin';")
    for row in rows:
        admin_id = str(row[0])
        if admin_id not in target_ids:
            target_ids.append(admin_id)

    items: list[dict[str, Any]] = []
    for target_id in target_ids:
        item = create_notification(
            user_id=target_id,
            type_value=type_value,
            title=title,
            body=body,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
        )
        if item:
            items.append(item)
    return items


def list_notifications(
    *,
    current_user: dict,
    status_value: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    if status_value and status_value not in NOTIFICATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效通知状态")

    conditions = ["user_id = %s"]
    params: list[Any] = [current_user["id"]]

    if status_value:
        conditions.append("status = %s")
        params.append(status_value)

    params.append(max(1, min(limit, 200)))
    rows = fetch_all(
        f"""
        SELECT
            id, user_id, type, title, body, status, resource_type,
            resource_id, metadata, read_at, created_at
        FROM notifications
        WHERE {" AND ".join(conditions)}
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )
    unread_row = fetch_one(
        "SELECT count(*) FROM notifications WHERE user_id = %s AND status = 'unread';",
        (current_user["id"],),
    )
    return {
        "items": [_map_notification_row(row) for row in rows],
        "unread_count": int(unread_row[0] or 0) if unread_row else 0,
    }


def mark_notification_read(*, notification_id: str, current_user: dict) -> dict[str, Any]:
    row = fetch_one(
        """
        UPDATE notifications
        SET status = 'read', read_at = COALESCE(read_at, now())
        WHERE id = %s AND user_id = %s
        RETURNING
            id, user_id, type, title, body, status, resource_type,
            resource_id, metadata, read_at, created_at;
        """,
        (notification_id, current_user["id"]),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在或无权查看")
    return _map_notification_row(row)


def mark_all_notifications_read(*, current_user: dict) -> int:
    row = fetch_one(
        """
        WITH updated AS (
            UPDATE notifications
            SET status = 'read', read_at = COALESCE(read_at, now())
            WHERE user_id = %s AND status = 'unread'
            RETURNING id
        )
        SELECT count(*) FROM updated;
        """,
        (current_user["id"],),
    )
    return int(row[0] or 0) if row else 0


def _map_notification_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "user_id": str(row[1]),
        "type": row[2],
        "title": row[3],
        "body": row[4],
        "status": row[5],
        "resource_type": row[6],
        "resource_id": row[7],
        "metadata": row[8] or {},
        "read_at": row[9].isoformat() if row[9] else None,
        "created_at": row[10].isoformat() if row[10] else None,
    }
