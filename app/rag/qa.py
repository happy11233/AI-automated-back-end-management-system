from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.llm import chat_model
from app.rag.retriever import retrieve_chunks

rag_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
你是公司客服知识库助手。

请严格根据【资料】回答用户问题。
如果资料中没有答案，必须回答：资料中没有找到相关信息。
不要编造资料中没有的信息。
回答要简洁、准确。
""".strip(),
    ),
    (
        "human",
        """
【资料】
{context}

【用户问题】
{question}
""".strip(),
    ),
])


rag_chain = rag_prompt | chat_model | StrOutputParser()

def format_context(chunks: list[dict]) -> str:
    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[资料{index}]\n"
            f"标题：{chunk['title']}\n"
            f"来源：{chunk['source']}\n"
            f"内容：{chunk['content']}"
        )

    return "\n\n".join(context_parts)


def build_citations(chunks: list[dict]) -> list[dict]:
    citations = []
    seen = set()

    for chunk in chunks:
        key = (chunk["title"], chunk["source"])

        if key in seen:
            continue

        seen.add(key)

        citations.append({
            "title": chunk["title"],
            "source": chunk["source"],
            "visibility": chunk["visibility"],
            "department": chunk.get("department"),
            "position_scope": chunk.get("position_scope"),
            "market_scope": chunk.get("market_scope"),
            "store_scope": chunk.get("store_scope"),
            "field_scope": chunk.get("field_scope"),
            "sensitivity_level": chunk.get("sensitivity_level"),
            "score": chunk["score"],
            "retrieval_sources": chunk.get("retrieval_sources", []),
        })

    return citations


def answer_question(
    question: str,
    role: str,
    top_k: int = 5,
    user_id: str | None = None,
    department: str | None = None,
    position: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    max_sensitivity_level: str | None = None,
) -> dict:
    chunks = retrieve_chunks(
        question,
        role=role,
        top_k=top_k,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )

    if not chunks:
        return {
            "answer": "资料中没有找到相关信息。",
            "citations": [],
            "chunks": [],
        }

    context = format_context(chunks)

    answer = rag_chain.invoke({
        "context": context,
        "question": question,
    })

    citations = build_citations(chunks)

    return {
        "answer": answer,
        "citations": citations,
        "chunks": chunks,
        "retrieval": {
            "top_k": top_k,
            "department": department,
            "position": position,
            "market_scope": market_scope,
            "store_scope": store_scope,
            "field_scope": field_scope,
            "max_sensitivity_level": max_sensitivity_level,
            "chunk_count": len(chunks),
        },
    }
