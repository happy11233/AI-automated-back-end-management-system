import jieba

from app.config import settings


def rerank_chunks(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    query_tokens = set(tokenize(query))

    reranked = []

    for chunk in chunks:
        content_tokens = set(tokenize(chunk["content"]))
        overlap_score = _overlap_score(query_tokens, content_tokens)
        vector_score = float(chunk.get("vector_score") or 0)
        keyword_score = float(chunk.get("keyword_score") or 0)
        score = (
            settings.rag_rerank_vector_weight * vector_score
            + settings.rag_rerank_keyword_weight * keyword_score
            + settings.rag_rerank_overlap_weight * overlap_score
        )

        reranked.append({
            **chunk,
            "score": score,
            "rerank_score": score,
            "overlap_score": overlap_score,
        })

    return sorted(
        reranked,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )[:top_k]


def tokenize(text: str) -> list[str]:
    return [
        token.strip().lower()
        for token in jieba.lcut(text)
        if token.strip()
    ]


def _overlap_score(query_tokens: set[str], content_tokens: set[str]) -> float:
    if not query_tokens or not content_tokens:
        return 0.0

    return len(query_tokens & content_tokens) / len(query_tokens)
