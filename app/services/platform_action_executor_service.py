from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from fastapi import HTTPException, status

from app.config import settings
from app.db import execute, fetch_one
from app.json_utils import dumps_json
from app.services.logging_service import write_audit_log
from app.services.notification_service import notify_user_and_admins
from app.services.platform_action_executor_config_service import resolve_platform_action_executor
from app.services.platform_action_security_service import open_platform_action_request
from app.services.platform_draft_service import (
    create_platform_action_execution,
    create_platform_execution_task,
    finish_platform_action_execution,
    finish_platform_execution_task,
    get_active_platform_execution_task,
    get_platform_draft,
    get_platform_execution_task,
    get_platform_execution_task_by_token,
    list_platform_action_executions,
    list_platform_execution_tasks,
    mark_platform_execution_task_dispatching,
    mark_platform_execution_task_waiting_callback,
    mark_platform_execution_task_waiting_executor,
    update_platform_draft_status,
    update_platform_draft_writeback,
    update_platform_execution_task_payload,
)
from app.services.run_record_service import (
    elapsed_ms,
    finish_run,
    now_ms,
    record_artifact,
    record_step,
    sanitize_metadata,
    sanitize_text,
    start_run,
)


def execute_platform_draft_action(
    *,
    draft_id: str,
    current_user: dict,
    trigger_source: str = "manual",
    final_publish: bool = False,
) -> dict[str, Any]:
    draft = get_platform_draft(draft_id=draft_id, current_user=current_user)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台草稿不存在或无权执行")

    if final_publish and draft["status"] != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="草稿必须先审核通过，才能发布或发送")

    action_type = _action_type_for_draft(draft, final_publish=final_publish)
    payload = _build_executor_payload(
        draft=draft,
        action_type=action_type,
        current_user=current_user,
        final_publish=final_publish,
    )
    if final_publish and get_active_platform_execution_task(draft_id=draft_id, action_type=action_type):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已有发布/发送任务正在等待外部执行结果")

    executor_config = resolve_platform_action_executor(action_type)
    task_target = str((executor_config or {}).get("webhook_url") or draft["external_target"])
    task = create_platform_execution_task(
        draft_id=draft_id,
        action_type=action_type,
        target=task_target,
        request_payload=payload,
        requested_by=current_user.get("id"),
        metadata={
            "trigger_source": trigger_source,
            "final_publish": final_publish,
            "draft_type": draft["draft_type"],
            "position": draft["position"],
            "executor_id": (executor_config or {}).get("id"),
            "executor_name": (executor_config or {}).get("name"),
            "executor_type": (executor_config or {}).get("executor_type"),
        },
    )
    payload = {
        **payload,
        "execution_task": {
            "id": task["id"],
            "callback_token": task["callback_token"],
            "callback_path": f"/platform-execution-tasks/{task['id']}/callback",
            "callback_method": "POST",
        },
    }
    task = update_platform_execution_task_payload(
        task_id=task["id"],
        request_payload=payload,
        metadata={"callback_path": f"/platform-execution-tasks/{task['id']}/callback"},
    )
    started_ms = now_ms()
    run_id = start_run(
        run_type="platform_publish_execution" if final_publish else "platform_action_execution",
        app_id=f"platform-action-{action_type}",
        app_name=_action_label(action_type),
        entrypoint="/platform-drafts/{draft_id}/publish" if final_publish else "/platform-drafts/{draft_id}/execute",
        current_user=current_user,
        resource_type="platform_draft",
        resource_id=draft_id,
        input_text=payload,
        metadata={
            "draft_id": draft_id,
            "draft_type": draft["draft_type"],
            "position": draft["position"],
            "trigger_source": trigger_source,
            "external_target": draft["external_target"],
            "final_publish": final_publish,
            "task_id": task["id"],
            "executor_id": (executor_config or {}).get("id"),
            "executor_name": (executor_config or {}).get("name"),
            "executor_type": (executor_config or {}).get("executor_type"),
        },
    )

    if not executor_config:
        message = _missing_executor_message(final_publish=final_publish)
        execution = create_platform_action_execution(
            draft_id=draft_id,
            action_type=action_type,
            executor_type="manual_waiting",
            target=draft["external_target"],
            status_value="waiting_executor",
            request_payload=payload,
            response_payload={"configured": False, "message": message},
            error_message=message,
            run_id=run_id,
            triggered_by=current_user.get("id"),
            finished=True,
        )
        task = mark_platform_execution_task_waiting_executor(
            task_id=task["id"],
            latest_execution_id=execution["id"],
            message=message,
        )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft_id,
            writeback_status="rpa_ready",
            writeback_message=message,
            metadata={
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": action_type,
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                "executor_configured": False,
                **_publication_metadata(execution, final_publish=final_publish, status_text="waiting_executor"),
            },
        )
        record_step(
            run_id=run_id,
            step_name="executor_configuration_check",
            step_order=1,
            status_value="blocked",
            provider="platform_action_executor",
            resource_type="platform_draft",
            resource_id=draft_id,
            input_text=payload,
            output_text=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "execution_id": execution["id"],
                "executor_type": execution["executor_type"],
            },
        )
        finish_run(
            run_id,
            status_value="blocked",
            output_text=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "execution_id": execution["id"],
                "draft_id": draft_id,
                "latest_execution_status": execution["status"],
            },
        )
        _audit_execution(current_user=current_user, draft=updated_draft, execution=execution)
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.waiting_executor",
            title="外部执行任务等待接入",
            body=message,
        )
        return {
            "draft": updated_draft,
            "execution": _without_callback_token(execution, current_user=current_user),
            "task": _without_callback_token(task, current_user=current_user),
            "run_id": run_id,
            "message": message,
        }

    try:
        execution = create_platform_action_execution(
            draft_id=draft_id,
            action_type=action_type,
            executor_type=str(executor_config["executor_type"]),
            target=executor_config["webhook_url"],
            status_value="running",
            request_payload=payload,
            response_payload={},
            run_id=run_id,
            triggered_by=current_user.get("id"),
        )
        task = mark_platform_execution_task_dispatching(
            task_id=task["id"],
            latest_execution_id=execution["id"],
            target=executor_config["webhook_url"],
        )
        record_step(
            run_id=run_id,
            step_name="webhook_prepare_payload",
            step_order=1,
            status_value="succeeded",
            provider="platform_action_executor",
            resource_type="platform_draft",
            resource_id=draft_id,
            input_text={"draft_id": draft_id, "action_type": action_type},
            output_text=payload,
            duration_ms=0,
            metadata={"execution_id": execution["id"]},
        )
        webhook_started_ms = now_ms()
        response_payload = _post_executor_webhook(payload, executor_config=executor_config)
        if _is_async_executor_response(response_payload):
            task = mark_platform_execution_task_waiting_callback(
                task_id=task["id"],
                response_payload=response_payload,
                external_reference=_external_reference(response_payload),
            )
            message = _waiting_callback_message(draft, response_payload, action_type=action_type)
            updated_draft = update_platform_draft_writeback(
                draft_id=draft_id,
                writeback_status="rpa_ready",
                writeback_message=message,
                metadata={
                    "latest_execution_id": execution["id"],
                    "latest_execution_status": execution["status"],
                    "latest_action_type": action_type,
                    "latest_execution_task_id": task["id"],
                    "latest_execution_task_status": task["status"],
                    "executor_configured": True,
                    "external_reference": task["external_reference"],
                    **_publication_metadata(execution, final_publish=final_publish, status_text="waiting_callback"),
                },
            )
            record_step(
                run_id=run_id,
                step_name="webhook_dispatch_waiting_callback",
                step_order=2,
                status_value="succeeded",
                provider="platform_action_executor",
                resource_type="platform_draft",
                resource_id=draft_id,
                input_text=payload,
                output_text=response_payload,
                duration_ms=elapsed_ms(webhook_started_ms),
                metadata={"execution_id": execution["id"], "task_id": task["id"]},
            )
            finish_run(
                run_id,
                status_value="succeeded",
                output_text=message,
                duration_ms=elapsed_ms(started_ms),
                metadata={
                    "execution_id": execution["id"],
                    "task_id": task["id"],
                    "task_status": task["status"],
                },
            )
            _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task)
            _notify_task_state(
                draft=updated_draft,
                task=task,
                type_value="platform_execution.waiting_callback",
                title="外部执行任务已派发",
                body=message,
            )
            return {
                "draft": updated_draft,
                "execution": _without_callback_token(execution, current_user=current_user),
                "task": _without_callback_token(task, current_user=current_user),
                "run_id": run_id,
                "message": message,
            }

        execution = finish_platform_action_execution(
            execution_id=execution["id"],
            status_value="succeeded",
            response_payload=response_payload,
        )
        task = finish_platform_execution_task(
            task_id=task["id"],
            status_value="succeeded",
            response_payload=response_payload,
            external_reference=_external_reference(response_payload),
        )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft_id,
            writeback_status="external_synced",
            writeback_message=_success_message(draft, response_payload, action_type=action_type),
            metadata={
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": action_type,
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                "executor_configured": True,
                "executor_id": executor_config["id"],
                "executor_name": executor_config["name"],
                "external_reference": task["external_reference"],
                **_publication_metadata(execution, final_publish=final_publish, status_text="succeeded"),
            },
        )
        if final_publish:
            updated_draft = update_platform_draft_status(
                draft_id=draft_id,
                status_value="published",
                metadata={
                    "published_by": current_user.get("id"),
                    "published_by_username": current_user.get("username"),
                    "published_at": _now_iso(),
                    "publish_action_type": action_type,
                    "publish_execution_id": execution["id"],
                    "publish_task_id": task["id"],
                },
            )
            _mark_related_business_record_published(draft=updated_draft, current_user=current_user)
        record_step(
            run_id=run_id,
            step_name="webhook_execute_action",
            step_order=2,
            status_value="succeeded",
            provider="platform_action_executor",
            resource_type="platform_draft",
            resource_id=draft_id,
            input_text=payload,
            output_text=response_payload,
            duration_ms=elapsed_ms(webhook_started_ms),
            metadata={"execution_id": execution["id"]},
        )
        record_artifact(
            run_id=run_id,
            artifact_type="platform_action_execution",
            name=execution["id"],
            external_ref=str(response_payload.get("external_reference") or execution["id"]),
            metadata={
                "draft_id": draft_id,
                "action_type": action_type,
                "status": execution["status"],
                "task_id": task["id"],
            },
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=response_payload,
            duration_ms=elapsed_ms(started_ms),
            metadata={
                "execution_id": execution["id"],
                "task_id": task["id"],
                "draft_id": draft_id,
                "external_reference": response_payload.get("external_reference"),
            },
        )
        _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task)
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.succeeded",
            title=_success_notification_title(action_type),
            body=updated_draft["writeback_message"] or _success_message(draft, response_payload, action_type=action_type),
        )
        return {
            "draft": updated_draft,
            "execution": _without_callback_token(execution, current_user=current_user),
            "task": _without_callback_token(task, current_user=current_user),
            "run_id": run_id,
            "message": updated_draft["writeback_message"],
        }
    except Exception as error:
        message = sanitize_text(str(error))
        execution = finish_platform_action_execution(
            execution_id=execution["id"] if "execution" in locals() else create_platform_action_execution(
                draft_id=draft_id,
                action_type=action_type,
                executor_type=str(executor_config["executor_type"]),
                target=task_target,
                status_value="running",
                request_payload=payload,
                response_payload={},
                run_id=run_id,
                triggered_by=current_user.get("id"),
            )["id"],
            status_value="failed",
            response_payload={},
            error_message=message,
        )
        if "task" in locals():
            task = finish_platform_execution_task(
                task_id=task["id"],
                status_value="failed",
                response_payload={},
                error_message=message,
            )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft_id,
            writeback_status="failed",
            writeback_message=f"{'发布/发送' if final_publish else '外部写回'}失败：{message}",
            metadata={
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": action_type,
                "latest_execution_task_id": task["id"] if "task" in locals() else None,
                "latest_execution_task_status": task["status"] if "task" in locals() else None,
                "executor_configured": True,
                **_publication_metadata(execution, final_publish=final_publish, status_text="failed"),
            },
        )
        record_step(
            run_id=run_id,
            step_name="webhook_execute_action",
            step_order=2,
            status_value="failed",
            provider="platform_action_executor",
            resource_type="platform_draft",
            resource_id=draft_id,
            input_text=payload,
            error_message=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"]},
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "draft_id": draft_id},
        )
        _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task if "task" in locals() else None)
        if "task" in locals():
            _notify_task_state(
                draft=updated_draft,
                task=task,
                type_value="platform_execution.failed",
                title="外部执行任务失败",
                body=updated_draft["writeback_message"] or f"外部执行失败：{message}",
            )
        return {
            "draft": updated_draft,
            "execution": _without_callback_token(execution, current_user=current_user),
            "task": _without_callback_token(task, current_user=current_user) if "task" in locals() else None,
            "run_id": run_id,
            "message": updated_draft["writeback_message"],
        }


