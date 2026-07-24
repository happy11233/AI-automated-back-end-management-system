from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from psycopg.errors import UniqueViolation

from app.db import fetch_all, fetch_one, transaction
from app.permissions import POSITION_LABELS
from app.rag.ingest import (
    FIELD_SCOPE_POSITION_ALLOWLIST,
    ensure_rag_document_scope_schema,
    normalize_market_scope,
    normalize_store_scope,
)
from app.services.logging_service import write_audit_log


TEAM_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
TEAM_STATUSES = {"active", "paused", "archived"}
MEMBER_ROLES = {"member", "supervisor", "auditor"}
MEMBER_STATUSES = {"active", "paused", "removed"}
ACCESS_MODES = {"open", "owner_only", "team_only", "explicit_grants", "owner_and_grants"}
SUBJECT_TYPES = {"user", "team"}
ACCESS_LEVELS = {"read", "manage"}
GRANT_STATUSES = {"active", "revoked", "expired"}
DOCUMENT_LIST_STATUSES = {"active", "deleted", "all"}


def list_rag_teams() -> dict[str, Any]:
    _ensure_schema()
    rows = fetch_all(
        """
        SELECT
            rt.id,
            rt.team_key,
            rt.name,
            rt.description,
            rt.position_scope,
            rt.market_scope,
            rt.store_scope,
            rt.status,
            rt.created_by,
            u.username AS created_by_username,
            COALESCE(m.member_count, 0) AS member_count,
            rt.created_at,
            rt.updated_at
        FROM rag_teams rt
        LEFT JOIN users u ON u.id = rt.created_by
        LEFT JOIN (
            SELECT team_id, count(*) AS member_count
            FROM rag_team_memberships
            WHERE status = 'active'
              AND (expires_at IS NULL OR expires_at > now())
              AND member_role IN ('member', 'supervisor')
            GROUP BY team_id
        ) m ON m.team_id = rt.id
        ORDER BY
            CASE rt.status
                WHEN 'active' THEN 0
                WHEN 'paused' THEN 1
                ELSE 2
            END,
            rt.updated_at DESC,
            rt.created_at DESC;
        """
    )
    items = [_team_from_row(row) for row in rows]
    return {"items": items, "total": len(items)}


def create_rag_team(*, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
    _ensure_schema()
    normalized = _normalize_team_payload(payload, partial=False)
    try:
        row = fetch_one(
            """
            INSERT INTO rag_teams (
                team_key,
                name,
                description,
                position_scope,
                market_scope,
                store_scope,
                status,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING
                id, team_key, name, description, position_scope, market_scope,
                store_scope, status, created_by, NULL::text AS created_by_username,
                0::bigint AS member_count, created_at, updated_at;
            """,
            (
                normalized["team_key"],
                normalized["name"],
                normalized.get("description"),
                normalized.get("position_scope"),
                normalized.get("market_scope"),
                normalized.get("store_scope"),
                normalized["status"],
                current_user.get("id"),
            ),
        )
    except UniqueViolation as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="团队 key 已存在") from error

    item = _team_from_row(row)
    item["created_by_username"] = current_user.get("username")
    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_team.create",
        resource_type="rag_team",
        resource_id=item["id"],
        metadata={
            **_actor_metadata(current_user),
            "team_id": item["id"],
            "team_key": item["team_key"],
            "name": item["name"],
            "position_scope": item["position_scope"],
            "market_scope": item["market_scope"],
            "store_scope": item["store_scope"],
            "status": item["status"],
        },
    )
    return item


