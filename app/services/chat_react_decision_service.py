from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.llm import chat_model
from app.permissions import POSITION_LABELS
from app.services.finance_compound_intent_service import (
    FINANCE_COMPOUND_INTENT,
    recognize_finance_compound_intent,
    should_handle_finance_compound_generation,
)


ChatAction = Literal[
    "chitchat",
    "ask_clarification",
    "rag_query",
    "erp_query",
    "order_query",
    "refund_request",
    "finance_compound_report_generation",
    "finance_salary_export",
    "finance_salary_wechat_send",
    "operations_listing_draft",
    "customer_service_reply_draft",
    "deny",
]


class ChatReActDecision(BaseModel):
    action: ChatAction = Field(description="下一步动作。")
    requested_position: Literal["operations", "customer_service", "finance", "unknown"] = Field(
        default="unknown",
        description="用户需求本质上属于哪个岗位权限。",
    )
    confidence: float = Field(default=0.7, ge=0, le=1, description="意图识别置信度。")
    reason: str = Field(default="", description="简短中文理由，不包含敏感信息。")
    clarification_question: str | None = Field(
        default=None,
        description="当 action=ask_clarification 时向用户追问的问题。",
    )


REACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
你是企业 AI 应用平台的 ReAct 意图规划器，不是最终回答助手。

你要先理解用户目标，再选择一个“下一步动作”。你不能执行工具，不能编造数据。
真正的权限校验和工具调用会由后端流程编排执行。

岗位边界：
- operations：Listing、标题、五点描述、关键词、促销文案、竞品分析、上架草稿。
- customer_service：客户消息、物流回复、退款/退货/换货话术、多语言客服、售后高风险转人工。
- finance：财务报表、工资表、销售发票、总账、收付款、采购发票、财务 Excel 导出。

动作选择规则：
- 用户问候、感谢、闲聊：chitchat。
- 用户问题不清晰，无法知道要查什么表、导出什么文件、处理哪个业务：ask_clarification。
- 用户要查规则、政策、流程、知识库：rag_query。
- 用户要查 ERP 业务数据：erp_query。
- 用户查本地订单状态：order_query。
- 用户申请退款或高风险退款审批：refund_request。
- 财务要生成财务报表、财务月报、经营汇总表，或一句话里同时要财务报表和工资表：finance_compound_report_generation。
- 财务要导出员工工资表/工资单 Excel：finance_salary_export。
- 财务要生成工资表并通过个人微信/微信发送给联系人：finance_salary_wechat_send。
- 运营要生成/上传/保存 Listing 或上架草稿：operations_listing_draft。
- 客服要根据客户消息自动回复/保存回复草稿：customer_service_reply_draft。
- 明确要求做不属于当前岗位的业务动作：仍然输出该业务动作对应 action，不要自己拒绝；后端权限闸门会拒绝。

必须只返回 JSON 对象，字段只能包含：
action, requested_position, confidence, reason, clarification_question。
不要输出 Markdown，不要输出解释。
""".strip(),
    ),
    (
        "human",
        """
当前用户岗位：{position_label}
当前用户消息：{message}

