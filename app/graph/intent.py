from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from app.llm import chat_model


class IntentResult(BaseModel):
    intent: Literal["policy", "order", "refund", "chitchat"] = Field(
        description=(
            "用户意图。"
            "policy=咨询规则知识库；"
            "order=查询订单状态；"
            "refund=退款或售后退款相关请求；"
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

你只能把用户问题分类成下面四类之一：

policy：用户在咨询规则、政策、流程、知识库内容，例如退款多久到账、发票怎么开、报销规则。
order：用户只是在查询订单状态、物流状态、订单是否签收。
refund：用户想申请退款、特殊退款、取消订单退款，或者询问某个订单能不能退款。
chitchat：用户在问候、寒暄、感谢、说再见、闲聊，例如你好、谢谢、你是谁、早上好。

必须只返回结构化结果，intent 字段只能是 policy、order、refund、chitchat 之一。
""".strip(),
    ),
    (
        "human",
        "{user_input}",
    ),
])


intent_chain = intent_prompt | chat_model.with_structured_output(IntentResult)


def classify_user_intent(user_input: str) -> str:
    result = intent_chain.invoke({
        "user_input": user_input,
    })

    return result.intent
