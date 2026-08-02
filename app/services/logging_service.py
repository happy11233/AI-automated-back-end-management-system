import re
from uuid import uuid4

from app.config import settings
from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json
from app.services.run_record_service import sanitize_metadata


def ensure_chat_thread_schema() -> None:
    execute(
        """
        ALTER TABLE chat_threads
        ADD COLUMN IF NOT EXISTS position TEXT;

        CREATE INDEX IF NOT EXISTS idx_chat_threads_user_updated_at
        ON chat_threads(user_id, updated_at DESC);

        CREATE INDEX IF NOT EXISTS idx_chat_threads_user_position_updated_at
        ON chat_threads(user_id, position, updated_at DESC);
        """
    )


def create_chat_thread(user_id: str, title: str | None = None, position: str | None = None) -> dict:
    thread_id = f"thread-{uuid4()}"
    row = fetch_one(
        """
        INSERT INTO chat_threads (id, user_id, title, position)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, title, status, position, created_at, updated_at;
        """,
        (thread_id, user_id, title, position),
    )
    return _thread_from_row(row)


def ensure_chat_thread(
    thread_id: str,
    user_id: str,
    title: str | None = None,
    position: str | None = None,
) -> dict:
    existing = get_thread(thread_id)
    if existing is not None:
        if existing["user_id"] != user_id:
            raise PermissionError("没有权限使用该会话。")
        if position and existing.get("position") and existing.get("position") != position:
            raise PermissionError("没有权限使用其他岗位的会话。")
        touch_chat_thread(thread_id, title=title or existing.get("title"))
        return get_thread(thread_id) or existing

    row = fetch_one(
        """
        INSERT INTO chat_threads (id, user_id, title, position)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, title, status, position, created_at, updated_at;
        """,
        (thread_id, user_id, title, position),
    )
    return _thread_from_row(row)


