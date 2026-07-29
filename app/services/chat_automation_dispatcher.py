from __future__ import annotations

import re
from typing import Any

from app.skills.executor import SkillExecutionResult, execute_skill
from app.skills.registry import SkillDefinition, skill_for_react_action


def detect_chat_automation(message: str, current_user: dict) -> dict[str, Any] | None:
    text = " ".join(message.strip().split())
    if not text:
        return None

    position = current_user.get("position")
    if current_user.get("role") == "admin":
        position = _admin_requested_position(text)

    if position == "operations" and _looks_like_operations_listing_request(text):
        return _route_for_action("operations_listing_draft")

    if position == "customer_service" and _looks_like_customer_reply_request(text):
        return _route_for_action("customer_service_reply_draft")

    return None


def run_chat_automation(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    forced_route: dict[str, Any] | None = None,
    react_decision: dict[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    source: str = "chat_automation",
) -> dict[str, Any] | None:
    route = forced_route
    if route is None and react_decision is None:
        route = detect_chat_automation(message, current_user)
    if route is None:
        return None

    if route["intent"] == "operations_listing_draft":
        return _run_operations_listing(
            message=message,
            current_user=current_user,
            thread_id=thread_id,
            route=route,
            react_decision=react_decision,
            attachments=attachments or [],
            source=source,
        )

    if route["intent"] == "customer_service_reply_draft":
        return _run_customer_service_reply(
            message=message,
            current_user=current_user,
            thread_id=thread_id,
            route=route,
            react_decision=react_decision,
            source=source,
        )

    return None


def _run_operations_listing(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    route: dict[str, Any],
    react_decision: dict[str, Any] | None,
    attachments: list[dict[str, Any]],
    source: str,
) -> dict[str, Any]:
    skill = _skill_from_route(route)
    result = execute_skill(
        skill_id=skill.skill_id,
        payload={
            "message": message,
            "attachments": attachments,
            "metadata": _chat_skill_metadata(thread_id=thread_id, current_user=current_user),
        },
        current_user=current_user,
        source=source,
        react_decision=react_decision,
    )
    draft = result.platform_draft
    draft_id = draft.get("id") if draft else "未返回"
    writeback_status = draft.get("writeback_status") if draft else "unknown"
    answer = (
        "已识别为运营上架自动化需求。AI 已根据 SKU、ERPNext 商品资料和图片信息生成 Listing 草稿，"
        "并保存为跨境平台草稿，等待运营确认后上传 Amazon。\n"
        f"草稿 ID：{draft_id}\n"
        f"写回状态：{writeback_status}\n\n"
        f"{result.answer or ''}"
    )
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": route["intent"],
        "risk_level": "low",
        "erp_references": result.erp_references,
        "attachments": [],
        "approval_result": None,
        "platform_draft": draft,
        "automation": _automation_metadata(
            skill=skill,
            route=route,
            result=result,
            extra={
                "type": "ai_workflow",
                "workflow_id": "operations_listing_launch",
                "amazon_upload_status": result.metadata.get("amazon_upload_status"),
            },
        ),
    }


