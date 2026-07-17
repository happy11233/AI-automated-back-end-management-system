from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from app.config import settings
from app.erp.diagnostics import build_erp_diagnostics
from app.erp.providers import PROVIDER_ORDER, get_provider
from app.erp.resources import ERP_RESOURCE_CATALOG, provider_fields_for, provider_resource_for
from app.feishu.client import get_configured_document_refs
from app.permissions import POSITION_ERP_SCOPES, POSITION_LABELS


def list_connectors() -> dict[str, Any]:
    items = _erp_connectors()
    items.extend(
        [
            _amazon_sp_api_connector(),
            _logistics_connector(),
            _amazon_ads_connector(),
            _feishu_connector(),
            _wechat_work_connector(),
            _email_connector(),
            _excel_connector(),
        ]
    )

    return {
        "summary": _summary(items),
        "items": items,
    }


def get_connector(connector_id: str) -> dict[str, Any]:
    normalized = connector_id.strip().lower()
    for item in list_connectors()["items"]:
        if item["id"] == normalized:
            return item

    from fastapi import HTTPException, status

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="连接器不存在",
    )


def _erp_connectors() -> list[dict[str, Any]]:
    diagnostics = build_erp_diagnostics()
    provider_diagnostics = {
        item["provider"]: item for item in diagnostics["providers"]
    }
    active_provider = str(diagnostics["active_provider"])
    checked_at = _checked_at()
    items: list[dict[str, Any]] = []

    for provider_id in PROVIDER_ORDER:
        provider = get_provider(provider_id)
        provider_diag = provider_diagnostics[provider_id]
        health = (
            diagnostics["active_health"]
            if provider_id == active_provider
            else provider.health_check()
        )
        resources = _erp_resources_for_provider(provider_id)

        items.append(
            {
                "id": provider_id,
                "label": provider.provider_label,
                "category": "ERP",
                "description": provider.description,
                "active": provider_id == active_provider,
                "configured": bool(provider_diag["configured"]),
                "status": _status_from_health(health),
                "health_status": str(health.get("status") or "unknown"),
                "health_message": str(health.get("message") or ""),
                "auth_type": _erp_auth_type(provider_id),
                "admin_only": True,
                "supports_real_health_check": provider_id == active_provider,
                "managed_by": "ERP 查询、AI 对话和岗位数据概览",
                "capabilities": [
                    "岗位权限资源查询",
                    "AI 对话 ERP 检索",
                    "首页岗位数据概览",
                    "运行记录与审计",
                ],
                "position_scopes": list(POSITION_ERP_SCOPES.keys()),
                "position_scope_labels": [POSITION_LABELS[item] for item in POSITION_ERP_SCOPES],
                "config_fields": provider_diag["config_fields"],
                "resources": resources,
                "next_steps": _erp_next_steps(provider_id, health),
                "last_checked_at": checked_at,
            }
        )

    return items


def _amazon_sp_api_connector() -> dict[str, Any]:
    fields = [
        _env_field("AMAZON_SP_API_CLIENT_ID", True, "Amazon SP-API LWA Client ID"),
        _env_field("AMAZON_SP_API_CLIENT_SECRET", True, "Amazon SP-API LWA Client Secret"),
        _env_field("AMAZON_SP_API_REFRESH_TOKEN", True, "Amazon SP-API Refresh Token"),
        _env_field("AMAZON_SP_API_REGION", False, "SP-API 区域，例如 NA / EU / FE"),
        _env_field("AMAZON_SELLER_ID", True, "Amazon Seller ID"),
    ]
    configured = all(item["configured"] for item in fields[:3])
    return _external_connector(
        connector_id="amazon_sp_api",
        label="Amazon SP-API",
        category="Marketplace",
        description="Amazon 跨境电商订单、Listing、库存和报表接口。",
        auth_type="OAuth2 / Login With Amazon",
        configured=configured,
        fields=fields,
        capabilities=["订单同步", "Listing 数据", "库存查询", "报表下载"],
        position_scopes=["operations", "finance"],
        resources=[
            _resource("Orders", "订单", "operations", "orders"),
            _resource("Listings Items", "Listing", "operations", "listing"),
            _resource("Inventory", "库存", "operations", "inventory"),
            _resource("Reports", "报表", "finance", "reports"),
        ],
    )


