from __future__ import annotations

from typing import Any

from app.db import fetch_all, fetch_one
from app.services.run_record_service import sanitize_text


DRAFT_STATUS_LABELS = {
    "pending_review": "待人工审核",
    "approved": "已审核",
    "published": "已发布/已发送",
    "rejected": "已驳回",
}

TASK_STATUS_LABELS = {
    "queued": "队列中",
    "dispatching": "派发中",
    "waiting_callback": "等待外部回调",
    "succeeded": "执行成功",
    "failed": "执行失败",
    "cancelled": "已取消",
}

WRITEBACK_STATUS_LABELS = {
    "draft_saved": "已保存平台草稿",
    "rpa_ready": "等待外部写回",
    "external_synced": "已同步外部平台",
    "failed": "写回失败",
}

ACTION_TYPE_LABELS = {
    "write_listing_draft": "写入 Listing 草稿",
    "write_customer_reply": "写入客服回复草稿",
    "publish_listing": "发布 Listing",
    "send_customer_reply": "发送客服回复",
}


def build_business_action_loop(
    *,
    current_user: dict,
    limit: int = 80,
) -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    conditions = ["1 = 1"]
    latest_task_conditions = ["draft_id = d.id"]
    where_params: list[Any] = []
    latest_task_params: list[Any] = []

    if current_user.get("role") != "admin":
        conditions.append("d.position = %s")
        where_params.append(current_user.get("position"))
        conditions.append(
            """
            (
                d.owner_user_id = %s
                OR EXISTS (
                    SELECT 1
                    FROM platform_execution_tasks owner_t
                    WHERE owner_t.draft_id = d.id
                      AND owner_t.requested_by = %s
                )
            )
            """
        )
        where_params.extend([current_user.get("id"), current_user.get("id")])
        latest_task_conditions.append("(d.owner_user_id = %s OR requested_by = %s)")
        latest_task_params.extend([current_user.get("id"), current_user.get("id")])

    params = [*latest_task_params, *where_params, limit]
    rows = fetch_all(
        f"""
        SELECT
            d.id,
            d.draft_type,
            d.platform,
            d.external_target,
            d.title,
            d.status,
            d.position,
            d.owner_user_id,
            d.source_run_id,
            d.source_resource_type,
            d.source_resource_id,
            d.writeback_status,
            d.writeback_message,
            d.metadata,
            d.created_at,
            d.updated_at,
            t.id,
            t.action_type,
            t.status,
            t.external_reference,
            t.attempt_count,
            t.max_attempts,
            t.last_error,
            t.completed_at,
            t.updated_at
        FROM platform_drafts d
        LEFT JOIN LATERAL (
            SELECT
                id, action_type, status, external_reference, attempt_count,
                max_attempts, last_error, completed_at, updated_at
            FROM platform_execution_tasks
            WHERE {" AND ".join(latest_task_conditions)}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
        ) t ON TRUE
        WHERE {" AND ".join(conditions)}
        ORDER BY d.updated_at DESC, d.created_at DESC
        LIMIT %s;
        """,
        tuple(params),
    )

    items = [_map_loop_row(row) for row in rows]
    return {
        "summary": _build_summary(items, current_user=current_user),
        "items": items,
    }


def _build_summary(items: list[dict[str, Any]], *, current_user: dict) -> dict[str, Any]:
    pending_review = sum(1 for item in items if item["draft_status"] == "pending_review")
    waiting_external = sum(1 for item in items if item["latest_task_status"] in {"queued", "dispatching", "waiting_callback"})
    succeeded = sum(1 for item in items if item["stage"] == "done")
    failed = sum(1 for item in items if item["stage"] == "failed")
    unread = _unread_business_notification_count(current_user)
    return {
        "total": len(items),
        "pending_review": pending_review,
        "waiting_external": waiting_external,
        "succeeded": succeeded,
        "failed": failed,
        "unread_notifications": unread,
    }


