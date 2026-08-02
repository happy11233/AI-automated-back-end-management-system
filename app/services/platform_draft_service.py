from __future__ import annotations

import json
import re
from typing import Any

from app.db import execute, fetch_all, fetch_one
from app.json_utils import dumps_json
from app.permissions import is_valid_position
from app.services.run_record_service import sanitize_metadata, sanitize_text


DRAFT_TYPES = {"listing", "customer_reply"}
DRAFT_STATUSES = {"pending_review", "approved", "published", "rejected"}
WRITEBACK_STATUSES = {"draft_saved", "rpa_ready", "external_synced", "failed"}
ACTION_TYPES = {
    "write_listing_draft",
    "write_customer_reply",
    "publish_listing",
    "send_customer_reply",
}
EXECUTOR_TYPES = {
    "webhook",
    "amazon_sp_api",
    "n8n",
    "playwright_mcp",
    "yingdao",
    "customer_service_system",
    "erp_writeback",
    "manual_waiting",
}
EXECUTION_STATUSES = {"waiting_executor", "running", "succeeded", "failed"}
TASK_STATUSES = {"queued", "dispatching", "waiting_callback", "succeeded", "failed", "cancelled"}


def ensure_platform_draft_schema() -> None:
    execute(
        """
        CREATE TABLE IF NOT EXISTS platform_drafts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            draft_type TEXT NOT NULL CHECK (draft_type IN ('listing', 'customer_reply')),
            platform TEXT NOT NULL DEFAULT 'amazon',
            external_target TEXT NOT NULL DEFAULT 'amazon_seller_central',
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_review'
                CHECK (status IN ('pending_review', 'approved', 'published', 'rejected')),
            position TEXT NOT NULL CHECK (position IN ('operations', 'customer_service', 'finance')),
            owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            source_run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
            source_resource_type TEXT,
            source_resource_id TEXT,
            content JSONB NOT NULL DEFAULT '{}'::jsonb,
            writeback_status TEXT NOT NULL DEFAULT 'draft_saved'
                CHECK (writeback_status IN ('draft_saved', 'rpa_ready', 'external_synced', 'failed')),
            writeback_message TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_drafts_position_created_at
        ON platform_drafts(position, created_at DESC);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_drafts_owner_created_at
        ON platform_drafts(owner_user_id, created_at DESC);
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS platform_action_executions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            draft_id UUID NOT NULL REFERENCES platform_drafts(id) ON DELETE CASCADE,
            action_type TEXT NOT NULL CHECK (action_type IN ('write_listing_draft', 'write_customer_reply', 'publish_listing', 'send_customer_reply')),
            executor_type TEXT NOT NULL CHECK (
                executor_type IN (
                    'webhook',
                    'amazon_sp_api',
                    'n8n',
                    'playwright_mcp',
                    'yingdao',
                    'customer_service_system',
                    'erp_writeback',
                    'manual_waiting'
                )
            ),
            target TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('waiting_executor', 'running', 'succeeded', 'failed')),
            request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            error_message TEXT,
            run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
            triggered_by UUID REFERENCES users(id) ON DELETE SET NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    execute(
        """
        ALTER TABLE platform_action_executions
        DROP CONSTRAINT IF EXISTS platform_action_executions_action_type_check;

        ALTER TABLE platform_action_executions
        ADD CONSTRAINT platform_action_executions_action_type_check
        CHECK (action_type IN ('write_listing_draft', 'write_customer_reply', 'publish_listing', 'send_customer_reply'));
        """
    )
    execute(
        """
        ALTER TABLE platform_action_executions
        DROP CONSTRAINT IF EXISTS platform_action_executions_executor_type_check;

        ALTER TABLE platform_action_executions
        ADD CONSTRAINT platform_action_executions_executor_type_check
        CHECK (
            executor_type IN (
                'webhook',
                'amazon_sp_api',
                'n8n',
                'playwright_mcp',
                'yingdao',
                'customer_service_system',
                'erp_writeback',
                'manual_waiting'
            )
        );
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_action_executions_draft_created_at
        ON platform_action_executions(draft_id, created_at DESC);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_action_executions_status_created_at
        ON platform_action_executions(status, created_at DESC);
        """
    )
    execute(
        """
        CREATE TABLE IF NOT EXISTS platform_execution_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            draft_id UUID NOT NULL REFERENCES platform_drafts(id) ON DELETE CASCADE,
            latest_execution_id UUID REFERENCES platform_action_executions(id) ON DELETE SET NULL,
            action_type TEXT NOT NULL CHECK (action_type IN ('write_listing_draft', 'write_customer_reply', 'publish_listing', 'send_customer_reply')),
            target TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'dispatching', 'waiting_callback', 'succeeded', 'failed', 'cancelled')),
            request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            external_reference TEXT,
            callback_token TEXT NOT NULL DEFAULT encode(gen_random_bytes(24), 'hex'),
            attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
            max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
            last_error TEXT,
            requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
            next_attempt_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    execute(
        """
        ALTER TABLE platform_execution_tasks
        DROP CONSTRAINT IF EXISTS platform_execution_tasks_action_type_check;

        ALTER TABLE platform_execution_tasks
        ADD CONSTRAINT platform_execution_tasks_action_type_check
        CHECK (action_type IN ('write_listing_draft', 'write_customer_reply', 'publish_listing', 'send_customer_reply'));
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_execution_tasks_status_created_at
        ON platform_execution_tasks(status, created_at DESC);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_execution_tasks_draft_created_at
        ON platform_execution_tasks(draft_id, created_at DESC);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS idx_platform_execution_tasks_requested_by_created_at
        ON platform_execution_tasks(requested_by, created_at DESC);
        """
    )


