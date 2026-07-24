from typing import NotRequired, TypedDict


class AgentState(TypedDict):
    user_input: str
    user_id: str
    role: str
    username: NotRequired[str]
    department: NotRequired[str]
    position: NotRequired[str]
    market_scope: NotRequired[str]
    store_scope: NotRequired[str]
    field_scope: NotRequired[str]
    max_sensitivity_level: NotRequired[str]
    thread_id: NotRequired[str]
    context: NotRequired[dict]
    context_text: NotRequired[str]
    intent: NotRequired[str]
    forced_intent: NotRequired[str]
    react_decision: NotRequired[dict]
    order_no: NotRequired[str]
    order_result: NotRequired[dict]
    erp_resource: NotRequired[str]
    erp_result: NotRequired[dict]
    rag_result: NotRequired[dict]
    risk_level: NotRequired[str]
    approval_result: NotRequired[dict]
    answer: NotRequired[str]
