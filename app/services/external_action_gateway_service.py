from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

@dataclass(frozen=True)
class ExternalActionIntent:
    external_action_type: str
    target_channel: str
    business_object: str
    data_source: str
    recipient_name: str | None
    confidence: float
    matched_actions: list[str]
    matched_targets: list[str]
    requires_confirmation: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SEND_ACTIONS = ["发送", "发给", "转发", "传给", "发到", "发送到", "send"]
FILL_ACTIONS = ["填写", "填入", "写入", "录入", "保存草稿", "填到"]
UPLOAD_ACTIONS = ["上传", "导入", "提交前准备", "放到", "放进"]
OPEN_ACTIONS = ["打开", "接管", "操作"]

ENTERPRISE_WECHAT_TARGETS = ["企业微信", "企微", "微信", "wechat", "weixin"]
EMAIL_TARGETS = ["邮箱", "邮件", "email", "e-mail", "smtp", "mail"]
AMAZON_TARGETS = ["amazon", "seller central", "亚马逊", "sellercentral"]
CUSTOMER_SYSTEM_TARGETS = ["客服系统", "客服平台", "工单系统", "回复草稿"]
ERP_WRITE_TARGETS = ["erp", "erpnext", "写入系统", "外部平台", "网页后台"]

LATEST_FILE_MARKERS = ["刚刚", "刚才", "上面", "上一份", "上一个", "最近", "当前文件", "这个文件", "这份文件", "这两份", "附件"]
PERIOD_MARKERS = [
    "这个月",
    "本月",
    "当前月",
    "上个月",
    "上月",
    "下个月",
    "下月",
    "last month",
    "next month",
]
FOLLOWUP_WINDOW_MARKERS = SEND_ACTIONS + FILL_ACTIONS + UPLOAD_ACTIONS + OPEN_ACTIONS + PERIOD_MARKERS + [
    "工资",
    "工资表",
    "薪资",
    "财务报表",
    "报表",
    "文件",
    "表格",
    "联系人",
    "接收人",
    "收件人",
    "给",
]


def recognize_external_action_intent(
    message: str,
    attachments: list[dict[str, Any]] | None = None,
) -> ExternalActionIntent | None:
    text = " ".join((message or "").strip().split())
    if not text:
        return None
    lowered = text.lower()
    attachment_list = attachments or []

    action_type, matched_actions = _detect_action_type(lowered)
    target_channel, matched_targets = _detect_target_channel(lowered)

    has_direct_recipient_send = action_type == "send_file" and _looks_like_send_to_recipient(text)
    if not matched_actions or (not matched_targets and not has_direct_recipient_send):
        return None

    if not matched_targets and has_direct_recipient_send:
        target_channel = "unknown_message_channel"
        matched_targets = ["接收人"]

    business_object = _detect_business_object(lowered, target_channel)
    data_source = _detect_data_source(lowered, business_object, attachment_list)
    recipient_name = _extract_recipient(text, target_channel)
    confidence = _confidence(
        matched_actions=matched_actions,
        matched_targets=matched_targets,
        business_object=business_object,
        data_source=data_source,
        recipient_name=recipient_name,
    )
    return ExternalActionIntent(
        external_action_type=action_type,
        target_channel=target_channel,
        business_object=business_object,
        data_source=data_source,
        recipient_name=recipient_name,
        confidence=confidence,
        matched_actions=matched_actions,
        matched_targets=matched_targets,
        requires_confirmation=True,
        reason="命中外部发送、填写、上传或写入动作，统一进入 plan-and-execute。",
    )


def external_action_intent_dict(intent: ExternalActionIntent | None) -> dict[str, Any] | None:
    return intent.to_dict() if intent else None


def get_pending_external_action(thread_id: str | None) -> dict[str, Any] | None:
    if not thread_id:
        return None
    from app.services.context_service import get_thread_state

    state = get_thread_state(thread_id)
    slots = state.get("slots") if isinstance(state.get("slots"), dict) else {}
    pending = slots.get("pending_external_action") if isinstance(slots, dict) else None
    if isinstance(pending, dict) and pending.get("active"):
        return _enrich_pending_action_from_recent_messages(thread_id, pending)
    execution_context = slots.get("execution_context") if isinstance(slots, dict) else None
    if isinstance(execution_context, dict) and execution_context.get("active"):
        return _enrich_pending_action_from_recent_messages(thread_id, execution_context)
    return None


