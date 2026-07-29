import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.services.platform_action_security_service import (
    open_platform_action_request,
    preview_platform_action_executor_url,
)


mcp = FastMCP(
    "company-n8n-dispatcher",
    instructions="受控 n8n 调度工具。调用前必须由后端完成权限、审批和审计。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """检查 n8n Webhook 是否已配置。不会发起业务动作。"""
    webhook_url = (settings.finance_wechat_n8n_webhook_url or "").strip()
    if not webhook_url:
        return {
            "ok": False,
            "status": "not_configured",
            "message": "FINANCE_WECHAT_N8N_WEBHOOK_URL 未配置。",
        }

    try:
        preview_platform_action_executor_url(webhook_url)
    except ValueError as error:
        return {
            "ok": False,
            "status": "invalid_config",
            "message": f"n8n Webhook 配置不合法：{error}",
        }

    return {
        "ok": True,
        "status": "configured",
        "message": "n8n Webhook 已配置；业务调用时会再次执行 allowlist 安全校验。",
        "webhook_url_preview": preview_platform_action_executor_url(webhook_url),
    }


@mcp.tool()
def dispatch_workflow(
    workflow_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """投递受控 n8n 工作流。payload 必须来自后端 executor，不能由大模型自由生成。"""
    webhook_url = (settings.finance_wechat_n8n_webhook_url or "").strip()
    if not webhook_url:
        return {
            "ok": False,
            "status": "waiting_executor",
            "configured": False,
            "message": "n8n Webhook 未配置，任务保持等待外部执行器接入。",
        }

    request_payload = {
        "workflow_type": workflow_type,
        "payload": payload,
        "safety": {
            "llm_direct_execution_allowed": False,
            "backend_permission_checked": True,
        },
    }
    headers = {
        "Content-Type": "application/json",
    }
    if settings.finance_wechat_n8n_api_key:
        headers["Authorization"] = f"Bearer {settings.finance_wechat_n8n_api_key}"

    request = Request(
        webhook_url,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with open_platform_action_request(
            request,
            timeout=max(1, int(settings.finance_wechat_executor_timeout_seconds or 12)),
        ) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
            response_payload = _parse_response(raw_body)
    except ValueError as error:
        return _failed(f"n8n Webhook 安全校验失败：{error}")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace") if error.fp else ""
        return _failed(f"n8n Webhook 返回 HTTP {error.code}：{error_body[:300]}")
    except (TimeoutError, URLError) as error:
        return _failed(f"n8n Webhook 请求失败：{error}")

    return {
        "ok": True,
        "status": str(response_payload.get("status") or "accepted"),
        "configured": True,
        "message": "n8n 已接收工作流任务。",
        "webhook_url_preview": preview_platform_action_executor_url(webhook_url),
        "response_payload": response_payload,
        "external_reference": _external_reference(response_payload),
        "accepted": True,
    }


def _parse_response(raw_body: str) -> dict[str, Any]:
    text = (raw_body or "").strip()
    if not text:
        return {"accepted": True}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"accepted": True, "raw": text[:500]}
    if isinstance(value, dict):
        return value
    return {"accepted": True, "items": value}


def _failed(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "failed",
        "configured": True,
        "message": message,
    }


def _external_reference(response_payload: dict[str, Any]) -> str | None:
    for key in ("external_reference", "execution_id", "task_id", "id"):
        value = response_payload.get(key)
        if value:
            return str(value)
    return None


if __name__ == "__main__":
    mcp.run(transport="stdio")
