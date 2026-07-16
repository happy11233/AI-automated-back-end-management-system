from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
import time
from typing import Any

from fastapi import HTTPException, status

from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json


PREVIEW_LIMIT = 240
ERROR_LIMIT = 500
METADATA_TEXT_LIMIT = 500
ALLOWED_STATUSES = {"running", "succeeded", "failed", "blocked"}
SECRET_KEYWORDS = (
    "token",
    "secret",
    "password",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "jwt",
    "connection_string",
    "database_url",
)
SENSITIVE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\b\d{15}(?:\d{2}[0-9Xx])?\b"),
    re.compile(r"\b\d{13,19}\b"),
    re.compile(r"(?i)(api[_-]?secret|api[_-]?key|password|token|jwt)=([^&\s]+)"),
]


def now_ms() -> float:
    return time.perf_counter() * 1000


def elapsed_ms(start_ms: float) -> int:
    return max(0, int(now_ms() - start_ms))


def start_run(
    *,
    run_type: str,
    app_id: str,
    app_name: str,
    entrypoint: str,
    current_user: dict | None = None,
    thread_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    input_text: Any = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    input_preview = preview_text(input_text)
    input_hash = hash_text(input_text)
    row = fetch_one(
        """
        INSERT INTO automation_runs (
            run_type, app_id, app_name, entrypoint, status, user_id, username,
            role, position, thread_id, resource_type, resource_id, input_preview,
            input_hash, metadata
        )
        VALUES (
            %s, %s, %s, %s, 'running', %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s::jsonb
        )
        RETURNING id;
        """,
        (
            run_type,
            app_id,
            app_name,
            entrypoint,
            (current_user or {}).get("id"),
            (current_user or {}).get("username"),
            (current_user or {}).get("role"),
            (current_user or {}).get("position"),
            thread_id,
            resource_type,
            resource_id,
            input_preview,
            input_hash,
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    return str(row[0])


def finish_run(
    run_id: str | None,
    *,
    status_value: str,
    output_text: Any = None,
    error_message: Any = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not run_id:
        return

    normalized_status = _normalize_status(status_value)
    execute(
        """
        UPDATE automation_runs
        SET status = %s,
            output_preview = COALESCE(%s, output_preview),
            error_message = COALESCE(%s, error_message),
            duration_ms = COALESCE(%s, duration_ms),
            metadata = metadata || %s::jsonb,
            finished_at = now()
        WHERE id = %s;
        """,
        (
            normalized_status,
            preview_text(output_text),
            preview_text(error_message, limit=ERROR_LIMIT),
            duration_ms,
            dumps_json(sanitize_metadata(metadata or {})),
            run_id,
        ),
    )


def record_step(
    *,
    run_id: str | None,
    step_name: str,
    status_value: str,
    step_order: int = 1,
    provider: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    input_text: Any = None,
    output_text: Any = None,
    error_message: Any = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    if not run_id:
        return None

    row = fetch_one(
        """
        INSERT INTO automation_run_steps (
            run_id, step_order, step_name, status, provider, resource_type,
            resource_id, input_preview, output_preview, error_message,
            duration_ms, metadata, started_at, finished_at
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s::jsonb, now(), now()
        )
        RETURNING id;
        """,
        (
            run_id,
            step_order,
            step_name,
            _normalize_status(status_value),
            provider,
            resource_type,
            resource_id,
            preview_text(input_text),
            preview_text(output_text),
            preview_text(error_message, limit=ERROR_LIMIT),
            duration_ms,
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    return str(row[0])


def record_artifact(
    *,
    run_id: str | None,
    artifact_type: str,
    name: str,
    mime_type: str | None = None,
    size_bytes: int | None = None,
    external_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    if not run_id:
        return None

    row = fetch_one(
        """
        INSERT INTO automation_run_artifacts (
            run_id, artifact_type, name, mime_type, size_bytes, external_ref, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            run_id,
            artifact_type,
            preview_text(name, limit=180) or "artifact",
            mime_type,
            size_bytes,
            preview_text(external_ref, limit=240),
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    return str(row[0])


def list_runs(
    *,
    current_user: dict,
    status_filter: str | None = None,
    run_type: str | None = None,
    app_id: str | None = None,
    position: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    role = current_user.get("role")

    if role != "admin":
        conditions.append("user_id = %s")
        params.append(current_user.get("id"))
        conditions.append("position IS NOT DISTINCT FROM %s")
        params.append(current_user.get("position"))
    else:
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        if position:
            conditions.append("position = %s")
            params.append(position)

    if status_filter:
        conditions.append("status = %s")
        params.append(status_filter)

    if run_type:
        conditions.append("run_type = %s")
        params.append(run_type)

    if app_id:
        conditions.append("app_id ILIKE %s")
        params.append(f"%{app_id}%")

    if resource_type:
        conditions.append("resource_type = %s")
        params.append(resource_type)

    if resource_id:
        conditions.append("resource_id ILIKE %s")
        params.append(f"%{resource_id}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    bounded_limit = max(1, min(limit, 200))
    params.append(bounded_limit)

    rows = fetch_all(
        f"""
        SELECT
            r.id, r.run_type, r.app_id, r.app_name, r.entrypoint, r.status,
            r.user_id, r.username, r.role, r.position, r.thread_id,
            r.resource_type, r.resource_id, r.input_preview, r.output_preview,
            r.error_message, r.duration_ms, r.metadata, r.started_at,
            r.finished_at, r.created_at,
            COALESCE(s.step_count, 0) AS step_count,
            COALESCE(a.artifact_count, 0) AS artifact_count
        FROM automation_runs r
        LEFT JOIN (
            SELECT run_id, count(*) AS step_count
            FROM automation_run_steps
            GROUP BY run_id
        ) s ON s.run_id = r.id
        LEFT JOIN (
            SELECT run_id, count(*) AS artifact_count
            FROM automation_run_artifacts
            GROUP BY run_id
        ) a ON a.run_id = r.id
        {where_clause}
        ORDER BY r.started_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )
    return [_map_run_row(row) for row in rows]


def get_run_detail(run_id: str, *, current_user: dict) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT
            r.id, r.run_type, r.app_id, r.app_name, r.entrypoint, r.status,
            r.user_id, r.username, r.role, r.position, r.thread_id,
            r.resource_type, r.resource_id, r.input_preview, r.output_preview,
            r.error_message, r.duration_ms, r.metadata, r.started_at,
            r.finished_at, r.created_at,
            COALESCE(s.step_count, 0) AS step_count,
            COALESCE(a.artifact_count, 0) AS artifact_count
        FROM automation_runs r
        LEFT JOIN (
            SELECT run_id, count(*) AS step_count
            FROM automation_run_steps
            GROUP BY run_id
        ) s ON s.run_id = r.id
        LEFT JOIN (
            SELECT run_id, count(*) AS artifact_count
            FROM automation_run_artifacts
            GROUP BY run_id
        ) a ON a.run_id = r.id
        WHERE r.id = %s;
        """,
        (run_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行记录不存在")

    run = _map_run_row(row)
    if not _can_read_run(current_user, run):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该运行记录")

    step_rows = fetch_all(
        """
        SELECT id, run_id, step_order, step_name, status, provider, resource_type,
               resource_id, input_preview, output_preview, error_message,
               duration_ms, metadata, started_at, finished_at
        FROM automation_run_steps
        WHERE run_id = %s
        ORDER BY step_order ASC, started_at ASC;
        """,
        (run_id,),
    )
    artifact_rows = fetch_all(
        """
        SELECT id, run_id, artifact_type, name, mime_type, size_bytes,
               external_ref, metadata, created_at
        FROM automation_run_artifacts
        WHERE run_id = %s
        ORDER BY created_at ASC;
        """,
        (run_id,),
    )

    return {
        "run": run,
        "steps": [_map_step_row(row) for row in step_rows],
        "artifacts": [_map_artifact_row(row) for row in artifact_rows],
    }


def preview_text(value: Any, *, limit: int = PREVIEW_LIMIT) -> str | None:
    if value is None:
        return None

    if isinstance(value, (dict, list, tuple)):
        text = dumps_json(sanitize_metadata(value))
    else:
        text = str(value)

    text = sanitize_text(text)
    text = " ".join(text.split())
    if not text:
        return None

    if len(text) <= limit:
        return text

    return f"{text[:limit]}..."


def hash_text(value: Any) -> str | None:
    if value is None:
        return None

    raw = dumps_json(value) if isinstance(value, (dict, list, tuple)) else str(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key)
            if _is_secret_key(text_key):
                sanitized[text_key] = "[REDACTED]"
            else:
                sanitized[text_key] = sanitize_metadata(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value[:50]]

    if isinstance(value, tuple):
        return [sanitize_metadata(item) for item in value[:50]]

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, str):
        return preview_text(sanitize_text(value), limit=METADATA_TEXT_LIMIT)

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    return preview_text(value, limit=METADATA_TEXT_LIMIT)


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        if pattern.pattern.startswith("(?i)("):
            sanitized = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", sanitized)
        else:
            sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_secret_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(secret in normalized for secret in SECRET_KEYWORDS)


def _normalize_status(value: str) -> str:
    if value not in ALLOWED_STATUSES:
        return "failed"
    return value


def _can_read_run(current_user: dict, run: dict[str, Any]) -> bool:
    if current_user.get("role") == "admin":
        return True

    return (
        run.get("user_id") == current_user.get("id")
        and run.get("position") == current_user.get("position")
    )


def _map_run_row(row) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "run_type": row[1],
        "app_id": row[2],
        "app_name": row[3],
        "entrypoint": row[4],
        "status": row[5],
        "user_id": str(row[6]) if row[6] else None,
        "username": row[7],
        "role": row[8],
        "position": row[9],
        "thread_id": row[10],
        "resource_type": row[11],
        "resource_id": row[12],
        "input_preview": row[13],
        "output_preview": row[14],
        "error_message": row[15],
        "duration_ms": row[16],
        "metadata": row[17] or {},
        "started_at": isoformat(row[18]),
        "finished_at": isoformat(row[19]),
        "created_at": isoformat(row[20]),
        "step_count": int(row[21] or 0),
        "artifact_count": int(row[22] or 0),
    }


def _map_step_row(row) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "run_id": str(row[1]),
        "step_order": row[2],
        "step_name": row[3],
        "status": row[4],
        "provider": row[5],
        "resource_type": row[6],
        "resource_id": row[7],
        "input_preview": row[8],
        "output_preview": row[9],
        "error_message": row[10],
        "duration_ms": row[11],
        "metadata": row[12] or {},
        "started_at": isoformat(row[13]),
        "finished_at": isoformat(row[14]),
    }


def _map_artifact_row(row) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "run_id": str(row[1]),
        "artifact_type": row[2],
        "name": row[3],
        "mime_type": row[4],
        "size_bytes": row[5],
        "external_ref": row[6],
        "metadata": row[7] or {},
        "created_at": isoformat(row[8]),
    }