def review_platform_draft(
    *,
    draft_id: str,
    current_user: dict,
    decision: str,
    comment: str | None = None,
) -> dict[str, Any]:
    draft = get_platform_draft(draft_id=draft_id, current_user=current_user)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台草稿不存在或无权审核")

    normalized_decision = decision.strip().lower()
    if normalized_decision not in {"approved", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="审核结果只能是 approved 或 rejected")

    _ensure_review_transition_allowed(draft=draft, decision=normalized_decision)
    status_value = "approved" if normalized_decision == "approved" else "rejected"
    updated_draft = update_platform_draft_status(
        draft_id=draft_id,
        status_value=status_value,
        metadata={
            "review_decision": normalized_decision,
            "review_comment": (comment or "").strip()[:1000],
            "reviewed_by": current_user.get("id"),
            "reviewed_by_username": current_user.get("username"),
            "reviewed_at": _now_iso(),
        },
    )
    write_audit_log(
        user_id=current_user.get("id"),
        action="platform_draft.review",
        resource_type="platform_draft",
        resource_id=draft_id,
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "draft_type": updated_draft["draft_type"],
            "draft_position": updated_draft["position"],
            "decision": normalized_decision,
            "comment": (comment or "").strip()[:300],
        },
    )
    notify_user_and_admins(
        user_id=updated_draft.get("owner_user_id"),
        type_value=f"platform_draft.{normalized_decision}",
        title="草稿已审核通过" if normalized_decision == "approved" else "草稿已驳回",
        body=(
            f"{updated_draft['title']} 已审核通过，可以进入发布或发送。"
            if normalized_decision == "approved"
            else f"{updated_draft['title']} 已被驳回，请按审核意见修改。"
        ),
        resource_type="platform_draft",
        resource_id=draft_id,
        metadata={
            "draft_type": updated_draft["draft_type"],
            "position": updated_draft["position"],
            "decision": normalized_decision,
            "comment": (comment or "").strip()[:300],
        },
    )
    return updated_draft


