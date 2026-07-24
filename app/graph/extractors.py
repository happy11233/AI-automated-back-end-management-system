from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.llm import chat_model


class OrderNoResult(BaseModel):
    order_no: str | None = Field(
        default=None,
        description="用户问题中的订单号。如果没有订单号，返回 null。",
    )


order_no_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
你是企业客服系统的信息抽取器。

你的任务是从用户问题中提取订单号。
如果用户没有提供订单号，order_no 返回 null。
只返回 JSON 结构化结果，不要解释。JSON 对象中只能包含 order_no 字段。
""".strip(),
    ),
    (
        "human",
        "{user_input}",
    ),
])


order_no_chain = order_no_prompt | chat_model.with_structured_output(OrderNoResult)


def extract_order_no_from_text(user_input: str) -> str | None:
    try:
        result = order_no_chain.invoke({
            "user_input": user_input,
        })
    except Exception:
        return _extract_order_no_by_rules(user_input)

    return result.order_no


def _extract_order_no_by_rules(user_input: str) -> str | None:
    import re

    patterns = [
        r"\bAMZ-[A-Z0-9-]+\b",
        r"\b\d{5,24}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_input, re.I)
        if match:
            return match.group(0)
    return None
