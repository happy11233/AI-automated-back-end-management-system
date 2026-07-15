from typing import Literal
from langgraph.graph import END, START, StateGraph
from app.graph.state import AgentState
from app.tools.order_tool import query_order_status_for_user
from uuid import uuid4
from app.tools.approval_tool import submit_approval_request
from app.graph.intent import classify_user_intent
from app.graph.extractors import extract_order_no_from_text
from app.tools.kb_tool import search_knowledge_base
from app.services.context_service import format_context_for_prompt
from app.services.erp_service import query_erp_for_current_user, summarize_erp_items
from app.llm import chat_model


CHITCHAT_SYSTEM_PROMPT = """
你是企业客服助手。

用户当前是在闲聊或寒暄。
请用中文自然、简短地回复用户。
不要查询知识库，不要编造订单信息，不要承诺退款或审批结果。
如果用户只是问候，例如“你好”，回复一句友好的问候并提示可以继续咨询订单、退款或规则问题。
""".strip()

def classify_intent(state: AgentState) -> dict:
    intent = classify_user_intent(state["user_input"])
    return {"intent": intent}

def extract_order_no(state: AgentState) -> dict:
    order_no = extract_order_no_from_text(state["user_input"])
    state_order_no = state.get("context", {}).get("state", {}).get("order_no")

    if not order_no:
        return {"order_no": state_order_no} if state_order_no else {}

    return {"order_no": order_no}

def query_order(state: AgentState) -> dict:
    order_no = state.get("order_no")

    if not order_no:
        return {
            "order_result": {
                "found": False,
                "message": "没有识别到订单号。",
            }
        }

    result = query_order_status_for_user(
        order_no=order_no,
        user_id=state["user_id"],
        role=state["role"],
    )
    return {"order_result": result}

def retrieve_policy(state: AgentState) -> dict:
    query = _build_contextual_query(state)
    result = search_knowledge_base.invoke({
        "query": query,
        "role": state["role"],
        "department": state.get("department"),
    })

    return {"rag_result": result}

def query_erp(state: AgentState) -> dict:
    query = _build_contextual_query(state)
    result = query_erp_for_current_user(
        user_input=state["user_input"],
        current_user={
            "id": state["user_id"],
            "role": state["role"],
            "position": state.get("position"),
            "department": state.get("department"),
            "username": state.get("username"),
        },
        query=query,
        limit=5,
        source="chat",
        thread_id=state.get("thread_id"),
    )

    if result.get("items"):
        result["summary"] = summarize_erp_items(
            result.get("resource") or "",
            result["items"],
        )

    return {"erp_result": result, "erp_resource": result.get("resource")}

def submit_approval(state: AgentState) -> dict:
    thread_id = state.get("thread_id") or f"local-{uuid4()}"
    order_result = state.get("order_result", {})

    payload = {
        "user_input": state["user_input"],
        "order_no": state.get("order_no"),
        "order_result": order_result,
        "risk_level": state.get("risk_level"),
        "context": state.get("context", {}),
    }

    approval_result = submit_approval_request.invoke({
        "thread_id": thread_id,
        "requested_by": state.get("user_id"),
        "action_type": "refund",
        "payload": payload,
    })

    return {
        "thread_id": thread_id,
        "approval_result": approval_result,
    }

def risk_check(state: AgentState) -> dict:
    if state.get("intent") != "refund":
        return {"risk_level": "low"}

    order_result = state.get("order_result", {})

    if not order_result.get("found"):
        return {"risk_level": "low"}

    if order_result.get("refundable") is False:
        return {"risk_level": "low"}

    return {"risk_level": "high"}

def generate_answer(state: AgentState) -> dict:
    intent = state.get("intent")

    if intent == "policy":
        return {
            "answer": state.get("rag_result", {}).get(
                "answer",
                "资料中没有找到相关信息。",
            )
        }

    if intent == "order":
        return {
            "answer": state.get("order_result", {}).get(
                "message",
                "没有找到订单信息。",
            )
        }

    if intent == "refund":
        order_message = state.get("order_result", {}).get("message", "")
        policy_answer = state.get("rag_result", {}).get("answer", "")

        if state.get("risk_level") == "high":
            approval_message = state.get("approval_result", {}).get(
                "message",
                "已提交人工审批。",
            )

            return {
                "answer": (
                    f"{order_message}\n"
                    f"{policy_answer}\n"
                    f"该请求涉及退款操作，需要人工审批。{approval_message}"
                )}

        return {
            "answer": (
                f"{order_message}\n"
                f"{policy_answer}"
            ).strip()
        }

    if intent == "erp":
        erp_result = state.get("erp_result", {})
        summary = erp_result.get("summary") or erp_result.get("message") or "ERP 查询暂时没有结果。"
        return {
            "answer": summary,
        }

    if intent == "chitchat":
        response = chat_model.invoke([
            ("system", CHITCHAT_SYSTEM_PROMPT),
            ("human", state["user_input"]),
        ])
        return {"answer": response.content}

    return {"answer": "我暂时无法处理这个问题。"}


def prepare_context(state: AgentState) -> dict:
    context = state.get("context") or {}
    return {
        "context_text": format_context_for_prompt(context),
    }


def _build_contextual_query(state: AgentState) -> str:
    context_state = state.get("context", {}).get("state", {})
    order_no = state.get("order_no") or context_state.get("order_no")

    if not order_no:
        return state["user_input"]

    return f"{state['user_input']}\n当前订单号：{order_no}"
#路由函数
def route_by_intent(state: AgentState) -> Literal[
    "retrieve_policy",
    "extract_order_no",
    "query_erp",
    "generate_answer",
]:
    if state["intent"] == "policy":
        return "retrieve_policy"

    if state["intent"] == "erp":
        return "query_erp"

    if state["intent"] == "chitchat":
        return "generate_answer"

    if state["intent"] == "refund":
        return "extract_order_no"

    return "extract_order_no"

def route_by_risk(state: AgentState) -> Literal[
    "submit_approval",
    "generate_answer",
]:
    if state.get("risk_level") == "high":
        return "submit_approval"

    return "generate_answer"

def route_after_order(state: AgentState) -> Literal[
    "generate_answer",
    "retrieve_policy",
]:
    if state["intent"] == "order":
        return "generate_answer"

    return "retrieve_policy"

#组装图
def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("prepare_context", prepare_context)
    builder.add_node("submit_approval", submit_approval)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("extract_order_no", extract_order_no)
    builder.add_node("query_order", query_order)
    builder.add_node("retrieve_policy", retrieve_policy)
    builder.add_node("query_erp", query_erp)
    builder.add_node("risk_check", risk_check)
    builder.add_node("generate_answer", generate_answer)

    builder.add_edge(START, "prepare_context")
    builder.add_edge("prepare_context", "classify_intent")
    builder.add_conditional_edges("classify_intent", route_by_intent)
    builder.add_edge("extract_order_no", "query_order")
    builder.add_conditional_edges("query_order", route_after_order)
    builder.add_edge("query_erp", "generate_answer")
    builder.add_edge("retrieve_policy", "risk_check")
    builder.add_conditional_edges("risk_check", route_by_risk)
    builder.add_edge("submit_approval", "generate_answer")
    builder.add_edge("generate_answer", END)

    return builder.compile()


graph = build_graph()