def create_platform_draft(
    *,
    draft_type: str,
    platform: str,
    external_target: str,
    title: str,
    position: str,
    owner_user_id: str | None,
    source_run_id: str | None,
    source_resource_type: str | None,
    source_resource_id: str | None,
    content: dict[str, Any],
    writeback_status: str = "draft_saved",
    writeback_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if draft_type not in DRAFT_TYPES:
        raise ValueError("无效草稿类型")
    if not is_valid_position(position):
        raise ValueError("无效岗位")

    row = fetch_one(
        """
        INSERT INTO platform_drafts (
            draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata
        )
        VALUES (
            %s, %s, %s, %s, 'pending_review', %s,
            %s, %s, %s, %s,
            %s::jsonb, %s, %s, %s::jsonb
        )
        RETURNING
            id, draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata,
            created_at, updated_at;
        """,
        (
            draft_type,
            platform,
            external_target,
            _clean_title(title),
            position,
            owner_user_id,
            source_run_id,
            source_resource_type,
            source_resource_id,
            dumps_json(content),
            writeback_status,
            writeback_message,
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    return _map_draft_row(row)


def list_platform_drafts(
    *,
    current_user: dict,
    draft_type: str | None = None,
    status_value: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    conditions = ["1 = 1"]
    params: list[Any] = []

    _apply_draft_owner_filter(
        conditions=conditions,
        params=params,
        current_user=current_user,
    )

    if draft_type:
        conditions.append("draft_type = %s")
        params.append(draft_type)

    if status_value:
        conditions.append("status = %s")
        params.append(status_value)

    params.append(limit)
    rows = fetch_all(
        f"""
        SELECT
            id, draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata,
            created_at, updated_at
        FROM platform_drafts
        WHERE {" AND ".join(conditions)}
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )
    return [_map_draft_row(row) for row in rows]


def get_latest_platform_draft_for_source_run(
    *,
    source_run_id: str,
    current_user: dict,
) -> dict[str, Any] | None:
    conditions = ["source_run_id = %s"]
    params: list[Any] = [source_run_id]

    _apply_draft_owner_filter(
        conditions=conditions,
        params=params,
        current_user=current_user,
    )

    row = fetch_one(
        f"""
        SELECT
            id, draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata,
            created_at, updated_at
        FROM platform_drafts
        WHERE {" AND ".join(conditions)}
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1;
        """,
        tuple(params),
    )
    return _map_draft_row(row) if row else None


def get_platform_draft(*, draft_id: str, current_user: dict) -> dict[str, Any] | None:
    conditions = ["id = %s"]
    params: list[Any] = [draft_id]

    _apply_draft_owner_filter(
        conditions=conditions,
        params=params,
        current_user=current_user,
    )

    row = fetch_one(
        f"""
        SELECT
            id, draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata,
            created_at, updated_at
        FROM platform_drafts
        WHERE {" AND ".join(conditions)}
        LIMIT 1;
        """,
        tuple(params),
    )
    return _map_draft_row(row) if row else None


def update_platform_draft_writeback(
    *,
    draft_id: str,
    writeback_status: str,
    writeback_message: str | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if writeback_status not in WRITEBACK_STATUSES:
        raise ValueError("无效写回状态")

    row = fetch_one(
        """
        UPDATE platform_drafts
        SET
            writeback_status = %s,
            writeback_message = %s,
            metadata = metadata || %s::jsonb,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata,
            created_at, updated_at;
        """,
        (
            writeback_status,
            writeback_message,
            dumps_json(sanitize_metadata(metadata or {})),
            draft_id,
        ),
    )
    if row is None:
        raise ValueError("平台草稿不存在")
    return _map_draft_row(row)


def update_platform_draft_status(
    *,
    draft_id: str,
    status_value: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status_value not in DRAFT_STATUSES:
        raise ValueError("无效草稿状态")

    row = fetch_one(
        """
        UPDATE platform_drafts
        SET
            status = %s,
            metadata = metadata || %s::jsonb,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_type, platform, external_target, title, status, position,
            owner_user_id, source_run_id, source_resource_type, source_resource_id,
            content, writeback_status, writeback_message, metadata,
            created_at, updated_at;
        """,
        (
            status_value,
            dumps_json(sanitize_metadata(metadata or {})),
            draft_id,
        ),
    )
    if row is None:
        raise ValueError("平台草稿不存在")
    return _map_draft_row(row)


def create_platform_action_execution(
    *,
    draft_id: str,
    action_type: str,
    executor_type: str,
    target: str,
    status_value: str,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
    run_id: str | None = None,
    triggered_by: str | None = None,
    finished: bool = False,
) -> dict[str, Any]:
    if action_type not in ACTION_TYPES:
        raise ValueError("无效平台动作类型")
    if executor_type not in EXECUTOR_TYPES:
        raise ValueError("无效执行器类型")
    if status_value not in EXECUTION_STATUSES:
        raise ValueError("无效执行状态")

    row = fetch_one(
        """
        INSERT INTO platform_action_executions (
            draft_id, action_type, executor_type, target, status,
            request_payload, response_payload, error_message, run_id,
            triggered_by, finished_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s::jsonb, %s::jsonb, %s, %s,
            %s, CASE WHEN %s THEN now() ELSE NULL END
        )
        RETURNING
            id, draft_id, action_type, executor_type, target, status,
            request_payload, response_payload, error_message, run_id,
            triggered_by, started_at, finished_at, created_at;
        """,
        (
            draft_id,
            action_type,
            executor_type,
            target,
            status_value,
            dumps_json(sanitize_metadata(request_payload)),
            dumps_json(sanitize_metadata(response_payload or {})),
            error_message,
            run_id,
            triggered_by,
            finished,
        ),
    )
    return _map_execution_row(row)


def finish_platform_action_execution(
    *,
    execution_id: str,
    status_value: str,
    response_payload: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    if status_value not in EXECUTION_STATUSES:
        raise ValueError("无效执行状态")

    row = fetch_one(
        """
        UPDATE platform_action_executions
        SET
            status = %s,
            response_payload = %s::jsonb,
            error_message = %s,
            finished_at = now()
        WHERE id = %s
        RETURNING
            id, draft_id, action_type, executor_type, target, status,
            request_payload, response_payload, error_message, run_id,
            triggered_by, started_at, finished_at, created_at;
        """,
        (
            status_value,
            dumps_json(sanitize_metadata(response_payload or {})),
            error_message,
            execution_id,
        ),
    )
    if row is None:
        raise ValueError("平台动作执行记录不存在")
    return _map_execution_row(row)


def list_platform_action_executions(
    *,
    draft_id: str,
    current_user: dict,
    limit: int = 20,
) -> list[dict[str, Any]]:
    draft = get_platform_draft(draft_id=draft_id, current_user=current_user)
    if draft is None:
        return []

    rows = fetch_all(
        """
        SELECT
            id, draft_id, action_type, executor_type, target, status,
            request_payload, response_payload, error_message, run_id,
            triggered_by, started_at, finished_at, created_at
        FROM platform_action_executions
        WHERE draft_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (draft_id, max(1, min(limit, 100))),
    )
    return [_map_execution_row(row) for row in rows]


def create_platform_execution_task(
    *,
    draft_id: str,
    action_type: str,
    target: str,
    request_payload: dict[str, Any],
    requested_by: str | None,
    max_attempts: int = 3,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if action_type not in ACTION_TYPES:
        raise ValueError("无效平台动作类型")

    row = fetch_one(
        """
        INSERT INTO platform_execution_tasks (
            draft_id, action_type, target, status, request_payload,
            requested_by, max_attempts, metadata
        )
        VALUES (%s, %s, %s, 'queued', %s::jsonb, %s, %s, %s::jsonb)
        RETURNING
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at;
        """,
        (
            draft_id,
            action_type,
            target,
            dumps_json(sanitize_metadata(request_payload)),
            requested_by,
            max(1, min(max_attempts, 10)),
            dumps_json(sanitize_metadata(metadata or {})),
        ),
    )
    return _map_task_row(row)


def update_platform_execution_task_payload(
    *,
    task_id: str,
    request_payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = fetch_one(
        """
        UPDATE platform_execution_tasks
        SET
            request_payload = %s::jsonb,
            metadata = metadata || %s::jsonb,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at;
        """,
        (
            dumps_json(sanitize_metadata(request_payload)),
            dumps_json(sanitize_metadata(metadata or {})),
            task_id,
        ),
    )
    if row is None:
        raise ValueError("平台执行任务不存在")
    return _map_task_row(row)


def mark_platform_execution_task_dispatching(
    *,
    task_id: str,
    latest_execution_id: str,
    target: str,
) -> dict[str, Any]:
    row = fetch_one(
        """
        UPDATE platform_execution_tasks
        SET
            latest_execution_id = %s,
            target = %s,
            status = 'dispatching',
            attempt_count = attempt_count + 1,
            last_error = NULL,
            completed_at = NULL,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at;
        """,
        (latest_execution_id, target, task_id),
    )
    if row is None:
        raise ValueError("平台执行任务不存在")
    return _map_task_row(row)


def mark_platform_execution_task_waiting_executor(
    *,
    task_id: str,
    latest_execution_id: str,
    message: str,
) -> dict[str, Any]:
    row = fetch_one(
        """
        UPDATE platform_execution_tasks
        SET
            latest_execution_id = %s,
            status = 'queued',
            last_error = %s,
            response_payload = %s::jsonb,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at;
        """,
        (
            latest_execution_id,
            message,
            dumps_json({"configured": False, "message": message}),
            task_id,
        ),
    )
    if row is None:
        raise ValueError("平台执行任务不存在")
    return _map_task_row(row)


def mark_platform_execution_task_waiting_callback(
    *,
    task_id: str,
    response_payload: dict[str, Any],
    external_reference: str | None = None,
) -> dict[str, Any]:
    row = fetch_one(
        """
        UPDATE platform_execution_tasks
        SET
            status = 'waiting_callback',
            response_payload = %s::jsonb,
            external_reference = COALESCE(%s, external_reference),
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at;
        """,
        (
            dumps_json(sanitize_metadata(response_payload)),
            external_reference,
            task_id,
        ),
    )
    if row is None:
        raise ValueError("平台执行任务不存在")
    return _map_task_row(row)


def finish_platform_execution_task(
    *,
    task_id: str,
    status_value: str,
    response_payload: dict[str, Any] | None = None,
    external_reference: str | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status_value not in {"succeeded", "failed", "cancelled"}:
        raise ValueError("无效任务完成状态")

    row = fetch_one(
        """
        UPDATE platform_execution_tasks
        SET
            status = %s,
            response_payload = %s::jsonb,
            external_reference = COALESCE(%s, external_reference),
            last_error = %s,
            completed_at = now(),
            metadata = metadata || %s::jsonb,
            updated_at = now()
        WHERE id = %s
        RETURNING
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at;
        """,
        (
            status_value,
            dumps_json(sanitize_metadata(response_payload or {})),
            external_reference,
            error_message,
            dumps_json(sanitize_metadata(metadata or {})),
            task_id,
        ),
    )
    if row is None:
        raise ValueError("平台执行任务不存在")
    return _map_task_row(row)


def list_platform_execution_tasks(
    *,
    current_user: dict,
    status_value: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    conditions = ["1 = 1"]
    params: list[Any] = []

    _apply_task_owner_filter(
        conditions=conditions,
        params=params,
        current_user=current_user,
    )

    if status_value:
        conditions.append("t.status = %s")
        params.append(status_value)

    params.append(limit)
    rows = fetch_all(
        f"""
        SELECT
            t.id, t.draft_id, t.latest_execution_id, t.action_type, t.target, t.status,
            t.request_payload, t.response_payload, t.external_reference, t.callback_token,
            t.attempt_count, t.max_attempts, t.last_error, t.requested_by, t.next_attempt_at,
            t.completed_at, t.metadata, t.created_at, t.updated_at,
            d.title, d.draft_type, d.status, d.position, d.writeback_status
        FROM platform_execution_tasks t
        JOIN platform_drafts d ON d.id = t.draft_id
        WHERE {" AND ".join(conditions)}
        ORDER BY t.created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )
    return [_map_task_row(row, with_draft=True) for row in rows]


def get_platform_execution_task(*, task_id: str, current_user: dict) -> dict[str, Any] | None:
    conditions = ["t.id = %s"]
    params: list[Any] = [task_id]

    _apply_task_owner_filter(
        conditions=conditions,
        params=params,
        current_user=current_user,
    )

    row = fetch_one(
        f"""
        SELECT
            t.id, t.draft_id, t.latest_execution_id, t.action_type, t.target, t.status,
            t.request_payload, t.response_payload, t.external_reference, t.callback_token,
            t.attempt_count, t.max_attempts, t.last_error, t.requested_by, t.next_attempt_at,
            t.completed_at, t.metadata, t.created_at, t.updated_at,
            d.title, d.draft_type, d.status, d.position, d.writeback_status
        FROM platform_execution_tasks t
        JOIN platform_drafts d ON d.id = t.draft_id
        WHERE {" AND ".join(conditions)}
        LIMIT 1;
        """,
        tuple(params),
    )
    return _map_task_row(row, with_draft=True) if row else None


def get_platform_execution_task_by_token(*, task_id: str, callback_token: str) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at
        FROM platform_execution_tasks
        WHERE id = %s AND callback_token = %s
        LIMIT 1;
        """,
        (task_id, callback_token),
    )
    return _map_task_row(row) if row else None


def get_active_platform_execution_task(*, draft_id: str, action_type: str) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT
            id, draft_id, latest_execution_id, action_type, target, status,
            request_payload, response_payload, external_reference, callback_token,
            attempt_count, max_attempts, last_error, requested_by, next_attempt_at,
            completed_at, metadata, created_at, updated_at
        FROM platform_execution_tasks
        WHERE draft_id = %s
          AND action_type = %s
          AND status IN ('queued', 'dispatching', 'waiting_callback')
        ORDER BY created_at DESC
        LIMIT 1;
        """,
        (draft_id, action_type),
    )
    return _map_task_row(row) if row else None


def _apply_draft_owner_filter(
    *,
    conditions: list[str],
    params: list[Any],
    current_user: dict,
    draft_alias: str | None = None,
) -> None:
    if current_user.get("role") == "admin":
        return

    prefix = f"{draft_alias}." if draft_alias else ""
    conditions.append(f"{prefix}position = %s")
    params.append(current_user.get("position"))
    conditions.append(f"{prefix}owner_user_id = %s")
    params.append(current_user.get("id"))


def _apply_task_owner_filter(
    *,
    conditions: list[str],
    params: list[Any],
    current_user: dict,
    draft_alias: str = "d",
    task_alias: str = "t",
) -> None:
    if current_user.get("role") == "admin":
        return

    conditions.append(f"{draft_alias}.position = %s")
    params.append(current_user.get("position"))
    conditions.append(f"({draft_alias}.owner_user_id = %s OR {task_alias}.requested_by = %s)")
    params.extend([current_user.get("id"), current_user.get("id")])


def listing_content_from_answer(answer: str, input_text: str) -> dict[str, Any]:
    parsed = _parse_listing_generation_answer(answer)
    review = parsed.get("review") if isinstance(parsed.get("review"), dict) else parsed
    amazon = parsed.get("amazon") if isinstance(parsed.get("amazon"), dict) else {}

    review_title_cn = _first_text(
        review,
        [
            "title_cn",
            "review_title_cn",
            "listing_title_cn",
            "listing_title",
        ],
    ) or _first_match(answer, [r"中文标题[^\n]*[:：]\s*(.+)", r"标题\s*[:：]\s*(.+)"])
    review_bullets_cn = _list_text(
        review.get("bullet_points_cn")
        or review.get("five_bullets_cn")
        or review.get("bullets_cn")
        or review.get("bullet_points")
        or review.get("five_bullets")
    ) or _extract_numbered_lines(answer, 5)
    review_description_cn = _first_text(
        review,
        [
            "description_cn",
            "product_description_cn",
            "review_description_cn",
        ],
    ) or _first_match(answer, [r"中文描述[^\n]*[:：]\s*(.+)", r"产品描述\s*[:：]\s*(.+)"])
    review_keywords_cn = _list_text(
        review.get("keywords_cn")
        or review.get("backend_search_terms_cn")
        or review.get("keywords")
    )
    review_promo_cn = _first_text(
        review,
        [
            "promo_copy_cn",
            "promotion_copy_cn",
            "review_promo_copy_cn",
        ],
    ) or _first_match(answer, [r"中文促销文案[^\n]*[:：]\s*(.+)", r"促销文案[^\n]*[:：]\s*(.+)"])
    review_notes_cn = _first_text(
        review,
        [
            "review_notes_cn",
            "notes_cn",
            "optimization_notes_cn",
        ],
    ) or _first_match(answer, [r"中文备注[^\n]*[:：]\s*(.+)", r"审核备注[^\n]*[:：]\s*(.+)"])

    amazon_title_en = _first_text(
        amazon,
        [
            "title_en",
            "listing_title_en",
            "amazon_title_en",
            "title",
        ],
    ) or _first_match(answer, [r"Title \(English\)\s*[:：]?\s*(.+)", r"英文标题[^\n]*[:：]\s*(.+)"])
    amazon_bullets_en = _list_text(
        amazon.get("bullet_points_en")
        or amazon.get("five_bullets_en")
        or amazon.get("bullets_en")
        or amazon.get("bullet_points")
    ) or _extract_numbered_lines(answer, 5)
    amazon_description_en = _first_text(
        amazon,
        [
            "description_en",
            "product_description_en",
            "amazon_description_en",
            "description",
        ],
    ) or _first_match(answer, [r"Product Description[^\n]*[:：]\s*(.+)", r"英文描述[^\n]*[:：]\s*(.+)"])
    amazon_keywords_en = _list_text(
        amazon.get("keywords_en")
        or amazon.get("backend_search_terms_en")
        or amazon.get("search_terms_en")
        or amazon.get("keywords")
    )
    amazon_promo_en = _first_text(
        amazon,
        [
            "promo_copy_en",
            "promotion_copy_en",
            "amazon_promo_copy_en",
            "promo_copy",
        ],
    ) or _first_match(answer, [r"Promo Copy[^\n]*[:：]\s*(.+)", r"English Promo[^\n]*[:：]\s*(.+)"])

    category_manual_required = True
    if isinstance(review.get("category_manual_required"), bool):
        category_manual_required = review["category_manual_required"]
    if isinstance(amazon.get("category_manual_required"), bool):
        category_manual_required = amazon["category_manual_required"]

    category_path_suggestion = _first_text(amazon, ["category_path", "category", "browse_node"])
    if not category_path_suggestion:
        category_path_suggestion = _first_match(answer, [r"类目路径[^\n]*[:：]\s*(.+)", r"Category Path[^\n]*[:：]\s*(.+)"])

    amazon_listing = {
        "title": amazon_title_en or "",
        "bullet_points": amazon_bullets_en,
        "description": amazon_description_en or "",
        "keywords": amazon_keywords_en,
        "promo_copy": amazon_promo_en or "",
        "category_path_suggestion": category_path_suggestion or None,
        "category_manual_required": category_manual_required,
    }

    return {
        "sku": _extract_sku(input_text),
        "marketplace": _extract_marketplace(input_text),
        "listing_title": review_title_cn or "AI 生成 Listing 草稿",
        "listing_title_cn": review_title_cn or "",
        "five_bullets": review_bullets_cn,
        "product_description": review_description_cn or "",
        "backend_search_terms": review_keywords_cn or "待人工确认后再整理为英文关键词。",
        "promo_copy": review_promo_cn or "",
        "review_notes": review_notes_cn or "",
        "category_manual_required": category_manual_required,
        "category_path_suggestion": category_path_suggestion or None,
        "amazon_listing": amazon_listing,
        "full_listing_package": answer,
        "source_input": input_text,
        "review_required": True,
        "publish_policy": "AI 已保存中文审核草稿；Amazon 实际上传时再转换为英文，类目必须运营人工手动选择，最终发布必须运营人工点击。",
    }


def customer_reply_content_from_message(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "customer_message_id": item["id"],
        "channel": item.get("channel"),
        "external_id": item.get("external_id"),
        "buyer_language": item.get("buyer_language"),
        "buyer_email": item.get("buyer_email"),
        "order_no": item.get("order_no"),
        "tracking_no": item.get("tracking_no"),
        "intent": item.get("intent"),
        "risk_level": item.get("risk_level"),
        "automation_decision": item.get("automation_decision"),
        "reply_draft": item.get("reply_draft"),
        "handoff_reason": item.get("handoff_reason"),
        "review_required": True,
        "send_policy": "AI 已保存客服回复草稿，低风险可由正式客服渠道发送，高风险必须人工审核。",
    }


def _map_draft_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "draft_type": row[1],
        "platform": row[2],
        "external_target": row[3],
        "title": row[4],
        "status": row[5],
        "position": row[6],
        "owner_user_id": str(row[7]) if row[7] else None,
        "source_run_id": str(row[8]) if row[8] else None,
        "source_resource_type": row[9],
        "source_resource_id": row[10],
        "content": row[11] or {},
        "writeback_status": row[12],
        "writeback_message": sanitize_text(row[13]) if row[13] else None,
        "metadata": row[14] or {},
        "created_at": row[15].isoformat() if row[15] else None,
        "updated_at": row[16].isoformat() if row[16] else None,
    }


def _map_execution_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "draft_id": str(row[1]),
        "action_type": row[2],
        "executor_type": row[3],
        "target": row[4],
        "status": row[5],
        "request_payload": row[6] or {},
        "response_payload": row[7] or {},
        "error_message": sanitize_text(row[8]) if row[8] else None,
        "run_id": str(row[9]) if row[9] else None,
        "triggered_by": str(row[10]) if row[10] else None,
        "started_at": row[11].isoformat() if row[11] else None,
        "finished_at": row[12].isoformat() if row[12] else None,
        "created_at": row[13].isoformat() if row[13] else None,
    }


def _map_task_row(row: tuple[Any, ...], *, with_draft: bool = False) -> dict[str, Any]:
    item = {
        "id": str(row[0]),
        "draft_id": str(row[1]),
        "latest_execution_id": str(row[2]) if row[2] else None,
        "action_type": row[3],
        "target": row[4],
        "status": row[5],
        "request_payload": row[6] or {},
        "response_payload": row[7] or {},
        "external_reference": row[8],
        "callback_token": row[9],
        "attempt_count": int(row[10] or 0),
        "max_attempts": int(row[11] or 0),
        "last_error": sanitize_text(row[12]) if row[12] else None,
        "requested_by": str(row[13]) if row[13] else None,
        "next_attempt_at": row[14].isoformat() if row[14] else None,
        "completed_at": row[15].isoformat() if row[15] else None,
        "metadata": row[16] or {},
        "created_at": row[17].isoformat() if row[17] else None,
        "updated_at": row[18].isoformat() if row[18] else None,
    }
    if with_draft:
        item.update({
            "draft_title": row[19],
            "draft_type": row[20],
            "draft_status": row[21],
            "draft_position": row[22],
            "draft_writeback_status": row[23],
        })
    return item


def _clean_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned[:160] or "AI 自动化草稿"


def _extract_sku(text: str) -> str | None:
    match = re.search(r"\b(?:SKU|sku)[:：\s-]*([A-Z0-9][A-Z0-9_-]{2,})\b", text)
    return match.group(1)[:64] if match else None


def _extract_marketplace(text: str) -> str:
    lowered = text.lower()
    for label, value in [("日本", "JP"), ("japan", "JP"), ("德国", "DE"), ("germany", "DE"), ("美国", "US"), ("us", "US")]:
        if label in lowered:
            return value
    return "US"


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()[:500]
    return None


def _extract_numbered_lines(text: str, max_items: int) -> list[str]:
    lines = []
    for line in text.splitlines():
        clean = re.sub(r"^\s*(?:[-*]|\d+[.)、])\s*", "", line).strip()
        if len(clean) >= 12 and not clean.lower().startswith(("title", "product description", "backend search")):
            lines.append(clean[:500])
        if len(lines) >= max_items:
            break
    return lines


def _parse_listing_generation_answer(answer: str) -> dict[str, Any]:
    text = (answer or "").strip()
    if not text:
        return {}

    candidates = [text]
    if text.startswith("```"):
        fenced = re.sub(r"^```(?:json)?\s*", "", text)
        fenced = re.sub(r"\s*```$", "", fenced)
        candidates.insert(0, fenced.strip())
    if "{" in text and "}" in text:
        start = text.find("{")
        end = text.rfind("}")
        if start < end:
            candidates.insert(0, text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _first_text(source: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:1000]
    return None


def _list_text(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items[:10]
    if isinstance(value, str) and value.strip():
        raw = [item.strip() for item in re.split(r"[，,;\n]+", value) if item.strip()]
        return raw[:10]
    return []