def publish_platform_draft_action(
    *,
    draft_id: str,
    current_user: dict,
) -> dict[str, Any]:
    return execute_platform_draft_action(
        draft_id=draft_id,
        current_user=current_user,
        trigger_source="review_center",
        final_publish=True,
    )


def list_platform_execution_task_items(
    *,
    current_user: dict,
    status_value: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    return [_without_callback_token(item, current_user=current_user) for item in list_platform_execution_tasks(
        current_user=current_user,
        status_value=status_value,
        limit=limit,
    )]


def get_platform_execution_task_item(*, task_id: str, current_user: dict) -> dict[str, Any] | None:
    item = get_platform_execution_task(task_id=task_id, current_user=current_user)
    return _without_callback_token(item, current_user=current_user) if item else None


def retry_platform_execution_task(*, task_id: str, current_user: dict) -> dict[str, Any]:
    task = get_platform_execution_task(task_id=task_id, current_user=current_user)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行任务不存在或无权操作")
    if task["status"] not in {"failed", "queued"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有失败或等待执行器的任务可以重试")
    if int(task.get("attempt_count") or 0) >= int(task.get("max_attempts") or 1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="任务已达到最大重试次数")

    draft = get_platform_draft(draft_id=task["draft_id"], current_user=current_user)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台草稿不存在或无权操作")
    if task["action_type"] in {"publish_listing", "send_customer_reply"}:
        if draft["status"] == "published":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="草稿已发布或已发送，不能重试")
        if draft["status"] != "approved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="草稿必须保持审核通过状态才能重试")

    result = _dispatch_platform_execution_task(task=task, draft=draft, current_user=current_user, trigger_source="retry")
    return _public_execution_result(result)


def handle_platform_execution_callback(
    *,
    task_id: str,
    callback_token: str,
    status_value: str,
    response_payload: dict[str, Any] | None = None,
    external_reference: str | None = None,
    message: str | None = None,
    raw_body: bytes | None = None,
    signature: str | None = None,
    timestamp: str | None = None,
    nonce: str | None = None,
) -> dict[str, Any]:
    _verify_callback_signature(
        task_id=task_id,
        raw_body=raw_body,
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )
    task = get_platform_execution_task_by_token(task_id=task_id, callback_token=callback_token)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="执行任务不存在或回调 token 无效")
    if task["status"] not in {"dispatching", "waiting_callback"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="执行任务当前状态不接受回调")

    normalized_status = status_value.strip().lower()
    if normalized_status not in {"succeeded", "failed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回调状态只能是 succeeded 或 failed")

    payload = response_payload or {}
    external_ref = external_reference or _external_reference(payload)
    execution = None
    if task.get("latest_execution_id"):
        execution = finish_platform_action_execution(
            execution_id=task["latest_execution_id"],
            status_value=normalized_status,
            response_payload=payload,
            error_message=sanitize_text(message) if normalized_status == "failed" and message else None,
        )

    task = finish_platform_execution_task(
        task_id=task_id,
        status_value=normalized_status,
        response_payload=payload,
        external_reference=external_ref,
        error_message=sanitize_text(message) if normalized_status == "failed" and message else None,
        metadata={"callback_received_at": _now_iso()},
    )
    system_user = {
        "id": task.get("requested_by"),
        "username": "external_executor_callback",
        "role": "system",
        "position": None,
    }
    draft = get_platform_draft(draft_id=task["draft_id"], current_user={"role": "admin"})
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="平台草稿不存在")

    if normalized_status == "succeeded":
        updated_draft = update_platform_draft_writeback(
            draft_id=draft["id"],
            writeback_status="external_synced",
            writeback_message=_success_message(draft, payload, action_type=task["action_type"]),
            metadata={
                "latest_execution_id": task.get("latest_execution_id"),
                "latest_execution_status": "succeeded",
                "latest_action_type": task["action_type"],
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                "external_reference": external_ref,
                **_publication_metadata_from_action(task, "succeeded"),
            },
        )
        if task["action_type"] in {"publish_listing", "send_customer_reply"}:
            updated_draft = update_platform_draft_status(
                draft_id=draft["id"],
                status_value="published",
                metadata={
                    "published_by": task.get("requested_by"),
                    "published_by_username": "external_executor_callback",
                    "published_at": _now_iso(),
                    "publish_action_type": task["action_type"],
                    "publish_execution_id": task.get("latest_execution_id"),
                    "publish_task_id": task["id"],
                },
            )
            _mark_related_business_record_published(draft=updated_draft, current_user=system_user)
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.succeeded",
            title=_success_notification_title(task["action_type"]),
            body=updated_draft["writeback_message"] or "外部执行任务已完成。",
        )
    else:
        updated_draft = update_platform_draft_writeback(
            draft_id=draft["id"],
            writeback_status="failed",
            writeback_message=sanitize_text(message) if message else "外部执行器回调失败。",
            metadata={
                "latest_execution_id": task.get("latest_execution_id"),
                "latest_execution_status": "failed",
                "latest_action_type": task["action_type"],
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                **_publication_metadata_from_action(task, "failed"),
            },
        )
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.failed",
            title="外部执行任务失败",
            body=updated_draft["writeback_message"] or "外部执行任务失败，请检查后重试。",
        )

    write_audit_log(
        user_id=task.get("requested_by"),
        action="platform_execution.callback",
        resource_type="platform_execution_task",
        resource_id=task["id"],
        metadata={
            "draft_id": draft["id"],
            "action_type": task["action_type"],
            "status": normalized_status,
            "external_reference": external_ref,
        },
    )
    return {
        "task": _without_callback_token(task, current_user={"role": "system"}),
        "draft": updated_draft,
        "execution": _without_callback_token(execution, current_user={"role": "system"}) if execution else None,
        "message": updated_draft["writeback_message"],
    }