def _logistics_connector() -> dict[str, Any]:
    fields = [
        _env_field("LOGISTICS_API_BASE_URL", False, "物流服务 API 地址"),
        _env_field("LOGISTICS_API_KEY", True, "物流服务 API Key"),
        _env_field("LOGISTICS_PROVIDER", False, "物流服务商标识"),
    ]
    configured = fields[0]["configured"] and fields[1]["configured"]
    return _external_connector(
        connector_id="logistics",
        label="物流轨迹",
        category="Logistics",
        description="第三方物流轨迹、签收状态和异常件查询。",
        auth_type="API Key",
        configured=configured,
        fields=fields,
        capabilities=["轨迹查询", "签收状态", "异常件提醒"],
        position_scopes=["customer_service", "operations"],
        resources=[
            _resource("Tracking", "物流轨迹", "customer_service", "tracking"),
            _resource("Delivery Exception", "异常件", "customer_service", "delivery_exception"),
        ],
    )


def _amazon_ads_connector() -> dict[str, Any]:
    fields = [
        _env_field("AMAZON_ADS_CLIENT_ID", True, "Amazon Ads Client ID"),
        _env_field("AMAZON_ADS_CLIENT_SECRET", True, "Amazon Ads Client Secret"),
        _env_field("AMAZON_ADS_REFRESH_TOKEN", True, "Amazon Ads Refresh Token"),
        _env_field("AMAZON_ADS_PROFILE_ID", True, "Amazon Ads Profile ID"),
    ]
    configured = all(item["configured"] for item in fields[:3])
    return _external_connector(
        connector_id="amazon_ads",
        label="Amazon Ads",
        category="Ads",
        description="Amazon 广告活动、关键词和花费数据。",
        auth_type="OAuth2",
        configured=configured,
        fields=fields,
        capabilities=["广告活动", "关键词表现", "花费分析"],
        position_scopes=["operations", "finance"],
        resources=[
            _resource("Campaigns", "广告活动", "operations", "campaigns"),
            _resource("Keywords", "广告关键词", "operations", "keywords"),
            _resource("Spend", "广告花费", "finance", "spend"),
        ],
    )


def _feishu_connector() -> dict[str, Any]:
    document_refs = get_configured_document_refs()
    fields = [
        _settings_field("FEISHU_APP_ID", settings.feishu_app_id, True, "飞书应用 App ID"),
        _settings_field("FEISHU_APP_SECRET", settings.feishu_app_secret, True, "飞书应用 App Secret"),
        _settings_field("FEISHU_DOCUMENT_IDS", settings.feishu_document_ids, False, "可同步的飞书文档 ID 列表"),
        _settings_field("FEISHU_BITABLE_APP_TOKEN", settings.feishu_bitable_app_token, True, "飞书多维表格 App Token"),
        _settings_field("FEISHU_BITABLE_TABLE_ID", settings.feishu_bitable_table_id, True, "飞书多维表格 Table ID"),
    ]
    configured = bool(settings.feishu_app_id and settings.feishu_app_secret)
    status = "configured_pending" if configured else "not_configured"
    return {
        "id": "feishu",
        "label": "飞书",
        "category": "Collaboration",
        "description": "飞书文档同步和飞书多维表格工单。",
        "active": configured,
        "configured": configured,
        "status": status,
        "health_status": status,
        "health_message": (
            "飞书参数已配置；真实连通性会在文档同步或工单创建时由 Feishu API 校验。"
            if configured
            else "未配置飞书 App ID / App Secret。"
        ),
        "auth_type": "Tenant Access Token",
        "admin_only": True,
        "supports_real_health_check": False,
        "managed_by": "知识库同步、外部工单 MCP",
        "capabilities": ["飞书文档同步", "飞书多维表格工单"],
        "position_scopes": ["platform", "customer_service"],
        "position_scope_labels": ["平台", "客服"],
        "config_fields": fields,
        "resources": [
            _resource("Feishu Docx", "飞书文档", "platform", f"{len(document_refs)} 个文档引用"),
            _resource("Bitable Ticket", "飞书工单表", "customer_service", "ticket"),
        ],
        "next_steps": (
            ["调用真实飞书文档同步或工单创建流程，检查飞书 API 权限。"]
            if configured
            else ["配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET。", "如需同步文档，配置 FEISHU_DOCUMENT_IDS。"]
        ),
        "last_checked_at": _checked_at(),
    }


