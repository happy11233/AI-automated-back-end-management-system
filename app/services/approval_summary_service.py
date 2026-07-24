from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from app.json_utils import dumps_json
from app.services.run_record_service import sanitize_metadata, sanitize_text


ACTION_LABELS = {
    "refund": "退款审批",
    "customer_service_refund": "客服退款审批",
    "customer_service_complaint": "客服投诉升级审批",
    "customer_service_bad_review": "客服差评风险审批",
    "customer_service_chargeback": "客服拒付风险审批",
}
SUMMARY_TIMEOUT_SECONDS = 18
_SUMMARY_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="approval-summary")


def summarize_approval(action_type: str, payload: dict[str, Any], *, prefer_llm: bool = True) -> dict[str, str]:
    cached = _cached_summary(action_type, payload)
    if cached:
        return {"summary": cached, "source": str(payload.get("summary_source") or "cached")}

    fallback = build_rule_summary(action_type, payload)
    if not prefer_llm:
        return {"summary": fallback, "source": "fallback"}

    prompt = _build_prompt(action_type, payload, fallback)

    try:
        future = _SUMMARY_EXECUTOR.submit(_chat_summary, prompt)
        summary = sanitize_text(str(future.result(timeout=SUMMARY_TIMEOUT_SECONDS)).strip())
        summary = _clean_summary(summary)
        if summary:
            return {"summary": summary, "source": "llm"}
    except (Exception, TimeoutError):
        pass

    return {"summary": fallback, "source": "fallback"}


def _chat_summary(prompt: str) -> str:
    from app.llm import chat

    return str(chat(prompt))


def build_rule_summary(action_type: str, payload: dict[str, Any]) -> str:
    label = ACTION_LABELS.get(action_type, _humanize_action_type(action_type))
    order_no = _first_text(payload, "order_no", "orderNo") or "未提供订单号"
    risk_level = _first_text(payload, "risk_level") or "未标记风险"
    user_text = _first_text(payload, "user_input", "buyer_message", "message", "handoff_reason")
    amount = _amount_text(payload)
    reviewer_label = _reviewer_label(action_type)

    pieces = [f"{label}：需要{reviewer_label}确认是否允许继续处理。"]
    pieces.append(f"订单：{order_no}。")
    if amount:
        pieces.append(f"金额：{amount}。")
    if risk_level != "未标记风险":
        pieces.append(f"风险：{_risk_label(risk_level)}。")
    if user_text:
        pieces.append(f"原因：{_compact_text(user_text, 80)}")

    return _clean_summary("".join(pieces))


def _build_prompt(action_type: str, payload: dict[str, Any], fallback: str) -> str:
    safe_payload = _approval_payload_for_prompt(payload)
    reviewer_label = _reviewer_label(action_type)
    return f"""
你是企业后台审批助手。请用中文给{reviewer_label}生成一条审批用途简述，让审批人也能快速判断这条审批是审批什么。

要求：
1. 只输出 1 句话，40 到 90 个中文字符。
2. 必须说明审批类型、涉及订单或客户、需要{reviewer_label}决定什么。
3. 不要输出 JSON、Markdown、编号或解释。
4. 不要泄露邮箱、手机号、token、secret、Authorization、callback_token 等敏感信息。
5. 如果信息不足，基于已有字段概括，不要编造。

审批类型：{ACTION_LABELS.get(action_type, action_type)}
规则化摘要：{fallback}
审批字段：
{dumps_json(safe_payload)}
""".strip()


def _approval_payload_for_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "order_no",
        "orderNo",
        "user_input",
        "buyer_message",
        "intent",
        "risk_level",
        "handoff_reason",
        "tracking_no",
        "customer_message_id",
        "erp_summary",
        "rag_summary",
        "order_result",
    }
    compact_payload: dict[str, Any] = {}
    for key in allowed_keys:
        if key in payload:
            compact_payload[key] = payload[key]

    return sanitize_metadata(compact_payload)


def _cached_summary(action_type: str, payload: dict[str, Any]) -> str:
    for key in ("summary_cn", "ai_summary_cn"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _clean_summary(_normalize_reviewer_text(action_type, value))
    return ""


def _first_text(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = sanitize_text(str(value)).strip()
        if text:
            return text
    return ""


def _amount_text(payload: dict[str, Any]) -> str:
    order_result = payload.get("order_result")
    if isinstance(order_result, dict):
        amount_cents = order_result.get("amount_cents")
        if isinstance(amount_cents, (int, float)):
            return f"{amount_cents / 100:.2f} 元"

    for key in ("amount", "refund_amount", "amount_cents"):
        value = payload.get(key)
        if value is None:
            continue
        if key == "amount_cents" and isinstance(value, (int, float)):
            return f"{value / 100:.2f} 元"
        return sanitize_text(str(value))
    return ""


def _risk_label(value: str) -> str:
    labels = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "critical": "严重风险",
    }
    return labels.get(value.lower(), value)


def _humanize_action_type(action_type: str) -> str:
    text = action_type.replace("customer_service", "客服").replace("_", " ")
    text = text.replace("refund", "退款").replace("complaint", "投诉")
    text = text.replace("bad review", "差评").replace("chargeback", "拒付")
    return f"{text.strip()}审批" if text.strip() else "人工审批"


def _reviewer_label(action_type: str) -> str:
    if action_type == "refund" or action_type.startswith("customer_service_"):
        return "客服"
    return "管理员"


def _normalize_reviewer_text(action_type: str, value: str) -> str:
    if _reviewer_label(action_type) != "客服":
        return value
    return (
        value
        .replace("需要管理员确认", "需要客服确认")
        .replace("需要管理员审批", "需要客服审批")
        .replace("让管理员", "让客服")
        .replace("管理员决定", "客服决定")
    )


def _compact_text(value: str, limit: int) -> str:
    text = " ".join(sanitize_text(value).split())
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _clean_summary(value: str) -> str:
    text = " ".join(sanitize_text(value).split())
    text = text.strip("`\"'“”")
    if len(text) > 120:
        text = f"{text[:120]}..."
    return text
