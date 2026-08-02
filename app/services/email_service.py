from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import re
import smtplib
import ssl
from typing import Any
from uuid import uuid4

from app.config import settings


EMAIL_ADDRESS_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)
EMAIL_TOKEN_RE = re.compile(r"([A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+(?:@[A-Za-z0-9.-]+)+)")


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str


@dataclass
class EmailSendResult:
    sent: bool
    recipient: str | None
    message_id: str | None
    provider: str
    error: str | None = None


def is_email_send_requested(message: str) -> bool:
    lowered = (message or "").lower()
    request_keywords = [
        "通过邮箱",
        "用邮箱",
        "邮箱是",
        "邮箱为",
        "邮箱：",
        "邮箱:",
        "发送到我的邮箱",
        "发到我的邮箱",
        "发我邮箱",
        "发邮箱",
        "发到邮箱",
        "发送邮箱",
        "发送到邮箱",
        "发送至邮箱",
        "邮箱发送",
        "发送邮件",
        "发邮件",
        "邮件发给我",
        "邮箱给我",
        "send to my email",
        "email it to me",
        "send me by email",
        "send it to my mailbox",
        "mail it to me",
    ]
    negative_keywords = [
        "不要发邮箱",
        "不用发邮箱",
        "不发送邮箱",
        "不要发送到我的邮箱",
        "do not email",
        "don't email",
    ]
    if any(keyword in lowered for keyword in negative_keywords):
        return False
    return any(keyword in lowered for keyword in request_keywords)


def resolve_email_recipient(message: str, fallback_email: str | None) -> tuple[str | None, str]:
    requested_email = extract_requested_email(message)
    if requested_email:
        return requested_email, "message"
    return (fallback_email or None), "profile" if fallback_email else "none"


def extract_requested_email(message: str) -> str | None:
    match = EMAIL_TOKEN_RE.search(message or "")
    if not match:
        return None
    return match.group(1).strip().strip("<>\"'")


def validate_email_address(email: str | None) -> str | None:
    normalized = (email or "").strip()
    if not normalized:
        return "没有填写邮箱地址。"
    if normalized.count("@") != 1 or not EMAIL_ADDRESS_RE.fullmatch(normalized):
        return f"邮箱地址格式不正确：{normalized}。请检查是否多写了 @，例如 name@example.com。"
    return None


def send_email_with_attachments(
    *,
    to_email: str | None,
    subject: str,
    body: str,
    attachments: list[EmailAttachment],
) -> EmailSendResult:
    normalized_to = (to_email or "").strip()
    if not normalized_to:
        return EmailSendResult(
            sent=False,
            recipient=None,
            message_id=None,
            provider="smtp",
            error="用户设置里没有邮箱，无法自动发送。",
        )
    validation_error = validate_email_address(normalized_to)
    if validation_error:
        return EmailSendResult(
            sent=False,
            recipient=normalized_to,
            message_id=None,
            provider="smtp",
            error=validation_error,
        )
    if not _is_configured():
        return EmailSendResult(
            sent=False,
            recipient=normalized_to,
            message_id=None,
            provider="smtp",
            error="SMTP 未配置，已生成文件但没有发送邮件。",
        )

    message_id = f"company-rag-{uuid4().hex}"
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = settings.smtp_from_email or settings.smtp_username or ""
    email["To"] = normalized_to
    email["X-Company-Rag-Message-Id"] = message_id
    email.set_content(body)

    for attachment in attachments:
        maintype, subtype = _split_mime_type(attachment.mime_type)
        email.add_attachment(
            attachment.content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )

    try:
        if settings.smtp_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=context,
            ) as server:
                _login(server)
                server.send_message(email)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as server:
                if settings.smtp_use_starttls:
                    server.starttls(context=ssl.create_default_context())
                _login(server)
                server.send_message(email)
    except Exception as error:
        return EmailSendResult(
            sent=False,
            recipient=normalized_to,
            message_id=message_id,
            provider="smtp",
            error=str(error),
        )

    return EmailSendResult(
        sent=True,
        recipient=normalized_to,
        message_id=message_id,
        provider="smtp",
    )


def email_result_metadata(result: EmailSendResult) -> dict[str, Any]:
    return {
        "email_requested": True,
        "email_sent": result.sent,
        "email_recipient": result.recipient,
        "email_provider": result.provider,
        "email_message_id": result.message_id,
        "email_error": result.error,
    }


def _is_configured() -> bool:
    return bool(settings.smtp_host and (settings.smtp_from_email or settings.smtp_username))


def _login(server: smtplib.SMTP) -> None:
    if settings.smtp_username and settings.smtp_password:
        server.login(settings.smtp_username, settings.smtp_password)


def _split_mime_type(mime_type: str) -> tuple[str, str]:
    if "/" not in mime_type:
        return "application", "octet-stream"
    maintype, subtype = mime_type.split("/", 1)
    return maintype or "application", subtype or "octet-stream"
