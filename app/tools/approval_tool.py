from uuid import UUID
import hashlib
import json
from langchain_core.tools import tool
from app.db import fetch_one, transaction
from app.json_utils import dumps_json
from app.services.approval_summary_service import summarize_approval
from app.services.logging_service import ensure_chat_thread


def normalize_uuid(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        return str(UUID(value))
    except ValueError:
        return None


def create_approval_request(
    thread_id: str,
    requested_by: str | None,
    action_type: str,
    payload: dict,
) -> dict:
    user_id = normalize_uuid(requested_by)
    if user_id is None:
        raise ValueError("审批请求缺少用户标识")
    if not isinstance(payload, dict):
        raise ValueError("审批内容必须是对象")

    ensure_chat_thread(thread_id, user_id, "人工审批会话")
    identity_payload = ({key: payload.get(key) for key in (
        "customer_message_id", "order_no", "intent", "risk_level", "buyer_message",
    )} if payload.get("customer_message_id") else payload)
    payload_hash = hashlib.sha256(json.dumps(identity_payload, sort_keys=True, ensure_ascii=False,
                                             default=str, separators=(",", ":")).encode()).hexdigest()
    existing = fetch_one(
        """SELECT a.id,a.status,o.status,o.external_ticket_id
           FROM approval_requests a LEFT JOIN approval_ticket_outbox o ON o.approval_id=a.id
           WHERE a.thread_id=%s AND a.action_type=%s AND a.payload_hash=%s""",
        (thread_id, action_type, payload_hash),
    )
    if existing:
        ticket_status = existing[2] or "pending"
        return {"approval_id": str(existing[0]), "status": existing[1],
                "external_ticket": {"status": ticket_status, "ticket_id": existing[3]},
                "message": f"已复用人工审批记录，审批ID：{existing[0]}；外部工单状态：{ticket_status}。"}
    summary = summarize_approval(action_type, payload)
    enriched_payload = {
        **payload,
        "summary_cn": summary["summary"],
        "summary_source": summary["source"],
    }
    with transaction() as conn:
        row = conn.execute(
            """INSERT INTO approval_requests(thread_id,requested_by,action_type,payload,payload_hash)
               VALUES (%s,%s,%s,%s::jsonb,%s)
               ON CONFLICT DO NOTHING RETURNING id,status""",
            (thread_id, user_id, action_type, dumps_json(enriched_payload), payload_hash),
        ).fetchone()
        if row:
            approval_id = str(row[0])
            conn.execute(
                """INSERT INTO approval_ticket_outbox(approval_id,idempotency_key)
                   VALUES (%s,%s)""", (approval_id, f"approval:{thread_id}:{action_type}:{payload_hash}"),
            )
        else:
            row = conn.execute(
                """SELECT id,status FROM approval_requests
                   WHERE thread_id=%s AND action_type=%s AND payload_hash=%s""",
                (thread_id, action_type, payload_hash),
            ).fetchone()
            if row is None:
                raise RuntimeError("审批幂等记录未找到")
            approval_id = str(row[0])
        ticket = conn.execute(
            """SELECT status,external_ticket_id FROM approval_ticket_outbox WHERE approval_id=%s""",
            (approval_id,),
        ).fetchone()
    ticket_status = ticket[0] if ticket else "pending"
    ticket_result = {"status": ticket_status, "ticket_id": ticket[1] if ticket else None}

    return {
        "approval_id": approval_id,
        "status": row[1],
        "external_ticket": ticket_result,
        "message": f"已保存人工审批记录，审批ID：{approval_id}；外部工单状态：{ticket_status}。",
    }
@tool
def submit_approval_request(
    thread_id: str,
    requested_by: str | None,
    action_type: str,
    payload: dict,
) -> dict:
    """创建人工审批请求。适合退款、特殊退款、改价、删除数据等高风险操作。"""
    return create_approval_request(
        thread_id=thread_id,
        requested_by=requested_by,
        action_type=action_type,
        payload=payload,
    )