def _wechat_work_connector() -> dict[str, Any]:
    fields = [
        _env_field("WECHAT_WORK_CORP_ID", True, "企业微信 Corp ID"),
        _env_field("WECHAT_WORK_AGENT_ID", True, "企业微信 Agent ID"),
        _env_field("WECHAT_WORK_SECRET", True, "企业微信应用 Secret"),
    ]
    configured = all(item["configured"] for item in fields)
    return _external_connector(
        connector_id="wechat_work",
        label="企业微信",
        category="Collaboration",
        description="企业微信通知、审批提醒和内部消息。",
        auth_type="Corp Secret",
        configured=configured,
        fields=fields,
        capabilities=["内部通知", "审批提醒", "消息推送"],
        position_scopes=["platform"],
        resources=[_resource("Message", "企业微信消息", "platform", "message")],
    )


def _email_connector() -> dict[str, Any]:
    fields = [
        _env_field("EMAIL_SMTP_HOST", False, "SMTP Host"),
        _env_field("EMAIL_SMTP_USER", True, "SMTP 用户"),
        _env_field("EMAIL_SMTP_PASSWORD", True, "SMTP 密码或授权码"),
        _env_field("EMAIL_IMAP_HOST", False, "IMAP Host"),
    ]
    configured = fields[0]["configured"] and fields[1]["configured"] and fields[2]["configured"]
    return _external_connector(
        connector_id="email",
        label="邮箱",
        category="Communication",
        description="客服邮件、通知邮件和周期报表发送。",
        auth_type="SMTP / IMAP",
        configured=configured,
        fields=fields,
        capabilities=["邮件发送", "客服邮件读取", "报表分发"],
        position_scopes=["customer_service", "finance", "platform"],
        resources=[
            _resource("Outbound Email", "发信", "platform", "smtp"),
            _resource("Support Inbox", "客服邮箱", "customer_service", "imap"),
        ],
    )


def _excel_connector() -> dict[str, Any]:
    return {
        "id": "excel",
        "label": "Excel 文件",
        "category": "File",
        "description": "本地 Excel 上传、财务处理和知识库文件入库。",
        "active": True,
        "configured": True,
        "status": "healthy",
        "health_status": "available",
        "health_message": "本地文件上传、财务 Excel 处理和财务对账自动化已接入真实后端流程。",
        "auth_type": "Local file upload",
        "admin_only": True,
        "supports_real_health_check": True,
        "managed_by": "知识库上传、财务 Excel 自动化、财务对账自动化",
        "capabilities": ["财务 Excel 生成", "财务对账自动化", "知识库文件入库", "真实文件上传下载"],
        "position_scopes": ["finance", "platform"],
        "position_scope_labels": ["财务", "平台"],
        "config_fields": [],
        "resources": [
            _resource("Finance Workbook", "财务 Excel", "finance", "xlsx"),
            _resource("Knowledge File", "知识库文件", "platform", "docx/pdf/xlsx"),
        ],
        "next_steps": ["保持真实文件上传下载回归，不使用模拟文件响应。"],
        "last_checked_at": _checked_at(),
    }


