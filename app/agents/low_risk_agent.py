from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from app.llm import chat_model
from app.rag.qa import answer_question
from app.services.context_service import format_context_for_prompt
from app.tools.order_tool import query_order_status_for_user


agent_checkpointer = InMemorySaver()


def build_user_tools(current_user: dict):
    @tool
    def search_knowledge_base(query: str) -> dict:
        """查询当前登录用户有权限访问的公司知识库。适合回答规则、政策、流程、报销、退款时效等问题。"""
        return answer_question(
            question=query,
            role=current_user["role"],
            department=current_user.get("department"),
            top_k=5,
        )

    @tool
    def get_order_status(order_no: str) -> dict:
        """查询当前登录用户有权限查看的订单状态、金额和是否可退款。"""
        return query_order_status_for_user(
            order_no=order_no,
            user_id=current_user["id"],
            role=current_user["role"],
        )

    return [
        search_knowledge_base,
        get_order_status,
    ]


def run_low_risk_agent(
    message: str,
    thread_id: str,
    current_user: dict,
    context: dict | None = None,
) -> dict:
    agent = create_agent(
        model=chat_model,
        tools=build_user_tools(current_user),
        system_prompt="""
你是公司客服助手。

你只能处理低风险问题：
1. 查询公司知识库。
2. 查询订单状态。
3. 根据工具返回结果回答用户。

如果用户要求退款、特殊退款、改价、删除数据、审批通过等高风险操作，
不要执行任何操作，只回答：该请求需要走公司审批流程。
不要编造工具没有返回的信息。
""".strip(),
        checkpointer=agent_checkpointer,
    )

    scoped_thread_id = f"{current_user['id']}:{thread_id}"

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "以下是当前会话的持久化上下文，请只作为辅助信息使用：\n"
                        f"{format_context_for_prompt(context or {})}"
                    ),
                },
                {
                    "role": "user",
                    "content": message,
                }
            ]
        },
        config={
            "configurable": {
                "thread_id": scoped_thread_id,
            }
        },
    )

    last_message = result["messages"][-1]

    return {
        "answer": last_message.content,
        "messages": result["messages"],
    }
