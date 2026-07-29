from __future__ import annotations

import re
from base64 import b64decode
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.services.enterprise_wechat_service import (
    EnterpriseWechatAttachment,
    enterprise_wechat_config_status,
    get_enterprise_wechat_contact,
    search_enterprise_wechat_recipients,
    send_enterprise_wechat_file,
)
from app.services.email_service import EmailAttachment, send_email_with_attachments


mcp = FastMCP(
    "company-message-sender",
    instructions="受控消息发送工具。敏感内容必须先由后端确认，不能由大模型直接发送。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """返回消息发送工具状态，不发送消息。"""
    smtp_configured = bool(settings.smtp_host and (settings.smtp_from_email or settings.smtp_username))
    real_send_enabled = bool(settings.message_sender_real_send_enabled)
    enterprise_wechat_status = enterprise_wechat_config_status()
    enterprise_wechat_configured = bool(enterprise_wechat_status["configured"])
    status = "configured" if (smtp_configured or enterprise_wechat_configured) and real_send_enabled else "stub_ready"
    return {
        "ok": True,
        "status": status,
        "message": _health_message(
            smtp_configured=smtp_configured,
            real_send_enabled=real_send_enabled,
            enterprise_wechat_configured=enterprise_wechat_configured,
        ),
        "channels": {
            "email": {
                "configured": smtp_configured,
                "real_send_enabled": real_send_enabled,
            },
            "enterprise_wechat": {
                "configured": enterprise_wechat_configured,
                "real_send_enabled": real_send_enabled,
                "status": enterprise_wechat_status["status"],
            },
        },
    }


@mcp.tool()
def prepare_message_draft(
    channel: str,
    recipient: str,
    subject: str,
    body: str,
    attachments: list[dict[str, Any]] | None = None,
    sensitive: bool = False,
) -> dict[str, Any]:
    """生成待确认消息草稿，不真实发送。"""
    normalized_channel = _normalize_channel(channel)
    normalized_recipient = str(recipient or "").strip()
    if not normalized_recipient:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "接收人不能为空。",
        }

    return {
        "ok": True,
        "status": "waiting_confirmation",
        "message": "已生成待确认消息草稿，确认后才会由后端发送。",
        "channel": normalized_channel,
        "recipient": _mask_recipient(normalized_recipient),
        "subject": str(subject or "").strip()[:160],
        "body_preview": str(body or "").strip()[:240],
        "attachment_count": len(attachments or []),
        "sensitive": bool(sensitive),
        "requires_confirmation": True,
        "llm_direct_execution_allowed": False,
    }


@mcp.tool()
def send_confirmed_email(
    recipient: str,
    subject: str,
    body: str,
    attachments: list[dict[str, Any]] | None = None,
    confirmed: bool = False,
    sensitive_confirmed: bool = False,
) -> dict[str, Any]:
    """发送已确认邮件；真实发送开关未启用时只返回待发送。"""
    normalized_recipient = str(recipient or "").strip()
    if not _looks_like_email(normalized_recipient):
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "邮箱地址格式不正确。",
        }
    if not _recipient_domain_allowed(normalized_recipient):
        return {
            "ok": False,
            "status": "blocked",
            "message": "接收邮箱域名不在允许范围内。",
        }
    if not confirmed:
        return {
            "ok": False,
            "status": "waiting_confirmation",
            "message": "发送前需要用户确认接收人和邮件内容。",
            "requires_confirmation": True,
        }
    if not sensitive_confirmed:
        return {
            "ok": False,
            "status": "waiting_confirmation",
            "message": "包含可能敏感的业务附件，发送前需要确认敏感数据。",
            "requires_sensitive_confirmation": True,
        }
    if not settings.message_sender_real_send_enabled:
        return {
            "ok": True,
            "status": "waiting_executor",
            "message": "真实邮件发送开关未启用，当前停留在待发送状态。",
            "channel": "email",
            "recipient": _mask_recipient(normalized_recipient),
            "attachment_count": len(attachments or []),
            "sent": False,
        }

    email_attachments = _normalize_email_attachments(attachments or [])
    result = send_email_with_attachments(
        to_email=normalized_recipient,
        subject=str(subject or "").strip()[:200],
        body=str(body or "").strip(),
        attachments=email_attachments,
    )
    if not result.sent:
        return {
            "ok": False,
            "status": "failed",
            "message": result.error or "邮件发送失败。",
            "channel": "email",
            "recipient": _mask_recipient(normalized_recipient),
            "provider": result.provider,
            "sent": False,
        }

    return {
        "ok": True,
        "status": "completed",
        "message": "邮件已发送。",
        "channel": "email",
        "recipient": _mask_recipient(normalized_recipient),
        "message_id": result.message_id,
        "provider": result.provider,
        "attachment_count": len(email_attachments),
        "sent": True,
    }


@mcp.tool()
def search_enterprise_wechat_recipient(
    query: str,
    object_types: list[str] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """搜索企业微信成员、群聊或部门，只返回候选摘要。"""
    return search_enterprise_wechat_recipients(
        query=query,
        object_types=object_types,
        limit=limit,
    )


@mcp.tool()
def send_confirmed_enterprise_wechat_file(
    recipient: dict[str, Any] | None = None,
    recipient_candidate_id: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    confirmed: bool = False,
    sensitive_confirmed: bool = False,
) -> dict[str, Any]:
    """发送已确认企业微信文件；不附带正文说明。"""
    resolved_recipient = _resolve_enterprise_wechat_recipient(
        recipient=recipient,
        recipient_candidate_id=recipient_candidate_id,
    )
    if not resolved_recipient:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "企业微信接收对象不能为空。",
        }

    normalized_attachments = _normalize_enterprise_wechat_attachments(attachments or [])
    return send_enterprise_wechat_file(
        recipient=resolved_recipient,
        attachments=normalized_attachments,
        confirmed=confirmed,
        sensitive_confirmed=sensitive_confirmed,
    )


def _health_message(
    *,
    smtp_configured: bool,
    real_send_enabled: bool,
    enterprise_wechat_configured: bool,
) -> str:
    if smtp_configured and real_send_enabled:
        return "SMTP 邮件发送已配置并启用；发送仍要求后端确认。"
    if smtp_configured:
        return "SMTP 已配置，但真实发送开关未启用；当前只生成待发送状态。"
    if enterprise_wechat_configured:
        return "企业微信应用已配置；真实发送开关未启用时只停留在待发送状态。"
    return "消息发送通道未配置；当前只生成待确认草稿。"


def _normalize_channel(value: str) -> str:
    channel = str(value or "").strip().lower()
    if channel in {"email", "mail", "smtp", "邮箱", "邮件"}:
        return "email"
    if channel in {"enterprise_wechat", "wecom", "企业微信"}:
        return "enterprise_wechat"
    return "email"


def _looks_like_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value))


def _recipient_domain_allowed(value: str) -> bool:
    allowlist = [
        item.strip().lower()
        for item in (settings.message_sender_allowed_email_domains or "").replace(" ", ",").split(",")
        if item.strip()
    ]
    if not allowlist:
        return True
    domain = value.rsplit("@", 1)[-1].lower()
    return domain in allowlist


def _mask_recipient(value: str) -> str:
    if "@" not in value:
        return value[:1] + "***" if value else ""
    name, domain = value.rsplit("@", 1)
    prefix = name[:2] if len(name) >= 2 else name[:1]
    return f"{prefix}***@{domain}"


def _normalize_email_attachments(items: list[dict[str, Any]]) -> list[EmailAttachment]:
    attachments: list[EmailAttachment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        content = _attachment_content(item)
        if not isinstance(content, bytes):
            continue
        filename = str(item.get("filename") or "attachment").strip()[:180]
        mime_type = str(item.get("mime_type") or "application/octet-stream").strip()
        attachments.append(EmailAttachment(filename=filename, content=content, mime_type=mime_type))
    return attachments


def _resolve_enterprise_wechat_recipient(
    *,
    recipient: dict[str, Any] | None,
    recipient_candidate_id: str | None,
) -> dict[str, Any] | None:
    candidate_id = str(recipient_candidate_id or "").strip()
    if candidate_id:
        contact = get_enterprise_wechat_contact(candidate_id)
        if contact:
            return contact

    if isinstance(recipient, dict) and recipient.get("name"):
        return recipient
    return None


def _normalize_enterprise_wechat_attachments(items: list[dict[str, Any]]) -> list[EnterpriseWechatAttachment]:
    attachments: list[EnterpriseWechatAttachment] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        content = _attachment_content(item)
        if not isinstance(content, bytes):
            continue
        filename = str(item.get("filename") or "attachment").strip()[:180]
        mime_type = str(item.get("mime_type") or "application/octet-stream").strip()
        attachments.append(EnterpriseWechatAttachment(filename=filename, content=content, mime_type=mime_type))
    return attachments


def _attachment_content(item: dict[str, Any]) -> bytes | None:
    raw_content = item.get("content")
    if isinstance(raw_content, bytes):
        return raw_content
    if isinstance(item.get("content_base64"), str):
        try:
            return b64decode(str(item["content_base64"]), validate=True)
        except Exception:
            return None
    if isinstance(item.get("local_file_path"), str):
        return _read_allowed_local_file(str(item["local_file_path"]))
    return None


def _read_allowed_local_file(value: str) -> bytes | None:
    try:
        path = Path(value).expanduser().resolve()
        storage_root = Path(settings.generated_file_storage_dir).expanduser().resolve()
    except OSError:
        return None
    if storage_root not in path.parents and path != storage_root:
        return None
    if not path.exists() or not path.is_file():
        return None
    return path.read_bytes()


if __name__ == "__main__":
    mcp.run(transport="stdio")
