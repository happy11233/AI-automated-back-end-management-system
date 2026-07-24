from hashlib import sha256
from typing import Any

from rank_bm25 import BM25Okapi

from app.config import settings
from app.db import fetch_all
from app.rag.ingest import (
    ensure_rag_document_scope_schema,
    field_scopes_for_position,
    sensitivity_levels_for_position,
)
from app.rag.query_rewrite import build_query_variants
from app.rag.reranker import rerank_chunks, tokenize
from app.rag.vector_store import vector_store
from app.services.logging_service import write_audit_log


RAG_AUTHORIZATION_AUDIT_MAX_DOCUMENTS = 10


def build_metadata_filter(
    role: str,
    department: str | None = None,
    position: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    max_sensitivity_level: str | None = None,
) -> dict:
    status_filter = {
        "$or": [
            {"status": {"$eq": "active"}},
            {"status": {"$exists": False}},
        ]
    }
    filters = [
        (
            {"visibility": {"$in": ["employee", "admin"]}}
            if role == "admin"
            else {"visibility": {"$eq": "employee"}}
        ),
        status_filter,
    ]

    if role == "admin":
        return {"$and": filters}

    if department:
        filters.append(
            {
                "$or": [
                    {"department": {"$eq": department}},
                    {"department": {"$eq": ""}},
                    {"department": {"$exists": False}},
                ]
            }
        )

    if position:
        filters.append(
            {
                "$or": [
                    {"position_scope": {"$eq": position}},
                    {"position_scope": {"$eq": ""}},
                    {"position_scope": {"$exists": False}},
                ]
            }
        )
    else:
        filters.append(
            {
                "$or": [
                    {"position_scope": {"$eq": ""}},
                    {"position_scope": {"$exists": False}},
                ]
            }
        )

    if market_scope:
        filters.append(
            {
                "$or": [
                    {"market_scope": {"$eq": market_scope}},
                    {"market_scope": {"$eq": ""}},
                    {"market_scope": {"$exists": False}},
                ]
            }
        )
    else:
        filters.append(
            {
                "$or": [
                    {"market_scope": {"$eq": ""}},
                    {"market_scope": {"$exists": False}},
                ]
            }
        )

    if store_scope:
        filters.append(
            {
                "$or": [
                    {"store_scope": {"$eq": store_scope}},
                    {"store_scope": {"$eq": ""}},
                    {"store_scope": {"$exists": False}},
                ]
            }
        )
    else:
        filters.append(
            {
                "$or": [
                    {"store_scope": {"$eq": ""}},
                    {"store_scope": {"$exists": False}},
                ]
            }
        )

    allowed_field_scopes = field_scopes_for_position(position, field_scope)
    if allowed_field_scopes:
        filters.append(
            {
                "$or": [
                    {"field_scope": {"$in": allowed_field_scopes}},
                    {"field_scope": {"$eq": ""}},
                    {"field_scope": {"$exists": False}},
                ]
            }
        )
    else:
        filters.append(
            {
                "$or": [
                    {"field_scope": {"$eq": ""}},
                    {"field_scope": {"$exists": False}},
                ]
            }
        )

    allowed_sensitivity_levels = sensitivity_levels_for_position(position, max_sensitivity_level)
    filters.append(
        {
            "$or": [
                {"sensitivity_level": {"$in": allowed_sensitivity_levels}},
                {"sensitivity_level": {"$eq": ""}},
                {"sensitivity_level": {"$exists": False}},
            ]
        }
    )

    return {"$and": filters}


