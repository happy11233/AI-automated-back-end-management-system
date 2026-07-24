from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from fastapi import HTTPException, status

from app.config import settings
from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json
from app.services.logging_service import write_audit_log
from app.services.platform_draft_service import ACTION_TYPES
from app.services.run_record_service import sanitize_metadata
from app.services.platform_action_security_service import (
    open_platform_action_request,
    preview_platform_action_executor_url,
    validate_platform_action_executor_url,
)


EXECUTOR_TYPES = {"webhook", "amazon_sp_api", "n8n", "yingdao", "customer_service_system", "erp_writeback"}
HEALTH_STATUSES = {"unknown", "healthy", "unhealthy", "not_configured", "disabled"}


def ensure_platform_action_executor_config_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS platform_action_executors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            executor_type TEXT NOT NULL CHECK (
                executor_type IN ('webhook', 'amazon_sp_api', 'n8n', 'yingdao', 'customer_service_system', 'erp_writeback')
            ),
            action_types TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            webhook_url TEXT,
            api_key TEXT,
            timeout_seconds INTEGER NOT NULL DEFAULT 12 CHECK (timeout_seconds BETWEEN 1 AND 120),
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            health_status TEXT NOT NULL DEFAULT 'unknown'
                CHECK (health_status IN ('unknown', 'healthy', 'unhealthy', 'not_configured', 'disabled')),
            health_message TEXT,
            last_checked_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_action_executors_enabled_updated_at
        ON platform_action_executors(enabled, updated_at DESC);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_action_executors_action_types
        ON platform_action_executors USING GIN(action_types);
        """
    )


def list_platform_action_executors() -> dict[str, Any]:
    items = [
        _map_executor_row(row)
        for row in fetch_all(
            """
            SELECT
                id, name, executor_type, action_types, webhook_url, api_key,
                timeout_seconds, enabled, health_status, health_message,
                last_checked_at, metadata, created_by, updated_by, created_at, updated_at
            FROM platform_action_executors
            ORDER BY enabled DESC, updated_at DESC, created_at DESC;
            """
        )
    ]
    fallback = _environment_fallback_executor()
    if fallback:
        items.append(fallback)

    return {
        "summary": _summary(items),
        "items": [_public_executor(item) for item in items],
        "action_types": _action_type_options(),
        "executor_types": _executor_type_options(),
    }


def get_platform_action_executor(executor_id: str) -> dict[str, Any]:
    if executor_id == "env_platform_action_executor":
        fallback = _environment_fallback_executor()
        if fallback:
            return _public_executor(fallback)

    row = fetch_one(
        """
        SELECT
            id, name, executor_type, action_types, webhook_url, api_key,
            timeout_seconds, enabled, health_status, health_message,
            last_checked_at, metadata, created_by, updated_by, created_at, updated_at
        FROM platform_action_executors
        WHERE id = %s
        LIMIT 1;
        """,
        (executor_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="外部执行器不存在")
    return _public_executor(_map_executor_row(row))


def create_platform_action_executor(*, payload: dict[str, Any], current_user: dict) -> dict[str, Any]:
    normalized = _normalize_executor_payload(payload, partial=False)
    row = fetch_one(
        """
        INSERT INTO platform_action_executors (
            name, executor_type, action_types, webhook_url, api_key,
            timeout_seconds, enabled, health_status, health_message,
            metadata, created_by, updated_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'unknown', NULL, %s::jsonb, %s, %s)
        RETURNING
            id, name, executor_type, action_types, webhook_url, api_key,
            timeout_seconds, enabled, health_status, health_message,
            last_checked_at, metadata, created_by, updated_by, created_at, updated_at;
        """,
        (
            normalized["name"],
            normalized["executor_type"],
            normalized["action_types"],
            normalized["webhook_url"],
            normalized["api_key"],
            normalized["timeout_seconds"],
            normalized["enabled"],
            dumps_json(sanitize_metadata(normalized.get("metadata") or {})),
            current_user.get("id"),
            current_user.get("id"),
        ),
    )
    item = _map_executor_row(row)
    write_audit_log(
        user_id=current_user.get("id"),
        action="platform_action_executor.create",
        resource_type="platform_action_executor",
        resource_id=item["id"],
        metadata={
            "name": item["name"],
            "executor_type": item["executor_type"],
            "action_types": item["action_types"],
            "enabled": item["enabled"],
        },
    )
    return _public_executor(item)


def update_platform_action_executor(
    *,
    executor_id: str,
    payload: dict[str, Any],
    current_user: dict,
) -> dict[str, Any]:
    if executor_id == "env_platform_action_executor":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="环境变量兜底执行器不能在后台修改")

    existing = _get_executor_private(executor_id)
    normalized = _normalize_executor_payload(payload, partial=True)
    next_values = {
        "name": normalized.get("name", existing["name"]),
        "executor_type": normalized.get("executor_type", existing["executor_type"]),
        "action_types": normalized.get("action_types", existing["action_types"]),
        "webhook_url": existing["webhook_url"] if normalized.get("webhook_url_unchanged") else normalized.get("webhook_url", existing["webhook_url"]),
        "api_key": existing["api_key"] if normalized.get("api_key_unchanged") else normalized.get("api_key", existing["api_key"]),
        "timeout_seconds": normalized.get("timeout_seconds", existing["timeout_seconds"]),
        "enabled": normalized.get("enabled", existing["enabled"]),
        "metadata": normalized.get("metadata", existing["metadata"]),
    }
    row = fetch_one(
        """
        UPDATE platform_action_executors
        SET
            name = %s,
            executor_type = %s,
            action_types = %s,
            webhook_url = %s,
            api_key = %s,
            timeout_seconds = %s,
            enabled = %s,
            health_status = CASE WHEN %s THEN health_status ELSE 'disabled' END,
            health_message = CASE WHEN %s THEN health_message ELSE '执行器已禁用。' END,
            metadata = %s::jsonb,
            updated_by = %s,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, name, executor_type, action_types, webhook_url, api_key,
            timeout_seconds, enabled, health_status, health_message,
            last_checked_at, metadata, created_by, updated_by, created_at, updated_at;
        """,
        (
            next_values["name"],
            next_values["executor_type"],
            next_values["action_types"],
            next_values["webhook_url"],
            next_values["api_key"],
            next_values["timeout_seconds"],
            next_values["enabled"],
            next_values["enabled"],
            next_values["enabled"],
            dumps_json(sanitize_metadata(next_values.get("metadata") or {})),
            current_user.get("id"),
            executor_id,
        ),
    )
    item = _map_executor_row(row)
    write_audit_log(
        user_id=current_user.get("id"),
        action="platform_action_executor.update",
        resource_type="platform_action_executor",
        resource_id=item["id"],
        metadata={
            "name": item["name"],
            "executor_type": item["executor_type"],
            "action_types": item["action_types"],
            "enabled": item["enabled"],
        },
    )
    return _public_executor(item)


def delete_platform_action_executor(*, executor_id: str, current_user: dict) -> dict[str, Any]:
    if executor_id == "env_platform_action_executor":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="环境变量兜底执行器不能删除")

    row = fetch_one(
        """
        DELETE FROM platform_action_executors
        WHERE id = %s
        RETURNING id, name, executor_type, action_types, enabled;
        """,
        (executor_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="外部执行器不存在")
    write_audit_log(
        user_id=current_user.get("id"),
        action="platform_action_executor.delete",
        resource_type="platform_action_executor",
        resource_id=str(row[0]),
        metadata={
            "name": row[1],
            "executor_type": row[2],
            "action_types": list(row[3] or []),
            "enabled": bool(row[4]),
        },
    )
    return {"ok": True, "id": str(row[0])}


def check_platform_action_executor_health(*, executor_id: str, current_user: dict) -> dict[str, Any]:
    executor = _environment_fallback_executor() if executor_id == "env_platform_action_executor" else _get_executor_private(executor_id)
    if executor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="外部执行器不存在")

    health = _check_executor_health(executor)
    if not executor.get("is_environment_fallback"):
        row = fetch_one(
            """
            UPDATE platform_action_executors
            SET
                health_status = %s,
                health_message = %s,
                last_checked_at = now(),
                updated_by = %s,
                updated_at = now()
            WHERE id = %s
            RETURNING
                id, name, executor_type, action_types, webhook_url, api_key,
                timeout_seconds, enabled, health_status, health_message,
                last_checked_at, metadata, created_by, updated_by, created_at, updated_at;
            """,
            (
                health["health_status"],
                health["health_message"],
                current_user.get("id"),
                executor_id,
            ),
        )
        executor = _map_executor_row(row)
    else:
        executor = {**executor, **health, "last_checked_at": _now_iso()}

    write_audit_log(
        user_id=current_user.get("id"),
        action="platform_action_executor.health_check",
        resource_type="platform_action_executor",
        resource_id=executor_id,
        metadata={
            "name": executor.get("name"),
            "executor_type": executor.get("executor_type"),
            "health_status": executor.get("health_status"),
        },
    )
    return _public_executor(executor)


def resolve_platform_action_executor(action_type: str) -> dict[str, Any] | None:
    if action_type not in ACTION_TYPES:
        raise ValueError("无效平台动作类型")

    row = fetch_one(
        """
        SELECT
            id, name, executor_type, action_types, webhook_url, api_key,
            timeout_seconds, enabled, health_status, health_message,
            last_checked_at, metadata, created_by, updated_by, created_at, updated_at
        FROM platform_action_executors
        WHERE enabled = TRUE
          AND %s = ANY(action_types)
          AND webhook_url IS NOT NULL
          AND btrim(webhook_url) <> ''
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1;
        """,
        (action_type,),
    )
    if row:
        return _map_executor_row(row)

    return _environment_fallback_executor()


def _get_executor_private(executor_id: str) -> dict[str, Any]:
    row = fetch_one(
        """
        SELECT
            id, name, executor_type, action_types, webhook_url, api_key,
            timeout_seconds, enabled, health_status, health_message,
            last_checked_at, metadata, created_by, updated_by, created_at, updated_at
        FROM platform_action_executors
        WHERE id = %s
        LIMIT 1;
        """,
        (executor_id,),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="外部执行器不存在")
    return _map_executor_row(row)


def _normalize_executor_payload(payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    if not partial or "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行器名称不能为空")
        normalized["name"] = name[:120]

    if not partial or "executor_type" in payload:
        executor_type = str(payload.get("executor_type") or "").strip()
        if executor_type not in EXECUTOR_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效执行器类型")
        normalized["executor_type"] = executor_type

    if not partial or "action_types" in payload:
        action_types = []
        for item in payload.get("action_types") or []:
            value = str(item).strip()
            if value in ACTION_TYPES and value not in action_types:
                action_types.append(value)
        if not action_types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少选择一个平台动作")
        normalized["action_types"] = action_types

    if not partial or "webhook_url" in payload:
        webhook_url = str(payload.get("webhook_url") or "").strip()
        if webhook_url == "__UNCHANGED__":
            normalized["webhook_url_unchanged"] = True
        elif webhook_url:
            try:
                normalized["webhook_url"] = validate_platform_action_executor_url(webhook_url)
            except ValueError as error:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
        else:
            normalized["webhook_url"] = None

    if "api_key" in payload:
        api_key = payload.get("api_key")
        if api_key is None:
            normalized["api_key"] = None
        else:
            api_key_text = str(api_key)
            if api_key_text == "__UNCHANGED__":
                normalized["api_key_unchanged"] = True
            else:
                normalized["api_key"] = api_key_text.strip() or None
    elif not partial:
        normalized["api_key"] = None

    if not partial or "timeout_seconds" in payload:
        timeout_seconds = int(payload.get("timeout_seconds") or settings.platform_action_executor_timeout_seconds)
        normalized["timeout_seconds"] = max(1, min(timeout_seconds, 120))

    if not partial or "enabled" in payload:
        normalized["enabled"] = bool(payload.get("enabled", True))

    if "metadata" in payload:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        normalized["metadata"] = metadata
    elif not partial:
        normalized["metadata"] = {}

    return normalized


def _check_executor_health(executor: dict[str, Any]) -> dict[str, str]:
    if not executor.get("enabled"):
        return {"health_status": "disabled", "health_message": "执行器已禁用。"}

    webhook_url = executor.get("webhook_url")
    if not webhook_url:
        return {"health_status": "not_configured", "health_message": "未配置 Webhook URL。"}

    payload = {
        "action_type": "health_check",
        "health_check": True,
        "executor_id": executor.get("id"),
        "executor_type": executor.get("executor_type"),
        "checked_at": _now_iso(),
    }
    try:
        response = _post_json(
            webhook_url=str(webhook_url),
            payload=payload,
            api_key=executor.get("api_key"),
            timeout_seconds=int(executor.get("timeout_seconds") or settings.platform_action_executor_timeout_seconds),
        )
        return {
            "health_status": "healthy",
            "health_message": str(response.get("message") or response.get("status") or "执行器健康检查通过。")[:500],
        }
    except Exception as error:
        return {
            "health_status": "unhealthy",
            "health_message": str(error)[:500],
        }


def _post_json(
    *,
    webhook_url: str,
    payload: dict[str, Any],
    api_key: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "company-rag-agent-platform-action-executor-config/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(webhook_url, data=body, headers=headers, method="POST")
    try:
        with open_platform_action_request(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw.strip() else {}
            if not isinstance(parsed, dict):
                return {"raw": parsed, "http_status": response.status}
            return {**parsed, "http_status": response.status}
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {raw[:500]}") from error
    except URLError as error:
        raise RuntimeError(f"连接外部执行器失败：{error.reason}") from error
    except TimeoutError as error:
        raise RuntimeError("连接外部执行器超时") from error


def _environment_fallback_executor() -> dict[str, Any] | None:
    if not settings.platform_action_executor_webhook_url:
        return None
    return {
        "id": "env_platform_action_executor",
        "name": "环境变量兜底执行器",
        "executor_type": "webhook",
        "action_types": sorted(ACTION_TYPES),
        "webhook_url": str(settings.platform_action_executor_webhook_url),
        "api_key": settings.platform_action_executor_api_key,
        "timeout_seconds": settings.platform_action_executor_timeout_seconds,
        "enabled": True,
        "health_status": "unknown",
        "health_message": "由 PLATFORM_ACTION_EXECUTOR_WEBHOOK_URL 提供，后台只读。",
        "last_checked_at": None,
        "metadata": {"managed_by": "environment"},
        "created_by": None,
        "updated_by": None,
        "created_at": None,
        "updated_at": None,
        "is_environment_fallback": True,
    }


def _map_executor_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "name": row[1],
        "executor_type": row[2],
        "action_types": list(row[3] or []),
        "webhook_url": row[4],
        "api_key": row[5],
        "timeout_seconds": int(row[6] or settings.platform_action_executor_timeout_seconds),
        "enabled": bool(row[7]),
        "health_status": row[8],
        "health_message": row[9],
        "last_checked_at": row[10].isoformat() if row[10] else None,
        "metadata": row[11] or {},
        "created_by": str(row[12]) if row[12] else None,
        "updated_by": str(row[13]) if row[13] else None,
        "created_at": row[14].isoformat() if row[14] else None,
        "updated_at": row[15].isoformat() if row[15] else None,
        "is_environment_fallback": False,
    }


def _public_executor(item: dict[str, Any]) -> dict[str, Any]:
    webhook_url = item.get("webhook_url")
    return {
        "id": item["id"],
        "name": item["name"],
        "executor_type": item["executor_type"],
        "executor_type_label": _executor_type_label(item["executor_type"]),
        "action_types": item["action_types"],
        "action_type_labels": [_action_type_label(value) for value in item["action_types"]],
        "webhook_url": None,
        "webhook_url_preview": preview_platform_action_executor_url(str(webhook_url)) if webhook_url else None,
        "api_key_configured": bool(item.get("api_key")),
        "api_key_preview": "***已配置***" if item.get("api_key") else None,
        "timeout_seconds": item["timeout_seconds"],
        "enabled": item["enabled"],
        "configured": bool(webhook_url),
        "health_status": item["health_status"],
        "health_message": item["health_message"],
        "last_checked_at": item["last_checked_at"],
        "metadata": sanitize_metadata(item.get("metadata") or {}),
        "is_environment_fallback": bool(item.get("is_environment_fallback")),
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def _summary(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(items),
        "enabled": sum(1 for item in items if item.get("enabled")),
        "configured": sum(1 for item in items if item.get("webhook_url")),
        "healthy": sum(1 for item in items if item.get("health_status") == "healthy"),
        "needs_config": sum(1 for item in items if not item.get("webhook_url")),
    }


def _action_type_options() -> list[dict[str, str]]:
    return [{"value": value, "label": _action_type_label(value)} for value in sorted(ACTION_TYPES)]


def _executor_type_options() -> list[dict[str, str]]:
    return [{"value": value, "label": _executor_type_label(value)} for value in sorted(EXECUTOR_TYPES)]


def _action_type_label(action_type: str) -> str:
    labels = {
        "write_listing_draft": "写入 Listing 草稿",
        "publish_listing": "发布 Listing",
        "write_customer_reply": "写入客服回复草稿",
        "send_customer_reply": "发送客服回复",
    }
    return labels.get(action_type, action_type)


def _executor_type_label(executor_type: str) -> str:
    labels = {
        "webhook": "通用 Webhook",
        "amazon_sp_api": "Amazon SP-API",
        "n8n": "n8n 工作流",
        "yingdao": "影刀 RPA",
        "customer_service_system": "客服系统",
        "erp_writeback": "ERP 写回",
    }
    return labels.get(executor_type, executor_type)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
