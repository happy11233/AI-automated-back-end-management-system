from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    user_input: str
    user_id: str
    role: str
    username: NotRequired[str]
    department: NotRequired[str]
    position: NotRequired[str]
    thread_id: NotRequired[str]
    context: NotRequired[dict]
    context_text: NotRequired[str]
    intent: NotRequired[str]
    order_no: NotRequired[str]
    order_result: NotRequired[dict]
    erp_resource: NotRequired[str]
    erp_result: NotRequired[dict]
    rag_result: NotRequired[dict]
    risk_level: NotRequired[str]
    approval_result: NotRequired[dict]
    answer: NotRequired[str]
