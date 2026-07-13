from app.db import fetch_all, fetch_one


def list_pending_approvals(limit: int = 20) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, thread_id, requested_by, action_type, payload, status, created_at
        FROM approval_requests
        WHERE status = 'pending'
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (limit,),
    )

    return [
        {
            "id": str(row[0]),
            "thread_id": row[1],
            "requested_by": str(row[2]) if row[2] else None,
            "action_type": row[3],
            "payload": row[4],
            "status": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def review_approval(
    approval_id: str,
    reviewer_id: str,
    approved: bool,
) -> dict:
    status = "approved" if approved else "rejected"

    row = fetch_one(
        """
        UPDATE approval_requests
        SET status = %s,
            reviewer_id = %s,
            reviewed_at = now()
        WHERE id = %s
          AND status = 'pending'
        RETURNING id, thread_id, action_type, status, payload, reviewed_at;
        """,
        (status, reviewer_id, approval_id),
    )

    if row is None:
        return {
            "found": False,
            "message": "审批记录不存在，或已经被处理。",
        }

    return {
        "found": True,
        "id": str(row[0]),
        "thread_id": row[1],
        "action_type": row[2],
        "status": row[3],
        "payload": row[4],
        "reviewed_at": row[5],
    }