def update_rag_team(
    *,
    team_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_team_id = _normalize_uuid(team_id, "团队 ID")
    existing = _get_team(normalized_team_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的团队字段")

    normalized = _normalize_team_payload(payload, partial=True)
    next_values = {
        "name": normalized.get("name", existing["name"]),
        "description": normalized.get("description", existing["description"]),
        "position_scope": normalized.get("position_scope", existing["position_scope"]),
        "market_scope": normalized.get("market_scope", existing["market_scope"]),
        "store_scope": normalized.get("store_scope", existing["store_scope"]),
        "status": normalized.get("status", existing["status"]),
    }

    row = fetch_one(
        """
        UPDATE rag_teams
        SET
            name = %s,
            description = %s,
            position_scope = %s,
            market_scope = %s,
            store_scope = %s,
            status = %s,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, team_key, name, description, position_scope, market_scope,
            store_scope, status, created_by, NULL::text AS created_by_username,
            0::bigint AS member_count, created_at, updated_at;
        """,
        (
            next_values["name"],
            next_values["description"],
            next_values["position_scope"],
            next_values["market_scope"],
            next_values["store_scope"],
            next_values["status"],
            normalized_team_id,
        ),
    )
    item = _team_from_row(row)
    item["created_by_username"] = existing.get("created_by_username")
    item["member_count"] = existing.get("member_count", 0)

    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_team.update",
        resource_type="rag_team",
        resource_id=item["id"],
        metadata={
            **_actor_metadata(current_user),
            "team_id": item["id"],
            "team_key": item["team_key"],
            "updated_fields": sorted(normalized.keys()),
            "position_scope": item["position_scope"],
            "market_scope": item["market_scope"],
            "store_scope": item["store_scope"],
            "status": item["status"],
        },
    )
    return item


def list_rag_team_members(*, team_id: str) -> dict[str, Any]:
    _ensure_schema()
    normalized_team_id = _normalize_uuid(team_id, "团队 ID")
    _get_team(normalized_team_id)
    rows = fetch_all(
        """
        SELECT
            m.id,
            m.team_id,
            m.user_id,
            u.username,
            u.display_name,
            u.role,
            u.position,
            u.department,
            m.member_role,
            m.status,
            m.expires_at,
            m.added_by,
            added.username AS added_by_username,
            m.created_at,
            m.updated_at
        FROM rag_team_memberships m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN users added ON added.id = m.added_by
        WHERE m.team_id = %s
        ORDER BY
            CASE m.status
                WHEN 'active' THEN 0
                WHEN 'paused' THEN 1
                ELSE 2
            END,
            m.updated_at DESC,
            m.created_at DESC;
        """,
        (normalized_team_id,),
    )
    items = [_membership_from_row(row) for row in rows]
    return {"items": items, "total": len(items)}


def add_rag_team_member(
    *,
    team_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_team_id = _normalize_uuid(team_id, "团队 ID")
    team = _get_team(normalized_team_id)
    if team["status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能给 active 团队添加成员")

    user_id = _normalize_uuid(payload.get("user_id"), "用户 ID")
    user = _get_user(user_id)
    member_role = _normalize_choice(payload.get("member_role") or "member", MEMBER_ROLES, "成员角色")
    expires_at = _normalize_future_datetime(payload.get("expires_at"), "成员过期时间")
    _validate_member_against_team(user=user, team=team)

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM rag_team_memberships
                WHERE team_id = %s
                  AND user_id = %s
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (normalized_team_id, user_id),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    SELECT id
                    FROM rag_team_memberships
                    WHERE team_id = %s
                      AND user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """,
                    (normalized_team_id, user_id),
                )
                row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    INSERT INTO rag_team_memberships (
                        team_id,
                        user_id,
                        member_role,
                        status,
                        added_by,
                        expires_at
                    )
                    VALUES (%s, %s, %s, 'active', %s, %s)
                    RETURNING id;
                    """,
                    (normalized_team_id, user_id, member_role, current_user.get("id"), expires_at),
                )
                membership_id = str(cur.fetchone()[0])
            else:
                membership_id = str(row[0])
                cur.execute(
                    """
                    UPDATE rag_team_memberships
                    SET
                        member_role = %s,
                        status = 'active',
                        added_by = %s,
                        expires_at = %s,
                        updated_at = now()
                    WHERE id = %s;
                    """,
                    (member_role, current_user.get("id"), expires_at, membership_id),
                )

    item = _get_membership(membership_id=membership_id)
    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_team.member_add",
        resource_type="rag_team",
        resource_id=team["id"],
        metadata={
            **_actor_metadata(current_user),
            "team_id": team["id"],
            "team_key": team["team_key"],
            "user_id": user["id"],
            "target_username": user["username"],
            "member_role": item["member_role"],
            "expires_at": _datetime_to_text(item.get("expires_at")),
        },
    )
    return item