def build_execution_context_from_result(graph_result: dict, user_message: str) -> dict[str, Any] | None:
    automation = graph_result.get("automation") if isinstance(graph_result.get("automation"), dict) else {}
    plan = automation.get("plan") if isinstance(automation.get("plan"), dict) else {}
    if not plan and isinstance(automation.get("execution_plan"), dict):
        plan = automation["execution_plan"]
    approval_result = graph_result.get("approval_result") if isinstance(graph_result.get("approval_result"), dict) else {}
    status = str(approval_result.get("status") or automation.get("status") or "").strip()
    intent_name = str(graph_result.get("intent") or automation.get("type") or "").strip()
    target_channel = _first_nonempty(
        plan.get("target_channel"),
        automation.get("target_channel"),
        _channel_from_wechat_automation(automation),
    )
    business_object = _first_nonempty(
        plan.get("business_object"),
        automation.get("business_object"),
        _business_object_from_automation(automation, user_message),
    )
    recipient_name = _first_nonempty(
        plan.get("recipient_name"),
        automation.get("recipient_name"),
        _recipient_from_wechat_automation(automation),
        _extract_recipient(user_message, target_channel),
    )
    source_message = _first_nonempty(
        plan.get("source_message"),
        automation.get("source_message"),
        user_message,
    )
    effective_message = _first_nonempty(
        plan.get("effective_message"),
        automation.get("effective_message"),
        source_message,
    )
    if not _looks_like_execution_context(
        intent_name=intent_name,
        status=status,
        target_channel=target_channel,
        business_object=business_object,
        user_message=user_message,
    ):
        return None

    history = automation.get("conversation_fragments")
    history_list = list(history) if isinstance(history, list) else []
    history_list.append({"role": "user", "content": user_message})
    history_list = history_list[-8:]
    status_normalized = status or "active"
    return {
        "active": status_normalized not in {"completed", "succeeded", "cancelled"},
        "status": status_normalized,
        "status_label": approval_result.get("status_label") or automation.get("status_label"),
        "source_message": source_message,
        "effective_message": effective_message,
        "summary": plan.get("summary") or automation.get("summary"),
        "external_action_type": _first_nonempty(
            plan.get("external_action_type"),
            automation.get("external_action_type"),
            "send_file" if target_channel in {"enterprise_wechat", "email", "unknown_message_channel"} else "",
        ),
        "target_channel": target_channel,
        "business_object": business_object,
        "data_source": _first_nonempty(plan.get("data_source"), automation.get("data_source"), _data_source_for_object(business_object)),
        "recipient_name": recipient_name,
        "question": graph_result.get("answer"),
        "last_error": _error_text_from_result(graph_result),
        "last_user_message": user_message,
        "conversation_fragments": history_list,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def should_resume_external_action_with_message(message: str, pending_action: dict[str, Any] | None) -> bool:
    if not isinstance(pending_action, dict) or not pending_action.get("active"):
        return False
    text = " ".join((message or "").strip().split())
    if not text:
        return False

    lowered = text.lower()
    if any(keyword in lowered for keyword in ["取消", "算了", "不用了", "不发了", "停止", "终止"]):
        return False

    target_markers = ENTERPRISE_WECHAT_TARGETS + EMAIL_TARGETS + AMAZON_TARGETS + ["企业微信", "微信", "邮箱", "邮件", "amazon", "亚马逊", "seller central", "sellercentral"]
    if len(text) <= 20 and any(keyword.lower() in lowered for keyword in target_markers):
        return True

    if len(text) <= 30 and any(keyword.lower() in lowered for keyword in PERIOD_MARKERS):
        return True

    if len(text) <= 40 and _extract_recipient(text, str(pending_action.get("target_channel") or "")):
        return True

    if len(text) <= 40 and any(keyword.lower() in lowered for keyword in FOLLOWUP_WINDOW_MARKERS):
        return True

    if len(text) <= 12 and not any(keyword in lowered for keyword in SEND_ACTIONS + FILL_ACTIONS + UPLOAD_ACTIONS + OPEN_ACTIONS):
        return True

    return False


def merge_external_action_followup_message(message: str, pending_action: dict[str, Any] | None) -> str:
    text = " ".join((message or "").strip().split())
    if not should_resume_external_action_with_message(text, pending_action):
        return text
    source_message = str((pending_action or {}).get("effective_message") or (pending_action or {}).get("source_message") or "").strip()
    if not source_message:
        return text
    if text and text in source_message:
        return source_message
    return f"{source_message} {text}".strip()


def resolve_external_action_message(
    message: str,
    thread_id: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    pending_action = get_pending_external_action(thread_id)
    merged_message = merge_external_action_followup_message(message, pending_action)
    return merged_message, pending_action


def resolve_external_action_followup_intent(
    message: str,
    thread_id: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> ExternalActionIntent | None:
    pending_action = get_pending_external_action(thread_id)
    if not should_resume_external_action_with_message(message, pending_action):
        return None

    merged_message = merge_external_action_followup_message(message, pending_action)
    intent = recognize_external_action_intent(merged_message, attachments or [])
    if intent is not None:
        intent = _merge_intent_with_pending(intent, pending_action)
        if pending_action and pending_action.get("recipient_name") and not intent.recipient_name:
            intent = ExternalActionIntent(
                **{
                    **intent.to_dict(),
                    "recipient_name": str(pending_action.get("recipient_name")),
                }
            )
        return intent

    if not pending_action:
        return None

    target_channel = str(_detect_target_channel((message or "").lower())[0] or pending_action.get("target_channel") or "")
    if target_channel == "unknown_message_channel":
        detected_channel = _detect_target_channel(merged_message.lower())[0]
        if detected_channel:
            target_channel = detected_channel
    recipient_name = (
        _extract_recipient(merged_message, target_channel)
        or str(pending_action.get("recipient_name") or "").strip()
        or None
    )
    return ExternalActionIntent(
        external_action_type=str(pending_action.get("external_action_type") or "send_file"),
        target_channel=target_channel or "unknown_message_channel",
        business_object=str(pending_action.get("business_object") or "latest_file"),
        data_source=str(pending_action.get("data_source") or "latest_generated_file"),
        recipient_name=recipient_name,
        confidence=0.9,
        matched_actions=list(pending_action.get("matched_actions") or ["发送"]),
        matched_targets=list(pending_action.get("matched_targets") or ([target_channel] if target_channel else ["接收人"])),
        requires_confirmation=True,
        reason="续接上一轮待确认的外部动作。",
    )


def _merge_intent_with_pending(intent: ExternalActionIntent, pending_action: dict[str, Any] | None) -> ExternalActionIntent:
    if not isinstance(pending_action, dict):
        return intent
    target_channel = intent.target_channel
    if target_channel == "unknown_message_channel":
        target_channel = str(pending_action.get("target_channel") or target_channel)
    return ExternalActionIntent(
        external_action_type=intent.external_action_type or str(pending_action.get("external_action_type") or "send_file"),
        target_channel=target_channel,
        business_object=(
            intent.business_object
            if intent.business_object != "latest_file"
            else str(pending_action.get("business_object") or intent.business_object)
        ),
        data_source=(
            intent.data_source
            if intent.data_source != "latest_generated_file"
            else str(pending_action.get("data_source") or intent.data_source)
        ),
        recipient_name=intent.recipient_name or str(pending_action.get("recipient_name") or "").strip() or None,
        confidence=max(intent.confidence, 0.9),
        matched_actions=_dedupe(list(intent.matched_actions) + list(pending_action.get("matched_actions") or [])),
        matched_targets=_dedupe(list(intent.matched_targets) + list(pending_action.get("matched_targets") or [])),
        requires_confirmation=True,
        reason="续接上一轮待确认的外部动作。",
    )


def _detect_action_type(lowered: str) -> tuple[str, list[str]]:
    groups = [
        ("send_file", SEND_ACTIONS),
        ("fill_web_form", FILL_ACTIONS),
        ("upload_file", UPLOAD_ACTIONS),
        ("write_draft", OPEN_ACTIONS),
    ]
    for action_type, keywords in groups:
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        if matched:
            return action_type, matched
    return "", []


def _detect_target_channel(lowered: str) -> tuple[str, list[str]]:
    email_match = _EMAIL_RE.search(lowered)
    target_groups = [
        ("enterprise_wechat", ENTERPRISE_WECHAT_TARGETS),
        ("email", EMAIL_TARGETS),
        ("amazon_seller_central", AMAZON_TARGETS),
        ("customer_service_system", CUSTOMER_SYSTEM_TARGETS),
        ("erp_or_external_platform", ERP_WRITE_TARGETS),
    ]
    if email_match:
        return "email", [email_match.group(0)]
    for channel, keywords in target_groups:
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        if matched:
            return channel, matched
    return "", []


def _detect_business_object(lowered: str, target_channel: str) -> str:
    if any(keyword in lowered for keyword in ["工资", "薪资", "工资表", "工资单", "salary", "payroll"]):
        if any(keyword in lowered for keyword in ["财务报表", "月报", "总账", "发票", "收付款"]):
            return "finance_package"
        return "salary_table"
    if any(keyword in lowered for keyword in ["财务报表", "财务资料", "月报", "经营报表", "总账", "销售发票", "采购发票", "收付款"]):
        return "finance_report"
    if any(keyword in lowered for keyword in ["库存", "库存表", "库存清单", "inventory", "stock"]):
        return "inventory_table"
    if any(keyword in lowered for keyword in ["员工表", "员工清单", "人员表", "employee", "staff"]):
        return "employee_table"
    if target_channel == "amazon_seller_central" or any(keyword in lowered for keyword in ["listing", "sku", "五点", "商品文案", "上架", "标题"]):
        return "listing_draft"
    if any(keyword in lowered for keyword in ["客服回复", "客户回复", "回复草稿", "工单", "售后"]):
        return "customer_reply_draft"
    if any(keyword in lowered for keyword in ["word", "excel", "xlsx", "pdf", "文件", "附件", "表格", "报告"] + LATEST_FILE_MARKERS):
        return "latest_file"
    return "latest_file"


def _detect_data_source(
    lowered: str,
    business_object: str,
    attachments: list[dict[str, Any]],
) -> str:
    if any(isinstance(item, dict) for item in attachments):
        return "uploaded_file"
    if any(keyword in lowered for keyword in LATEST_FILE_MARKERS):
        return "latest_generated_file"
    if business_object in {
        "salary_table",
        "finance_report",
        "finance_package",
        "inventory_table",
        "employee_table",
        "listing_draft",
        "customer_reply_draft",
    }:
        return "erp_resource"
    return "latest_generated_file"


def _looks_like_send_to_recipient(text: str) -> bool:
    if _EMAIL_RE.search(text):
        return True
    return bool(re.search(r"(?:发送给|发给|传给|转发给|发到)\s*[\w\-\u4e00-\u9fff@.]{2,64}", text, re.I))


def _extract_recipient(text: str, target_channel: str) -> str | None:
    email_match = _EMAIL_RE.search(text)
    if email_match:
        return email_match.group(0)
    if target_channel == "amazon_seller_central":
        return None
    patterns = [
        r"(?:发送|发给|传给|转发|发到|发送到)\s*(?:企业微信|企微|微信|邮箱|邮件|email|e-mail)\s*(?:给|到)?\s*([A-Za-z0-9_\-@\.\u4e00-\u9fff]{2,64})",
        r"(?:发送给|发给|传给|转发给|发到|发送到)\s*([A-Za-z0-9_\-@\.\u4e00-\u9fff]{2,64})",
        r"(?:给)\s*([A-Za-z0-9_\-@\.\u4e00-\u9fff]{2,64})",
        r"(?:联系人|接收人|收件人)\s*[:：]\s*([A-Za-z0-9_\-@\.\u4e00-\u9fff]{2,64})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        candidate = _clean_recipient(match.group(1))
        if candidate:
            return candidate
    return None


def _clean_recipient(value: str) -> str | None:
    text = re.sub(r"[，,。；;！!？?].*$", "", value or "").strip()
    text = re.sub(r"(企业微信|微信|邮箱|邮件|发送|发给|文件|表格|确认|草稿)$", "", text).strip()
    return text or None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _channel_from_wechat_automation(automation: dict[str, Any]) -> str:
    if not isinstance(automation, dict):
        return ""
    if str(automation.get("type") or "").endswith("wechat_send"):
        return "enterprise_wechat"
    if automation.get("wechat_send") or automation.get("confirmation_card"):
        return "enterprise_wechat"
    return ""


def _business_object_from_automation(automation: dict[str, Any], user_message: str) -> str:
    text = f"{user_message} {automation.get('type') or ''} {automation.get('workflow_id') or ''}".lower()
    if any(keyword in text for keyword in ["工资", "薪资", "salary"]):
        return "salary_table"
    if any(keyword in text for keyword in ["财务报表", "月报", "finance"]):
        return "finance_report"
    if any(keyword in text for keyword in ["listing", "amazon", "亚马逊"]):
        return "listing_draft"
    if any(keyword in text for keyword in ["文件", "附件", "excel", "word", "pdf"]):
        return "latest_file"
    return ""


def _recipient_from_wechat_automation(automation: dict[str, Any]) -> str:
    wechat_send = automation.get("wechat_send") if isinstance(automation.get("wechat_send"), dict) else {}
    payload = wechat_send.get("payload") if isinstance(wechat_send.get("payload"), dict) else {}
    return _first_nonempty(
        wechat_send.get("recipient_name"),
        payload.get("recipient_name"),
        automation.get("recipient_name"),
    )


def _data_source_for_object(business_object: str) -> str:
    if business_object in {
        "salary_table",
        "finance_report",
        "finance_package",
        "inventory_table",
        "employee_table",
        "listing_draft",
        "customer_reply_draft",
    }:
        return "erp_resource"
    return "latest_generated_file"


def _looks_like_execution_context(
    *,
    intent_name: str,
    status: str,
    target_channel: str,
    business_object: str,
    user_message: str,
) -> bool:
    haystack = f"{intent_name} {status} {target_channel} {business_object} {user_message}".lower()
    if any(keyword in haystack for keyword in ["rag", "document_qa", "chitchat", "闲聊"]):
        return False
    if target_channel or business_object in {
        "salary_table",
        "finance_report",
        "finance_package",
        "latest_file",
        "listing_draft",
    }:
        return True
    return any(keyword in haystack for keyword in ["wechat", "微信", "邮箱", "发送", "工资", "salary", "外部"])


def _error_text_from_result(graph_result: dict[str, Any]) -> str:
    automation = graph_result.get("automation") if isinstance(graph_result.get("automation"), dict) else {}
    candidates = [
        graph_result.get("error"),
        graph_result.get("answer"),
        automation.get("error"),
        automation.get("message"),
    ]
    for value in candidates:
        text = str(value or "").strip()
        if text and any(keyword in text for keyword in ["失败", "没有查到", "请确认", "错误", "不可用"]):
            return text[:500]
    return ""


def _enrich_pending_action_from_recent_messages(thread_id: str, pending: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.services.context_service import list_recent_messages

        recent_messages = list_recent_messages(thread_id=thread_id, limit=8)
    except Exception:
        return pending

    user_fragments = [
        str(item.get("content") or "").strip()
        for item in recent_messages
        if isinstance(item, dict) and item.get("role") == "user" and str(item.get("content") or "").strip()
    ]
    if not user_fragments:
        return pending

    source_message = str(pending.get("source_message") or "").strip()
    if not source_message:
        source_message = _pick_source_message(user_fragments)
    merged = " ".join(_dedupe([source_message, *user_fragments])).strip()
    target_channel = _first_nonempty(
        _detect_target_channel(merged.lower())[0],
        pending.get("target_channel"),
    )
    recipient_name = _first_nonempty(
        _extract_recipient(merged, target_channel),
        pending.get("recipient_name"),
    )
    business_object = _first_nonempty(
        _detect_business_object(merged.lower(), target_channel),
        pending.get("business_object"),
    )
    data_source = _first_nonempty(pending.get("data_source"), _data_source_for_object(business_object))
    return {
        **pending,
        "source_message": source_message or pending.get("source_message"),
        "effective_message": merged or pending.get("effective_message") or pending.get("source_message"),
        "target_channel": target_channel or pending.get("target_channel"),
        "recipient_name": recipient_name or pending.get("recipient_name"),
        "business_object": business_object or pending.get("business_object"),
        "data_source": data_source or pending.get("data_source"),
        "conversation_fragments": [
            {"role": "user", "content": item}
            for item in user_fragments[-8:]
        ],
    }


def _pick_source_message(user_fragments: list[str]) -> str:
    for text in reversed(user_fragments):
        lowered = text.lower()
        if any(keyword.lower() in lowered for keyword in FOLLOWUP_WINDOW_MARKERS):
            return text
    return user_fragments[-1] if user_fragments else ""


def _confidence(
    *,
    matched_actions: list[str],
    matched_targets: list[str],
    business_object: str,
    data_source: str,
    recipient_name: str | None,
) -> float:
    score = 0.68 + min(len(matched_actions), 2) * 0.06 + min(len(matched_targets), 2) * 0.06
    if business_object != "latest_file":
        score += 0.08
    if data_source != "latest_generated_file":
        score += 0.04
    if recipient_name:
        score += 0.04
    return round(min(score, 0.98), 2)


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
