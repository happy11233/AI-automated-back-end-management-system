from typing import Literal
import re

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.llm import chat_model


class IntentResult(BaseModel):
    intent: Literal["policy", "order", "refund", "erp", "chitchat"] = Field(
        description=(
            "用户意图。"
            "policy=咨询规则知识库；"
            "order=查询订单状态；"
            "refund=退款或售后退款相关请求；"
            "erp=查询 ERP 中的业务数据；"
            "chitchat=问候、寒暄、感谢、闲聊。"
        )
    )


intent_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
你是企业客服系统的意图识别器。

你的唯一任务是判断用户输入属于哪一种意图。
你不能回答用户问题，不能输出解释，不能输出寒暄内容。

你只能把用户问题分类成下面五类之一：

policy：用户在咨询规则、政策、流程、知识库内容，例如退款多久到账、发票怎么开、报销规则。
order：用户只是在查询单笔订单状态、物流状态、是否签收、预计送达时间。
refund：用户想申请退款、特殊退款、取消订单退款，或者询问某个订单能不能退款。
erp：用户想查询 ERP 里的商品、价格、销售订单列表、客户资料、物流单、工单、工资、财务分录、收付款等业务数据。
chitchat：用户在问候、寒暄、感谢、说再见、闲聊，例如你好、谢谢、你是谁、早上好。

必须只返回结构化结果，intent 字段只能是 policy、order、refund、erp、chitchat 之一。
""".strip(),
    ),
    (
        "human",
        "{user_input}",
    ),
])


intent_chain = intent_prompt | chat_model.with_structured_output(IntentResult)


def classify_user_intent(user_input: str) -> str:
    deterministic_intent = _classify_by_rules(user_input)
    if deterministic_intent:
        return deterministic_intent

    result = intent_chain.invoke({
        "user_input": user_input,
    })

    return result.intent


def _classify_by_rules(user_input: str) -> str | None:
    text = user_input.strip().lower()
    if not text:
        return None

    refund_phrases = [
        "申请退款",
        "我要退款",
        "能不能退款",
        "是否可以退款",
        "取消订单退款",
    ]
    if any(phrase in text for phrase in refund_phrases):
        return "refund"

    erp_keywords = [
        "erp",
        "sku",
        "商品",
        "价格",
        "客户",
        "买家",
        "销售订单",
        "销售单",
        "物流",
        "出库",
        "运单",
        "工单",
        "售后",
        "退货请求",
        "工资",
        "发票",
        "总账",
        "收付款",
    ]
    has_amazon_identifier = bool(re.search(r"\bAMZ-[A-Z0-9-]+\b", user_input, re.I))

    if any(keyword in text for keyword in erp_keywords) and (
        "查" in text or "查询" in text or "看" in text or has_amazon_identifier
    ):
        return "erp"

    return None
