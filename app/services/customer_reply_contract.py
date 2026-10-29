"""Separate customer text from staff guidance before persistence or dispatch."""
from __future__ import annotations

import json
import re
from typing import Any


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate reply field")
        result[key] = value
    return result


def parse_customer_reply(raw: str) -> dict[str, Any]:
    """Invalid output stays internal; never guess where customer text ends."""
    text = raw.strip() if isinstance(raw, str) else ""
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        value = json.loads(text, object_pairs_hook=_unique_object)
        if not isinstance(value, dict) or set(value) != {"customer_reply", "internal_note", "needs_human_review"}:
            raise ValueError("Unexpected reply fields")
        if not isinstance(value["customer_reply"], str) or not value["customer_reply"].strip():
            raise ValueError("Missing customer text")
        if not isinstance(value["internal_note"], str) or type(value["needs_human_review"]) is not bool:
            raise ValueError("Invalid staff guidance fields")
        if re.search(
            r"^\s*(?:[-*#\d.)]+\s*)?(?:客服内部处理建议|内部处理建议|内部建议|internal_note|needs_human_review|staff notes?|internal notes?)\s*[:：]",
            value["customer_reply"], re.I | re.M,
        ):
            raise ValueError("Staff guidance heading in customer text")
        return {
            "customer_reply": value["customer_reply"].strip(),
            "internal_note": value["internal_note"].strip(),
            "needs_human_review": value["needs_human_review"],
            "reply_parse_status": "validated",
            "reply_unparsed_output": None,
        }
    except (ValueError, TypeError):
        return {
            "customer_reply": "",
            "internal_note": "AI 回复结构校验未通过，请人工检查原始输出并重新生成回复。",
            "needs_human_review": True,
            "reply_parse_status": "invalid",
            "reply_unparsed_output": raw if isinstance(raw, str) else None,
        }


def apply_customer_reply_review(
    decision: dict[str, str], reply: dict[str, Any],
) -> dict[str, str]:
    if decision["status"] == "human_handoff":
        return decision
    if reply.get("reply_parse_status") != "validated":
        return {"status": "drafted", "decision": "draft_only",
                "handoff_reason": "AI 回复结构校验未通过，需要人工复核，禁止自动写回。"}
    if reply.get("needs_human_review") is not False:
        return {"status": "drafted", "decision": "draft_only",
                "handoff_reason": decision.get("handoff_reason") or "AI 标记需要人工复核，确认后再处理。"}
    return decision


def can_auto_write_customer_reply(
    classification: dict[str, Any], decision: dict[str, Any], reply: dict[str, Any],
) -> bool:
    return (
        classification.get("risk_level") == "low"
        and decision.get("status") == "auto_reply_ready"
        and decision.get("decision") == "low_risk_auto_reply_ready"
        and reply.get("reply_parse_status") == "validated"
        and reply.get("needs_human_review") is False
        and bool(reply.get("customer_reply"))
    )


def customer_reply_external_content(content: dict[str, Any]) -> dict[str, Any]:
    """Explicit allowlist also applies when dispatching an older queued task."""
    body = content.get("reply_draft")
    if content.get("reply_parse_status") != "validated" or not isinstance(body, str) or not body.strip():
        raise ValueError("客服正文未通过结构校验，请重新生成并复核回复，不能写回或发送旧版混合草稿。")
    keys = ("customer_message_id", "channel", "external_id", "buyer_language",
            "buyer_email", "order_no", "tracking_no")
    return {**{key: content.get(key) for key in keys}, "reply_draft": body.strip(),
            "reply_parse_status": "validated"}
