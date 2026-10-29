"""Isolated regression for email confirmation and high-risk MCP execution gates."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import email_confirmation_service as email_gate  # noqa: E402
from app.services import mcp_tool_registry_service as mcp_registry  # noqa: E402
from app.services.email_service import EmailSendResult  # noqa: E402
from app.mcp_servers import message_sender as message_sender_mcp  # noqa: E402


USER = {"id": "00000000-0000-0000-0000-000000000001", "role": "admin", "position": "finance"}
ARTIFACT = {"artifact_id": "artifact-1", "filename": "salary.xlsx", "mime_type": "application/vnd.ms-excel",
            "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
            "download_path": "/files/artifact-1/download"}
REFERENCE = {"id": "artifact-1", "filename": "salary.xlsx", "mime_type": "application/vnd.ms-excel",
             "storage_path": "safe-path"}


def assert_rejected(action, expected_status=409):
    try:
        action()
    except HTTPException as exc:
        assert exc.status_code == expected_status, exc
    else:
        raise AssertionError("Expected confirmation to be rejected")


def verify_email_gate():
    future = datetime.now(timezone.utc) + timedelta(minutes=20)
    row = (USER["id"], "finance@example.com", "工资表", "请查收", [ARTIFACT], "pending", future, None, None)
    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "get_generated_file_storage_reference", return_value=REFERENCE), \
         patch.object(email_gate, "read_artifact", return_value=b"hello"), \
         patch.object(email_gate, "fetch_one", return_value=("00000000-0000-0000-0000-000000000002", future)) as insert, \
         patch.object(email_gate, "send_email_with_attachments") as send, \
         patch.object(email_gate, "write_audit_log"):
        card = email_gate.create_email_confirmation(
            current_user=USER, recipient="finance@example.com", subject="工资表",
            body="请查收", artifact_ids=["artifact-1"], sensitive_type="员工工资表",
        )
        assert card["status"] == "waiting_email_confirmation"
        assert card["file_count"] == 1
        assert "sha256" not in str(card)
        assert ARTIFACT["sha256"] in str(insert.call_args)
        send.assert_not_called()

    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "fetch_one", return_value=row), \
         patch.object(email_gate, "get_generated_file_storage_reference") as get_file, \
         patch.object(email_gate, "read_artifact") as read_file, \
         patch.object(email_gate, "send_email_with_attachments") as send, \
         patch.object(email_gate, "write_audit_log"):
        get_file.return_value = REFERENCE
        read_file.return_value = b"hello"
        base = {"confirmation_id": "00000000-0000-0000-0000-000000000002",
                "recipient": "finance@example.com", "artifact_ids": ["artifact-1"], "current_user": USER}
        assert_rejected(lambda: email_gate.confirm_email_send(**{**base, "recipient": "other@example.com"}))
        assert_rejected(lambda: email_gate.confirm_email_send(**{**base, "artifact_ids": ["artifact-2"]}))
        send.assert_not_called()
        get_file.assert_not_called()

    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "fetch_one", side_effect=[row, (base["confirmation_id"],)]), \
         patch.object(email_gate, "get_generated_file_storage_reference", return_value=REFERENCE), \
         patch.object(email_gate, "read_artifact", return_value=b"tampered"), \
         patch.object(email_gate, "send_email_with_attachments") as send, \
         patch.object(email_gate, "write_audit_log"):
        assert_rejected(lambda: email_gate.confirm_email_send(**base))
        send.assert_not_called()

    expired = (*row[:6], datetime.now(timezone.utc) - timedelta(minutes=1), None, None)
    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "fetch_one", return_value=expired), \
         patch.object(email_gate, "send_email_with_attachments") as send, \
         patch.object(email_gate, "write_audit_log"):
        assert_rejected(lambda: email_gate.confirm_email_send(**base))
        send.assert_not_called()

    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "fetch_one", side_effect=[row, None]), \
         patch.object(email_gate, "get_generated_file_storage_reference", return_value=REFERENCE), \
         patch.object(email_gate, "read_artifact", return_value=b"hello"), \
         patch.object(email_gate, "send_email_with_attachments") as send, \
         patch.object(email_gate, "write_audit_log"):
        assert_rejected(lambda: email_gate.confirm_email_send(**base))
        send.assert_not_called()

    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "fetch_one", side_effect=[row, (base["confirmation_id"],)]), \
         patch.object(email_gate, "get_generated_file_storage_reference", return_value=REFERENCE), \
         patch.object(email_gate, "read_artifact", return_value=b"hello"), \
         patch.object(email_gate, "send_email_with_attachments", return_value=EmailSendResult(
             sent=True, recipient="finance@example.com", message_id="test-1", provider="mock")) as send, \
         patch.object(email_gate, "execute"), \
         patch.object(email_gate, "write_audit_log"):
        result = email_gate.confirm_email_send(**base)
        assert result["status"] == "sent", result
        send.assert_called_once()

    with patch.object(email_gate, "ensure_email_confirmation_schema"), \
         patch.object(email_gate, "fetch_one", side_effect=[row, (base["confirmation_id"],)]), \
         patch.object(email_gate, "get_generated_file_storage_reference", return_value=REFERENCE), \
         patch.object(email_gate, "read_artifact", return_value=b"hello"), \
         patch.object(email_gate, "send_email_with_attachments", return_value=EmailSendResult(
             sent=False, recipient="finance@example.com", message_id="uncertain-1", provider="mock", error="timeout")), \
         patch.object(email_gate, "execute") as update, \
         patch.object(email_gate, "write_audit_log"):
        result = email_gate.confirm_email_send(**base)
        assert result["status"] == "unknown", result
        assert update.call_args_list[0].args[1][0] == "unknown"


def verify_mcp_gate():
    previous_flag = message_sender_mcp.settings.message_sender_real_send_enabled
    try:
        message_sender_mcp.settings.message_sender_real_send_enabled = True
        with patch("app.services.email_service.send_email_with_attachments") as send:
            direct = message_sender_mcp.send_confirmed_email(
                recipient="finance@example.com", subject="工资表", body="请查收",
                attachments=[], confirmed=True, sensitive_confirmed=True,
            )
            assert direct["status"] == "blocked" and direct["sent"] is False
            send.assert_not_called()
    finally:
        message_sender_mcp.settings.message_sender_real_send_enabled = previous_flag

    with patch.object(mcp_registry, "ensure_mcp_tool_registry_schema"), \
         patch.object(mcp_registry, "_get_tool_setting", return_value=None), \
         patch.object(mcp_registry, "_ensure_position_allowed"), \
         patch.object(mcp_registry, "write_audit_log") as audit, \
         patch.object(mcp_registry, "call_mcp_tool") as call:
        call.return_value = {"ok": True}
        assert_rejected(lambda: mcp_registry.execute_managed_mcp_tool(
            tool_id="message_sender.send_confirmed_email",
            arguments={"confirmed": True, "sensitive_confirmed": True},
            current_user=USER, source="chat_plan_execute"), expected_status=403)
        call.assert_not_called()
        assert any(item.kwargs.get("action") == "mcp_tool.approval_denied" for item in audit.call_args_list)
        result = mcp_registry.execute_managed_mcp_tool(
            tool_id="file_center.get_generated_file_download_path",
            arguments={"artifact_id": "artifact-1"}, current_user=USER, source="chat_plan_execute")
        assert result == {"ok": True}
        call.assert_called_once()

    with patch.object(mcp_registry, "ensure_mcp_tool_registry_schema"), \
         patch.object(mcp_registry, "_get_tool_setting", return_value=None), \
         patch.object(mcp_registry, "_ensure_position_allowed"), \
         patch.object(mcp_registry, "fetch_one", return_value=None), \
         patch.object(mcp_registry, "write_audit_log"), \
         patch.object(mcp_registry, "call_mcp_tool") as call:
        assert_rejected(lambda: mcp_registry.execute_managed_mcp_tool(
            tool_id="n8n.dispatch_workflow", arguments={"workflow_type": "demo", "payload": {}},
            current_user=USER, source="finance_salary_wechat_send", approval_id="forged"), expected_status=403)
        call.assert_not_called()

    with patch.object(mcp_registry, "ensure_mcp_tool_registry_schema"), \
         patch.object(mcp_registry, "_get_tool_setting", return_value=None), \
         patch.object(mcp_registry, "_ensure_position_allowed"), \
         patch.object(mcp_registry, "fetch_one", return_value=("approved",)), \
         patch.object(mcp_registry, "write_audit_log"), \
         patch.object(mcp_registry, "call_mcp_tool", return_value={"ok": True}) as call:
        result = mcp_registry.execute_managed_mcp_tool(
            tool_id="n8n.dispatch_workflow", arguments={"workflow_type": "demo", "payload": {}},
            current_user=USER, source="finance_salary_wechat_send", approval_id="approved")
        assert result == {"ok": True}
        call.assert_called_once()


if __name__ == "__main__":
    verify_email_gate()
    verify_mcp_gate()
    print("email confirmation and MCP execution gates: OK")
