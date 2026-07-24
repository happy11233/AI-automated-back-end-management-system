from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib
import ssl
from typing import Any
from uuid import uuid4

from app.config import settings


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
        "发送到我的邮箱",
        "发到我的邮箱",
        "发我邮箱",
        "发邮箱",
        "发送邮箱",
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
