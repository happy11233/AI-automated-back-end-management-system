import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.llm import chat_model


query_rewrite_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
你是企业知识库检索优化器。

请把用户问题改写成多个适合检索的中文查询。
要求：
1. 保留原始问题的核心意思。
2. 可以补充常见同义说法。
3. 只返回 JSON 数组字符串，不要解释。
""".strip(),
    ),
    (
        "human",
        "用户问题：{question}\n最多返回 {count} 个查询。",
    ),
])

query_rewrite_chain = query_rewrite_prompt | chat_model | StrOutputParser()


LOCAL_SYNONYMS = {
    "退款": ["退货退款", "售后退款", "退款申请"],
    "发票": ["开票", "电子发票", "票据"],
    "报销": ["费用报销", "报销流程", "报销规则"],
    "订单": ["物流", "配送", "订单状态"],
    "审批": ["审核", "人工审批", "负责人审批"],
}


def build_query_variants(question: str, count: int | None = None) -> list[str]:
    max_count = count or settings.rag_multi_query_count
    variants = [question]

    if settings.rag_enable_llm_query_rewrite:
        variants.extend(_build_llm_variants(question, max_count))

    variants.extend(_build_local_variants(question))

    return _dedupe_preserve_order(variants)[:max_count]


def _build_llm_variants(question: str, count: int) -> list[str]:
    try:
        raw = query_rewrite_chain.invoke({
            "question": question,
            "count": count,
        })
        parsed = json.loads(raw)
    except Exception:
        return []

    if not isinstance(parsed, list):
        return []

    return [
        item.strip()
        for item in parsed
        if isinstance(item, str) and item.strip()
    ]


def _build_local_variants(question: str) -> list[str]:
    variants = []

    for keyword, synonyms in LOCAL_SYNONYMS.items():
        if keyword not in question:
            continue

        for synonym in synonyms:
            variants.append(question.replace(keyword, synonym))

    return variants


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    deduped = []

    for value in values:
        normalized = value.strip()

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        deduped.append(normalized)

    return deduped
