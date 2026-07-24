from uuid import UUID
from langchain_core.tools import tool
from app.db import fetch_one
from app.json_utils import dumps_json
from app.services.approval_summary_service import summarize_approval
from app.services.logging_service import ensure_chat_thread
from app.services.mcp_service import create_external_ticket


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
    ticket_result = create_external_ticket(
        title=f"人工审批：{action_type}",
        description=dumps_json(
            {
                "thread_id": thread_id,
                "requested_by": requested_by,
                "action_type": action_type,
                "payload": payload,
            }
        ),
        priority="high",
        requester=requested_by,
        source="company-rag-agent",
    )
    enriched_payload = {
        **payload,
        "external_ticket": ticket_result,
    }
    summary = summarize_approval(action_type, enriched_payload)
    enriched_payload = {
        **enriched_payload,
        "summary_cn": summary["summary"],
        "summary_source": summary["source"],
    }

    if user_id is None:
        raise ValueError("审批请求缺少用户标识")

    ensure_chat_thread(thread_id, user_id, "人工审批会话")

    row = fetch_one(
        """
        INSERT INTO approval_requests (
            thread_id,
            requested_by,
            action_type,
            payload
        )
        VALUES (%s, %s, %s, %s::jsonb)
        RETURNING id, status;
        """,
        (
            thread_id,
            user_id,
            action_type,
            dumps_json(enriched_payload),
        ),
    )

    return {
        "approval_id": str(row[0]),
        "status": row[1],
        "external_ticket": ticket_result,
        "message": f"已创建人工审批记录，审批ID：{row[0]}；外部工单：{ticket_result.get('ticket_id')}。",
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