def retrieve_chunks(
    query: str,
    role: str,
    top_k: int = 5,
    user_id: str | None = None,
    department: str | None = None,
    position: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    max_sensitivity_level: str | None = None,
) -> list[dict]:
    ensure_rag_document_scope_schema()
    final_top_k = top_k or settings.rag_final_top_k
    audit_collector = (
        _new_authorization_audit_collector()
        if _should_audit_rag_authorization(role=role, user_id=user_id)
        else None
    )
    query_variants = build_query_variants(
        question=query,
        count=settings.rag_multi_query_count,
    )

    vector_chunks = _retrieve_vector_candidates(
        queries=query_variants,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
        candidate_k=settings.rag_vector_candidate_k,
        audit_collector=audit_collector,
    )
    keyword_chunks = _retrieve_keyword_candidates(
        query=query,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
        candidate_k=settings.rag_keyword_candidate_k,
        audit_collector=audit_collector,
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

    final_chunks = _replace_with_parent_chunks(reranked_chunks)
    if audit_collector is not None:
        _write_rag_authorization_audit(
            query=query,
            role=role,
            user_id=user_id,
            department=department,
            position=position,
            market_scope=market_scope,
            store_scope=store_scope,
            field_scope=field_scope,
            max_sensitivity_level=max_sensitivity_level,
            chunks=final_chunks,
            audit_collector=audit_collector,
        )

    return final_chunks


def _retrieve_vector_candidates(
    queries: list[str],
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
    candidate_k: int,
    audit_collector: dict[str, Any] | None = None,
) -> list[dict]:
    metadata_filter = build_metadata_filter(
        role=role,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
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
                "position_scope": metadata.get("position_scope"),
                "market_scope": metadata.get("market_scope"),
                "store_scope": metadata.get("store_scope"),
                "field_scope": metadata.get("field_scope"),
                "sensitivity_level": metadata.get("sensitivity_level"),
                "score": vector_score,
                "vector_score": vector_score,
                "keyword_score": 0.0,
                "distance": float(distance),
                "rank": rank,
                "retrieval_sources": ["vector"],
                "matched_query": query,
                "query_index": query_index,
            })

    return _filter_authorized_candidates(
        candidates,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
        audit_collector=audit_collector,
        audit_source="vector",
    )


def _retrieve_keyword_candidates(
    query: str,
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
    candidate_k: int,
    audit_collector: dict[str, Any] | None = None,
) -> list[dict]:
    rows = _load_keyword_corpus(
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
    if audit_collector is not None:
        _collect_denied_keyword_authorization_candidates(
            query=query,
            role=role,
            user_id=user_id,
            department=department,
            position=position,
            market_scope=market_scope,
            store_scope=store_scope,
            field_scope=field_scope,
            max_sensitivity_level=max_sensitivity_level,
            audit_collector=audit_collector,
        )

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


def _load_keyword_corpus(
    role: str,
    user_id: str | None = None,
    department: str | None = None,
    position: str | None = None,
    market_scope: str | None = None,
    store_scope: str | None = None,
    field_scope: str | None = None,
    max_sensitivity_level: str | None = None,
) -> list[dict]:
    where_parts, params = _build_authorized_document_where(
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
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
            d.department,
            d.position_scope,
            d.market_scope,
            d.store_scope,
            d.field_scope,
            d.sensitivity_level,
            d.owner_user_id,
            d.owner_team_id,
            d.access_mode
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
            "position_scope": row[8],
            "market_scope": row[9],
            "store_scope": row[10],
            "field_scope": row[11],
            "sensitivity_level": row[12],
            "owner_user_id": str(row[13]) if row[13] else None,
            "owner_team_id": str(row[14]) if row[14] else None,
            "access_mode": row[15] or "open",
        }
        for row in rows
    ]


def _build_authorized_document_where(
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
) -> tuple[list[str], list[object]]:
    where_parts, params = _build_base_document_where(
        role=role,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )

    if role == "admin":
        return where_parts, params

    user_team_condition, user_team_params = _build_user_team_authorization_condition(user_id)
    where_parts.append(user_team_condition)
    params.extend(user_team_params)

    return where_parts, params


def _build_base_document_where(
    role: str,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
) -> tuple[list[str], list[object]]:
    params: list[object] = []
    where_parts = ["d.status = 'active'"]

    if role == "admin":
        where_parts.append("d.visibility IN ('employee', 'admin')")
        return where_parts, params

    where_parts.append("d.visibility = 'employee'")

    if department:
        where_parts.append("(d.department = %s OR d.department IS NULL OR d.department = '')")
        params.append(department)

    if position:
        where_parts.append("(d.position_scope = %s OR d.position_scope IS NULL OR d.position_scope = '')")
        params.append(position)
    else:
        where_parts.append("(d.position_scope IS NULL OR d.position_scope = '')")

    if market_scope:
        where_parts.append("(d.market_scope = %s OR d.market_scope IS NULL OR d.market_scope = '')")
        params.append(market_scope)
    else:
        where_parts.append("(d.market_scope IS NULL OR d.market_scope = '')")

    if store_scope:
        where_parts.append("(d.store_scope = %s OR d.store_scope IS NULL OR d.store_scope = '')")
        params.append(store_scope)
    else:
        where_parts.append("(d.store_scope IS NULL OR d.store_scope = '')")

    allowed_field_scopes = field_scopes_for_position(position, field_scope)
    if allowed_field_scopes:
        placeholders = ", ".join(["%s"] * len(allowed_field_scopes))
        where_parts.append(
            f"(d.field_scope IN ({placeholders}) OR d.field_scope IS NULL OR d.field_scope = '')"
        )
        params.extend(allowed_field_scopes)
    else:
        where_parts.append("(d.field_scope IS NULL OR d.field_scope = '')")

    allowed_sensitivity_levels = sensitivity_levels_for_position(position, max_sensitivity_level)
    placeholders = ", ".join(["%s"] * len(allowed_sensitivity_levels))
    where_parts.append(
        f"(d.sensitivity_level IN ({placeholders}) OR d.sensitivity_level IS NULL OR d.sensitivity_level = '')"
    )
    params.extend(allowed_sensitivity_levels)

    return where_parts, params


