from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.config import settings
from app.db import execute, fetch_all, fetch_one
from app.services.run_record_service import isoformat, preview_text, record_artifact, sanitize_metadata


DOWNLOADABLE_ARTIFACT_TYPES = {
    "excel_file",
    "word_file",
    "docx_file",
    "report_file",
}


def ensure_generated_file_schema() -> None:
    execute(
        """
        ALTER TABLE automation_run_artifacts
        ADD COLUMN IF NOT EXISTS storage_path TEXT;
        """
    )
    execute(
        """
        ALTER TABLE automation_run_artifacts
        ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
        """
    )
    execute(
        """
        ALTER TABLE automation_run_artifacts
        ADD COLUMN IF NOT EXISTS downloadable BOOLEAN NOT NULL DEFAULT FALSE;
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_automation_run_artifacts_downloadable_expires
        ON automation_run_artifacts(downloadable, expires_at, created_at DESC);
        """
    )


def save_generated_file(
    *,
    run_id: str | None,
    content: bytes,
    filename: str,
    artifact_type: str,
    mime_type: str,
    current_user: dict,
    metadata: dict[str, Any] | None = None,
    retention_days: int | None = None,
) -> str | None:
    if not run_id:
        return None

    safe_name = _safe_filename(filename)
    storage_dir = _storage_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4().hex}_{safe_name}"
    storage_path = storage_dir / storage_name
    storage_path.write_bytes(content)

    days = retention_days or settings.generated_file_retention_days
    expires_at = datetime.now(timezone.utc) + timedelta(days=max(1, days))
    merged_metadata = {
        **(metadata or {}),
        "storage": "local",
        "generated_by": current_user.get("username"),
        "retention_days": max(1, days),
        "downloadable": True,
    }
    artifact_id = record_artifact(
        run_id=run_id,
        artifact_type=artifact_type,
        name=safe_name,
        mime_type=mime_type,
        size_bytes=len(content),
        external_ref=safe_name,
        metadata=merged_metadata,
    )
    if artifact_id:
        execute(
            """
            UPDATE automation_run_artifacts
            SET storage_path = %s,
                expires_at = %s,
                downloadable = TRUE
            WHERE id = %s;
            """,
            (str(storage_path), expires_at, artifact_id),
        )
    return artifact_id


