from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json

def ensure_chat_thread(thread_id: str, user_id: str, title: str | None = None) -> None:
    execute(
        """
        INSERT INTO chat_threads (id, user_id, title)
        VALUES (%s, %s, %s)
        ON CONFLICT (id)
        DO UPDATE SET updated_at = now();
        """,
        (thread_id, user_id, title),
    )


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
            dumps_json(metadata or {}),
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
        SELECT id, user_id, title, status, created_at, updated_at
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
        "created_at": row[4],
        "updated_at": row[5],
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
