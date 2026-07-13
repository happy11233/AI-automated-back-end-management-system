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
只返回结构化结果，不要解释。
""".strip(),
    ),
    (
        "human",
        "{user_input}",
    ),
])


order_no_chain = order_no_prompt | chat_model.with_structured_output(OrderNoResult)


def extract_order_no_from_text(user_input: str) -> str | None:
    result = order_no_chain.invoke({
        "user_input": user_input,
    })

    return result.order_no