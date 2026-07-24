from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one
from app.services.logging_service import write_audit_log
from app.services.notification_service import create_notification, notify_user_and_admins


FEEDBACK_STATUSES = {"open", "completed"}
FEEDBACK_PRIORITIES = {"low", "normal", "high", "urgent"}
FEEDBACK_CATEGORIES = {
    "功能建议",
    "体验问题",
    "数据问题",
    "自动化需求",
    "权限流程",
    "其他",
}


def ensure_feedback_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS feedback_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            submitted_by UUID REFERENCES users(id) ON DELETE SET NULL,
            username TEXT NOT NULL,
            display_name TEXT,
            position TEXT CHECK (position IS NULL OR position IN ('operations', 'customer_service', 'finance')),
            category TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'completed')),
            admin_note TEXT,
            completed_by UUID REFERENCES users(id) ON DELETE SET NULL,
            completed_by_username TEXT,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_feedback_items_status_created_at
        ON feedback_items(status, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_feedback_items_submitted_created_at
        ON feedback_items(submitted_by, created_at DESC);
        """
    )


def list_feedback(
    *,
    current_user: dict,
    status_value: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    if status_value in {None, ""}:
        status_value = "all"
    if status_value != "all" and status_value not in FEEDBACK_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效反馈状态")

    conditions: list[str] = []
    params: list[Any] = []

    if current_user.get("role") != "admin":
        conditions.append("submitted_by = %s")
        params.append(current_user["id"])

    summary = _feedback_summary(conditions, params)

    if status_value != "all":
        conditions.append("status = %s")
        params.append(status_value)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(max(1, min(limit, 200)))
    rows = fetch_all(
        f"""
        SELECT
            id,
            submitted_by,
            username,
            display_name,
            position,
            category,
            priority,
            title,
            description,
            status,
            admin_note,
            completed_by,
            completed_by_username,
            completed_at,
            created_at,
            updated_at
        FROM feedback_items
        {where_sql}
        ORDER BY
            CASE status WHEN 'open' THEN 0 ELSE 1 END,
            created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )

    return {
        "items": [_feedback_from_row(row) for row in rows],
        "summary": summary,
    }


def create_feedback(
    *,
    current_user: dict,
    category: str,
    priority: str,
    title: str,
    description: str,
) -> dict[str, Any]:
    normalized_category = _normalize_category(category)
    normalized_priority = _normalize_priority(priority)
    clean_title = title.strip()
    clean_description = description.strip()

    if len(clean_title) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="反馈标题至少需要 2 个字")
    if len(clean_description) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="反馈内容至少需要 4 个字")

    row = fetch_one(
        """
        INSERT INTO feedback_items (
            submitted_by,
            username,
            display_name,
            position,
            category,
            priority,
            title,
            description
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING
            id,
            submitted_by,
            username,
            display_name,
            position,
            category,
            priority,
            title,
            description,
            status,
            admin_note,
            completed_by,
            completed_by_username,
            completed_at,
            created_at,
            updated_at;
        """,
        (
            current_user["id"],
            current_user["username"],
            current_user.get("display_name"),
            current_user.get("position"),
            normalized_category,
            normalized_priority,
            clean_title[:120],
            clean_description[:3000],
        ),
    )
    item = _feedback_from_row(row)

    write_audit_log(
        user_id=current_user["id"],
        action="feedback.create",
        resource_type="feedback",
        resource_id=item["id"],
        metadata={
            "username": current_user["username"],
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "category": item["category"],
            "priority": item["priority"],
            "title": item["title"],
        },
    )
    notify_user_and_admins(
        user_id=None,
        type_value="feedback.submitted",
        title="收到新的员工反馈",
        body=f"{_position_label(item['position'])}{item['username']} 提交了反馈：{item['title']}",
        resource_type="feedback",
        resource_id=item["id"],
        metadata={
            "category": item["category"],
            "priority": item["priority"],
            "position": item["position"],
        },
    )
    return item


def complete_feedback(
    *,
    feedback_id: str,
    admin_note: str | None,
    current_user: dict,
) -> dict[str, Any]:
    clean_note = (admin_note or "").strip()[:1000] or "管理员已完成该反馈处理。"
    row = fetch_one(
        """
        UPDATE feedback_items
        SET
            status = 'completed',
            admin_note = %s,
            completed_by = %s,
            completed_by_username = %s,
            completed_at = COALESCE(completed_at, now()),
            updated_at = now()
        WHERE id = %s
        RETURNING
            id,
            submitted_by,
            username,
            display_name,
            position,
            category,
            priority,
            title,
            description,
            status,
            admin_note,
            completed_by,
            completed_by_username,
            completed_at,
            created_at,
            updated_at;
        """,
        (
            clean_note,
            current_user["id"],
            current_user["username"],
            feedback_id,
        ),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="反馈不存在")

    item = _feedback_from_row(row)
    write_audit_log(
        user_id=current_user["id"],
        action="feedback.complete",
        resource_type="feedback",
        resource_id=item["id"],
        metadata={
            "admin_username": current_user["username"],
            "submitted_by": item["submitted_by"],
            "submitted_username": item["username"],
            "title": item["title"],
            "admin_note": item["admin_note"],
        },
    )
    create_notification(
        user_id=item["submitted_by"],
        type_value="feedback.completed",
        title="你的反馈已完成",
        body=f"反馈「{item['title']}」已由管理员处理完成：{item['admin_note']}",
        resource_type="feedback",
        resource_id=item["id"],
        metadata={
            "category": item["category"],
            "priority": item["priority"],
            "completed_by": item["completed_by_username"],
        },
    )
    return item


def _feedback_summary(conditions: list[str], params: list[Any]) -> dict[str, int]:
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    row = fetch_one(
        f"""
        SELECT
            count(*) AS total,
            count(*) FILTER (WHERE status = 'open') AS open_count,
            count(*) FILTER (WHERE status = 'completed') AS completed_count
        FROM feedback_items
        {where_sql};
        """,
        tuple(params),
    )
    return {
        "total": int(row[0] or 0) if row else 0,
        "open": int(row[1] or 0) if row else 0,
        "completed": int(row[2] or 0) if row else 0,
    }


def _normalize_category(value: str) -> str:
    category = (value or "").strip()
    if category not in FEEDBACK_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效反馈分类")
    return category


def _normalize_priority(value: str) -> str:
    priority = (value or "normal").strip()
    if priority not in FEEDBACK_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效反馈优先级")
    return priority


def _position_label(position: str | None) -> str:
    return {
        "operations": "运营 ",
        "customer_service": "客服 ",
        "finance": "财务 ",
    }.get(position or "", "")


def _feedback_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "submitted_by": str(row[1]) if row[1] else None,
        "username": row[2],
        "display_name": row[3],
        "position": row[4],
        "category": row[5],
        "priority": row[6],
        "title": row[7],
        "description": row[8],
        "status": row[9],
        "admin_note": row[10],
        "completed_by": str(row[11]) if row[11] else None,
        "completed_by_username": row[12],
        "completed_at": row[13].isoformat() if row[13] else None,
        "created_at": row[14].isoformat() if row[14] else None,
        "updated_at": row[15].isoformat() if row[15] else None,
    }
