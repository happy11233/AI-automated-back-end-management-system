from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.mcp_client import MCP_SERVERS, call_mcp_tool  # noqa: E402
from app.services.mcp_tool_registry_service import (  # noqa: E402
    get_mcp_tool_definition,
    list_static_mcp_tools,
)


def main() -> None:
    expected_servers = {
        "desktop_rpa",
        "document_system",
        "erpnext_tools",
        "file_center",
        "message_sender",
        "n8n_dispatcher",
        "playwright_amazon",
        "postgres_readonly",
        "ticket_system",
    }
    assert expected_servers.issubset(set(MCP_SERVERS)), MCP_SERVERS

    tools = list_static_mcp_tools()
    tool_ids = {item["tool_id"] for item in tools}
    expected_tools = {
        "erpnext.query_salary_slips",
        "file_center.get_generated_file_download_path",
        "n8n.dispatch_workflow",
        "desktop_rpa.prepare_wechat_attachment",
        "playwright_amazon.prepare_seller_central_listing",
        "message_sender.prepare_message_draft",
        "message_sender.send_confirmed_email",
        "postgres_readonly.summarize_automation_runs",
        "postgres_readonly.list_recent_failures",
        "postgres_readonly.get_run_diagnostics",
        "document_system.list_documents",
        "ticket_system.create_ticket",
    }
    assert expected_tools.issubset(tool_ids), tool_ids

    salary_tool = get_mcp_tool_definition("erpnext.query_salary_slips")
    assert salary_tool.risk_level == "high", salary_tool
    assert "finance" in salary_tool.position_scopes, salary_tool
    assert salary_tool.requires_approval is True, salary_tool

    desktop_tool = get_mcp_tool_definition("desktop_rpa.prepare_wechat_attachment")
    assert desktop_tool.risk_level == "high", desktop_tool
    assert desktop_tool.requires_approval is True, desktop_tool
    assert any(item["name"] == "local_file_path" for item in desktop_tool.input_schema), desktop_tool

    playwright_tool = get_mcp_tool_definition("playwright_amazon.prepare_seller_central_listing")
    assert playwright_tool.risk_level == "high", playwright_tool
    assert "operations" in playwright_tool.position_scopes, playwright_tool
    assert playwright_tool.requires_approval is True, playwright_tool

    email_tool = get_mcp_tool_definition("message_sender.send_confirmed_email")
    assert email_tool.risk_level == "high", email_tool
    assert "finance" in email_tool.position_scopes, email_tool
    assert email_tool.requires_approval is True, email_tool

    postgres_tool = get_mcp_tool_definition("postgres_readonly.get_run_diagnostics")
    assert postgres_tool.risk_level == "high", postgres_tool
    assert tuple(postgres_tool.position_scopes) == ("platform",), postgres_tool
    assert postgres_tool.requires_approval is False, postgres_tool

    file_result = call_mcp_tool(
        "file_center",
        "get_generated_file_download_path",
        {"artifact_id": "artifact-demo"},
    )
    assert file_result["download_path"] == "/files/artifact-demo/download", file_result

    os.environ["FINANCE_WECHAT_MAC_RPA_ENABLED"] = "false"
    rpa_result = call_mcp_tool(
        "desktop_rpa",
        "prepare_wechat_attachment",
        {
            "recipient_name": "张三",
            "artifact_id": "artifact-demo",
            "filename": "salary-demo.xlsx",
            "download_path": "/files/artifact-demo/download",
        },
    )
    assert rpa_result["manual_final_send_required"] is True, rpa_result
    assert rpa_result["auto_click_send_allowed"] is False, rpa_result
    assert rpa_result["status"] in {"waiting_executor", "waiting_manual_send"}, rpa_result

    n8n_health = call_mcp_tool("n8n_dispatcher", "health_check", {})
    assert n8n_health["status"] in {"not_configured", "configured", "invalid_config"}, n8n_health

    os.environ["AMAZON_PLAYWRIGHT_ENABLED"] = "false"
    playwright_result = call_mcp_tool(
        "playwright_amazon",
        "prepare_seller_central_listing",
        {
            "target_marketplace": "US",
            "sku": "DEMO-SKU-001",
            "listing": {
                "title": "Demo insulated tumbler",
                "bullet_points": ["Keeps drinks warm", "Leak resistant"],
                "description": "Demo listing content for verification.",
                "keywords": "tumbler insulated cup",
                "price": "19.99",
                "inventory": 20,
            },
            "stop_before_publish": True,
        },
    )
    assert playwright_result["status"] == "waiting_executor", playwright_result
    assert playwright_result["auto_publish_allowed"] is False, playwright_result
    assert playwright_result["manual_final_publish_required"] is True, playwright_result

    message_draft = call_mcp_tool(
        "message_sender",
        "prepare_message_draft",
        {
            "channel": "email",
            "recipient": "finance@example.com",
            "subject": "演示邮件",
            "body": "这是验证脚本生成的待确认草稿。",
            "attachments": [{"filename": "demo.xlsx"}],
            "sensitive": True,
        },
    )
    assert message_draft["status"] == "waiting_confirmation", message_draft
    assert message_draft["requires_confirmation"] is True, message_draft

    os.environ["MESSAGE_SENDER_REAL_SEND_ENABLED"] = "false"
    email_result = call_mcp_tool(
        "message_sender",
        "send_confirmed_email",
        {
            "recipient": "finance@example.com",
            "subject": "演示邮件",
            "body": "这是验证脚本生成的待发送邮件。",
            "attachments": [],
            "confirmed": False,
            "sensitive_confirmed": False,
        },
    )
    assert email_result["status"] == "waiting_confirmation", email_result

    postgres_health = call_mcp_tool("postgres_readonly", "health_check", {})
    assert postgres_health["status"] in {"healthy", "unhealthy"}, postgres_health
    assert postgres_health.get("free_sql_allowed") is False or postgres_health["status"] == "unhealthy", postgres_health

    print(json.dumps({
        "ok": True,
        "server_count": len(MCP_SERVERS),
        "tool_count": len(tools),
        "expected_tools_checked": sorted(expected_tools),
        "file_center_checked": True,
        "desktop_rpa_checked": True,
        "desktop_rpa_real_mac_guard_checked": True,
        "n8n_health_status": n8n_health["status"],
        "playwright_amazon_checked": True,
        "message_sender_checked": True,
        "postgres_readonly_health_status": postgres_health["status"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
