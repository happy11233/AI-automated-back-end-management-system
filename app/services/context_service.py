import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.db import execute, fetch_all, fetch_one, transaction
from app.json_utils import dumps_json
from app.llm import chat_model


summary_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
你是客服系统的会话摘要器。

请根据旧摘要和最近对话，更新一份简洁摘要。
摘要需要保留：
1. 用户正在咨询的问题。
2. 已确认的订单号、退款、审批、风险状态。
3. 已给出的关键结论。
4. 未解决的待办。

不要编造没有出现的信息。
""".strip(),
    ),
    (
        "human",
        """
【旧摘要】
{old_summary}

【最近对话】
{recent_messages}

请输出更新后的摘要。
""".strip(),
    ),
])

summary_chain = summary_prompt | chat_model | StrOutputParser()


def build_context_bundle(
    thread_id: str,
    user_id: str,
    recent_limit: int | None = None,
) -> dict:
    return {
        "summary": get_thread_summary(thread_id),
        "state": get_thread_state(thread_id),
        "recent_messages": list_recent_messages(
            thread_id=thread_id,
            limit=recent_limit or settings.context_recent_message_limit,
        ),
        "memories": list_user_memories(
            user_id=user_id,
            limit=settings.context_memory_limit,
        ),
    }


def get_thread_summary(thread_id: str) -> dict:
    row = fetch_one(
        """
        SELECT thread_id, summary, message_count, updated_at
        FROM chat_thread_summaries
        WHERE thread_id = %s;
        """,
        (thread_id,),
    )

    if row is None:
        return {
            "thread_id": thread_id,
            "summary": "",
            "message_count": 0,
            "updated_at": None,
        }

    return {
        "thread_id": row[0],
        "summary": row[1],
        "message_count": row[2],
        "updated_at": row[3],
    }


def upsert_thread_summary(thread_id: str, summary: str, message_count: int) -> None:
    execute(
        """
        INSERT INTO chat_thread_summaries (thread_id, summary, message_count)
        VALUES (%s, %s, %s)
        ON CONFLICT (thread_id)
        DO UPDATE SET
            summary = EXCLUDED.summary,
            message_count = EXCLUDED.message_count,
            updated_at = now();
        """,
        (thread_id, summary, message_count),
    )


def get_thread_state(thread_id: str) -> dict:
    row = fetch_one(
        """
        SELECT
            thread_id,
            user_id,
            current_intent,
            order_no,
            risk_level,
            approval_id,
            status,
            slots,
            updated_at
        FROM chat_thread_state
        WHERE thread_id = %s;
        """,
        (thread_id,),
    )

    if row is None:
        return {
            "thread_id": thread_id,
            "user_id": None,
            "current_intent": None,
            "order_no": None,
            "risk_level": None,
            "approval_id": None,
            "status": "active",
            "slots": {},
            "updated_at": None,
        }

    return {
        "thread_id": row[0],
        "user_id": str(row[1]) if row[1] else None,
        "current_intent": row[2],
        "order_no": row[3],
        "risk_level": row[4],
        "approval_id": str(row[5]) if row[5] else None,
        "status": row[6],
        "slots": row[7] or {},
        "updated_at": row[8],
    }


def upsert_thread_state(
    thread_id: str,
    user_id: str | None,
    current_intent: str | None = None,
    order_no: str | None = None,
    risk_level: str | None = None,
    approval_id: str | None = None,
    status: str = "active",
    slots: dict | None = None,
) -> None:
    execute(
        """
        INSERT INTO chat_thread_state (
            thread_id,
            user_id,
            current_intent,
            order_no,
            risk_level,
            approval_id,
            status,
            slots
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (thread_id)
        DO UPDATE SET
            user_id = COALESCE(EXCLUDED.user_id, chat_thread_state.user_id),
            current_intent = COALESCE(EXCLUDED.current_intent, chat_thread_state.current_intent),
            order_no = COALESCE(EXCLUDED.order_no, chat_thread_state.order_no),
            risk_level = COALESCE(EXCLUDED.risk_level, chat_thread_state.risk_level),
            approval_id = COALESCE(EXCLUDED.approval_id, chat_thread_state.approval_id),
            status = EXCLUDED.status,
            slots = chat_thread_state.slots || EXCLUDED.slots,
            updated_at = now();
        """,
        (
            thread_id,
            user_id,
            current_intent,
            order_no,
            risk_level,
            _normalize_uuid(approval_id),
            status,
            dumps_json(slots or {}),
        ),
    )


def list_recent_messages(thread_id: str, limit: int) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, role, content, metadata, created_at
        FROM chat_messages
        WHERE thread_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (thread_id, limit),
    )

    messages = [
        {
            "id": str(row[0]),
            "role": row[1],
            "content": row[2],
            "metadata": row[3] or {},
            "created_at": row[4],
        }
        for row in rows
    ]

    return list(reversed(messages))


def count_thread_messages(thread_id: str) -> int:
    row = fetch_one(
        """
        SELECT COUNT(*)
        FROM chat_messages
        WHERE thread_id = %s;
        """,
        (thread_id,),
    )

    return int(row[0]) if row else 0


def list_user_memories(user_id: str, limit: int) -> list[dict]:
    rows = fetch_all(
        """
        SELECT id, memory_type, memory_key, memory_value, confidence, metadata, expires_at
        FROM user_memories
        WHERE user_id = %s
          AND (expires_at IS NULL OR expires_at > now())
        ORDER BY updated_at DESC
        LIMIT %s;
        """,
        (user_id, limit),
    )

    return [
        {
            "id": str(row[0]),
            "memory_type": row[1],
            "memory_key": row[2],
            "memory_value": row[3],
            "confidence": float(row[4]),
            "metadata": row[5] or {},
            "expires_at": row[6],
        }
        for row in rows
    ]


def upsert_user_memory(
    user_id: str,
    memory_type: str,
    memory_key: str,
    memory_value: str,
    confidence: float = 0.7,
    source_thread_id: str | None = None,
    metadata: dict | None = None,
    expires_at: datetime | None = None,
) -> None:
    execute(
        """
        INSERT INTO user_memories (
            user_id,
            memory_type,
            memory_key,
            memory_value,
            confidence,
            source_thread_id,
            metadata,
            expires_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (user_id, memory_type, memory_key)
        DO UPDATE SET
            memory_value = EXCLUDED.memory_value,
            confidence = GREATEST(user_memories.confidence, EXCLUDED.confidence),
            source_thread_id = COALESCE(EXCLUDED.source_thread_id, user_memories.source_thread_id),
            metadata = user_memories.metadata || EXCLUDED.metadata,
            expires_at = EXCLUDED.expires_at,
            updated_at = now();
        """,
        (
            user_id,
            memory_type,
            memory_key,
            memory_value,
            confidence,
            source_thread_id,
            dumps_json(metadata or {}),
            expires_at,
        ),
    )


def update_context_after_turn(
    thread_id: str,
    user_id: str,
    user_message: str,
    graph_result: dict,
) -> None:
    approval_id = _extract_approval_id(graph_result.get("approval_result"))
    slots = {
        "last_user_message": user_message,
        "last_answer": graph_result.get("answer"),
    }

    upsert_thread_state(
        thread_id=thread_id,
        user_id=user_id,
        current_intent=graph_result.get("intent"),
        order_no=graph_result.get("order_no"),
        risk_level=graph_result.get("risk_level"),
        approval_id=approval_id,
        status="active",
        slots={key: value for key, value in slots.items() if value},
    )
    maybe_update_thread_summary(thread_id)
    maybe_extract_user_memories(
        user_id=user_id,
        thread_id=thread_id,
        user_message=user_message,
        graph_result=graph_result,
    )


def maybe_update_thread_summary(thread_id: str) -> None:
    total_message_count = count_thread_messages(thread_id)
    saved_summary = get_thread_summary(thread_id)

    if (
        saved_summary.get("summary")
        and total_message_count - saved_summary.get("message_count", 0)
        < settings.context_summary_interval
    ):
        return

    messages = list_recent_messages(
        thread_id=thread_id,
        limit=settings.context_summary_message_limit,
    )

    if not messages:
        return

    old_summary = saved_summary.get("summary") or ""
    recent_text = format_messages_for_prompt(messages)

    if settings.context_enable_llm_summary:
        try:
            summary = summary_chain.invoke({
                "old_summary": old_summary or "暂无",
                "recent_messages": recent_text,
            })
        except Exception:
            summary = _fallback_summary(messages)
    else:
        summary = _fallback_summary(messages)

    upsert_thread_summary(
        thread_id=thread_id,
        summary=summary.strip(),
        message_count=total_message_count,
    )


def maybe_extract_user_memories(
    user_id: str,
    thread_id: str,
    user_message: str,
    graph_result: dict,
) -> None:
    order_no = graph_result.get("order_no") or _extract_order_no(user_message)

    if order_no:
        upsert_user_memory(
            user_id=user_id,
            memory_type="recent_order",
            memory_key=order_no,
            memory_value=f"用户最近咨询过订单 {order_no}",
            confidence=0.9,
            source_thread_id=thread_id,
            metadata={
                "intent": graph_result.get("intent"),
                "risk_level": graph_result.get("risk_level"),
            },
            expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.user_memory_retention_days
            ),
        )


def format_context_for_prompt(context_bundle: dict) -> str:
    summary = context_bundle.get("summary", {}).get("summary") or "暂无"
    state = context_bundle.get("state") or {}
    memories = context_bundle.get("memories") or []
    recent_messages = context_bundle.get("recent_messages") or []

    memory_text = "\n".join(
        f"- {item['memory_type']}:{item['memory_key']} = {item['memory_value']}"
        for item in memories
    ) or "暂无"

    return (
        f"【会话摘要】\n{summary}\n\n"
        f"【当前业务状态】\n{dumps_json(state)}\n\n"
        f"【用户长期记忆】\n{memory_text}\n\n"
        f"【最近对话】\n{format_messages_for_prompt(recent_messages)}"
    )


def format_messages_for_prompt(messages: list[dict]) -> str:
    if not messages:
        return "暂无"

    return "\n".join(
        f"{message['role']}: {message['content']}"
        for message in messages
    )


def cleanup_expired_context(
    chat_message_retention_days: int | None = None,
    audit_log_retention_days: int | None = None,
    closed_thread_retention_days: int | None = None,
) -> dict:
    chat_days = chat_message_retention_days or settings.chat_message_retention_days
    audit_days = audit_log_retention_days or settings.audit_log_retention_days
    thread_days = closed_thread_retention_days or settings.closed_thread_retention_days

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM user_memories
                WHERE expires_at IS NOT NULL AND expires_at < now()
                RETURNING 1;
                """
            )
            expired_memory_count = len(cur.fetchall())

            cur.execute(
                """
                DELETE FROM audit_logs
                WHERE created_at < now() - (%s || ' days')::interval
                RETURNING 1;
                """,
                (audit_days,),
            )
            expired_audit_count = len(cur.fetchall())

            cur.execute(
                """
                DELETE FROM chat_messages
                WHERE created_at < now() - (%s || ' days')::interval
                RETURNING 1;
                """,
                (chat_days,),
            )
            expired_message_count = len(cur.fetchall())

            cur.execute(
                """
                DELETE FROM chat_threads
                WHERE status = 'closed'
                  AND updated_at < now() - (%s || ' days')::interval
                RETURNING 1;
                """,
                (thread_days,),
            )
            expired_thread_count = len(cur.fetchall())

    return {
        "expired_memories_deleted": expired_memory_count,
        "expired_audit_logs_deleted": expired_audit_count,
        "expired_chat_messages_deleted": expired_message_count,
        "expired_closed_threads_deleted": expired_thread_count,
        "chat_message_retention_days": chat_days,
        "audit_log_retention_days": audit_days,
        "closed_thread_retention_days": thread_days,
    }


def _fallback_summary(messages: list[dict]) -> str:
    useful_messages = [
        message
        for message in messages
        if message["role"] in {"user", "assistant", "system"}
    ][-6:]

    return "；".join(
        f"{message['role']}：{message['content'][:120]}"
        for message in useful_messages
    )


def _extract_order_no(text: str) -> str | None:
    match = re.search(r"\d{4,}", text)
    return match.group(0) if match else None


def _extract_approval_id(approval_result: dict | None) -> str | None:
    if not approval_result:
        return None

    return approval_result.get("approval_id")


def _normalize_uuid(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        return str(UUID(value))
    except ValueError:
        return None