def list_generated_files(
    *,
    current_user: dict,
    search: str | None = None,
    date_range: str = "30d",
    file_type: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    cleanup_expired_generated_files()
    conditions = [
        "a.downloadable = TRUE",
        "a.storage_path IS NOT NULL",
        "(a.expires_at IS NULL OR a.expires_at > now())",
    ]
    params: list[Any] = []

    if current_user.get("role") != "admin":
        conditions.append("r.user_id = %s")
        params.append(current_user.get("id"))
        conditions.append("r.position IS NOT DISTINCT FROM %s")
        params.append(current_user.get("position"))

    since = _date_range_since(date_range)
    if since is not None:
        conditions.append("a.created_at >= %s")
        params.append(since)

    normalized_search = (search or "").strip()
    if normalized_search:
        conditions.append("(a.name ILIKE %s OR r.app_name ILIKE %s OR r.app_id ILIKE %s)")
        value = f"%{normalized_search}%"
        params.extend([value, value, value])

    normalized_file_type = (file_type or "").strip().lower()
    if normalized_file_type and normalized_file_type != "all":
        if normalized_file_type == "excel":
            conditions.append("(a.mime_type ILIKE %s OR a.name ILIKE %s OR a.name ILIKE %s)")
            params.extend(["%spreadsheet%", "%.xlsx", "%.xls"])
        elif normalized_file_type == "word":
            conditions.append("(a.mime_type ILIKE %s OR a.name ILIKE %s)")
            params.extend(["%wordprocessingml%", "%.docx"])
        else:
            conditions.append("a.artifact_type = %s")
            params.append(normalized_file_type)

    params.append(max(1, min(limit, 200)))
    rows = fetch_all(
        f"""
        SELECT
            a.id, a.run_id, a.artifact_type, a.name, a.mime_type, a.size_bytes,
            a.external_ref, a.metadata, a.created_at, a.expires_at, a.downloadable,
            r.app_id, r.app_name, r.run_type, r.status, r.username, r.position
        FROM automation_run_artifacts a
        JOIN automation_runs r ON r.id = a.run_id
        WHERE {' AND '.join(conditions)}
        ORDER BY a.created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )
    return [_map_file_row(row) for row in rows]


def get_generated_file(
    artifact_id: str,
    *,
    current_user: dict,
) -> dict[str, Any]:
    item = get_generated_file_storage_reference(artifact_id, current_user=current_user)
    return {
        "id": item["id"],
        "filename": item["filename"],
        "mime_type": item["mime_type"],
        "content": Path(item["storage_path"]).read_bytes(),
    }


def get_generated_file_storage_reference(
    artifact_id: str,
    *,
    current_user: dict,
) -> dict[str, Any]:
    cleanup_expired_generated_files()
    row = fetch_one(
        """
        SELECT
            a.id, a.run_id, a.artifact_type, a.name, a.mime_type, a.size_bytes,
            a.external_ref, a.metadata, a.created_at, a.expires_at, a.downloadable,
            a.storage_path, r.app_id, r.app_name, r.run_type, r.status,
            r.user_id, r.username, r.position
        FROM automation_run_artifacts a
        JOIN automation_runs r ON r.id = a.run_id
        WHERE a.id = %s;
        """,
        (artifact_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    owner_user_id = str(row[16]) if row[16] else None
    owner_position = row[18]
    if current_user.get("role") != "admin" and (
        owner_user_id != current_user.get("id")
        or owner_position != current_user.get("position")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权下载该文件")

    if not row[10] or not row[11]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该产物没有可下载文件")

    expires_at = row[9]
    if expires_at and expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="文件已超过 1 个月保存期")

    path = Path(str(row[11]))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件存储已不存在")

    return {
        "id": str(row[0]),
        "run_id": str(row[1]),
        "artifact_type": row[2],
        "filename": row[3],
        "mime_type": row[4] or "application/octet-stream",
        "size_bytes": row[5],
        "metadata": sanitize_metadata(row[7] or {}),
        "created_at": isoformat(row[8]),
        "storage_path": str(path),
        "app_id": row[12],
        "app_name": row[13],
        "run_type": row[14],
        "run_status": row[15],
        "owner_user_id": owner_user_id,
        "owner_position": owner_position,
    }


def get_latest_generated_file_for_thread(
    *,
    thread_id: str,
    current_user: dict,
    allowed_types: set[str] | None = None,
) -> dict[str, Any] | None:
    files = list_recent_generated_files_for_thread(
        thread_id=thread_id,
        current_user=current_user,
        allowed_types=allowed_types,
        limit=10,
    )
    return files[0] if files else None


def list_recent_generated_files_for_thread(
    *,
    thread_id: str,
    current_user: dict,
    allowed_types: set[str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    cleanup_expired_generated_files()
    types = allowed_types or DOWNLOADABLE_ARTIFACT_TYPES
    rows = fetch_all(
        """
        SELECT
            a.id, a.run_id, a.artifact_type, a.name, a.mime_type, a.size_bytes,
            a.external_ref, a.metadata, a.created_at, a.expires_at, a.downloadable,
            a.storage_path, r.app_id, r.app_name, r.run_type, r.status,
            r.user_id, r.username, r.position
        FROM automation_run_artifacts a
        JOIN automation_runs r ON r.id = a.run_id
        WHERE r.thread_id = %s
          AND a.downloadable = TRUE
          AND a.storage_path IS NOT NULL
          AND (a.expires_at IS NULL OR a.expires_at > now())
          AND a.artifact_type = ANY(%s)
        ORDER BY a.created_at DESC
        LIMIT %s;
        """,
        (thread_id, list(types), max(1, min(limit, 20))),
    )

    files: list[dict[str, Any]] = []
    for row in rows:
        try:
            files.append(get_generated_file_storage_reference(str(row[0]), current_user=current_user))
        except HTTPException:
            continue
    return files


def cleanup_expired_generated_files() -> int:
    rows = fetch_all(
        """
        SELECT id, storage_path
        FROM automation_run_artifacts
        WHERE downloadable = TRUE
          AND storage_path IS NOT NULL
          AND expires_at IS NOT NULL
          AND expires_at <= now();
        """
    )
    deleted = 0
    for row in rows:
        path = Path(str(row[1]))
        try:
            if path.exists() and path.is_file():
                path.unlink()
                deleted += 1
        except OSError:
            pass
    if rows:
        execute(
            """
            UPDATE automation_run_artifacts
            SET downloadable = FALSE
            WHERE expires_at IS NOT NULL AND expires_at <= now();
            """
        )
    return deleted


def _map_file_row(row) -> dict[str, Any]:
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
        "expires_at": isoformat(row[9]),
        "downloadable": bool(row[10]),
        "app_id": row[11],
        "app_name": row[12],
        "run_type": row[13],
        "status": row[14],
        "username": row[15],
        "position": row[16],
    }


def _date_range_since(value: str | None) -> datetime | None:
    now = datetime.now(timezone.utc)
    if value == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if value == "7d":
        return now - timedelta(days=7)
    if value == "30d" or not value:
        return now - timedelta(days=30)
    if value == "all":
        return None
    return now - timedelta(days=30)


def _storage_dir() -> Path:
    path = Path(settings.generated_file_storage_dir)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _safe_filename(value: str) -> str:
    safe = preview_text(value, limit=180) or "generated_file"
    safe = safe.replace("/", "_").replace("\\", "_").replace(":", "_")
    return safe.strip() or "generated_file"