请返回 JSON。
""".strip(),
    ),
])


_decision_chain = REACT_PROMPT | chat_model.with_structured_output(ChatReActDecision)


def decide_chat_action(message: str, current_user: dict) -> ChatReActDecision:
    text = " ".join((message or "").split())
    if not text:
        return ChatReActDecision(
            action="ask_clarification",
            requested_position="unknown",
            confidence=1,
            reason="用户消息为空",
            clarification_question="请告诉我你想处理什么业务，例如查询订单、导出工资表或生成 Listing 草稿。",
        )

    deterministic = _deterministic_decision(text)
    if deterministic and deterministic.confidence >= 0.92:
        return deterministic

    try:
        decision = _decision_chain.invoke({
            "position_label": POSITION_LABELS.get(str(current_user.get("position")), "管理员/未绑定岗位"),
            "message": text,
        })
    except Exception:
        return deterministic or _fallback_decision(text)

    if decision.action == "ask_clarification" and not decision.clarification_question:
        decision.clarification_question = _default_clarification(decision.requested_position)
    if decision.action != "ask_clarification":
        decision.clarification_question = None

    return _normalize_decision(decision, text)


def forced_graph_intent_for_action(action: str) -> str | None:
    mapping = {
        "chitchat": "chitchat",
        "rag_query": "policy",
        "erp_query": "erp",
        "order_query": "order",
        "refund_request": "refund",
    }
    return mapping.get(action)


def permission_denial_for_decision(decision: ChatReActDecision, current_user: dict) -> str | None:
    if current_user.get("role") == "admin":
        return None

    position = current_user.get("position")
    action_positions = {
        "operations_listing_draft": "operations",
        "customer_service_reply_draft": "customer_service",
        "finance_compound_report_generation": "finance",
        "finance_salary_export": "finance",
        "finance_salary_wechat_send": "finance",
    }
    required_position = action_positions.get(decision.action)
    if required_position and required_position != position:
        return _denial_message(position, required_position, decision.action)

    if decision.requested_position != "unknown" and decision.requested_position != position:
        return _denial_message(position, decision.requested_position, decision.action)

    return None


def _deterministic_decision(text: str) -> ChatReActDecision | None:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)

    if compact in {"你好", "您好", "hi", "hello", "在吗", "早上好", "下午好", "晚上好"}:
        return ChatReActDecision(
            action="chitchat",
            requested_position="unknown",
            confidence=0.98,
            reason="问候寒暄",
        )

    if _looks_like_listing(text):
        return ChatReActDecision(
            action="operations_listing_draft",
            requested_position="operations",
            confidence=0.95,
            reason="用户要求生成或保存 Listing/上架草稿",
        )

    compound_intent = recognize_finance_compound_intent(text)
    if should_handle_finance_compound_generation(compound_intent) and compound_intent.confidence >= 0.78:
        return ChatReActDecision(
            action="finance_compound_report_generation",
            requested_position="finance",
            confidence=max(compound_intent.confidence, 0.94),
            reason="用户要求生成财务报表或同时生成多份财务资料",
        )

    if _looks_like_salary_wechat_send(text):
        return ChatReActDecision(
            action="finance_salary_wechat_send",
            requested_position="finance",
            confidence=0.96,
            reason="用户要求生成工资表并准备通过微信发送",
        )

    if _looks_like_salary_export(text):
        return ChatReActDecision(
            action="finance_salary_export",
            requested_position="finance",
            confidence=0.95,
            reason="用户要求导出员工工资表 Excel",
        )

    if _looks_like_ambiguous_excel(text):
        return ChatReActDecision(
            action="ask_clarification",
            requested_position="finance",
            confidence=0.94,
            reason="只说明导出 Excel，但未说明表类型",
            clarification_question="你需要导出哪一类财务 Excel？例如员工工资表、销售发票、总账分录、收付款单或采购发票。",
        )

    if _looks_like_customer_reply(text):
        return ChatReActDecision(
            action="customer_service_reply_draft",
            requested_position="customer_service",
            confidence=0.93,
            reason="用户要求处理客户消息或生成客服回复",
        )

    return None


def _fallback_decision(text: str) -> ChatReActDecision:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["erp", "工资", "发票", "总账", "收付款", "销售订单", "物流", "工单", "sku"]):
        return ChatReActDecision(action="erp_query", requested_position="unknown", confidence=0.62, reason="规则兜底识别为 ERP 查询")
    if any(keyword in lowered for keyword in ["退款", "退货", "refund"]):
        return ChatReActDecision(action="refund_request", requested_position="customer_service", confidence=0.62, reason="规则兜底识别为退款售后")
    if any(keyword in lowered for keyword in ["规则", "政策", "流程", "多久到账", "怎么开"]):
        return ChatReActDecision(action="rag_query", requested_position="unknown", confidence=0.62, reason="规则兜底识别为知识库查询")
    return ChatReActDecision(action="chitchat", requested_position="unknown", confidence=0.55, reason="无法明确业务动作，按普通对话处理")


def _normalize_decision(decision: ChatReActDecision, text: str) -> ChatReActDecision:
    compound_intent = recognize_finance_compound_intent(text)
    if should_handle_finance_compound_generation(compound_intent) and decision.action in {
        "finance_salary_export",
        "finance_salary_wechat_send",
        "erp_query",
        "rag_query",
        "chitchat",
    }:
        return ChatReActDecision(
            action=FINANCE_COMPOUND_INTENT,
            requested_position="finance",
            confidence=max(decision.confidence, compound_intent.confidence, 0.9),
            reason="规则纠正为财务报表/多财务表生成请求",
        )

    if decision.action == "finance_salary_export" and _looks_like_salary_wechat_send(text):
        return ChatReActDecision(
            action="finance_salary_wechat_send",
            requested_position="finance",
            confidence=max(decision.confidence, 0.93),
            reason="规则纠正为工资表微信发送准备",
        )

    if decision.action == "finance_salary_export" and not _looks_like_salary_export(text):
        if _looks_like_ambiguous_excel(text):
            return ChatReActDecision(
                action="ask_clarification",
                requested_position="finance",
                confidence=max(decision.confidence, 0.9),
                reason="导出表格需求不够明确",
                clarification_question="你需要导出哪一类财务 Excel？例如员工工资表、销售发票、总账分录、收付款单或采购发票。",
            )

    return decision


def _looks_like_listing(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["listing", "标题", "五点", "关键词", "促销文案", "上架", "保存草稿", "上传草稿"])


def _looks_like_salary_export(text: str) -> bool:
    lowered = text.lower()
    has_salary = any(keyword in lowered for keyword in ["工资", "薪资", "薪水", "薪酬", "工资表", "工资单", "salary", "payroll"])
    has_export = any(keyword in lowered for keyword in ["导出", "生成", "下载", "excel", "xlsx", "表", "发给我", "发送"])
    return has_salary and has_export


def _looks_like_salary_wechat_send(text: str) -> bool:
    lowered = text.lower()
    has_salary_export = _looks_like_salary_export(text)
    has_wechat = any(keyword in lowered for keyword in ["微信", "个人微信", "wechat", "weixin"])
    has_send = any(keyword in lowered for keyword in ["发送", "发给", "传给", "转发", "send"])
    return has_salary_export and has_wechat and has_send


def _looks_like_ambiguous_excel(text: str) -> bool:
    lowered = text.lower()
    wants_excel = any(keyword in lowered for keyword in ["excel", "xlsx", "表格", "导出", "生成表", "下载表"])
    has_specific_table = any(keyword in lowered for keyword in ["工资", "薪资", "薪水", "薪酬", "财务报表", "发票", "总账", "收付款", "采购", "销售", "利润", "对账"])
    return wants_excel and not has_specific_table


def _looks_like_customer_reply(text: str) -> bool:
    lowered = text.lower()
    has_customer = any(keyword in lowered for keyword in ["客户", "买家", "客服", "customer", "buyer", "回复", "自动回复", "话术"])
    has_topic = any(keyword in lowered for keyword in ["物流", "退款", "退货", "换货", "优惠码", "发货", "tracking", "refund", "return", "reply"])
    return has_customer and has_topic


def _default_clarification(position: str) -> str:
    if position == "finance":
        return "请说明你要导出或分析哪一类财务数据，例如工资表、销售发票、总账分录、收付款单或采购发票。"
    if position == "operations":
        return "请说明要处理哪个商品、SKU、站点，以及需要生成 Listing、标题、五点描述还是完整上架草稿。"
    if position == "customer_service":
        return "请提供客户问题、订单号或物流单号，并说明是要自动回复、退款售后还是转人工。"
    return "请再说明具体要处理什么业务，以及需要查询、生成文件还是保存草稿。"


def _denial_message(current_position: str | None, required_position: str, action: str) -> str:
    current_label = POSITION_LABELS.get(str(current_position), "当前")
    required_label = POSITION_LABELS.get(required_position, required_position)
    action_labels = {
        "operations_listing_draft": "生成 Listing 或上架草稿",
        "customer_service_reply_draft": "处理客服自动回复",
        "finance_compound_report_generation": "生成财务报表或多份财务资料",
        "finance_salary_export": "导出财务工资表",
        "finance_salary_wechat_send": "准备通过微信发送工资表",
    }
    action_label = action_labels.get(action, f"{required_label}岗位业务")
    return (
        f"{current_label}岗位没有权限执行“{action_label}”。"
        f"这个需求属于{required_label}岗位权限范围，请联系管理员调整账号权限，或让{required_label}岗位账号处理。"
    )