def latest_platform_action_executions(
    *,
    draft_id: str,
    current_user: dict,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return [_without_callback_token(item, current_user=current_user) for item in list_platform_action_executions(
        draft_id=draft_id,
        current_user=current_user,
        limit=limit,
    )]


def _dispatch_platform_execution_task(
    *,
    task: dict[str, Any],
    draft: dict[str, Any],
    current_user: dict,
    trigger_source: str,
) -> dict[str, Any]:
    action_type = task["action_type"]
    final_publish = action_type in {"publish_listing", "send_customer_reply"}
    executor_config = resolve_platform_action_executor(action_type)
    task_target = str((executor_config or {}).get("webhook_url") or draft["external_target"])
    payload = {
        **(task.get("request_payload") or {}),
        "retry": {
            "attempt": int(task.get("attempt_count") or 0) + 1,
            "trigger_source": trigger_source,
            "executor_id": (executor_config or {}).get("id"),
            "executor_name": (executor_config or {}).get("name"),
        },
    }
    started_ms = now_ms()
    run_id = start_run(
        run_type="platform_publish_execution" if final_publish else "platform_action_execution",
        app_id=f"platform-action-{action_type}",
        app_name=_action_label(action_type),
        entrypoint="/platform-execution-tasks/{task_id}/retry",
        current_user=current_user,
        resource_type="platform_execution_task",
        resource_id=task["id"],
        input_text=payload,
        metadata={
            "task_id": task["id"],
            "draft_id": draft["id"],
            "action_type": action_type,
            "trigger_source": trigger_source,
            "final_publish": final_publish,
            "executor_id": (executor_config or {}).get("id"),
            "executor_name": (executor_config or {}).get("name"),
            "executor_type": (executor_config or {}).get("executor_type"),
        },
    )

    if not executor_config:
        message = _missing_executor_message(final_publish=final_publish)
        execution = create_platform_action_execution(
            draft_id=draft["id"],
            action_type=action_type,
            executor_type="manual_waiting",
            target=draft["external_target"],
            status_value="waiting_executor",
            request_payload=payload,
            response_payload={"configured": False, "message": message},
            error_message=message,
            run_id=run_id,
            triggered_by=current_user.get("id"),
            finished=True,
        )
        task = mark_platform_execution_task_waiting_executor(
            task_id=task["id"],
            latest_execution_id=execution["id"],
            message=message,
        )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft["id"],
            writeback_status="rpa_ready",
            writeback_message=message,
            metadata={
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": action_type,
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                "executor_configured": False,
                **_publication_metadata(execution, final_publish=final_publish, status_text="waiting_executor"),
            },
        )
        record_step(
            run_id=run_id,
            step_name="executor_configuration_check",
            step_order=1,
            status_value="blocked",
            provider="platform_action_executor",
            resource_type="platform_execution_task",
            resource_id=task["id"],
            input_text=payload,
            output_text=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "task_id": task["id"]},
        )
        finish_run(
            run_id,
            status_value="blocked",
            output_text=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "task_id": task["id"]},
        )
        _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task)
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.waiting_executor",
            title="外部执行任务等待接入",
            body=message,
        )
        return _public_execution_result({
            "draft": updated_draft,
            "execution": execution,
            "task": task,
            "run_id": run_id,
            "message": message,
            "current_user": current_user,
        })

    try:
        execution = create_platform_action_execution(
            draft_id=draft["id"],
            action_type=action_type,
            executor_type=str(executor_config["executor_type"]),
            target=executor_config["webhook_url"],
            status_value="running",
            request_payload=payload,
            response_payload={},
            run_id=run_id,
            triggered_by=current_user.get("id"),
        )
        task = mark_platform_execution_task_dispatching(
            task_id=task["id"],
            latest_execution_id=execution["id"],
            target=executor_config["webhook_url"],
        )
        response_payload = _post_executor_webhook(payload, executor_config=executor_config)
        if _is_async_executor_response(response_payload):
            task = mark_platform_execution_task_waiting_callback(
                task_id=task["id"],
                response_payload=response_payload,
                external_reference=_external_reference(response_payload),
            )
            message = _waiting_callback_message(draft, response_payload, action_type=action_type)
            updated_draft = update_platform_draft_writeback(
                draft_id=draft["id"],
                writeback_status="rpa_ready",
                writeback_message=message,
                metadata={
                    "latest_execution_id": execution["id"],
                    "latest_execution_status": execution["status"],
                    "latest_action_type": action_type,
                    "latest_execution_task_id": task["id"],
                    "latest_execution_task_status": task["status"],
                    "executor_configured": True,
                    "executor_id": executor_config["id"],
                    "executor_name": executor_config["name"],
                    "external_reference": task["external_reference"],
                    **_publication_metadata(execution, final_publish=final_publish, status_text="waiting_callback"),
                },
            )
            record_step(
                run_id=run_id,
                step_name="webhook_dispatch_waiting_callback",
                step_order=1,
                status_value="succeeded",
                provider="platform_action_executor",
                resource_type="platform_execution_task",
                resource_id=task["id"],
                input_text=payload,
                output_text=response_payload,
                duration_ms=elapsed_ms(started_ms),
                metadata={"execution_id": execution["id"], "task_id": task["id"]},
            )
            finish_run(
                run_id,
                status_value="succeeded",
                output_text=message,
                duration_ms=elapsed_ms(started_ms),
                metadata={"execution_id": execution["id"], "task_id": task["id"], "task_status": task["status"]},
            )
            _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task)
            _notify_task_state(
                draft=updated_draft,
                task=task,
                type_value="platform_execution.waiting_callback",
                title="外部执行任务已重新派发",
                body=message,
            )
            return _public_execution_result({
                "draft": updated_draft,
                "execution": execution,
                "task": task,
                "run_id": run_id,
                "message": message,
                "current_user": current_user,
            })

        execution = finish_platform_action_execution(
            execution_id=execution["id"],
            status_value="succeeded",
            response_payload=response_payload,
        )
        task = finish_platform_execution_task(
            task_id=task["id"],
            status_value="succeeded",
            response_payload=response_payload,
            external_reference=_external_reference(response_payload),
        )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft["id"],
            writeback_status="external_synced",
            writeback_message=_success_message(draft, response_payload, action_type=action_type),
            metadata={
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": action_type,
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                "executor_configured": True,
                "executor_id": executor_config["id"],
                "executor_name": executor_config["name"],
                "external_reference": task["external_reference"],
                **_publication_metadata(execution, final_publish=final_publish, status_text="succeeded"),
            },
        )
        if final_publish:
            updated_draft = update_platform_draft_status(
                draft_id=draft["id"],
                status_value="published",
                metadata={
                    "published_by": current_user.get("id"),
                    "published_by_username": current_user.get("username"),
                    "published_at": _now_iso(),
                    "publish_action_type": action_type,
                    "publish_execution_id": execution["id"],
                    "publish_task_id": task["id"],
                },
            )
            _mark_related_business_record_published(draft=updated_draft, current_user=current_user)
        record_step(
            run_id=run_id,
            step_name="webhook_execute_action",
            step_order=1,
            status_value="succeeded",
            provider="platform_action_executor",
            resource_type="platform_execution_task",
            resource_id=task["id"],
            input_text=payload,
            output_text=response_payload,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "task_id": task["id"]},
        )
        finish_run(
            run_id,
            status_value="succeeded",
            output_text=response_payload,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "task_id": task["id"]},
        )
        _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task)
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.succeeded",
            title=_success_notification_title(action_type),
            body=updated_draft["writeback_message"] or "外部执行任务已完成。",
        )
        return _public_execution_result({
            "draft": updated_draft,
            "execution": execution,
            "task": task,
            "run_id": run_id,
            "message": updated_draft["writeback_message"],
            "current_user": current_user,
        })
    except Exception as error:
        message = sanitize_text(str(error))
        execution = finish_platform_action_execution(
            execution_id=execution["id"] if "execution" in locals() else create_platform_action_execution(
                draft_id=draft["id"],
                action_type=action_type,
                executor_type=str(executor_config["executor_type"]),
                target=task_target,
                status_value="running",
                request_payload=payload,
                response_payload={},
                run_id=run_id,
                triggered_by=current_user.get("id"),
            )["id"],
            status_value="failed",
            response_payload={},
            error_message=message,
        )
        task = finish_platform_execution_task(
            task_id=task["id"],
            status_value="failed",
            response_payload={},
            error_message=message,
        )
        updated_draft = update_platform_draft_writeback(
            draft_id=draft["id"],
            writeback_status="failed",
            writeback_message=f"外部执行任务重试失败：{message}",
            metadata={
                "latest_execution_id": execution["id"],
                "latest_execution_status": execution["status"],
                "latest_action_type": action_type,
                "latest_execution_task_id": task["id"],
                "latest_execution_task_status": task["status"],
                "executor_configured": True,
                **_publication_metadata(execution, final_publish=final_publish, status_text="failed"),
            },
        )
        record_step(
            run_id=run_id,
            step_name="webhook_execute_action",
            step_order=1,
            status_value="failed",
            provider="platform_action_executor",
            resource_type="platform_execution_task",
            resource_id=task["id"],
            input_text=payload,
            error_message=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "task_id": task["id"]},
        )
        finish_run(
            run_id,
            status_value="failed",
            error_message=message,
            duration_ms=elapsed_ms(started_ms),
            metadata={"execution_id": execution["id"], "task_id": task["id"]},
        )
        _audit_execution(current_user=current_user, draft=updated_draft, execution=execution, task=task)
        _notify_task_state(
            draft=updated_draft,
            task=task,
            type_value="platform_execution.failed",
            title="外部执行任务重试失败",
            body=updated_draft["writeback_message"] or f"外部执行任务重试失败：{message}",
        )
        return _public_execution_result({
            "draft": updated_draft,
            "execution": execution,
            "task": task,
            "run_id": run_id,
            "message": updated_draft["writeback_message"],
            "current_user": current_user,
        })