def remove_rag_team_member(
    *,
    team_id: str,
    user_id: str,
    current_user: dict,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_team_id = _normalize_uuid(team_id, "团队 ID")
    normalized_user_id = _normalize_uuid(user_id, "用户 ID")
    team = _get_team(normalized_team_id)
    user = _get_user(normalized_user_id)
    existing = _get_active_membership(team_id=normalized_team_id, user_id=normalized_user_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="团队 active 成员不存在")

    row = fetch_one(
        """
        UPDATE rag_team_memberships
        SET status = 'removed',
            updated_at = now()
        WHERE id = %s
        RETURNING id;
        """,
        (existing["id"],),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="移除团队成员失败")

    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_team.member_remove",
        resource_type="rag_team",
        resource_id=team["id"],
        metadata={
            **_actor_metadata(current_user),
            "team_id": team["id"],
            "team_key": team["team_key"],
            "user_id": user["id"],
            "target_username": user["username"],
            "previous_member_role": existing["member_role"],
        },
    )
    return {"ok": True, "team_id": team["id"], "user_id": user["id"]}


def get_document_access(*, document_id: str) -> dict[str, Any]:
    _ensure_schema()
    normalized_document_id = _normalize_uuid(document_id, "文档 ID")
    return _get_document(normalized_document_id)


