"""Exercise real one-time MCP grants with the external MCP call replaced."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import close_pool, execute, fetch_one, open_pool  # noqa: E402
from app.services import mcp_tool_registry_service as registry  # noqa: E402


def main() -> None:
    open_pool()
    approval_id = None
    try:
        row = fetch_one("SELECT id, role, position FROM users WHERE role = 'admin' LIMIT 1;")
        assert row is not None, "Need one local admin fixture"
        current_user = {"id": str(row[0]), "role": row[1], "position": row[2]}
        args = {"workflow_type": "isolated_test", "payload": {"artifact_id": "mock-only"}}
        with patch.object(registry, "write_audit_log"), \
             patch.object(registry, "_get_tool_setting", return_value=None), \
             patch.object(registry, "call_mcp_tool", return_value={"ok": True}) as external:
            approval_id = registry.issue_managed_mcp_approval(
                tool_id="n8n.dispatch_workflow", arguments=args,
                current_user=current_user, source="finance_salary_wechat_send",
            )
            try:
                registry.execute_managed_mcp_tool(
                    tool_id="n8n.dispatch_workflow", arguments={**args, "payload": {"artifact_id": "changed"}},
                    current_user=current_user, source="finance_salary_wechat_send", approval_id=approval_id,
                )
            except HTTPException as exc:
                assert exc.status_code == 403
            else:
                raise AssertionError("Changed arguments bypassed grant")
            external.assert_not_called()
            result = registry.execute_managed_mcp_tool(
                tool_id="n8n.dispatch_workflow", arguments=args, current_user=current_user,
                source="finance_salary_wechat_send", approval_id=approval_id,
            )
            assert result["ok"] is True
            external.assert_called_once()
            try:
                registry.execute_managed_mcp_tool(
                    tool_id="n8n.dispatch_workflow", arguments=args, current_user=current_user,
                    source="finance_salary_wechat_send", approval_id=approval_id,
                )
            except HTTPException as exc:
                assert exc.status_code == 403
            else:
                raise AssertionError("Grant replay was accepted")
            external.assert_called_once()
        print("MCP approval argument binding and one-time use: OK")
    finally:
        if approval_id:
            execute("DELETE FROM mcp_execution_approvals WHERE id = %s;", (approval_id,))
        close_pool()


if __name__ == "__main__":
    main()