def _post_executor_webhook(payload: dict[str, Any], *, executor_config: dict[str, Any]) -> dict[str, Any]:
    webhook_url = str(executor_config["webhook_url"])
    body = json.dumps(
        {
            **payload,
            "executor": {
                "id": executor_config.get("id"),
                "name": executor_config.get("name"),
                "type": executor_config.get("executor_type"),
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "company-rag-agent-platform-action-executor/1.0",
    }
    if executor_config.get("api_key"):
        headers["Authorization"] = f"Bearer {executor_config['api_key']}"

    request = Request(
        webhook_url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with open_platform_action_request(
            request,
            timeout=int(executor_config.get("timeout_seconds") or settings.platform_action_executor_timeout_seconds),
        ) as response:
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


def _verify_callback_signature(
    *,
    task_id: str,
    raw_body: bytes | None,
    signature: str | None,
    timestamp: str | None,
    nonce: str | None,
) -> None:
    secret = settings.platform_action_execution_callback_secret
    if not secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未配置外部执行器回调签名密钥")
    if not raw_body:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调缺少原始请求体")
    if not signature or not timestamp or not nonce:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调缺少签名头")

    try:
        timestamp_value = int(timestamp)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调时间戳无效") from error

    now_value = int(datetime.now(timezone.utc).timestamp())
    tolerance = max(30, int(settings.platform_action_execution_callback_tolerance_seconds or 300))
    if abs(now_value - timestamp_value) > tolerance:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调签名已过期")

    body_sha = hashlib.sha256(raw_body).hexdigest()
    signing_text = f"v1:{timestamp}:{nonce}:{task_id}:{body_sha}"
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), signing_text.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.strip()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调签名无效")
    _remember_callback_nonce(task_id=task_id, nonce=nonce)


def _remember_callback_nonce(*, task_id: str, nonce: str) -> None:
    if not nonce or len(nonce) > 160:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调 nonce 无效")
    row = fetch_one(
        """
        UPDATE platform_execution_tasks
        SET
            metadata = metadata || jsonb_build_object(
                'callback_nonces',
                COALESCE(metadata->'callback_nonces', '[]'::jsonb) || to_jsonb(%s::text)
            ),
            updated_at = now()
        WHERE id = %s
          AND NOT (COALESCE(metadata->'callback_nonces', '[]'::jsonb) ? %s)
        RETURNING id;
        """,
        (nonce, task_id, nonce),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="回调 nonce 已使用或任务不存在")


def _build_executor_payload(
    *,
    draft: dict[str, Any],
    action_type: str,
    current_user: dict,
    final_publish: bool,
) -> dict[str, Any]:
    return {
        "action_type": action_type,
        "action_phase": "publish_or_send" if final_publish else "draft_writeback",
        "draft_id": draft["id"],
        "draft_type": draft["draft_type"],
        "platform": draft["platform"],
        "external_target": draft["external_target"],
        "title": draft["title"],
        "position": draft["position"],
        "status": draft["status"],
        "writeback_status": draft["writeback_status"],
        "content": draft["content"],
        "metadata": draft["metadata"],
        "triggered_by": {
            "id": current_user.get("id"),
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
        },
    }


def _action_type_for_draft(draft: dict[str, Any], *, final_publish: bool = False) -> str:
    if draft["draft_type"] == "listing":
        return "publish_listing" if final_publish else "write_listing_draft"
    if draft["draft_type"] == "customer_reply":
        return "send_customer_reply" if final_publish else "write_customer_reply"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的草稿类型")


def _action_label(action_type: str) -> str:
    labels = {
        "write_listing_draft": "写入 Listing 平台草稿",
        "write_customer_reply": "写入客服回复草稿",
        "publish_listing": "发布 Listing",
        "send_customer_reply": "发送客服回复",
    }
    return labels.get(action_type, "平台业务动作执行")


def _success_message(draft: dict[str, Any], response_payload: dict[str, Any], *, action_type: str) -> str:
    external_reference = response_payload.get("external_reference") or response_payload.get("id")
    if action_type == "publish_listing":
        if external_reference:
            return f"外部执行器已真实发布 Listing，外部引用：{external_reference}"
        return "外部执行器已真实发布 Listing。"
    if action_type == "send_customer_reply":
        if external_reference:
            return f"外部执行器已真实发送客服回复，外部引用：{external_reference}"
        return "外部执行器已真实发送客服回复。"
    if external_reference:
        return f"外部执行器已真实写回 {draft['external_target']}，外部引用：{external_reference}"
    return f"外部执行器已真实写回 {draft['external_target']}，等待人工审核发布或发送。"


def _missing_executor_message(*, final_publish: bool) -> str:
    if final_publish:
        return (
            "未配置 PLATFORM_ACTION_EXECUTOR_WEBHOOK_URL，草稿已审核通过，"
            "当前等待 Amazon SP-API、影刀、n8n 或客服系统执行器接入后再真实发布或发送。"
        )
    return (
        "未配置 PLATFORM_ACTION_EXECUTOR_WEBHOOK_URL，AI 已完成草稿准备，"
        "当前等待 Amazon SP-API、影刀、n8n 或客服系统执行器接入后再真实写回。"
    )


def _is_async_executor_response(response_payload: dict[str, Any]) -> bool:
    if not response_payload:
        return False

    if response_payload.get("async") is True:
        return True
    if response_payload.get("accepted") is True:
        return True
    if response_payload.get("requires_callback") is True:
        return True
    if response_payload.get("completed") is False:
        return True

    http_status = response_payload.get("http_status")
    if isinstance(http_status, int) and http_status == 202:
        return True

    status_text = str(response_payload.get("status") or "").strip().lower()
    return status_text in {"accepted", "queued", "pending", "processing", "running", "waiting_callback"}


def _external_reference(response_payload: dict[str, Any]) -> str | None:
    for key in ("external_reference", "external_ref", "external_id", "task_id", "job_id", "id"):
        value = response_payload.get(key)
        if value:
            return str(value)[:200]
    nested = response_payload.get("data")
    if isinstance(nested, dict):
        for key in ("external_reference", "external_ref", "external_id", "task_id", "job_id", "id"):
            value = nested.get(key)
            if value:
                return str(value)[:200]
    return None


def _waiting_callback_message(
    draft: dict[str, Any],
    response_payload: dict[str, Any],
    *,
    action_type: str,
) -> str:
    external_reference = _external_reference(response_payload)
    label = _action_label(action_type)
    if external_reference:
        return f"外部执行器已接收“{draft['title']}”的{label}任务，外部引用：{external_reference}，正在等待执行完成回调。"
    return f"外部执行器已接收“{draft['title']}”的{label}任务，正在等待执行完成回调。"


def _success_notification_title(action_type: str) -> str:
    titles = {
        "write_listing_draft": "Listing 草稿已写入",
        "write_customer_reply": "客服回复草稿已写入",
        "publish_listing": "Listing 已发布",
        "send_customer_reply": "客服回复已发送",
    }
    return titles.get(action_type, "外部执行任务已完成")


def _notify_task_state(
    *,
    draft: dict[str, Any],
    task: dict[str, Any] | None,
    type_value: str,
    title: str,
    body: str,
) -> None:
    notify_user_and_admins(
        user_id=draft.get("owner_user_id"),
        type_value=type_value,
        title=title,
        body=body,
        resource_type="platform_execution_task" if task else "platform_draft",
        resource_id=task.get("id") if task else draft.get("id"),
        metadata={
            "draft_id": draft.get("id"),
            "draft_title": draft.get("title"),
            "draft_type": draft.get("draft_type"),
            "position": draft.get("position"),
            "task_id": task.get("id") if task else None,
            "task_status": task.get("status") if task else None,
            "action_type": task.get("action_type") if task else None,
        },
    )


def _without_callback_token(item: dict[str, Any] | None, *, current_user: dict | None = None) -> dict[str, Any] | None:
    if item is None:
        return None
    cleaned = dict(item)
    cleaned.pop("callback_token", None)
    cleaned["request_payload"] = _strip_callback_tokens(cleaned.get("request_payload"))
    cleaned["response_payload"] = _strip_callback_tokens(cleaned.get("response_payload"))
    cleaned["metadata"] = sanitize_metadata(cleaned.get("metadata") or {})
    cleaned["last_error"] = sanitize_text(cleaned["last_error"]) if cleaned.get("last_error") else cleaned.get("last_error")
    cleaned["error_message"] = sanitize_text(cleaned["error_message"]) if cleaned.get("error_message") else cleaned.get("error_message")
    if (current_user or {}).get("role") != "admin":
        cleaned["target"] = "[REDACTED]" if cleaned.get("target") else cleaned.get("target")
        cleaned["request_payload"] = {"redacted": True, "message": "执行器请求载荷仅管理员可见"}
        cleaned["response_payload"] = {"redacted": True, "message": "执行器响应载荷仅管理员可见"}
    return cleaned


def _public_execution_result(result: dict[str, Any]) -> dict[str, Any]:
    current_user = result.get("current_user") if isinstance(result.get("current_user"), dict) else None
    return {
        **{key: value for key, value in result.items() if key != "current_user"},
        "execution": _without_callback_token(result.get("execution"), current_user=current_user),
        "task": _without_callback_token(result.get("task"), current_user=current_user),
    }


def _strip_callback_tokens(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() == "callback_token":
                continue
            cleaned[key] = _strip_callback_tokens(item)
        return cleaned
    if isinstance(value, list):
        return [_strip_callback_tokens(item) for item in value]
    return value


def _ensure_review_transition_allowed(*, draft: dict[str, Any], decision: str) -> None:
    current_status = draft["status"]
    if current_status == "published":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已发布或已发送的草稿不能再次审核")

    if decision == "approved" and current_status not in {"pending_review", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有待审核或已驳回草稿可以审核通过")

    if decision == "rejected" and current_status not in {"pending_review", "approved"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有待审核或已审核草稿可以驳回")


def _publication_metadata(
    execution: dict[str, Any],
    *,
    final_publish: bool,
    status_text: str,
) -> dict[str, Any]:
    if not final_publish:
        return {}
    return {
        "latest_publication_execution_id": execution["id"],
        "latest_publication_status": status_text,
    }


def _publication_metadata_from_action(task: dict[str, Any], status_text: str) -> dict[str, Any]:
    if task.get("action_type") not in {"publish_listing", "send_customer_reply"}:
        return {}
    return {
        "latest_publication_execution_id": task.get("latest_execution_id"),
        "latest_publication_status": status_text,
    }


def _mark_related_business_record_published(*, draft: dict[str, Any], current_user: dict) -> None:
    if draft["draft_type"] != "customer_reply":
        return

    message_id = draft.get("content", {}).get("customer_message_id")
    if not message_id:
        return

    execute(
        """
        UPDATE customer_service_messages
        SET
            status = 'closed',
            metadata = metadata || %s::jsonb,
            updated_at = now()
        WHERE id = %s;
        """,
        (
            dumps_json({
                "platform_draft_status": "published",
                "reply_sent_by": current_user.get("id"),
                "reply_sent_by_username": current_user.get("username"),
                "reply_sent_at": _now_iso(),
            }),
            message_id,
        ),
    )
    execute(
        """
        INSERT INTO customer_service_message_events (
            message_id, event_type, actor_id, content, metadata
        )
        VALUES (%s, 'reply_sent', %s, %s, %s::jsonb);
        """,
        (
            message_id,
            current_user.get("id"),
            "审核通过后已通过外部执行器真实发送客服回复",
            dumps_json({
                "draft_id": draft["id"],
                "external_target": draft["external_target"],
            }),
        ),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_execution(
    *,
    current_user: dict,
    draft: dict[str, Any],
    execution: dict[str, Any],
    task: dict[str, Any] | None = None,
) -> None:
    write_audit_log(
        user_id=current_user.get("id"),
        action="platform_draft.execute",
        resource_type="platform_draft",
        resource_id=draft["id"],
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "draft_type": draft["draft_type"],
            "writeback_status": draft["writeback_status"],
            "execution_id": execution["id"],
            "execution_status": execution["status"],
            "executor_type": execution["executor_type"],
            "task_id": task.get("id") if task else None,
            "task_status": task.get("status") if task else None,
            "action_type": task.get("action_type") if task else execution.get("action_type"),
        },
    )