def normalize_document_access_inputs(
    *,
    access_mode: str | None = None,
    owner_user_id: str | None = None,
    owner_team_id: str | None = None,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_access_mode = _normalize_choice(access_mode or "open", ACCESS_MODES, "访问模式")
    normalized_owner_user_id = _normalize_optional_uuid(owner_user_id, "owner 用户 ID")
    if normalized_owner_user_id:
        _get_user(normalized_owner_user_id)

    normalized_owner_team_id = _normalize_optional_uuid(owner_team_id, "owner 团队 ID")
    if normalized_owner_team_id:
        team = _get_team(normalized_owner_team_id)
        if team["status"] == "archived":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能把文档归属给 archived 团队")

    _validate_document_access_state(
        access_mode=normalized_access_mode,
        owner_user_id=normalized_owner_user_id,
        owner_team_id=normalized_owner_team_id,
    )
    return {
        "access_mode": normalized_access_mode,
        "owner_user_id": normalized_owner_user_id,
        "owner_team_id": normalized_owner_team_id,
    }


def normalize_document_grant_inputs(
    *,
    subject_type: str | None = None,
    subject_id: str | None = None,
    access_level: str | None = None,
    reason: str | None = None,
    expires_at: datetime | None = None,
    document: dict[str, Any],
) -> dict[str, Any] | None:
    _ensure_schema()
    has_grant_input = any(
        value is not None and str(value).strip()
        for value in (subject_type, subject_id, access_level, reason, expires_at)
    )
    if not has_grant_input:
        return None

    normalized_subject_type = _normalize_choice(subject_type, SUBJECT_TYPES, "授权对象类型")
    normalized_subject_id = _normalize_uuid(subject_id, "授权对象 ID")
    normalized_access_level = _normalize_choice(access_level or "read", ACCESS_LEVELS, "授权级别")
    normalized_reason = _normalize_optional_text(reason, max_length=500)
    normalized_expires_at = _normalize_future_datetime(expires_at, "授权过期时间")
    subject = _get_grant_subject(subject_type=normalized_subject_type, subject_id=normalized_subject_id)
    _validate_grant_against_document(
        document=document,
        subject_type=normalized_subject_type,
        subject=subject,
    )
    return {
        "subject_type": normalized_subject_type,
        "subject_id": normalized_subject_id,
        "access_level": normalized_access_level,
        "reason": normalized_reason,
        "expires_at": normalized_expires_at,
    }


def list_rag_documents(
    *,
    search: str | None = None,
    status: str = "active",
    limit: int = 50,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_status = _normalize_choice(status or "active", DOCUMENT_LIST_STATUSES, "文档状态")
    normalized_limit = _normalize_limit(limit, default=50, maximum=100)
    search_text = str(search or "").strip()

    conditions: list[str] = []
    params: list[Any] = []

    if normalized_status != "all":
        conditions.append("status = %s")
        params.append(normalized_status)

    if search_text:
        search_conditions = ["title ILIKE %s", "source ILIKE %s", "id::text = %s"]
        search_pattern = f"%{search_text}%"
        params.extend([search_pattern, search_pattern, search_text])
        conditions.append(f"({' OR '.join(search_conditions)})")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = fetch_all(
        f"""
        SELECT
            id,
            title,
            source,
            visibility,
            department,
            position_scope,
            market_scope,
            store_scope,
            field_scope,
            sensitivity_level,
            owner_user_id,
            owner_team_id,
            access_mode,
            status,
            created_at,
            updated_at
        FROM documents
        {where_clause}
        ORDER BY updated_at DESC, created_at DESC
        LIMIT %s;
        """,
        tuple([*params, normalized_limit]),
    )
    items = [_document_from_row(row) for row in rows]
    return {"items": items, "total": len(items)}


def update_document_access(
    *,
    document_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_document_id = _normalize_uuid(document_id, "文档 ID")
    existing = _get_document(normalized_document_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的文档授权字段")

    owner_user_id = existing["owner_user_id"]
    if "owner_user_id" in payload:
        owner_user_id = _normalize_optional_uuid(payload.get("owner_user_id"), "owner 用户 ID")
        if owner_user_id:
            _get_user(owner_user_id)

    owner_team_id = existing["owner_team_id"]
    if "owner_team_id" in payload:
        owner_team_id = _normalize_optional_uuid(payload.get("owner_team_id"), "owner 团队 ID")
        if owner_team_id:
            team = _get_team(owner_team_id)
            if team["status"] == "archived":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能把文档归属给 archived 团队")

    access_mode = existing["access_mode"]
    if "access_mode" in payload:
        access_mode = _normalize_choice(payload.get("access_mode"), ACCESS_MODES, "访问模式")

    _validate_document_access_state(
        access_mode=access_mode,
        owner_user_id=owner_user_id,
        owner_team_id=owner_team_id,
    )

    row = fetch_one(
        """
        UPDATE documents
        SET
            owner_user_id = %s,
            owner_team_id = %s,
            access_mode = %s,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, title, source, visibility, department, position_scope, market_scope,
            store_scope, field_scope, sensitivity_level, owner_user_id, owner_team_id,
            access_mode, status, created_at, updated_at;
        """,
        (owner_user_id, owner_team_id, access_mode, normalized_document_id),
    )
    item = _document_from_row(row)
    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_document.access_update",
        resource_type="rag_document",
        resource_id=item["id"],
        metadata={
            **_actor_metadata(current_user),
            "document_id": item["id"],
            "access_mode": item["access_mode"],
            "owner_user_id": item["owner_user_id"],
            "owner_team_id": item["owner_team_id"],
            "position_scope": item["position_scope"],
            "market_scope": item["market_scope"],
            "store_scope": item["store_scope"],
            "field_scope": item["field_scope"],
            "sensitivity_level": item["sensitivity_level"],
            "updated_fields": sorted(payload.keys()),
        },
    )
    return item


def list_document_grants(*, document_id: str) -> dict[str, Any]:
    _ensure_schema()
    normalized_document_id = _normalize_uuid(document_id, "文档 ID")
    _get_document(normalized_document_id)
    rows = fetch_all(
        """
        SELECT
            g.id,
            g.document_id,
            g.subject_type,
            g.subject_id,
            COALESCE(u.username, rt.name) AS subject_name,
            g.access_level,
            g.status,
            g.granted_by,
            granted.username AS granted_by_username,
            g.reason,
            g.expires_at,
            g.created_at,
            g.updated_at
        FROM rag_document_access_grants g
        LEFT JOIN users u ON g.subject_type = 'user' AND u.id = g.subject_id
        LEFT JOIN rag_teams rt ON g.subject_type = 'team' AND rt.id = g.subject_id
        LEFT JOIN users granted ON granted.id = g.granted_by
        WHERE g.document_id = %s
        ORDER BY
            CASE g.status
                WHEN 'active' THEN 0
                WHEN 'expired' THEN 1
                ELSE 2
            END,
            g.updated_at DESC,
            g.created_at DESC;
        """,
        (normalized_document_id,),
    )
    items = [_grant_from_row(row) for row in rows]
    return {"items": items, "total": len(items)}


def create_document_grant(
    *,
    document_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_document_id = _normalize_uuid(document_id, "文档 ID")
    document = _get_document(normalized_document_id)
    subject_type = _normalize_choice(payload.get("subject_type"), SUBJECT_TYPES, "授权对象类型")
    subject_id = _normalize_uuid(payload.get("subject_id"), "授权对象 ID")
    access_level = _normalize_choice(payload.get("access_level") or "read", ACCESS_LEVELS, "授权级别")
    reason = _normalize_optional_text(payload.get("reason"), max_length=500)
    expires_at = _normalize_future_datetime(payload.get("expires_at"), "授权过期时间")
    subject = _get_grant_subject(subject_type=subject_type, subject_id=subject_id)
    _validate_grant_against_document(document=document, subject_type=subject_type, subject=subject)

    with transaction() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM rag_document_access_grants
                WHERE document_id = %s
                  AND subject_type = %s
                  AND subject_id = %s
                  AND access_level = %s
                  AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (normalized_document_id, subject_type, subject_id, access_level),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """
                    INSERT INTO rag_document_access_grants (
                        document_id,
                        subject_type,
                        subject_id,
                        access_level,
                        status,
                        granted_by,
                        reason,
                        expires_at
                    )
                    VALUES (%s, %s, %s, %s, 'active', %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        normalized_document_id,
                        subject_type,
                        subject_id,
                        access_level,
                        current_user.get("id"),
                        reason,
                        expires_at,
                    ),
                )
                grant_id = str(cur.fetchone()[0])
            else:
                grant_id = str(row[0])
                cur.execute(
                    """
                    UPDATE rag_document_access_grants
                    SET
                        reason = %s,
                        expires_at = %s,
                        granted_by = %s,
                        updated_at = now()
                    WHERE id = %s;
                    """,
                    (reason, expires_at, current_user.get("id"), grant_id),
                )

    item = _get_grant(document_id=normalized_document_id, grant_id=grant_id)
    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_document.grant_create",
        resource_type="rag_document_grant",
        resource_id=item["id"],
        metadata={
            **_actor_metadata(current_user),
            "document_id": document["id"],
            "access_mode": document["access_mode"],
            "owner_user_id": document["owner_user_id"],
            "owner_team_id": document["owner_team_id"],
            "grant_id": item["id"],
            "subject_type": item["subject_type"],
            "subject_id": item["subject_id"],
            "subject_name": item["subject_name"],
            "access_level": item["access_level"],
            "reason": item["reason"],
            "expires_at": _datetime_to_text(item.get("expires_at")),
            "position_scope": document["position_scope"],
            "market_scope": document["market_scope"],
            "store_scope": document["store_scope"],
            "field_scope": document["field_scope"],
            "sensitivity_level": document["sensitivity_level"],
        },
    )
    return item


def revoke_document_grant(
    *,
    document_id: str,
    grant_id: str,
    current_user: dict,
) -> dict[str, Any]:
    _ensure_schema()
    normalized_document_id = _normalize_uuid(document_id, "文档 ID")
    normalized_grant_id = _normalize_uuid(grant_id, "授权 ID")
    document = _get_document(normalized_document_id)
    existing = _get_grant(document_id=normalized_document_id, grant_id=normalized_grant_id)

    if existing["status"] == "active":
        row = fetch_one(
            """
            UPDATE rag_document_access_grants
            SET status = 'revoked',
                updated_at = now()
            WHERE id = %s
            RETURNING id;
            """,
            (normalized_grant_id,),
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="撤销授权失败")
        item = _get_grant(document_id=normalized_document_id, grant_id=normalized_grant_id)
    else:
        item = existing

    write_audit_log(
        user_id=current_user.get("id"),
        action="admin.rag_document.grant_revoke",
        resource_type="rag_document_grant",
        resource_id=item["id"],
        metadata={
            **_actor_metadata(current_user),
            "document_id": document["id"],
            "access_mode": document["access_mode"],
            "owner_user_id": document["owner_user_id"],
            "owner_team_id": document["owner_team_id"],
            "grant_id": item["id"],
            "subject_type": item["subject_type"],
            "subject_id": item["subject_id"],
            "access_level": item["access_level"],
            "previous_status": existing["status"],
            "status": item["status"],
            "reason": item["reason"],
            "expires_at": _datetime_to_text(item.get("expires_at")),
        },
    )
    return {"ok": True, "item": item}


def _ensure_schema() -> None:
    ensure_rag_document_scope_schema()


def _normalize_team_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    if "team_key" in payload:
        team_key = str(payload.get("team_key") or "").strip().lower()
        if not TEAM_KEY_PATTERN.fullmatch(team_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="团队 key 只能包含小写字母、数字、下划线或中划线，长度 2-64",
            )
        normalized["team_key"] = team_key
    elif not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="团队 key 不能为空")

    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="团队名称不能为空")
        if len(name) > 120:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="团队名称不能超过 120 个字符")
        normalized["name"] = name
    elif not partial:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="团队名称不能为空")

    if "description" in payload:
        normalized["description"] = _normalize_optional_text(payload.get("description"), max_length=500)

    if "position_scope" in payload:
        normalized["position_scope"] = _normalize_position_scope(payload.get("position_scope"))

    try:
        if "market_scope" in payload:
            normalized["market_scope"] = normalize_market_scope(payload.get("market_scope"))
        if "store_scope" in payload:
            normalized["store_scope"] = normalize_store_scope(payload.get("store_scope"))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    if "status" in payload:
        normalized["status"] = _normalize_choice(payload.get("status"), TEAM_STATUSES, "团队状态")
    elif not partial:
        normalized["status"] = "active"

    return normalized


def _normalize_optional_text(value: Any, *, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > max_length:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文本不能超过 {max_length} 个字符")
    return text


def _normalize_position_scope(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if normalized not in POSITION_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="position_scope 只能是 operations、customer_service 或 finance",
        )
    return normalized


def _normalize_choice(value: Any, allowed: set[str], label: str) -> str:
    normalized = str(value or "").strip()
    if normalized not in allowed:
        allowed_values = "、".join(sorted(allowed))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 只能是 {allowed_values}")
    return normalized


def _normalize_limit(value: Any, *, default: int, maximum: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = default
    return max(1, min(maximum, normalized))


def _normalize_uuid(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 不能为空")
    try:
        return str(UUID(text))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 格式不正确") from error


def _normalize_optional_uuid(value: Any, label: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return _normalize_uuid(text, label)


def _normalize_future_datetime(value: Any, label: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 格式不正确")
    normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if normalized <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} 必须晚于当前时间")
    return normalized


def _validate_document_access_state(
    *,
    access_mode: str,
    owner_user_id: str | None,
    owner_team_id: str | None,
) -> None:
    if access_mode == "owner_only" and not owner_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="owner_only 文档必须设置 owner_user_id")
    if access_mode == "team_only" and not owner_team_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="team_only 文档必须设置 owner_team_id")
    if access_mode == "open":
        return


def _validate_member_against_team(*, user: dict[str, Any], team: dict[str, Any]) -> None:
    team_position = team.get("position_scope")
    user_position = user.get("position")
    if user.get("role") == "employee" and team_position and user_position != team_position:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="成员岗位必须匹配团队 position_scope",
        )


def _validate_grant_against_document(
    *,
    document: dict[str, Any],
    subject_type: str,
    subject: dict[str, Any],
) -> None:
    document_position = document.get("position_scope")
    document_field_scope = document.get("field_scope")
    subject_position = subject.get("position_scope") if subject_type == "team" else subject.get("position")

    if subject_type == "team" and subject.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能授权给 active 团队")

    if document_position and subject_position and subject_position != document_position:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="授权对象岗位不能跨越文档 position_scope")

    allowed_positions = FIELD_SCOPE_POSITION_ALLOWLIST.get(document_field_scope or "")
    if allowed_positions and subject_position and subject_position not in allowed_positions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="授权对象岗位不能跨越文档 field_scope")


def _get_team(team_id: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT
            rt.id,
            rt.team_key,
            rt.name,
            rt.description,
            rt.position_scope,
            rt.market_scope,
            rt.store_scope,
            rt.status,
            rt.created_by,
            u.username AS created_by_username,
            COALESCE(m.member_count, 0) AS member_count,
            rt.created_at,
            rt.updated_at
        FROM rag_teams rt
        LEFT JOIN users u ON u.id = rt.created_by
        LEFT JOIN (
            SELECT team_id, count(*) AS member_count
            FROM rag_team_memberships
            WHERE status = 'active'
              AND (expires_at IS NULL OR expires_at > now())
              AND member_role IN ('member', 'supervisor')
            GROUP BY team_id
        ) m ON m.team_id = rt.id
        WHERE rt.id = %s
        LIMIT 1;
        """,
        (team_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG 团队不存在")
    return _team_from_row(row)


def _get_user(user_id: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT id, username, role, department, position, display_name, email, created_at
        FROM users
        WHERE id = %s
        LIMIT 1;
        """,
        (user_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return {
        "id": str(row[0]),
        "username": row[1],
        "role": row[2],
        "department": row[3],
        "position": row[4],
        "display_name": row[5],
        "email": row[6],
        "created_at": row[7],
    }


def _get_document(document_id: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT
            id,
            title,
            source,
            visibility,
            department,
            position_scope,
            market_scope,
            store_scope,
            field_scope,
            sensitivity_level,
            owner_user_id,
            owner_team_id,
            access_mode,
            status,
            created_at,
            updated_at
        FROM documents
        WHERE id = %s
        LIMIT 1;
        """,
        (document_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG 文档不存在")
    return _document_from_row(row)


def _get_active_membership(*, team_id: str, user_id: str) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT
            m.id,
            m.team_id,
            m.user_id,
            u.username,
            u.display_name,
            u.role,
            u.position,
            u.department,
            m.member_role,
            m.status,
            m.expires_at,
            m.added_by,
            added.username AS added_by_username,
            m.created_at,
            m.updated_at
        FROM rag_team_memberships m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN users added ON added.id = m.added_by
        WHERE m.team_id = %s
          AND m.user_id = %s
          AND m.status = 'active'
        ORDER BY m.created_at DESC
        LIMIT 1;
        """,
        (team_id, user_id),
    )
    return _membership_from_row(row) if row else None


def _get_membership(*, membership_id: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT
            m.id,
            m.team_id,
            m.user_id,
            u.username,
            u.display_name,
            u.role,
            u.position,
            u.department,
            m.member_role,
            m.status,
            m.expires_at,
            m.added_by,
            added.username AS added_by_username,
            m.created_at,
            m.updated_at
        FROM rag_team_memberships m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN users added ON added.id = m.added_by
        WHERE m.id = %s
        LIMIT 1;
        """,
        (membership_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="团队成员关系不存在")
    return _membership_from_row(row)


def _get_grant_subject(*, subject_type: str, subject_id: str) -> dict[str, Any]:
    if subject_type == "user":
        return _get_user(subject_id)
    return _get_team(subject_id)


def _get_grant(*, document_id: str, grant_id: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT
            g.id,
            g.document_id,
            g.subject_type,
            g.subject_id,
            COALESCE(u.username, rt.name) AS subject_name,
            g.access_level,
            g.status,
            g.granted_by,
            granted.username AS granted_by_username,
            g.reason,
            g.expires_at,
            g.created_at,
            g.updated_at
        FROM rag_document_access_grants g
        LEFT JOIN users u ON g.subject_type = 'user' AND u.id = g.subject_id
        LEFT JOIN rag_teams rt ON g.subject_type = 'team' AND rt.id = g.subject_id
        LEFT JOIN users granted ON granted.id = g.granted_by
        WHERE g.document_id = %s
          AND g.id = %s
        LIMIT 1;
        """,
        (document_id, grant_id),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档授权不存在")
    return _grant_from_row(row)


def _team_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "team_key": row[1],
        "name": row[2],
        "description": row[3],
        "position_scope": row[4],
        "market_scope": row[5],
        "store_scope": row[6],
        "status": row[7],
        "created_by": str(row[8]) if row[8] else None,
        "created_by_username": row[9],
        "member_count": int(row[10] or 0),
        "created_at": row[11],
        "updated_at": row[12],
    }


def _membership_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "team_id": str(row[1]),
        "user_id": str(row[2]),
        "username": row[3],
        "display_name": row[4],
        "role": row[5],
        "position": row[6],
        "department": row[7],
        "member_role": row[8],
        "status": row[9],
        "expires_at": row[10],
        "added_by": str(row[11]) if row[11] else None,
        "added_by_username": row[12],
        "created_at": row[13],
        "updated_at": row[14],
    }


def _document_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row[0]),
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
        "access_mode": row[12],
        "status": row[13],
        "created_at": row[14],
        "updated_at": row[15],
    }


def _grant_from_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "document_id": str(row[1]),
        "subject_type": row[2],
        "subject_id": str(row[3]),
        "subject_name": row[4],
        "access_level": row[5],
        "status": row[6],
        "granted_by": str(row[7]) if row[7] else None,
        "granted_by_username": row[8],
        "reason": row[9],
        "expires_at": row[10],
        "created_at": row[11],
        "updated_at": row[12],
    }


def _actor_metadata(current_user: dict) -> dict[str, Any]:
    return {
        "actor_username": current_user.get("username"),
        "actor_role": current_user.get("role"),
        "actor_position": current_user.get("position"),
        "username": current_user.get("username"),
        "role": current_user.get("role"),
        "position": current_user.get("position"),
    }


def _datetime_to_text(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
