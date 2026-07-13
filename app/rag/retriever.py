from rank_bm25 import BM25Okapi

from app.config import settings
from app.db import fetch_all
from app.rag.query_rewrite import build_query_variants
from app.rag.reranker import rerank_chunks, tokenize
from app.rag.vector_store import vector_store


def build_metadata_filter(role: str, department: str | None = None) -> dict:
    visibility_filter = (
        {"visibility": {"$in": ["employee", "admin"]}}
        if role == "admin"
        else {"visibility": {"$eq": "employee"}}
    )

    if role == "admin" or not department:
        return visibility_filter

    return {
        "$and": [
            visibility_filter,
            {
                "$or": [
                    {"department": {"$eq": department}},
                    {"department": {"$eq": ""}},
                    {"department": {"$exists": False}},
                ]
            },
        ]
    }


def retrieve_chunks(
    query: str,
    role: str,
    top_k: int = 5,
    department: str | None = None,
) -> list[dict]:
    final_top_k = top_k or settings.rag_final_top_k
    query_variants = build_query_variants(
        question=query,
        count=settings.rag_multi_query_count,
    )

    vector_chunks = _retrieve_vector_candidates(
        queries=query_variants,
        role=role,
        department=department,
        candidate_k=settings.rag_vector_candidate_k,
    )
    keyword_chunks = _retrieve_keyword_candidates(
        query=query,
        role=role,
        department=department,
        candidate_k=settings.rag_keyword_candidate_k,
    )
    fused_chunks = _fuse_candidates(vector_chunks, keyword_chunks)
    thresholded_chunks = [
        chunk
        for chunk in fused_chunks
        if chunk["score"] >= settings.rag_min_score
    ]
    reranked_chunks = rerank_chunks(
        query=query,
        chunks=thresholded_chunks,
        top_k=final_top_k,
    )

    return _replace_with_parent_chunks(reranked_chunks)


def _retrieve_vector_candidates(
    queries: list[str],
    role: str,
    department: str | None,
    candidate_k: int,
) -> list[dict]:
    metadata_filter = build_metadata_filter(role=role, department=department)
    candidates = []

    for query_index, query in enumerate(queries):
        results = vector_store.similarity_search_with_score(
            query=query,
            k=candidate_k,
            filter=metadata_filter,
        )

        for rank, (doc, distance) in enumerate(results, start=1):
            metadata = doc.metadata or {}
            vector_score = _distance_to_score(float(distance))

            candidates.append({
                "chunk_id": metadata.get("chunk_id", ""),
                "parent_chunk_id": metadata.get("parent_chunk_id"),
                "document_id": metadata.get("document_id", ""),
                "content": doc.page_content,
                "title": metadata.get("title", ""),
                "source": metadata.get("source", ""),
                "visibility": metadata.get("visibility", ""),
                "department": metadata.get("department"),
                "score": vector_score,
                "vector_score": vector_score,
                "keyword_score": 0.0,
                "distance": float(distance),
                "rank": rank,
                "retrieval_sources": ["vector"],
                "matched_query": query,
                "query_index": query_index,
            })

    return candidates


