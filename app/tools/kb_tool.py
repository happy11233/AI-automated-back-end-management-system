from langchain_core.tools import tool

from app.rag.qa import answer_question


@tool
def search_knowledge_base(
    query: str,
    role: str = "employee",
    department: str | None = None,
) -> dict:
    """查询公司知识库。适合回答退款规则、发票规则、报销制度、会员政策、售后流程等规则类问题。"""
    return answer_question(
        question=query,
        role=role,
        department=department,
        top_k=5,
    )