def _build_user_team_authorization_condition(user_id: str | None) -> tuple[str, list[object]]:
    if not user_id:
        return "COALESCE(d.access_mode, 'open') = 'open'", []

    user_param = str(user_id)
    condition = """
        (
            COALESCE(d.access_mode, 'open') = 'open'
            OR d.owner_user_id = %s::uuid
            OR (
                d.owner_team_id IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM rag_team_memberships rtm
                    JOIN rag_teams rt ON rt.id = rtm.team_id
                    WHERE rtm.team_id = d.owner_team_id
                      AND rtm.user_id = %s::uuid
                      AND rtm.status = 'active'
                      AND rtm.member_role IN ('member', 'supervisor')
                      AND (rtm.expires_at IS NULL OR rtm.expires_at > now())
                      AND rt.status = 'active'
                )
            )
            OR (
                COALESCE(d.access_mode, 'open') IN ('explicit_grants', 'owner_and_grants')
                AND EXISTS (
                    SELECT 1
                    FROM rag_document_access_grants g
                    WHERE g.document_id = d.id
                      AND g.subject_type = 'user'
                      AND g.subject_id = %s::uuid
                      AND g.access_level IN ('read', 'manage')
                      AND g.status = 'active'
                      AND (g.expires_at IS NULL OR g.expires_at > now())
                )
            )
            OR (
                COALESCE(d.access_mode, 'open') IN ('explicit_grants', 'owner_and_grants')
                AND EXISTS (
                    SELECT 1
                    FROM rag_document_access_grants g
                    JOIN rag_team_memberships rtm ON rtm.team_id = g.subject_id
                    JOIN rag_teams rt ON rt.id = rtm.team_id
                    WHERE g.document_id = d.id
                      AND g.subject_type = 'team'
                      AND g.access_level IN ('read', 'manage')
                      AND g.status = 'active'
                      AND (g.expires_at IS NULL OR g.expires_at > now())
                      AND rtm.user_id = %s::uuid
                      AND rtm.status = 'active'
                      AND rtm.member_role IN ('member', 'supervisor')
                      AND (rtm.expires_at IS NULL OR rtm.expires_at > now())
                      AND rt.status = 'active'
                )
            )
        )
    """

    return condition, [user_param, user_param, user_param, user_param]


