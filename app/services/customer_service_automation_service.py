from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one
from app.graph.extractors import extract_order_no_from_text
from app.json_utils import dumps_json
from app.llm import chat
from app.permissions import POSITION_LABELS, is_valid_position
from app.rag.qa import answer_question
from app.services.erp_service import query_erp_for_current_user, summarize_erp_items
from app.services.logging_service import write_audit_log
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    now_ms,
    record_step,
    sanitize_metadata,
    start_run,
)
from app.tools.approval_tool import create_approval_request


ALLOWED_CHANNELS = {"manual", "amazon", "email", "ticket", "api"}
LOW_RISK_INTENTS = {"logistics", "return_policy", "size_advice", "exchange", "shipping_time", "promo_code"}
HIGH_RISK_INTENTS = {"refund", "complaint", "bad_review", "chargeback"}


def ensure_customer_service_automation_schema() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "sql" / "007_customer_service_automation.sql"
    if not sql_path.exists():
        return

    statements = [statement.strip() for statement in sql_path.read_text(encoding="utf-8").split(";")]
    for statement in statements:
        if statement:
            execute(f"{statement};")


def create_customer_message(
    *,
    current_user: dict,
    channel: str,
    message: str,
    buyer_name: str | None = None,
    buyer_email: str | None = None,
    buyer_language: str = "auto",
    marketplace: str | None = None,
    order_no: str | None = None,
    tracking_no: str | None = None,
    sku: str | None = None,
    subject: str | None = None,
    external_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_customer_service_user(current_user)
    normalized_channel = channel.strip().lower()
    if normalized_channel not in ALLOWED_CHANNELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的客户消息渠道")

    normalized_message = message.strip()
    if not normalized_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="客户消息不能为空")

    normalized_order_no = (order_no or extract_order_no_from_text(normalized_message) or "").strip() or None
    normalized_tracking_no = (tracking_no or _extract_tracking_no(normalized_message) or "").strip() or None
    normalized_sku = (sku or _extract_sku(normalized_message) or "").strip() or None
    normalized_language = (buyer_language or "auto").strip()[:40] or "auto"
    row = fetch_one(
        """
        INSERT INTO customer_service_messages (
            channel, external_id, buyer_name, buyer_email, buyer_language,
            marketplace, order_no, tracking_no, sku, subject, message,
            created_by, metadata
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s::jsonb
        )
        RETURNING
            id, channel, external_id, buyer_name, buyer_email, buyer_language,
            marketplace, order_no, tracking_no, sku, subject, message, intent,
            risk_level, status, automation_decision, reply_draft, handoff_reason,
            erp_summary, rag_summary, erp_references, citations, approval_id,
            run_id, assigned_to, created_by, processed_by, processed_at,
            metadata, created_at, updated_at;
        """,
        (
            normalized_channel,
            _clean_optional(external_id, 160),
            _clean_optional(buyer_name, 120),
            _clean_optional(buyer_email, 180),
            normalized_language,
            _clean_optional(marketplace, 80),
            _clean_optional(normalized_order_no, 120),
            _clean_optional(normalized_tracking_no, 120),
            _clean_optional(normalized_sku, 120),
            _clean_optional(subject, 180),
            normalized_message,
            current_user.get("id"),
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    item = _map_message_row(row)
    _add_event(
        message_id=item["id"],
        event_type="created",
        actor_id=current_user.get("id"),
        content="客户消息已进入客服自动化收件箱",
        metadata={"channel": normalized_channel},
    )
    write_audit_log(
        user_id=current_user.get("id"),
        action="customer_service.message.create",
        resource_type="customer_service_message",
        resource_id=item["id"],
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": "customer_service",
            "channel": normalized_channel,
            "order_no": item.get("order_no"),
            "tracking_no": item.get("tracking_no"),
        },
    )
    return item


def list_customer_messages(
    *,
    current_user: dict,
    status_filter: str | None = None,
    risk_level: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    _ensure_customer_service_user(current_user)
    conditions: list[str] = []
    params: list[Any] = []

    if current_user.get("role") != "admin":
        conditions.append("(created_by = %s OR assigned_to = %s OR assigned_to IS NULL)")
        params.extend([current_user.get("id"), current_user.get("id")])

    if status_filter and status_filter != "all":
        conditions.append("status = %s")
        params.append(status_filter)

    if risk_level and risk_level != "all":
        conditions.append("risk_level = %s")
        params.append(risk_level)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(max(1, min(limit, 100)))
    rows = fetch_all(
        f"""
        SELECT
            id, channel, external_id, buyer_name, buyer_email, buyer_language,
            marketplace, order_no, tracking_no, sku, subject, message, intent,
            risk_level, status, automation_decision, reply_draft, handoff_reason,
            erp_summary, rag_summary, erp_references, citations, approval_id,
            run_id, assigned_to, created_by, processed_by, processed_at,
            metadata, created_at, updated_at
        FROM customer_service_messages
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )
    return [_map_message_row(row) for row in rows]


def get_customer_message_detail(*, message_id: str, current_user: dict) -> dict[str, Any]:
    _ensure_customer_service_user(current_user)
    row = fetch_one(
        """
        SELECT
            id, channel, external_id, buyer_name, buyer_email, buyer_language,
            marketplace, order_no, tracking_no, sku, subject, message, intent,
            risk_level, status, automation_decision, reply_draft, handoff_reason,
            erp_summary, rag_summary, erp_references, citations, approval_id,
            run_id, assigned_to, created_by, processed_by, processed_at,
            metadata, created_at, updated_at
        FROM customer_service_messages
        WHERE id = %s;
        """,
        (message_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客服消息不存在")

    item = _map_message_row(row)
    _ensure_message_visible(current_user, item)
    return {
        "item": item,
        "events": list_customer_message_events(message_id=message_id, current_user=current_user),
    }


def list_customer_message_events(*, message_id: str, current_user: dict) -> list[dict[str, Any]]:
    row = fetch_one("SELECT id, created_by, assigned_to FROM customer_service_messages WHERE id = %s;", (message_id,))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客服消息不存在")

    item = {
        "id": str(row[0]),
        "created_by": str(row[1]) if row[1] else None,
        "assigned_to": str(row[2]) if row[2] else None,
    }
    _ensure_message_visible(current_user, item)
    rows = fetch_all(
        """
        SELECT id, message_id, event_type, actor_id, content, metadata, created_at
        FROM customer_service_message_events
        WHERE message_id = %s
        ORDER BY created_at ASC;
        """,
        (message_id,),
    )
    return [_map_event_row(row) for row in rows]


def process_customer_message(*, message_id: str, current_user: dict) -> dict[str, Any]:
    _ensure_customer_service_user(current_user)
    detail = get_customer_message_detail(message_id=message_id, current_user=current_user)
    item = detail["item"]
    _mark_processing(message_id=message_id, current_user=current_user)
    started_ms = now_ms()
    run_id = start_run(
        run_type="customer_service_automation",
        app_id="customer-service-message-loop",
        app_name="客服消息自动化闭环",
        entrypoint=f"/customer-service/messages/{message_id}/process",
        current_user=_execution_user(current_user),
        resource_type="customer_service_message",
        resource_id=message_id,
        input_text=item["message"],
        metadata={
            "channel": item["channel"],
            "buyer_language": item["buyer_language"],
            "order_no": item.get("order_no"),
            "tracking_no": item.get("tracking_no"),
        },
    )
    steps: list[dict[str, Any]] = []

    try:
        intent_started_ms = now_ms()
        classification = classify_customer_message(item)
        _record_loop_step(
            steps=steps,
            run_id=run_id,
            order=1,
            name="classify_intent_and_risk",
            status_value="succeeded",
            input_text=item["message"],
            output_text=classification,
            duration_ms=elapsed_ms(intent_started_ms),
        )

        erp_started_ms = now_ms()
        erp_result = _query_customer_erp(item=item, classification=classification, current_user=current_user)
        erp_summary = _erp_summary_from_result(erp_result)
        _record_loop_step(
            steps=steps,
            run_id=run_id,
            order=2,
            name="erp_permission_query",
            status_value="succeeded" if erp_result.get("ok") else "blocked",
            input_text=_erp_query_text(item, classification),
            output_text=erp_summary or erp_result.get("message"),
            duration_ms=elapsed_ms(erp_started_ms),
            metadata={
                "resource": erp_result.get("resource"),
                "status": erp_result.get("status"),
                "reference_count": len(erp_result.get("references") or []),
            },
        )

        rag_started_ms = now_ms()
        rag_result = answer_question(
            question=_rag_question(item, classification),
            role="employee",
            department="客服部",
            top_k=5,
        )
        rag_summary = str(rag_result.get("answer") or "")
        _record_loop_step(
            steps=steps,
            run_id=run_id,
            order=3,
            name="rag_policy_lookup",
            status_value="succeeded",
            input_text=_rag_question(item, classification),
            output_text=rag_summary,
            duration_ms=elapsed_ms(rag_started_ms),
            metadata={"citation_count": len(rag_result.get("citations") or [])},
        )

        decision = decide_customer_action(classification, erp_result, rag_result)
        approval_result = None
        if decision["status"] == "human_handoff" and classification["intent"] in HIGH_RISK_INTENTS:
            approval_result = create_approval_request(
                thread_id=f"customer-service-{message_id}",
                requested_by=current_user.get("id"),
                action_type=f"customer_service_{classification['intent']}",
                payload={
                    "customer_message_id": message_id,
                    "intent": classification["intent"],
                    "risk_level": classification["risk_level"],
                    "buyer_message": item["message"],
                    "order_no": item.get("order_no"),
                    "tracking_no": item.get("tracking_no"),
                    "erp_summary": erp_summary,
                    "rag_summary": rag_summary,
                    "handoff_reason": decision["handoff_reason"],
                },
            )

        llm_started_ms = now_ms()
        reply_draft = generate_customer_reply(
            item=item,
            classification=classification,
            erp_summary=erp_summary,
            rag_summary=rag_summary,
            decision=decision,
        )
        _record_loop_step(
            steps=steps,
            run_id=run_id,
            order=4,
            name="generate_reply_draft",
            status_value="succeeded",
            input_text=item["message"],
            output_text=reply_draft,
            duration_ms=elapsed_ms(llm_started_ms),
        )

        final_item = _finish_message_processing(
            message_id=message_id,
            current_user=current_user,
            run_id=run_id,
            classification=classification,
            decision=decision,
            reply_draft=reply_draft,
            erp_result=erp_result,
            erp_summary=erp_summary,
            rag_result=rag_result,
            rag_summary=rag_summary,
            approval_result=approval_result,
            duration_ms=elapsed_ms(started_ms),
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=reply_draft,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "intent": classification["intent"],
                "risk_level": classification["risk_level"],
                "automation_decision": decision["decision"],
                "final_status": decision["status"],
                "step_count": len(steps),
                "approval_id": approval_result.get("approval_id") if approval_result else None,
            },
        )
    except Exception as error:
        _mark_failed(message_id=message_id, current_user=current_user, run_id=run_id, error=error)
        record_step(
            run_id=run_id,
            step_name="customer_service_loop_error",
            step_order=len(steps) + 1,
            status_value="failed",
            provider="customer_service_automation",
            resource_type="customer_service_message",
            resource_id=message_id,
            input_text=item["message"],
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=error,
            duration_ms=elapsed_ms(started_ms),
        )
        raise

    write_audit_log(
        user_id=current_user.get("id"),
        action="customer_service.message.process",
        resource_type="customer_service_message",
        resource_id=message_id,
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": "customer_service",
            "intent": final_item["intent"],
            "risk_level": final_item["risk_level"],
            "status": final_item["status"],
            "run_id": run_id,
            "approval_id": final_item.get("approval_id"),
        },
    )
    return {
        "item": final_item,
        "run_id": run_id,
        "steps": steps,
        "events": list_customer_message_events(message_id=message_id, current_user=current_user),
    }


def classify_customer_message(item: dict[str, Any]) -> dict[str, str]:
    text = " ".join(
        str(value or "")
        for value in [
            item.get("subject"),
            item.get("message"),
            item.get("order_no"),
            item.get("tracking_no"),
            item.get("sku"),
        ]
    ).lower()
    rules: list[tuple[str, list[str]]] = [
        ("bad_review", ["bad review", "negative review", "one star", "差评", "一星", "差的评价"]),
        ("chargeback", ["chargeback", "dispute", "拒付", "信用卡争议"]),
        ("complaint", ["complaint", "angry", "投诉", "生气", "欺骗", "骗子"]),
        ("refund", ["refund", "money back", "退款", "退钱", "cancel order", "取消订单"]),
        ("exchange", ["exchange", "replace", "换货", "更换", "replacement"]),
        ("return_policy", ["return", "退货", "退回", "return policy"]),
        ("size_advice", ["size", "sizing", "尺码", "尺寸", "fit", "适合"]),
        ("promo_code", ["coupon", "promo", "discount", "优惠码", "折扣码"]),
        ("shipping_time", ["when ship", "ship out", "多久发货", "什么时候发货", "发货时间"]),
        ("logistics", ["where is my order", "tracking", "delivered", "delivery", "package", "物流", "快递", "运单", "到哪里", "签收"]),
    ]
    intent = "general_question"
    for candidate, keywords in rules:
        if any(keyword in text for keyword in keywords):
            intent = candidate
            break

    risk_level = "low"
    reason = "常规客服问题，可生成回复草稿。"
    if intent in {"refund", "complaint", "bad_review", "chargeback"}:
        risk_level = "high"
        reason = "涉及退款、投诉、差评或拒付，需要人工介入。"
    elif intent in {"exchange", "return_policy"}:
        risk_level = "medium"
        reason = "涉及售后处理边界，需要客服确认规则后回复。"
    elif _contains_high_risk_terms(text):
        risk_level = "high"
        reason = "消息包含高风险表达，需要人工处理。"

    language = detect_customer_language(item.get("message") or "")
    return {
        "intent": intent,
        "risk_level": risk_level,
        "reason": reason,
        "language": item.get("buyer_language") if item.get("buyer_language") != "auto" else language,
    }


def decide_customer_action(
    classification: dict[str, str],
    erp_result: dict[str, Any],
    rag_result: dict[str, Any],
) -> dict[str, str]:
    risk_level = classification["risk_level"]
    intent = classification["intent"]
    if risk_level == "high":
        return {
            "status": "human_handoff",
            "decision": "handoff_required",
            "handoff_reason": classification["reason"],
        }

    missing_erp_for_order = intent in {"logistics", "shipping_time", "exchange", "refund"} and not erp_result.get("items")
    if missing_erp_for_order:
        return {
            "status": "drafted",
            "decision": "draft_only",
            "handoff_reason": "没有查到足够订单/物流记录，需客服确认后发送。",
        }

    if risk_level == "medium":
        return {
            "status": "drafted",
            "decision": "draft_only",
            "handoff_reason": "中风险售后问题，建议人工确认后发送。",
        }

    return {
        "status": "auto_reply_ready",
        "decision": "low_risk_auto_reply_ready",
        "handoff_reason": "",
    }


def generate_customer_reply(
    *,
    item: dict[str, Any],
    classification: dict[str, str],
    erp_summary: str,
    rag_summary: str,
    decision: dict[str, str],
) -> str:
    target_language = classification.get("language") or "English"
    prompt = f"""你是跨境电商企业内部的客服自动化助手。
请基于客户原话、ERP 查询摘要和知识库摘要，生成一段可给客服使用的客户回复。
如果是低风险问题，可以写成可直接发送的回复；如果需要人工介入，回复要避免承诺退款、赔付、删除差评或已经执行系统动作。

客户渠道：{item.get('channel')}
客户姓名：{item.get('buyer_name') or '未知'}
站点：{item.get('marketplace') or '未知'}
订单号：{item.get('order_no') or '未提供'}
物流单号：{item.get('tracking_no') or '未提供'}
SKU：{item.get('sku') or '未提供'}
识别意图：{classification['intent']}
风险等级：{classification['risk_level']}
自动化决策：{decision['decision']}
目标语言：{target_language}

客户原话：
{item.get('message') or ''}

ERP 查询摘要：
{erp_summary or '未查到 ERP 记录。'}

知识库摘要：
{rag_summary or '资料中没有找到相关信息。'}

请输出：
1. 客户回复正文
2. 客服内部处理建议
3. 是否需要人工介入
"""
    return chat(prompt)


def detect_customer_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "Chinese"
    if re.search(r"\b(wo|ist|nicht|bitte|danke|lieferung)\b", text, re.I):
        return "German"
    if re.search(r"[\u3040-\u30ff]", text):
        return "Japanese"
    return "English"


def _ensure_customer_service_user(current_user: dict) -> None:
    if current_user.get("role") == "admin":
        return

    position = current_user.get("position")
    if position != "customer_service" or not is_valid_position(position):
        label = POSITION_LABELS.get(position, position or "未绑定岗位")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{label}无权使用客服自动化闭环。",
        )


def _ensure_message_visible(current_user: dict, item: dict[str, Any]) -> None:
    if current_user.get("role") == "admin":
        return

    user_id = current_user.get("id")
    if item.get("created_by") in (None, user_id) or item.get("assigned_to") in (None, user_id):
        return

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客服消息不存在或无权查看")


def _execution_user(current_user: dict) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        return current_user

    return {
        **current_user,
        "position": "customer_service",
        "department": "客服部",
    }


def _query_customer_erp(
    *,
    item: dict[str, Any],
    classification: dict[str, str],
    current_user: dict,
) -> dict[str, Any]:
    query_text = _erp_query_text(item, classification)
    resources = _resources_for_intent(classification["intent"])
    return query_erp_for_current_user(
        user_input=query_text,
        current_user=_execution_user(current_user),
        query=query_text,
        limit=5,
        source="customer_service_automation",
        thread_id=f"customer-service-{item['id']}",
        allowed_resources=resources,
    )


def _resources_for_intent(intent: str) -> list[str]:
    if intent in {"logistics", "shipping_time"}:
        return ["Delivery Note", "Sales Order", "Issue"]
    if intent in {"refund", "return_policy", "exchange", "complaint", "bad_review", "chargeback"}:
        return ["Sales Order", "Delivery Note", "Issue", "Return request", "Customer"]
    if intent == "size_advice":
        return ["Sales Order", "Issue", "Customer"]
    if intent == "promo_code":
        return ["Sales Order", "Customer"]
    return ["Customer", "Sales Order", "Delivery Note", "Issue", "Return request"]


def _erp_query_text(item: dict[str, Any], classification: dict[str, str]) -> str:
    parts = [
        classification.get("intent"),
        item.get("message"),
        item.get("order_no"),
        item.get("tracking_no"),
        item.get("sku"),
        item.get("buyer_email"),
        item.get("buyer_name"),
    ]
    return " ".join(str(part) for part in parts if part)


def _rag_question(item: dict[str, Any], classification: dict[str, str]) -> str:
    return (
        f"客服场景：{classification['intent']}。"
        f"客户问题：{item.get('message') or ''}。"
        "请检索公司客服政策、退货退款规则、物流回复规则、尺码建议、优惠码使用规则。"
    )


def _erp_summary_from_result(erp_result: dict[str, Any]) -> str:
    items = erp_result.get("items")
    resource = erp_result.get("resource") or ""
    if isinstance(items, list) and items:
        return summarize_erp_items(resource, items)

    return str(erp_result.get("message") or "")


def _finish_message_processing(
    *,
    message_id: str,
    current_user: dict,
    run_id: str,
    classification: dict[str, str],
    decision: dict[str, str],
    reply_draft: str,
    erp_result: dict[str, Any],
    erp_summary: str,
    rag_result: dict[str, Any],
    rag_summary: str,
    approval_result: dict[str, Any] | None,
    duration_ms: int,
) -> dict[str, Any]:
    row = fetch_one(
        """
        UPDATE customer_service_messages
        SET intent = %s,
            risk_level = %s,
            status = %s,
            automation_decision = %s,
            reply_draft = %s,
            handoff_reason = %s,
            erp_summary = %s,
            rag_summary = %s,
            erp_references = %s::jsonb,
            citations = %s::jsonb,
            approval_id = %s,
            run_id = %s,
            processed_by = %s,
            processed_at = now(),
            updated_at = now(),
            metadata = metadata || %s::jsonb
        WHERE id = %s
        RETURNING
            id, channel, external_id, buyer_name, buyer_email, buyer_language,
            marketplace, order_no, tracking_no, sku, subject, message, intent,
            risk_level, status, automation_decision, reply_draft, handoff_reason,
            erp_summary, rag_summary, erp_references, citations, approval_id,
            run_id, assigned_to, created_by, processed_by, processed_at,
            metadata, created_at, updated_at;
        """,
        (
            classification["intent"],
            classification["risk_level"],
            decision["status"],
            decision["decision"],
            reply_draft,
            decision.get("handoff_reason") or None,
            erp_summary,
            rag_summary,
            dumps_json(erp_result.get("references") or []),
            dumps_json(rag_result.get("citations") or []),
            approval_result.get("approval_id") if approval_result else None,
            run_id,
            current_user.get("id"),
            dumps_json(sanitize_metadata({
                "classification_reason": classification["reason"],
                "duration_ms": duration_ms,
                "erp_status": erp_result.get("status"),
                "erp_resource": erp_result.get("resource"),
                "approval": approval_result,
            })),
            message_id,
        ),
    )
    item = _map_message_row(row)
    _add_event(
        message_id=message_id,
        event_type="processed",
        actor_id=current_user.get("id"),
        content="AI 已完成客服消息处理",
        metadata={
            "intent": classification["intent"],
            "risk_level": classification["risk_level"],
            "status": decision["status"],
            "decision": decision["decision"],
            "run_id": run_id,
            "approval_id": item.get("approval_id"),
        },
    )
    return item


def _mark_processing(*, message_id: str, current_user: dict) -> None:
    fetch_one(
        """
        UPDATE customer_service_messages
        SET status = 'processing', processed_by = %s, updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (current_user.get("id"), message_id),
    )
    _add_event(
        message_id=message_id,
        event_type="processing_started",
        actor_id=current_user.get("id"),
        content="AI 开始处理客户消息",
        metadata={},
    )


def _mark_failed(*, message_id: str, current_user: dict, run_id: str | None, error: Exception) -> None:
    fetch_one(
        """
        UPDATE customer_service_messages
        SET status = 'failed',
            handoff_reason = %s,
            run_id = COALESCE(%s, run_id),
            processed_by = %s,
            processed_at = now(),
            updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (str(error)[:500], run_id, current_user.get("id"), message_id),
    )
    _add_event(
        message_id=message_id,
        event_type="failed",
        actor_id=current_user.get("id"),
        content="AI 处理失败",
        metadata={"error": str(error)[:500], "run_id": run_id},
    )


def _record_loop_step(
    *,
    steps: list[dict[str, Any]],
    run_id: str,
    order: int,
    name: str,
    status_value: str,
    input_text: Any,
    output_text: Any,
    duration_ms: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    record_step(
        run_id=run_id,
        step_name=name,
        step_order=order,
        status_value=status_value,
        provider="customer_service_automation",
        resource_type="customer_service_message",
        resource_id=None,
        input_text=input_text,
        output_text=output_text,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )
    steps.append({
        "step_order": order,
        "step_name": name,
        "status": status_value,
        "duration_ms": duration_ms,
    })


def _add_event(
    *,
    message_id: str,
    event_type: str,
    actor_id: str | None,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    fetch_one(
        """
        INSERT INTO customer_service_message_events (
            message_id, event_type, actor_id, content, metadata
        )
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            message_id,
            event_type,
            actor_id,
            content,
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )


def _map_message_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "channel": row[1],
        "external_id": row[2],
        "buyer_name": row[3],
        "buyer_email": row[4],
        "buyer_language": row[5],
        "marketplace": row[6],
        "order_no": row[7],
        "tracking_no": row[8],
        "sku": row[9],
        "subject": row[10],
        "message": row[11],
        "intent": row[12],
        "risk_level": row[13],
        "status": row[14],
        "automation_decision": row[15],
        "reply_draft": row[16],
        "handoff_reason": row[17],
        "erp_summary": row[18],
        "rag_summary": row[19],
        "erp_references": row[20] or [],
        "citations": row[21] or [],
        "approval_id": str(row[22]) if row[22] else None,
        "run_id": str(row[23]) if row[23] else None,
        "assigned_to": str(row[24]) if row[24] else None,
        "created_by": str(row[25]) if row[25] else None,
        "processed_by": str(row[26]) if row[26] else None,
        "processed_at": _iso(row[27]),
        "metadata": row[28] or {},
        "created_at": _iso(row[29]),
        "updated_at": _iso(row[30]),
    }


def _map_event_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "message_id": str(row[1]),
        "event_type": row[2],
        "actor_id": str(row[3]) if row[3] else None,
        "content": row[4],
        "metadata": row[5] or {},
        "created_at": _iso(row[6]),
    }


def _clean_optional(value: str | None, limit: int) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped[:limit] if stripped else None


def _extract_tracking_no(text: str) -> str | None:
    match = re.search(
        r"\b(?:1Z[A-Z0-9]{10,}|DHL-[A-Z]{2}-AMZ-\d{10,}|YAMATO-[A-Z]{2}-\d{10,})\b",
        text,
        re.I,
    )
    return match.group(0).upper() if match else None


def _extract_sku(text: str) -> str | None:
    match = re.search(r"\bAMZ-[A-Z0-9]+(?:-[A-Z0-9]+)+\b", text, re.I)
    return match.group(0).upper() if match else None


def _contains_high_risk_terms(text: str) -> bool:
    terms = ["lawsuit", "legal", "chargeback", "scam", "fraud", "起诉", "律师", "拒付", "欺诈", "差评"]
    return any(term in text for term in terms)


def _iso(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    return str(value)
