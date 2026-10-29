from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from app.services.chat_intent_guard_service import is_information_request, is_action_negated, has_execution_request, is_social_request, is_unsupported_leave_action, instruction_text

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
    if is_information_request(text) or is_action_negated(text) or is_unsupported_leave_action(text):
        return None
    text = instruction_text(text)
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
    if (isinstance(execution_context, dict) and execution_context.get("active")
            and execution_context.get("external_action_type") and execution_context.get("target_channel")):
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
        "active": status_normalized.startswith("waiting_") or (status_normalized == "failed" and bool(target_channel)),
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
        "artifact_id": plan.get("artifact_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def should_resume_external_action_with_message(message: str, pending_action: dict[str, Any] | None) -> bool:
    if not isinstance(pending_action, dict) or not pending_action.get("active") or pending_action.get("status") in {"completed", "succeeded", "cancelled"}:
        return False
    text = " ".join((message or "").strip().split())
    if not text:
        return False

    lowered = text.lower()
    if any(keyword in lowered for keyword in ["取消", "算了", "不用了", "不发了", "停止", "终止"]):
        return False
    if is_information_request(text) or is_social_request(text) or is_action_negated(text):
        return False

    if lowered in {"继续", "继续上一任务", "继续刚才的任务", "按刚才的继续", "按上一步继续"}:
        return True

    channel, _ = _detect_target_channel(lowered)
    if channel and lowered in {item.lower() for item in (
        ENTERPRISE_WECHAT_TARGETS + EMAIL_TARGETS + AMAZON_TARGETS
    )}:
        return True

    # Explicit slot edits on the same task are continuations.
    if re.fullmatch(r"(?:发给|发送给|收件人[：:]?)\s*[\w\-\u4e00-\u9fff]{2,20}", text):
        return True
    if (pending_action.get("business_object") == "salary_table" and
            re.fullmatch(r"(?:生成|改成|改为)(?:这个月|本月|上个月|上月|下个月|下月)的?工资表", text)):
        return True
    # A new command is routed independently; it cannot inherit old recipients.
    if has_execution_request(text):
        return False
    target_channel = str(channel or pending_action.get("target_channel") or "")
    if (pending_action.get("business_object") in {"salary_table", "finance_package", "finance_report"}
            and re.fullmatch(r"(?:改成|改为|用|期间是)?(?:这个月|本月|上个月|上月|下个月|下月|last month|next month)", lowered)):
        return True
    if target_channel == "email":
        return bool(_EMAIL_RE.fullmatch(text) or re.fullmatch(
            r"(?:收件邮箱|邮箱|收件人)\s*[:：]?\s*" + _EMAIL_RE.pattern,
            text,
            re.I,
        ))

    if len(text) <= 40 and _extract_recipient(text, target_channel):
        return True

    if (not pending_action.get("recipient_name")
            and (pending_action.get("status") == "waiting_recipient_selection" or
                 (pending_action.get("status") == "waiting_clarification" and
                  any(word in str(pending_action.get("question") or "") for word in ("接收对象", "收件人", "联系人", "接收人"))))
            and re.fullmatch(r"[\u4e00-\u9fff]{2,4}|[A-Za-z][A-Za-z0-9_\-]{1,19}", text)
            and not any(word in text for word in ("请假", "流程", "规则", "政策", "工资", "文件", "报表"))):
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
    if not should_resume_external_action_with_message(message, pending_action):
        return message, None
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

    # Keep persisted slots authoritative; parse only this reply for new slots.
    target_channel = str(_detect_target_channel((message or "").lower())[0] or pending_action.get("target_channel") or "unknown_message_channel")
    recipient_name = _extract_recipient(message, target_channel)
    previous_channel = str(pending_action.get("target_channel") or "")
    if not recipient_name and (target_channel == previous_channel or (previous_channel == "unknown_message_channel" and target_channel == "enterprise_wechat")):
        recipient_name = str(pending_action.get("recipient_name") or "").strip() or None
    if (not recipient_name and target_channel != "email"
            and str(pending_action.get("status") or "") in {"waiting_recipient_selection", "waiting_clarification"}
            and re.fullmatch(r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9_\-]{1,19}", message.strip())
            and not _detect_target_channel(message.lower())[0]):
        recipient_name = message.strip()
    return ExternalActionIntent(
        external_action_type=str(pending_action.get("external_action_type") or "send_file"),
        target_channel=target_channel,
        business_object=str(pending_action.get("business_object") or "latest_file"),
        data_source=str(pending_action.get("data_source") or "latest_generated_file"),
        recipient_name=recipient_name,
        confidence=0.9,
        matched_actions=list(pending_action.get("matched_actions") or ["发送"]),
        matched_targets=[target_channel],
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
    return bool(re.search(r"(?:发送给|发给|传给|转发给|发到)\s*[\w\-\u4e00-\u9fff@.]{1,64}", text, re.I))


def _extract_recipient(text: str, target_channel: str) -> str | None:
    email_match = _EMAIL_RE.search(text)
    if email_match:
        return email_match.group(0)
    if target_channel == "email":
        return None
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
    if any(marker in text for marker in ("谁", "什么", "怎么", "如何", "哪", "是否", "请假", "流程", "规则")):
        return None
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
    if intent_name in {"policy", "rag_query", "erp", "order", "refund", "ask_clarification", "permission_denied", "chitchat", "document_qa"}:
        return False
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
    """Persisted execution slots already contain accepted follow-ups.

    Never infer recipients/channels by replaying unrelated conversation history.
    """
    return dict(pending)


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