def _filter_authorized_candidates(
    candidates: list[dict],
    *,
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
    audit_collector: dict[str, Any] | None = None,
    audit_source: str | None = None,
) -> list[dict]:
    if not candidates:
        return []

    document_ids = sorted({
        str(candidate.get("document_id"))
        for candidate in candidates
        if candidate.get("document_id")
    })
    if not document_ids:
        return []

    decisions = _load_authorization_decisions(
        document_ids=document_ids,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
    authorized_documents = {
        document_id: decision
        for document_id, decision in decisions.items()
        if decision["authorization_reason"] != "denied"
    }

    if audit_collector is not None and audit_source:
        for document_id, decision in decisions.items():
            if decision["authorization_reason"] == "denied":
                _add_authorization_audit_candidate(
                    audit_collector=audit_collector,
                    bucket="denied",
                    document_id=document_id,
                    decision=decision,
                    retrieval_source=audit_source,
                )

    return [
        {
            **candidate,
            "owner_user_id": authorized_documents[str(candidate["document_id"])]["owner_user_id"],
            "owner_team_id": authorized_documents[str(candidate["document_id"])]["owner_team_id"],
            "access_mode": authorized_documents[str(candidate["document_id"])]["access_mode"],
            "authorization_reason": authorized_documents[str(candidate["document_id"])]["authorization_reason"],
            "authorization_grant_id": authorized_documents[str(candidate["document_id"])].get("authorization_grant_id"),
        }
        for candidate in candidates
        if str(candidate.get("document_id")) in authorized_documents
    ]


def _load_authorization_decisions(
    *,
    document_ids: list[str],
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
) -> dict[str, dict[str, Any]]:
    if not document_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(document_ids))
    where_parts, params = _build_base_document_where(
        role=role,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
    rows = fetch_all(
        f"""
        SELECT
            d.id,
            d.title,
            d.source,
            d.visibility,
            d.department,
            d.position_scope,
            d.market_scope,
            d.store_scope,
            d.field_scope,
            d.sensitivity_level,
            d.owner_user_id,
            d.owner_team_id,
            COALESCE(d.access_mode, 'open') AS access_mode
        FROM documents d
        WHERE d.id IN ({placeholders})
          AND {' AND '.join(where_parts)};
        """,
        tuple([*document_ids, *params]),
    )
    decisions = {
        str(row[0]): {
            "document_id": str(row[0]),
            "title": row[1],
            "source": row[2],
            "visibility": row[3],
            "department": row[4],
            "position_scope": row[5],
            "market_scope": row[6],
            "store_scope": row[7],
            "field_scope": row[8],
            "sensitivity_level": row[9],
            "owner_user_id": str(row[10]) if row[10] else None,
            "owner_team_id": str(row[11]) if row[11] else None,
            "access_mode": row[12] or "open",
            "authorization_reason": "denied",
            "authorization_grant_id": None,
        }
        for row in rows
    }

    if not decisions:
        return {}

    if role == "admin":
        for decision in decisions.values():
            decision["authorization_reason"] = "admin"
        return decisions

    if not user_id:
        for decision in decisions.values():
            if decision["access_mode"] == "open":
                decision["authorization_reason"] = "open"
        return decisions

    scoped_document_ids = list(decisions.keys())
    active_team_ids = _load_active_team_ids_for_user(user_id)
    user_grants = _load_active_user_grants(
        document_ids=scoped_document_ids,
        user_id=user_id,
    )
    team_grants = _load_active_team_grants(
        document_ids=scoped_document_ids,
        team_ids=active_team_ids,
    )

    for document_id, decision in decisions.items():
        access_mode = decision["access_mode"]
        if access_mode == "open":
            decision["authorization_reason"] = "open"
            continue
        if decision["owner_user_id"] == str(user_id):
            decision["authorization_reason"] = "owner_user"
            continue
        if decision["owner_team_id"] and decision["owner_team_id"] in active_team_ids:
            decision["authorization_reason"] = "owner_team"
            continue
        if access_mode in {"explicit_grants", "owner_and_grants"} and document_id in user_grants:
            decision["authorization_reason"] = "user_grant"
            decision["authorization_grant_id"] = user_grants[document_id]
            continue
        if access_mode in {"explicit_grants", "owner_and_grants"} and document_id in team_grants:
            decision["authorization_reason"] = "team_grant"
            decision["authorization_grant_id"] = team_grants[document_id]["grant_id"]
            decision["authorization_team_id"] = team_grants[document_id]["team_id"]
            continue

    return decisions


def _load_active_team_ids_for_user(user_id: str) -> set[str]:
    rows = fetch_all(
        """
        SELECT rtm.team_id
        FROM rag_team_memberships rtm
        JOIN rag_teams rt ON rt.id = rtm.team_id
        WHERE rtm.user_id = %s::uuid
          AND rtm.status = 'active'
          AND rtm.member_role IN ('member', 'supervisor')
          AND (rtm.expires_at IS NULL OR rtm.expires_at > now())
          AND rt.status = 'active';
        """,
        (str(user_id),),
    )
    return {str(row[0]) for row in rows}


def _load_active_user_grants(*, document_ids: list[str], user_id: str) -> dict[str, str]:
    if not document_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(document_ids))
    rows = fetch_all(
        f"""
        SELECT document_id, id
        FROM rag_document_access_grants
        WHERE document_id IN ({placeholders})
          AND subject_type = 'user'
          AND subject_id = %s::uuid
          AND access_level IN ('read', 'manage')
          AND status = 'active'
          AND (expires_at IS NULL OR expires_at > now())
        ORDER BY created_at DESC;
        """,
        tuple([*document_ids, str(user_id)]),
    )
    grants: dict[str, str] = {}
    for row in rows:
        grants.setdefault(str(row[0]), str(row[1]))
    return grants


