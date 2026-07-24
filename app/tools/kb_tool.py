from langchain_core.tools import tool

from app.rag.qa import answer_question


@tool
def search_knowledge_base(
    query: str,
    role: str = "employee",
    user_id: str | None = None,
    department: str | None = None,
    position: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    max_sensitivity_level: str | None = None,
) -> dict:
    """查询公司知识库。适合回答退款规则、发票规则、报销制度、会员政策、售后流程等规则类问题。"""
    return answer_question(
        question=query,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
        top_k=5,
    )