def _run_customer_service_reply(
    *,
    message: str,
    current_user: dict,
    thread_id: str,
    route: dict[str, Any],
    react_decision: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    skill = _skill_from_route(route)
    result = execute_skill(
        skill_id=skill.skill_id,
        payload={
            "message": message,
            "channel": _detect_customer_channel(message),
            "buyer_name": _extract_labeled_value(message, ["客户", "buyer", "name"]),
            "buyer_email": _extract_email(message),
            "buyer_language": "auto",
            "marketplace": _extract_marketplace(message),
            "order_no": _extract_labeled_value(message, ["订单号", "订单", "order", "order no", "order id"]),
            "tracking_no": _extract_labeled_value(message, ["物流单号", "运单号", "tracking", "tracking no"]),
            "sku": _extract_labeled_value(message, ["sku", "SKU"]),
            "subject": "AI 对话触发客服自动化",
            "metadata": _chat_skill_metadata(thread_id=thread_id, current_user=current_user),
        },
        current_user=current_user,
        source=source,
        react_decision=react_decision,
    )
    metadata = result.metadata
    draft = result.platform_draft
    draft_id = draft.get("id") if draft else None
    answer = (
        "已识别为客服自动化回复需求。AI 已自动分类客户问题、查询客服岗位权限内的 ERP/RAG 信息，"
        "并生成回复草稿保存到客服平台草稿区。\n"
        f"客户消息 ID：{metadata.get('message_id') or '未返回'}\n"
        f"意图：{metadata.get('intent') or '未识别'}\n"
        f"风险等级：{metadata.get('risk_level')}\n"
        f"处理结果：{result.status}\n"
        f"草稿 ID：{draft_id or '未生成'}\n"
        f"写回状态：{metadata.get('writeback_status') or 'draft_saved'}\n\n"
        f"{result.answer or ''}"
    )
    return {
        "thread_id": thread_id,
        "answer": answer,
        "intent": route["intent"],
        "risk_level": metadata.get("risk_level"),
        "erp_references": result.erp_references,
        "attachments": [],
        "approval_result": result.approval_result,
        "platform_draft": draft,
        "automation": _automation_metadata(
            skill=skill,
            route=route,
            result=result,
            extra={
                "type": "customer_service_message_loop",
                "message_id": metadata.get("message_id"),
                "status": result.status,
                "automation_decision": metadata.get("automation_decision"),
            },
        ),
    }


def _route_for_action(action: str) -> dict[str, Any] | None:
    skill = skill_for_react_action(action)
    if skill is None:
        return None
    return _route_from_skill(skill=skill, intent=action)


def _route_from_skill(*, skill: SkillDefinition, intent: str) -> dict[str, Any]:
    route: dict[str, Any] = {
        "intent": intent,
        "position": skill.position,
        "skill_id": skill.skill_id,
        "flow_key": skill.flow_key,
        "label": skill.name,
    }
    workflow_id = _legacy_workflow_id(skill)
    if workflow_id:
        route["workflow_id"] = workflow_id
    return route


def _skill_from_route(route: dict[str, Any]) -> SkillDefinition:
    skill_id = route.get("skill_id")
    if skill_id:
        skill = skill_for_react_action(str(route["intent"]))
        if skill and skill.skill_id == skill_id:
            return skill

    skill = skill_for_react_action(str(route["intent"]))
    if skill is None:
        raise ValueError(f"聊天自动化动作未注册 Skill：{route.get('intent')}")
    return skill


def _legacy_workflow_id(skill: SkillDefinition) -> str | None:
    return next((item for item in skill.legacy_ids if item.endswith("_launch")), None)


def _chat_skill_metadata(*, thread_id: str, current_user: dict) -> dict[str, Any]:
    return {
        "source": "chat_automation",
        "thread_id": thread_id,
        "requested_by": current_user.get("id"),
    }


def _automation_metadata(
    *,
    skill: SkillDefinition,
    route: dict[str, Any],
    result: SkillExecutionResult,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "skill_id": skill.skill_id,
        "skill_name": skill.name,
        "flow_key": skill.flow_key,
        "app_id": skill.app_id,
        "source": result.metadata.get("source"),
        "run_id": result.run_id,
        "step_count": result.metadata.get("step_count"),
        "react_action": route.get("intent"),
    }
    metadata.update(extra or {})
    return {key: value for key, value in metadata.items() if value is not None}


def _looks_like_operations_listing_request(text: str) -> bool:
    lowered = text.lower()
    has_product_context = any(
        keyword in lowered
        for keyword in [
            "sku",
            "asin",
            "商品",
            "产品",
            "listing",
            "上架",
            "五点",
            "关键词",
            "标题",
            "卖点",
            "促销文案",
            "seller central",
            "amazon",
        ]
    )
    wants_draft_or_publish = any(
        keyword in lowered
        for keyword in [
            "草稿",
            "保存",
            "上传",
            "写入",
            "上架",
            "生成listing",
            "生成 listing",
            "listing draft",
            "upload",
            "draft",
            "write",
            "launch",
        ]
    )
    return has_product_context and wants_draft_or_publish


def _looks_like_customer_reply_request(text: str) -> bool:
    lowered = text.lower()
    has_customer_context = any(
        keyword in lowered
        for keyword in [
            "客户",
            "买家",
            "客服",
            "回复",
            "自动回复",
            "话术",
            "customer",
            "buyer",
            "reply",
            "respond",
            "message",
            "where is my order",
        ]
    )
    has_service_topic = any(
        keyword in lowered
        for keyword in [
            "物流",
            "退款",
            "退货",
            "换货",
            "尺码",
            "优惠码",
            "发货",
            "订单",
            "运单",
            "tracking",
            "delivery",
            "package",
            "refund",
            "return",
            "exchange",
            "size",
            "coupon",
            "promo",
            "ship",
        ]
    )
    return has_customer_context and has_service_topic


def _position_execution_user(current_user: dict, position: str) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        return current_user

    return {
        **current_user,
        "position": position,
    }


def _admin_requested_position(text: str) -> str | None:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["运营", "listing", "上架", "seller central"]):
        return "operations"
    if any(keyword in lowered for keyword in ["客服", "客户", "买家", "customer", "buyer", "reply"]):
        return "customer_service"
    if any(keyword in lowered for keyword in ["财务", "工资", "salary", "报表", "对账"]):
        return "finance"
    return None


def _detect_customer_channel(text: str) -> str:
    lowered = text.lower()
    if "email" in lowered or "邮箱" in lowered:
        return "email"
    if "ticket" in lowered or "工单" in lowered:
        return "ticket"
    if "api" in lowered or "webhook" in lowered:
        return "api"
    return "amazon"


def _extract_labeled_value(text: str, labels: list[str]) -> str | None:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:：#]?\s*([A-Za-z0-9][A-Za-z0-9_.@-]{{2,80}})"
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()[:120]
    return None


def _extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    return match.group(0)[:180] if match else None


def _extract_marketplace(text: str) -> str | None:
    lowered = text.lower()
    for label, value in [
        ("美国", "US"),
        ("us", "US"),
        ("德国", "DE"),
        ("germany", "DE"),
        ("日本", "JP"),
        ("japan", "JP"),
        ("英国", "UK"),
        ("uk", "UK"),
    ]:
        if label in lowered:
            return value
    return None
