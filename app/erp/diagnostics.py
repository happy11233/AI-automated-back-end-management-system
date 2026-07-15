from typing import Any

from app.config import settings
from app.erp.providers import PROVIDER_ORDER, get_active_provider, get_provider, list_providers
from app.erp.resources import ERP_RESOURCE_CATALOG, provider_fields_for, provider_resource_for
from app.permissions import POSITION_ERP_SCOPES, POSITION_LABELS


PROVIDER_CONFIG_FIELDS: dict[str, list[tuple[str, str, bool, str]]] = {
    "erpnext": [
        ("ERP_BASE_URL", "erp_base_url", False, "ERPNext/Frappe REST API 地址"),
        ("ERP_API_KEY", "erp_api_key", True, "ERPNext 用户 API Key"),
        ("ERP_API_SECRET", "erp_api_secret", True, "ERPNext 用户 API Secret"),
        ("ERP_TIMEOUT_SECONDS", "erp_timeout_seconds", False, "ERPNext 请求超时时间"),
    ],
    "kingdee": [
        ("ERP_KINGDEE_BASE_URL", "erp_kingdee_base_url", False, "金蝶 OpenAPI 地址"),
        ("ERP_KINGDEE_ACCOUNT_ID", "erp_kingdee_account_id", True, "金蝶账套或数据中心 ID"),
        ("ERP_KINGDEE_APP_ID", "erp_kingdee_app_id", True, "金蝶应用 ID"),
        ("ERP_KINGDEE_APP_SECRET", "erp_kingdee_app_secret", True, "金蝶应用密钥"),
    ],
    "yonyou": [
        ("ERP_YONYOU_BASE_URL", "erp_yonyou_base_url", False, "用友 OpenAPI 地址"),
        ("ERP_YONYOU_TENANT_ID", "erp_yonyou_tenant_id", True, "用友租户 ID"),
        ("ERP_YONYOU_APP_KEY", "erp_yonyou_app_key", True, "用友应用 Key"),
        ("ERP_YONYOU_APP_SECRET", "erp_yonyou_app_secret", True, "用友应用密钥"),
    ],
}


def build_erp_diagnostics() -> dict[str, Any]:
    active_provider = get_active_provider()
    active_health = active_provider.health_check()

    return {
        "active_provider": active_provider.provider_id,
        "active_provider_label": active_provider.provider_label,
        "active_configured": active_provider.is_configured(),
        "active_health": active_health,
        "providers": _build_provider_diagnostics(),
        "position_resource_mappings": _build_position_resource_mappings(
            active_provider.provider_id
        ),
        "local_development": _build_local_development_hints(active_provider.provider_id),
        "next_steps": _build_next_steps(active_provider.provider_id, active_health),
    }


def _build_provider_diagnostics() -> list[dict[str, Any]]:
    provider_items = {item["provider"]: item for item in list_providers()}
    diagnostics: list[dict[str, Any]] = []

    for provider_id in PROVIDER_ORDER:
        provider = get_provider(provider_id)
        item = provider_items.get(provider_id, {})
        diagnostics.append(
            {
                "provider": provider.provider_id,
                "label": provider.provider_label,
                "description": provider.description,
                "active": bool(item.get("active")),
                "configured": provider.is_configured(),
                "config_fields": _build_config_fields(provider.provider_id),
            }
        )

    return diagnostics


def _build_config_fields(provider_id: str) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []

    for env_name, attr_name, secret, description in PROVIDER_CONFIG_FIELDS.get(
        provider_id, []
    ):
        raw_value = getattr(settings, attr_name, None)
        value = "" if raw_value is None else str(raw_value)
        fields.append(
            {
                "name": env_name,
                "configured": bool(value),
                "secret": secret,
                "value_preview": _mask_value(value, secret),
                "description": description,
            }
        )

    return fields


def _build_position_resource_mappings(provider_id: str) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []

    for position, scopes in POSITION_ERP_SCOPES.items():
        resources = []
        for resource in scopes:
            definition = ERP_RESOURCE_CATALOG.get(resource)
            if definition is None:
                continue

            provider_resource = provider_resource_for(resource, provider_id)
            resources.append(
                {
                    "resource": resource,
                    "label": definition["label"],
                    "provider_resource": provider_resource,
                    "supported": bool(provider_resource),
                    "fields": provider_fields_for(resource, provider_id),
                }
            )

        mappings.append(
            {
                "position": position,
                "position_label": POSITION_LABELS.get(position, position),
                "resources": resources,
            }
        )

    return mappings


def _build_local_development_hints(provider_id: str) -> dict[str, Any]:
    if provider_id != "erpnext":
        return {
            "message": "当前激活的不是 ERPNext；请按对应 ERP 厂商的 OpenAPI 网关地址配置。",
        }

    return {
        "host_browser_url": "http://127.0.0.1:8080",
        "docker_api_url": "http://host.docker.internal:8080",
        "message": "如果 API 运行在 Docker 容器中，ERP_BASE_URL 应使用 http://host.docker.internal:8080；如果直接在宿主机运行后端，可使用 http://127.0.0.1:8080。",
    }


def _build_next_steps(provider_id: str, health: dict[str, Any]) -> list[str]:
    status = str(health.get("status") or "")

    if provider_id == "erpnext" and status == "not_configured":
        return [
            "在 ERPNext 用户里生成 API Key 和 API Secret。",
            "API 运行在 Docker 时，把 .env 里的 ERP_BASE_URL 设置为 http://host.docker.internal:8080。",
            "填写 ERP_API_KEY、ERP_API_SECRET 后重启 company-rag-api 容器。",
            "重新调用 /erp/diagnostics 和 /erp/status 验证连接。",
        ]

    if status == "ok":
        return [
            "连接已经可用，下一步可以用不同岗位账号测试 /erp/query 和 AI 对话里的 ERP 查询。",
            "补充真实业务字段映射，例如 Amazon 订单号、SKU、店铺、币种、物流单号。",
        ]

    return [
        "根据 active_health.message 修正 ERP 地址、网络、凭据或 API 权限。",
        "确认当前岗位资源映射里的 provider_resource 是否存在于目标 ERP。",
    ]


def _mask_value(value: str, secret: bool) -> str | None:
    if not value:
        return None

    if not secret:
        return value

    if len(value) <= 4:
        return "****"

    return f"{value[:2]}***{value[-2:]}"
