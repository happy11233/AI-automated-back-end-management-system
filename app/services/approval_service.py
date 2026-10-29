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
        SELECT a.id, a.thread_id, a.requested_by, a.action_type, a.payload,
               a.status, a.created_at, a.refund_status, o.status, o.external_ticket_id
        FROM approval_requests a
        LEFT JOIN approval_ticket_outbox o ON o.approval_id=a.id
        WHERE {" AND ".join(conditions)}
        ORDER BY a.created_at DESC
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
                SET payload = payload || %s::jsonb
                WHERE id = %s
                  AND NOT (payload ? 'summary_cn');
                """,
                (dumps_json({"summary_cn": summary["summary"], "summary_source": summary["source"]}), row[0]),
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
            "refund_status": row[7],
            "ticket_status": row[8],
            "external_ticket_id": row[9],
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
                SELECT id, thread_id, action_type, status, payload, requested_by
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

            if is_customer_service_approval(str(approval[2])) and str(approval[5]) == str(reviewer.get("id")):
                cur.execute(
                    """INSERT INTO audit_logs(user_id, action, resource_type, resource_id, metadata)
                       VALUES (%s, 'approval.self_review_rejected', 'approval', %s, %s::jsonb)""",
                    (reviewer["id"], approval_id, dumps_json({"reason": "applicant_cannot_review_own_request"})),
                )
                return {"found": False, "forbidden": True, "message": "申请人不能审批自己的客服退款或售后请求。"}

            payload = approval[4] if isinstance(approval[4], dict) else {}
            if (approved and is_customer_service_approval(str(approval[2]))
                    and (payload.get("risk_level") == "high" or payload.get("requires_supervisor_approval"))):
                cur.execute(
                    """SELECT 1 FROM rag_team_memberships m
                       JOIN rag_teams t ON t.id=m.team_id
                       WHERE m.user_id=%s AND m.member_role='supervisor' AND m.status='active'
                         AND (m.expires_at IS NULL OR m.expires_at>now())
                         AND t.status='active' AND t.position_scope='customer_service'
                       LIMIT 1""",
                    (reviewer["id"],),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """INSERT INTO audit_logs(user_id, action, resource_type, resource_id, metadata)
                           VALUES (%s, 'approval.supervisor_required', 'approval', %s, %s::jsonb)""",
                        (reviewer["id"], approval_id, dumps_json({"reason": "high_risk_refund_requires_supervisor"})),
                    )
                    return {"found": False, "forbidden": True, "message": "高风险客服退款需要客服主管审批。"}

            cur.execute(
                """
                UPDATE approval_requests
                SET status = %s,
                    refund_status = CASE WHEN %s = 'approved' AND action_type IN ('refund','customer_service_refund')
                        THEN 'pending' ELSE NULL END,
                    reviewer_id = %s,
                    reviewed_at = now()
                WHERE id = %s
                RETURNING id, thread_id, action_type, status, payload, reviewed_at, refund_status;
                """,
                (status, status, reviewer["id"], approval_id),
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
        "refund_status": row[6],
    }


def authorize_refund_retry(approval_id: str, reviewer: dict[str, Any]) -> dict:
    row = fetch_one(
        """SELECT id, action_type, status, refund_status, requested_by, payload
           FROM approval_requests WHERE id=%s""", (approval_id,),
    )
    if row is None or row[1] not in REFUND_APPROVAL_ACTIONS:
        raise HTTPException(status_code=404, detail="退款审批不存在。")
    _ensure_can_review_approval(reviewer, str(row[1]))
    if str(row[4]) == str(reviewer.get("id")):
        raise HTTPException(status_code=403, detail="申请人不能重试自己的退款。")
    if row[2] != "approved" or row[3] not in {"failed", "pending", "succeeded"}:
        raise HTTPException(status_code=409, detail="该审批当前不能执行退款重试。")
    payload = row[5] if isinstance(row[5], dict) else {}
    if payload.get("risk_level") == "high" or payload.get("requires_supervisor_approval"):
        supervisor = fetch_one(
            """SELECT 1 FROM rag_team_memberships m JOIN rag_teams t ON t.id=m.team_id
               WHERE m.user_id=%s AND m.member_role='supervisor' AND m.status='active'
                 AND (m.expires_at IS NULL OR m.expires_at>now())
                 AND t.status='active' AND t.position_scope='customer_service' LIMIT 1""",
            (reviewer["id"],),
        )
        if supervisor is None:
            raise HTTPException(status_code=403, detail="高风险客服退款需要客服主管处理。")
    return {"id": str(row[0]), "status": row[2], "refund_status": row[3]}


def _approval_scope_conditions(current_user: dict[str, Any]) -> tuple[list[str], list[Any]]:
    if current_user.get("role") == "admin":
        return [
            "a.action_type <> %s",
            "a.action_type NOT LIKE %s",
        ], [
            "refund",
            "customer_service_%",
        ]

    if current_user.get("role") == "employee" and current_user.get("position") == "customer_service":
        return [
            "(a.action_type = %s OR a.action_type LIKE %s)",
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
