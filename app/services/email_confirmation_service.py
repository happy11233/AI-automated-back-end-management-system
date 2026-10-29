from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.artifact_storage import read_artifact
from app.db import execute, fetch_one
from app.json_utils import dumps_json
from app.services.email_service import EmailAttachment, send_email_with_attachments, validate_email_address
from app.services.generated_file_service import get_generated_file_storage_reference
from app.services.logging_service import write_audit_log
from app.services.run_record_service import elapsed_ms, now_ms, record_step


logger = logging.getLogger(__name__)
_SCHEMA_READY = False


def ensure_email_confirmation_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    execute("""
        CREATE TABLE IF NOT EXISTS email_send_confirmations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            artifacts JSONB NOT NULL CHECK (jsonb_typeof(artifacts) = 'array'),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'sending', 'sent', 'failed', 'unknown')),
            run_id UUID REFERENCES automation_runs(id) ON DELETE SET NULL,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '30 minutes'),
            sent_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_email_send_confirmations_user_status
            ON email_send_confirmations(user_id, status, expires_at);
    """)
    _SCHEMA_READY = True


def create_email_confirmation(
    *, current_user: dict, recipient: str | None, subject: str, body: str,
    artifact_ids: list[str], sensitive_type: str,
) -> dict[str, Any]:
    error = validate_email_address(recipient)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if not artifact_ids:
        raise HTTPException(status_code=400, detail="文件未持久化，无法准备邮件发送确认。")
    artifacts = []
    run_id = None
    for artifact_id in artifact_ids:
        ref = get_generated_file_storage_reference(artifact_id, current_user=current_user)
        if run_id is None:
            run_id = ref.get("run_id")
        content = read_artifact(ref["storage_path"])
        artifacts.append({
            "artifact_id": ref["id"], "filename": ref["filename"],
            "mime_type": ref["mime_type"], "sha256": hashlib.sha256(content).hexdigest(),
            "download_path": f"/files/{ref['id']}/download",
        })
    ensure_email_confirmation_schema()
    row = fetch_one("""
        INSERT INTO email_send_confirmations (user_id, recipient, subject, body, artifacts, run_id)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
        RETURNING id, expires_at;
    """, (current_user["id"], recipient.strip(), subject, body, dumps_json(artifacts), run_id))
    card = {
        "type": "email_file_send_confirmation",
        "status": "waiting_email_confirmation",
        "status_label": "等待邮箱发送确认",
        "message": "文件已生成，请预览附件并确认收件人后发送。",
        "channel": "email",
        "confirmation_id": str(row[0]),
        "expires_at": row[1].isoformat(),
        "confirm_endpoint": "/automation/files/email-send/confirm",
        "recipient": recipient.strip(),
        "subject": subject,
        "sensitive_type": sensitive_type,
        "file_count": len(artifacts),
        "requires_confirmation": True,
        "requires_sensitive_confirmation": True,
        "artifacts": [{key: item[key] for key in ("artifact_id", "filename", "mime_type", "download_path")}
                      for item in artifacts],
    }
    card["artifact"] = card["artifacts"][0]
    write_audit_log(
        user_id=current_user["id"], action="email_send.confirmation_created",
        resource_type="email_send_confirmation", resource_id=card["confirmation_id"],
        metadata={"recipient": card["recipient"], "artifact_ids": artifact_ids, "sensitive_type": sensitive_type},
    )
    return card