def _map_loop_row(row: tuple[Any, ...]) -> dict[str, Any]:
    draft_status = str(row[5])
    writeback_status = str(row[11])
    task_id = str(row[16]) if row[16] else None
    task_status = str(row[18]) if row[18] else None
    stage = _stage(draft_status=draft_status, writeback_status=writeback_status, task_status=task_status)
    return {
        "draft_id": str(row[0]),
        "draft_type": row[1],
        "platform": row[2],
        "external_target": row[3],
        "title": row[4],
        "draft_status": draft_status,
        "draft_status_label": DRAFT_STATUS_LABELS.get(draft_status, draft_status),
        "position": row[6],
        "owner_user_id": str(row[7]) if row[7] else None,
        "source_run_id": str(row[8]) if row[8] else None,
        "source_resource_type": row[9],
        "source_resource_id": row[10],
        "writeback_status": writeback_status,
        "writeback_status_label": WRITEBACK_STATUS_LABELS.get(writeback_status, writeback_status),
        "writeback_message": sanitize_text(row[12]) if row[12] else None,
        "metadata": row[13] or {},
        "created_at": row[14].isoformat() if row[14] else None,
        "updated_at": row[15].isoformat() if row[15] else None,
        "latest_task_id": task_id,
        "latest_action_type": row[17],
        "latest_action_label": ACTION_TYPE_LABELS.get(str(row[17]), str(row[17])) if row[17] else None,
        "latest_task_status": task_status,
        "latest_task_status_label": TASK_STATUS_LABELS.get(task_status, task_status) if task_status else None,
        "external_reference": row[19],
        "attempt_count": int(row[20] or 0),
        "max_attempts": int(row[21] or 0),
        "last_error": sanitize_text(row[22]) if row[22] else None,
        "completed_at": row[23].isoformat() if row[23] else None,
        "task_updated_at": row[24].isoformat() if row[24] else None,
        "stage": stage,
        "stage_label": _stage_label(stage),
        "next_action": _next_action(draft_status=draft_status, writeback_status=writeback_status, task_status=task_status),
    }


def _stage(*, draft_status: str, writeback_status: str, task_status: str | None) -> str:
    if writeback_status == "failed" or task_status == "failed":
        return "failed"
    if draft_status == "published":
        return "done"
    if task_status in {"queued", "dispatching", "waiting_callback"}:
        return "external_running"
    if draft_status == "approved":
        return "ready_to_publish"
    if draft_status == "pending_review":
        return "needs_review"
    if draft_status == "rejected":
        return "rejected"
    return "draft_saved"


def _stage_label(stage: str) -> str:
    labels = {
        "draft_saved": "AI 已保存草稿",
        "needs_review": "等待人工审核",
        "ready_to_publish": "等待发布/发送",
        "external_running": "外部执行中",
        "done": "闭环完成",
        "failed": "需要处理失败",
        "rejected": "已驳回",
    }
    return labels.get(stage, stage)


def _next_action(*, draft_status: str, writeback_status: str, task_status: str | None) -> str:
    if writeback_status == "failed" or task_status == "failed":
        return "检查失败原因后重试外部执行任务。"
    if task_status in {"queued", "dispatching", "waiting_callback"}:
        return "等待外部执行器完成回调。"
    if draft_status == "pending_review":
        return "审核 AI 草稿，确认无误后通过。"
    if draft_status == "approved":
        return "点击发布或发送，由外部执行器完成真实业务动作。"
    if draft_status == "published":
        return "业务动作已完成，可查看外部引用和运行记录。"
    if draft_status == "rejected":
        return "根据审核意见重新生成或修改草稿。"
    return "继续查看草稿详情。"


def _unread_business_notification_count(current_user: dict) -> int:
    if not current_user.get("id"):
        return 0
    row = fetch_one(
        """
        SELECT count(*)
        FROM notifications
        WHERE user_id = %s
          AND status = 'unread'
          AND (
              resource_type IN ('platform_draft', 'platform_execution_task')
              OR type LIKE 'platform_draft.%%'
              OR type LIKE 'platform_execution.%%'
          );
        """,
        (current_user["id"],),
    )
    return int(row[0] or 0) if row else 0