def _load_active_team_grants(*, document_ids: list[str], team_ids: set[str]) -> dict[str, dict[str, str]]:
    if not document_ids or not team_ids:
        return {}

    document_placeholders = ", ".join(["%s"] * len(document_ids))
    team_id_list = sorted(team_ids)
    team_placeholders = ", ".join(["%s"] * len(team_id_list))
    rows = fetch_all(
        f"""
        SELECT document_id, id, subject_id
        FROM rag_document_access_grants
        WHERE document_id IN ({document_placeholders})
          AND subject_type = 'team'
          AND subject_id IN ({team_placeholders})
          AND access_level IN ('read', 'manage')
          AND status = 'active'
          AND (expires_at IS NULL OR expires_at > now())
        ORDER BY created_at DESC;
        """,
        tuple([*document_ids, *team_id_list]),
    )
    grants: dict[str, dict[str, str]] = {}
    for row in rows:
        document_id = str(row[0])
        grants.setdefault(
            document_id,
            {
                "grant_id": str(row[1]),
                "team_id": str(row[2]),
            },
        )
    return grants


def _collect_denied_keyword_authorization_candidates(
    *,
    query: str,
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
    audit_collector: dict[str, Any],
) -> None:
    where_parts, params = _build_base_document_where(
        role=role,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
    where_parts.append("COALESCE(d.access_mode, 'open') <> 'open'")
    rows = fetch_all(
        f"""
        SELECT
            c.document_id,
            c.content
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE {' AND '.join(where_parts)}
        ORDER BY c.created_at DESC;
        """,
        tuple(params),
    )
    if not rows:
        return

    tokenized_corpus = [tokenize(row[1]) for row in rows]
    query_tokens = set(tokenize(query))
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(list(query_tokens))
    scored_by_document: dict[str, float] = {}

    for row, content_tokens, raw_score in zip(rows, tokenized_corpus, scores):
        overlap = query_tokens & set(content_tokens)
        if not overlap:
            continue
        overlap_score = len(overlap) / max(1, len(query_tokens))
        score = max(0.0, float(raw_score), overlap_score)
        document_id = str(row[0])
        scored_by_document[document_id] = max(scored_by_document.get(document_id, 0.0), score)

    if not scored_by_document:
        return

    top_document_ids = [
        document_id
        for document_id, _score in sorted(
            scored_by_document.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:RAG_AUTHORIZATION_AUDIT_MAX_DOCUMENTS]
    ]
    decisions = _load_authorization_decisions(
        document_ids=top_document_ids,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )

    for document_id, decision in decisions.items():
        if decision["authorization_reason"] != "denied":
            continue
        _add_authorization_audit_candidate(
            audit_collector=audit_collector,
            bucket="denied",
            document_id=document_id,
            decision=decision,
            retrieval_source="keyword",
            score=scored_by_document.get(document_id),
        )


def _new_authorization_audit_collector() -> dict[str, Any]:
    return {
        "denied": {},
    }


def _should_audit_rag_authorization(*, role: str, user_id: str | None) -> bool:
    return role != "admin" and bool(user_id)


def _add_authorization_audit_candidate(
    *,
    audit_collector: dict[str, Any],
    bucket: str,
    document_id: str,
    decision: dict[str, Any],
    retrieval_source: str,
    score: float | None = None,
) -> None:
    items = audit_collector.setdefault(bucket, {})
    item = items.setdefault(
        document_id,
        {
            **decision,
            "retrieval_sources": [],
            "max_score": None,
        },
    )
    if retrieval_source not in item["retrieval_sources"]:
        item["retrieval_sources"].append(retrieval_source)
    if score is not None:
        item["max_score"] = max(float(item["max_score"] or 0.0), float(score))


def _write_rag_authorization_audit(
    *,
    query: str,
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
    chunks: list[dict],
    audit_collector: dict[str, Any],
) -> None:
    if not _should_audit_rag_authorization(role=role, user_id=user_id):
        return

    query_metadata = _rag_authorization_query_metadata(
        query=query,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
    hit_document_ids = sorted({
        str(chunk.get("document_id"))
        for chunk in chunks
        if chunk.get("document_id") and (chunk.get("access_mode") or "open") != "open"
    })
    hit_decisions = _load_authorization_decisions(
        document_ids=hit_document_ids,
        role=role,
        user_id=user_id,
        department=department,
        position=position,
        market_scope=market_scope,
        store_scope=store_scope,
        field_scope=field_scope,
        max_sensitivity_level=max_sensitivity_level,
    )
    chunks_by_document: dict[str, list[dict]] = {}
    for chunk in chunks:
        document_id = str(chunk.get("document_id") or "")
        if document_id in hit_decisions:
            chunks_by_document.setdefault(document_id, []).append(chunk)

    for document_id, decision in list(hit_decisions.items())[:RAG_AUTHORIZATION_AUDIT_MAX_DOCUMENTS]:
        if decision["authorization_reason"] in {"open", "denied"}:
            continue
        document_chunks = chunks_by_document.get(document_id, [])
        write_audit_log(
            user_id=user_id,
            action="rag.authorization.hit",
            resource_type="rag_document",
            resource_id=document_id,
            metadata={
                **query_metadata,
                **_rag_authorization_decision_metadata(decision),
                "rag_access_result": "hit",
                "retrieval_sources": sorted({
                    source
                    for chunk in document_chunks
                    for source in chunk.get("retrieval_sources", [])
                }),
                "max_score": _max_chunk_score(document_chunks),
            },
        )

    denied_items = audit_collector.get("denied") or {}
    for document_id, decision in list(denied_items.items())[:RAG_AUTHORIZATION_AUDIT_MAX_DOCUMENTS]:
        if document_id in hit_decisions:
            continue
        write_audit_log(
            user_id=user_id,
            action="rag.authorization.deny",
            resource_type="rag_document",
            resource_id=document_id,
            metadata={
                **query_metadata,
                **_rag_authorization_decision_metadata(decision),
                "rag_access_result": "deny",
                "rag_access_reason": "not_owner_or_grant",
                "retrieval_sources": sorted(decision.get("retrieval_sources") or []),
                "max_score": decision.get("max_score"),
            },
        )


def _rag_authorization_query_metadata(
    *,
    query: str,
    role: str,
    user_id: str | None,
    department: str | None,
    position: str | None,
    market_scope: str | None,
    store_scope: str | None,
    field_scope: str | None,
    max_sensitivity_level: str | None,
) -> dict[str, Any]:
    return {
        "query_hash": sha256(query.encode("utf-8")).hexdigest(),
        "query_length": len(query),
        "role": role,
        "user_id": user_id,
        "department": department,
        "position": position,
        "market_scope": market_scope,
        "store_scope": store_scope,
        "field_scope": field_scope,
        "max_sensitivity_level": max_sensitivity_level,
    }


def _rag_authorization_decision_metadata(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": decision.get("document_id"),
        "access_mode": decision.get("access_mode"),
        "owner_user_id": decision.get("owner_user_id"),
        "owner_team_id": decision.get("owner_team_id"),
        "rag_access_reason": decision.get("authorization_reason"),
        "rag_access_grant_id": decision.get("authorization_grant_id"),
        "rag_access_team_id": decision.get("authorization_team_id"),
        "visibility": decision.get("visibility"),
        "document_department": decision.get("department"),
        "position_scope": decision.get("position_scope"),
        "market_scope": decision.get("market_scope"),
        "store_scope": decision.get("store_scope"),
        "field_scope": decision.get("field_scope"),
        "sensitivity_level": decision.get("sensitivity_level"),
    }


def _max_chunk_score(chunks: list[dict]) -> float | None:
    scores = [
        float(chunk.get("score") or 0.0)
        for chunk in chunks
        if chunk.get("score") is not None
    ]
    return max(scores) if scores else None


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
            d.department,
            d.position_scope,
            d.market_scope,
            d.store_scope,
            d.field_scope,
            d.sensitivity_level
        FROM document_parent_chunks p
        JOIN documents d ON d.id = p.document_id
        WHERE p.id IN ({placeholders})
          AND d.status = 'active';
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
            "position_scope": row[7],
            "market_scope": row[8],
            "store_scope": row[9],
            "field_scope": row[10],
            "sensitivity_level": row[11],
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
                "position_scope": parent["position_scope"],
                "market_scope": parent["market_scope"],
                "store_scope": parent["store_scope"],
                "field_scope": parent["field_scope"],
                "sensitivity_level": parent["sensitivity_level"],
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