def confirm_email_send(
    *, confirmation_id: str, recipient: str, artifact_ids: list[str],
    current_user: dict,
) -> dict[str, Any]:
    started_ms = now_ms()
    ensure_email_confirmation_schema()
    row = fetch_one("""
        SELECT user_id, recipient, subject, body, artifacts, status, expires_at, error, run_id
        FROM email_send_confirmations WHERE id = %s;
    """, (confirmation_id,))
    if row is None or str(row[0]) != str(current_user.get("id")):
        raise HTTPException(status_code=404, detail="邮件确认不存在。")
    stored_recipient, subject, body, artifacts, current_status, expires_at, _, run_id = row[1:]

    def deny(reason: str, code: int = 409) -> None:
        write_audit_log(
            user_id=current_user["id"], action="email_send.confirmation_denied",
            resource_type="email_send_confirmation", resource_id=confirmation_id,
            metadata={"reason": reason, "status": current_status},
        )
        raise HTTPException(status_code=code, detail=reason)

    if current_status not in {"pending", "failed"}:
        deny("此邮件确认已处理或正在发送。")
    if expires_at <= datetime.now(timezone.utc):
        deny("邮件确认已过期，请重新生成确认卡。")
    if recipient.strip() != stored_recipient:
        deny("收件人已变更，请重新生成确认卡。")
    if artifact_ids != [item["artifact_id"] for item in artifacts]:
        deny("附件列表已变更，请重新生成确认卡。")

    attachments: list[EmailAttachment] = []
    for item in artifacts:
        ref = get_generated_file_storage_reference(item["artifact_id"], current_user=current_user)
        content = read_artifact(ref["storage_path"])
        if (ref["filename"] != item["filename"] or ref["mime_type"] != item["mime_type"]
                or hashlib.sha256(content).hexdigest() != item["sha256"]):
            deny("附件内容已变更，请重新生成确认卡。")
        attachments.append(EmailAttachment(filename=item["filename"], content=content, mime_type=item["mime_type"]))

    claimed = fetch_one("""
        UPDATE email_send_confirmations SET status = 'sending', error = NULL
        WHERE id = %s AND user_id = %s AND status = %s AND expires_at > now()
        RETURNING id;
    """, (confirmation_id, current_user["id"], current_status))
    if claimed is None:
        deny("此邮件确认已被处理，请刷新状态。")

    try:
        result = send_email_with_attachments(
            to_email=stored_recipient, subject=subject, body=body, attachments=attachments,
        )
    except Exception as exc:
        execute("UPDATE email_send_confirmations SET status = 'unknown', error = %s WHERE id = %s;", (str(exc), confirmation_id))
        raise
    next_status = "sent" if result.sent else ("unknown" if result.message_id else "failed")
    execute("""
        UPDATE email_send_confirmations
        SET status = %s, error = %s, sent_at = CASE WHEN %s THEN now() ELSE NULL END
        WHERE id = %s AND status = 'sending';
    """, (next_status, result.error, result.sent, confirmation_id))
    write_audit_log(
        user_id=current_user["id"], action=f"email_send.{next_status}",
        resource_type="email_send_confirmation", resource_id=confirmation_id,
        metadata={"recipient": stored_recipient, "artifact_ids": artifact_ids, "message_id": result.message_id,
                  "error": result.error},
    )
    if run_id:
        record_step(
            run_id=str(run_id), step_name="email_delivery", step_order=99,
            status_value="succeeded" if result.sent else "failed" if next_status == "failed" else "blocked",
            provider=result.provider, resource_type="email", resource_id=stored_recipient,
            input_text={"confirmation_id": confirmation_id, "artifact_ids": artifact_ids},
            output_text=next_status, error_message=result.error,
            duration_ms=elapsed_ms(started_ms),
            metadata={"confirmation_id": confirmation_id, "message_id": result.message_id, "status": next_status},
        )
    if result.sent:
        try:
            execute("""
                UPDATE chat_messages
                SET metadata = jsonb_set(
                    jsonb_set(metadata, '{approval_result,status}', '"sent"'::jsonb, true),
                    '{automation,confirmation_card,status}', '"sent"'::jsonb, true
                )
                WHERE user_id = %s AND role = 'assistant'
                  AND metadata->'approval_result'->>'confirmation_id' = %s;
            """, (current_user["id"], confirmation_id))
        except Exception:
            logger.exception("Failed to update sent email confirmation card %s", confirmation_id)
    return {
        "confirmation_id": confirmation_id, "status": next_status,
        "status_label": "邮件已发送" if result.sent else "邮件发送结果未知，请人工核对" if next_status == "unknown" else "邮件发送失败，可重试",
        "recipient": stored_recipient, "artifact_ids": artifact_ids,
        "message_id": result.message_id, "error": result.error,
    }