def _external_connector(
    *,
    connector_id: str,
    label: str,
    category: str,
    description: str,
    auth_type: str,
    configured: bool,
    fields: list[dict[str, Any]],
    capabilities: list[str],
    position_scopes: list[str],
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    status = "configured_pending" if configured else "not_configured"
    return {
        "id": connector_id,
        "label": label,
        "category": category,
        "description": description,
        "active": configured,
        "configured": configured,
        "status": status,
        "health_status": status,
        "health_message": (
            "连接参数已配置；等待接入真实业务 API 后执行连通性检查。"
            if configured
            else "未配置连接参数。"
        ),
        "auth_type": auth_type,
        "admin_only": True,
        "supports_real_health_check": False,
        "managed_by": "连接器中心",
        "capabilities": capabilities,
        "position_scopes": position_scopes,
        "position_scope_labels": [_position_label(item) for item in position_scopes],
        "config_fields": fields,
        "resources": resources,
        "next_steps": (
            ["补充真实 API 文档和联调账号后接入健康检查。"]
            if configured
            else ["配置所需环境变量。", "拿到真实 API 文档后增加 provider 适配器。"]
        ),
        "last_checked_at": _checked_at(),
    }


def _erp_resources_for_provider(provider_id: str) -> list[dict[str, Any]]:
    items = []
    for resource, definition in ERP_RESOURCE_CATALOG.items():
        provider_resource = provider_resource_for(resource, provider_id)
        if not provider_resource:
            continue

        positions = [
            position
            for position, scopes in POSITION_ERP_SCOPES.items()
            if resource in scopes
        ]
        items.append(
            {
                "resource": resource,
                "label": definition["label"],
                "provider_resource": provider_resource,
                "position_scopes": positions,
                "position_scope_labels": [POSITION_LABELS[item] for item in positions],
                "fields": provider_fields_for(resource, provider_id),
            }
        )

    return items


def _erp_auth_type(provider_id: str) -> str:
    if provider_id == "erpnext":
        return "Token API Key / Secret"
    if provider_id == "kingdee":
        return "OpenAPI App Secret"
    if provider_id == "yonyou":
        return "YonBIP App Key / Secret"
    return "API Credential"


def _erp_next_steps(provider_id: str, health: dict[str, Any]) -> list[str]:
    status = str(health.get("status") or "")
    if status == "ok":
        return ["保持 ERPNext 真实查询和岗位越权回归。"]
    if status == "not_implemented":
        return ["等待真实接口规范后实现鉴权、查询和健康检查。"]
    if provider_id == "erpnext":
        return ["检查 ERP_BASE_URL、ERP_API_KEY、ERP_API_SECRET，并重启 API 容器。"]
    return ["配置连接参数，并接入真实厂商 OpenAPI。"]


def _resource(
    resource: str,
    label: str,
    position: str,
    provider_resource: str,
) -> dict[str, Any]:
    return {
        "resource": resource,
        "label": label,
        "provider_resource": provider_resource,
        "position_scopes": [position],
        "position_scope_labels": [_position_label(position)],
        "fields": [],
    }


def _position_label(position: str) -> str:
    if position == "platform":
        return "平台"
    return POSITION_LABELS.get(position, position)


def _summary(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(items),
        "configured": sum(1 for item in items if item["configured"]),
        "healthy": sum(1 for item in items if item["status"] == "healthy"),
        "needs_config": sum(1 for item in items if item["status"] == "not_configured"),
        "pending": sum(1 for item in items if item["status"] in {"configured_pending", "not_implemented"}),
    }


def _status_from_health(health: dict[str, Any]) -> str:
    if bool(health.get("ok")):
        return "healthy"

    status = str(health.get("status") or "unknown")
    if status == "not_configured":
        return "not_configured"
    if status == "not_implemented":
        return "not_implemented"
    return "degraded"


def _env_field(env_name: str, secret: bool, description: str) -> dict[str, Any]:
    return _settings_field(env_name, os.getenv(env_name), secret, description)


def _settings_field(
    name: str,
    value: str | int | None,
    secret: bool,
    description: str,
) -> dict[str, Any]:
    text = "" if value is None else str(value)
    return {
        "name": name,
        "configured": bool(text),
        "secret": secret,
        "value_preview": _mask_value(text, secret),
        "description": description,
    }


def _mask_value(value: str, secret: bool) -> str | None:
    if not value:
        return None

    if not secret:
        return value

    if len(value) <= 4:
        return "****"

    return f"{value[:2]}***{value[-2:]}"


def _checked_at() -> str:
    return datetime.now(timezone.utc).isoformat()
