from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    spec = read("docs/specs/019_operations_listing_amazon_seller_central_closure.md")
    service = read("app/services/operations_listing_amazon_service.py")
    platform_api = read("app/api/platform_drafts.py")
    playwright_mcp = read("app/mcp_servers/playwright_amazon.py")
    chat_dispatcher = read("app/services/chat_automation_dispatcher.py")
    main_py = read("app/main.py")
    ai_workflow = read("app/services/ai_workflow_service.py")
    automation_api = read("app/api/automation.py")

    assert "真实 Amazon Seller Central" in spec, "Spec 019 must target real Seller Central"
    assert "网页逐字段填写" in spec and "批量 Excel 模板" in spec, "Spec must include both upload modes"

    assert "def generate_operations_listing_draft" in service, "operations Listing Skill must have dedicated service"
    assert "query_listing_erp_context" in service, "service must query ERPNext listing context"
    assert "analyze_listing_images" in service, "service must process product images"
    assert "confirm_and_prepare_amazon_listing_upload" in service, "service must expose confirmed upload flow"
    assert "execute_managed_mcp_tool" in service and "playwright_amazon.prepare_seller_central_listing" in service
    assert "manual_final_publish_required" in service and "auto_publish_allowed" in service

    assert "@router.post(\"/{draft_id}/amazon-upload\"" in platform_api, "confirm upload API missing"
    assert "AmazonListingUploadRequest" in platform_api, "upload request model missing"

    assert "upload_mode" in playwright_mcp and "batch_excel" in playwright_mcp and "web_form" in playwright_mcp
    assert "page.set_input_files" in playwright_mcp, "Playwright MCP must support file upload"
    assert "page.locator" in playwright_mcp, "Playwright MCP must support field filling"
    assert "auto_publish_allowed" in playwright_mcp and "False" in playwright_mcp

    assert "attachments" in chat_dispatcher and "generate_operations_listing_draft" not in chat_dispatcher
    assert "attachments: list[dict[str, Any]]" in main_py, "ChatRequest must accept attachments"
    assert "operations_listing_amazon" in main_py, "stream progress must include operations Listing workflow"

    assert "execute_platform_draft_action" not in ai_workflow, "Listing workflow must not auto-submit external writeback"
    assert "execute_platform_draft_action" not in automation_api, "Automation generate must not auto-submit Listing writeback"
    assert "waiting_confirmation" in ai_workflow and "waiting_confirmation" in automation_api

    print(json.dumps({
        "ok": True,
        "spec": "019_operations_listing_amazon_seller_central_closure",
        "contracts_checked": [
            "confirmed_upload_api",
            "erp_sku_context",
            "image_attachment_context",
            "playwright_mcp_web_form",
            "playwright_mcp_batch_excel",
            "no_auto_external_writeback_after_draft",
            "manual_final_publish_required",
        ],
    }, ensure_ascii=False, indent=2))


def read(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.exists(), path
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
