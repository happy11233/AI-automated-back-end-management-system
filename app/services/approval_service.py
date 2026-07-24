from typing import Any

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one, transaction
from app.json_utils import dumps_json
from app.services.approval_summary_service import summarize_approval


REFUND_APPROVAL_ACTIONS = {"refund", "customer_service_refund"}


def is_customer_service_approval(action_type: str) -> bool:
    return action_type in REFUND_APPROVAL_ACTIONS or action_type.startswith("customer_service_")


def list_pending_approvals(current_user: dict[str, Any], limit: int = 20) -> list[dict]:
    conditions, params = _approval_scope_conditions(current_user)
    params = [*params, limit]
    rows = fetch_all(
        f"""
        SELECT id, thread_id, requested_by, action_type, payload, status, created_at
        FROM approval_requests
        WHERE status = 'pending'
          AND {" AND ".join(conditions)}
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )

    items = []
    for row in rows:
        payload = row[4] or {}
        summary = summarize_approval(row[3], payload, prefer_llm=False)
        if not payload.get("summary_cn"):
            payload = {
                **payload,
                "summary_cn": summary["summary"],
                "summary_source": summary["source"],
            }
            execute(
                """
                UPDATE approval_requests
                SET payload = %s::jsonb
                WHERE id = %s
                  AND NOT (payload ? 'summary_cn');
                """,
                (dumps_json(payload), row[0]),
            )

        items.append({
            "id": str(row[0]),
            "thread_id": row[1],
            "requested_by": str(row[2]) if row[2] else None,
            "action_type": row[3],
            "payload": payload,
            "summary_cn": summary["summary"],
            "summary_source": summary["source"],
            "status": row[5],
            "created_at": row[6],
        })

    return items


def review_approval(
    approval_id: str,
    reviewer: dict[str, Any],
    approved: bool,
) -> dict:
    status = "approved" if approved else "rejected"

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, thread_id, action_type, status, payload
                FROM approval_requests
                WHERE id = %s
                FOR UPDATE;
                """,
                (approval_id,),
            )
            approval = cur.fetchone()

            if approval is None:
                return {
                    "found": False,
                    "message": "审批记录不存在，或已经被处理。",
                }

            _ensure_can_review_approval(reviewer, str(approval[2]))

            if approval[3] != "pending":
                return {
                    "found": False,
                    "message": "审批记录不存在，或已经被处理。",
                }

            cur.execute(
                """
                UPDATE approval_requests
                SET status = %s,
                    reviewer_id = %s,
                    reviewed_at = now()
                WHERE id = %s
                RETURNING id, thread_id, action_type, status, payload, reviewed_at;
                """,
                (status, reviewer["id"], approval_id),
            )
            row = cur.fetchone()

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


def _approval_scope_conditions(current_user: dict[str, Any]) -> tuple[list[str], list[Any]]:
    if current_user.get("role") == "admin":
        return [
            "action_type <> %s",
            "action_type NOT LIKE %s",
        ], [
            "refund",
            "customer_service_%",
        ]

    if current_user.get("role") == "employee" and current_user.get("position") == "customer_service":
        return [
            "(action_type = %s OR action_type LIKE %s)",
        ], [
            "refund",
            "customer_service_%",
        ]

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="只有客服岗位可以查看退款和售后审批。",
    )


def _ensure_can_review_approval(current_user: dict[str, Any], action_type: str) -> None:
    if is_customer_service_approval(action_type):
        if current_user.get("role") == "employee" and current_user.get("position") == "customer_service":
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="退款和售后审批需要由客服岗位处理，管理员不负责审批用户退款。",
        )

    if current_user.get("role") == "admin":
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="当前账号无权处理该审批。",
    )