def _retrieve_keyword_candidates(
    query: str,
    role: str,
    department: str | None,
    candidate_k: int,
) -> list[dict]:
    rows = _load_keyword_corpus(role=role, department=department)

    if not rows:
        return []

    tokenized_corpus = [tokenize(row["content"]) for row in rows]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenize(query))

    scored_rows = sorted(
        zip(rows, scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    max_score = float(scored_rows[0][1]) if scored_rows else 0.0

    candidates = []

    for rank, (row, raw_score) in enumerate(scored_rows[:candidate_k], start=1):
        keyword_score = _normalize_keyword_score(float(raw_score), max_score)

        if keyword_score <= 0:
            continue

        candidates.append({
            **row,
            "score": keyword_score,
            "vector_score": 0.0,
            "keyword_score": keyword_score,
            "distance": None,
            "rank": rank,
            "retrieval_sources": ["keyword"],
            "matched_query": query,
            "query_index": 0,
        })

    return candidates


def _load_keyword_corpus(role: str, department: str | None) -> list[dict]:
    params: list[str] = []
    where_parts = []

    if role != "admin":
        where_parts.append("d.visibility = 'employee'")

        if department:
            where_parts.append("(d.department = %s OR d.department IS NULL OR d.department = '')")
            params.append(department)

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    rows = fetch_all(
        f"""
        SELECT
            c.id,
            c.parent_chunk_id,
            c.document_id,
            c.content,
            d.title,
            d.source,
            d.visibility,
            d.department
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        {where_sql}
        ORDER BY c.created_at DESC;
        """,
        tuple(params),
    )

    return [
        {
            "chunk_id": str(row[0]),
            "parent_chunk_id": str(row[1]) if row[1] else None,
            "document_id": str(row[2]),
            "content": row[3],
            "title": row[4],
            "source": row[5],
            "visibility": row[6],
            "department": row[7],
        }
        for row in rows
    ]


def _fuse_candidates(vector_chunks: list[dict], keyword_chunks: list[dict]) -> list[dict]:
    fused: dict[str, dict] = {}

    for candidate in vector_chunks + keyword_chunks:
        key = candidate.get("chunk_id") or f"{candidate['source']}:{candidate['content']}"

        if key not in fused:
            fused[key] = {
                **candidate,
                "rrf_score": 0.0,
                "retrieval_sources": [],
            }

        existing = fused[key]
        existing["vector_score"] = max(
            float(existing.get("vector_score") or 0),
            float(candidate.get("vector_score") or 0),
        )
        existing["keyword_score"] = max(
            float(existing.get("keyword_score") or 0),
            float(candidate.get("keyword_score") or 0),
        )
        existing["rrf_score"] += 1 / (60 + int(candidate.get("rank") or 0))

        for source in candidate.get("retrieval_sources", []):
            if source not in existing["retrieval_sources"]:
                existing["retrieval_sources"].append(source)

        existing["score"] = max(
            existing["vector_score"],
            existing["keyword_score"],
            existing["rrf_score"],
        )

    return sorted(
        fused.values(),
        key=lambda item: item["score"],
        reverse=True,
    )


def _replace_with_parent_chunks(chunks: list[dict]) -> list[dict]:
    parent_ids = [
        chunk["parent_chunk_id"]
        for chunk in chunks
        if chunk.get("parent_chunk_id")
    ]

    if not parent_ids:
        return chunks

    placeholders = ", ".join(["%s"] * len(parent_ids))
    parent_rows = fetch_all(
        f"""
        SELECT
            p.id,
            p.content,
            p.metadata,
            d.title,
            d.source,
            d.visibility,
            d.department
        FROM document_parent_chunks p
        JOIN documents d ON d.id = p.document_id
        WHERE p.id IN ({placeholders});
        """,
        tuple(parent_ids),
    )
    parents = {
        str(row[0]): {
            "parent_content": row[1],
            "parent_metadata": row[2] or {},
            "title": row[3],
            "source": row[4],
            "visibility": row[5],
            "department": row[6],
        }
        for row in parent_rows
    }

    enriched = []
    seen_parent_ids = set()

    for chunk in chunks:
        parent_id = chunk.get("parent_chunk_id")
        parent = parents.get(parent_id)

        if parent and parent_id not in seen_parent_ids:
            seen_parent_ids.add(parent_id)
            enriched.append({
                **chunk,
                "child_chunk_id": chunk.get("chunk_id"),
                "chunk_id": parent_id,
                "content": parent["parent_content"],
                "title": parent["title"],
                "source": parent["source"],
                "visibility": parent["visibility"],
                "department": parent["department"],
                "metadata": parent["parent_metadata"],
            })
            continue

        if not parent:
            enriched.append(chunk)

    return enriched


def _distance_to_score(distance: float) -> float:
    return max(0.0, 1.0 - distance)


def _normalize_keyword_score(score: float, max_score: float) -> float:
    if max_score <= 0:
        return 0.0

    return score / max_score