def list_chat_threads(
    current_user: dict,
    limit: int = 80,
    search: str | None = None,
) -> list[dict]:
    limit = max(1, min(limit, 200))
    conditions = [
        "t.user_id = %s",
        "t.updated_at >= now() - (%s || ' days')::interval",
    ]
    params: list[object] = [current_user["id"], settings.chat_thread_retention_days]

    if current_user.get("position"):
        conditions.append("COALESCE(t.position, u.position) = %s")
        params.append(current_user.get("position"))

    if search:
        conditions.append(
            """
            (
                t.id ILIKE %s
                OR t.title ILIKE %s
                OR u.username ILIKE %s
                OR u.display_name ILIKE %s
                OR u.position ILIKE %s
            )
            """
        )
        like_search = f"%{search}%"
        params.extend([like_search] * 5)

    params.append(limit)
    rows = fetch_all(
        f"""
        SELECT
            t.id,
            t.user_id,
            t.title,
            t.status,
            t.position,
            t.created_at,
            t.updated_at,
            u.username,
            u.display_name,
            u.role,
            u.position,
            COALESCE(stats.message_count, 0) AS message_count,
            first_user_message.content AS first_user_message_preview,
            last_message.content AS last_message_preview,
            last_message.role AS last_message_role
        FROM chat_threads t
        LEFT JOIN users u ON u.id = t.user_id
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS message_count
            FROM chat_messages m
            WHERE m.thread_id = t.id
        ) stats ON true
        LEFT JOIN LATERAL (
            SELECT content
            FROM chat_messages m
            WHERE m.thread_id = t.id
              AND m.role = 'user'
            ORDER BY m.created_at ASC
            LIMIT 1
        ) first_user_message ON true
        LEFT JOIN LATERAL (
            SELECT role, content
            FROM chat_messages m
            WHERE m.thread_id = t.id
            ORDER BY m.created_at DESC
            LIMIT 1
        ) last_message ON true
        WHERE {" AND ".join(conditions)}
        ORDER BY t.updated_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )

    return [_thread_list_item_from_row(row) for row in rows]


def get_latest_thread_for_user(user_id: str, position: str | None = None) -> dict | None:
    position_filter = "AND COALESCE(position, %s) = %s" if position else ""
    params: tuple[object, ...]
    if position:
        params = (user_id, settings.chat_thread_retention_days, position, position)
    else:
        params = (user_id, settings.chat_thread_retention_days)

    row = fetch_one(
        f"""
        SELECT id, user_id, title, status, position, created_at, updated_at
        FROM chat_threads
        WHERE user_id = %s
          AND updated_at >= now() - (%s || ' days')::interval
          {position_filter}
        ORDER BY updated_at DESC
        LIMIT 1;
        """,
        params,
    )
    return _thread_from_row(row) if row else None


def touch_chat_thread(thread_id: str, title: str | None = None) -> None:
    execute(
        """
        UPDATE chat_threads
        SET
            title = CASE
                WHEN %s::text IS NOT NULL
                  AND (title IS NULL OR title = '' OR title = '新会话')
                THEN %s::text
                ELSE title
            END,
            updated_at = now()
        WHERE id = %s;
        """,
        (title, title, thread_id),
    )


def update_chat_thread_title(thread_id: str, title: str) -> dict | None:
    row = fetch_one(
        """
        UPDATE chat_threads
        SET title = %s
        WHERE id = %s
        RETURNING id, user_id, title, status, created_at, updated_at;
        """,
        (title, thread_id),
    )
    return _thread_from_row(row) if row else None


def save_chat_message(
    thread_id: str,
    user_id: str | None,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    execute(
        """
        INSERT INTO chat_messages (thread_id, user_id, role, content, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb);
        """,
        (
            thread_id,
            user_id,
            role,
            content,
            dumps_json(metadata or {}),
        ),
    )


def update_chat_message(
    *,
    message_id: str,
    thread_id: str,
    content: str | None = None,
    metadata: dict | None = None,
) -> dict | None:
    row = fetch_one(
        """
        UPDATE chat_messages
        SET content = COALESCE(%s, content),
            metadata = CASE
                WHEN %s::jsonb IS NULL THEN metadata
                ELSE metadata || %s::jsonb
            END
        WHERE id = %s
          AND thread_id = %s
        RETURNING id, thread_id, user_id, role, content, metadata, created_at;
        """,
        (
            content,
            dumps_json(metadata) if metadata is not None else None,
            dumps_json(metadata) if metadata is not None else None,
            message_id,
            thread_id,
        ),
    )
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "thread_id": row[1],
        "user_id": str(row[2]) if row[2] else None,
        "role": row[3],
        "content": row[4],
        "metadata": row[5],
        "created_at": row[6],
    }


def update_latest_chat_message_by_artifact(
    *,
    thread_id: str,
    artifact_id: str,
    content: str | None = None,
    metadata: dict | None = None,
) -> dict | None:
    metadata_json = dumps_json(metadata) if metadata is not None else None
    attachment_match = dumps_json({"attachments": [{"metadata": {"artifact_id": artifact_id}}]})
    automation_match = dumps_json({"automation": {"artifact_id": artifact_id}})
    approval_match = dumps_json({
        "approval_result": {
            "confirmation_card": {
                "artifact": {
                    "artifact_id": artifact_id,
                },
            },
        },
    })
    row = fetch_one(
        """
        UPDATE chat_messages
        SET content = COALESCE(%s, content),
            metadata = CASE
                WHEN %s::jsonb IS NULL THEN metadata
                ELSE metadata || %s::jsonb
            END
        WHERE id = (
            SELECT id
            FROM chat_messages
            WHERE thread_id = %s
              AND role = 'assistant'
              AND (
                metadata @> %s::jsonb
                OR metadata @> %s::jsonb
                OR metadata @> %s::jsonb
                OR metadata::text LIKE %s
              )
            ORDER BY created_at DESC
            LIMIT 1
        )
        RETURNING id, thread_id, user_id, role, content, metadata, created_at;
        """,
        (
            content,
            metadata_json,
            metadata_json,
            thread_id,
            attachment_match,
            automation_match,
            approval_match,
            f"%{artifact_id}%",
        ),
    )
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "thread_id": row[1],
        "user_id": str(row[2]) if row[2] else None,
        "role": row[3],
        "content": row[4],
        "metadata": row[5],
        "created_at": row[6],
    }


def write_audit_log(
    user_id: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    execute(
        """
        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb);
        """,
        (
            user_id,
            action,
            resource_type,
            resource_id,
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )


def save_approval_message(
    thread_id: str,
    reviewer_id: str,
    approval_id: str,
    approved: bool,
    refund_result: dict | None = None,
) -> None:
    if approved:
        refund_message = ""

        if refund_result is not None:
            refund_message = f"退款执行结果：{refund_result.get('message', '')}"

        content = f"审批已通过。{refund_message}".strip()
    else:
        content = "审批已拒绝，相关操作不会执行。"

    save_chat_message(
        thread_id=thread_id,
        user_id=reviewer_id,
        role="system",
        content=content,
        metadata={
            "approval_id": approval_id,
            "approved": approved,
            "refund_result": refund_result,
        },
    )


def get_thread(thread_id: str) -> dict | None:
    row = fetch_one(
        """
        SELECT id, user_id, title, status, position, created_at, updated_at
        FROM chat_threads
        WHERE id = %s;
        """,
        (thread_id,),
    )

    if row is None:
        return None

    return {
        "id": row[0],
        "user_id": str(row[1]) if row[1] else None,
        "title": row[2],
        "status": row[3],
        "position": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def thread_belongs_to_user(thread: dict | None, current_user: dict) -> bool:
    if thread is None:
        return False
    if str(thread.get("user_id") or "") != str(current_user.get("id") or ""):
        return False
    if (
        current_user.get("role") != "admin"
        and thread.get("position")
        and thread.get("position") != current_user.get("position")
    ):
        return False
    return True


def get_thread_for_user(thread_id: str, current_user: dict) -> dict | None:
    thread = get_thread(thread_id)
    return thread if thread_belongs_to_user(thread, current_user) else None


def _thread_from_row(row) -> dict:
    return {
        "id": row[0],
        "user_id": str(row[1]) if row[1] else None,
        "title": row[2],
        "status": row[3],
        "position": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def _thread_list_item_from_row(row) -> dict:
    return {
        "id": row[0],
        "user_id": str(row[1]) if row[1] else None,
        "title": row[2],
        "status": row[3],
        "position": row[4] or row[10],
        "created_at": row[5],
        "updated_at": row[6],
        "username": row[7],
        "display_name": row[8],
        "role": row[9],
        "message_count": int(row[11] or 0),
        "first_user_message_preview": (row[12] or "")[:160],
        "last_message_preview": (row[13] or "")[:160],
        "last_message_role": row[14],
    }


def list_thread_messages(thread_id: str) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, thread_id, user_id, role, content, metadata, created_at
        FROM chat_messages
        WHERE thread_id = %s
        ORDER BY created_at ASC;
        """,
        (thread_id,),
    )

    return [
        {
            "id": str(row[0]),
            "thread_id": row[1],
            "user_id": str(row[2]) if row[2] else None,
            "role": row[3],
            "content": row[4],
            "metadata": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def list_thread_messages_for_user(thread_id: str, current_user: dict) -> list[dict] | None:
    if get_thread_for_user(thread_id, current_user) is None:
        return None
    return list_thread_messages(thread_id)


def list_audit_logs(
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    position: str | None = None,
) -> list[dict]:
    conditions = []
    params: list[object] = []

    if action:
        conditions.append("action ILIKE %s")
        params.append(f"%{action}%")

    if resource_type:
        conditions.append("resource_type = %s")
        params.append(resource_type)

    if position:
        conditions.append("metadata->>'position' = %s")
        params.append(position)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = fetch_all(
        f"""
        SELECT id, user_id, action, resource_type, resource_id, metadata, created_at
        FROM audit_logs
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )

    return [
        {
            "id": str(row[0]),
            "user_id": str(row[1]) if row[1] else None,
            "action": row[2],
            "resource_type": row[3],
            "resource_id": row[4],
            "metadata": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]
