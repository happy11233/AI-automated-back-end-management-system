from typing import Any

from app.erp.base import ERPProvider


class KingdeeProvider(ERPProvider):
    provider_id = "kingdee"
    provider_label = "金蝶"
    description = "金蝶云星空/OpenAPI 适配器预留"

    def __init__(
        self,
        base_url: str | None,
        account_id: str | None,
        app_id: str | None,
        app_secret: str | None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.account_id = account_id or ""
        self.app_id = app_id or ""
        self.app_secret = app_secret or ""

    def is_configured(self) -> bool:
        return bool(self.base_url and self.account_id and self.app_id and self.app_secret)

    def health_check(self) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "configured": False,
                "status": "not_configured",
                "message": "金蝶适配器已预留，请配置 ERP_KINGDEE_BASE_URL、ERP_KINGDEE_ACCOUNT_ID、ERP_KINGDEE_APP_ID、ERP_KINGDEE_APP_SECRET。",
            }

        return {
            "ok": False,
            "configured": True,
            "status": "not_implemented",
            "message": "金蝶连接参数已存在，真实登录和业务查询将在拿到接口规范后接入。",
        }

    def query_resource(
        self,
        resource: str,
        provider_resource: str,
        query: str | None,
        filters: dict[str, Any] | list[Any] | None,
        fields: list[str],
        limit: int,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "configured": self.is_configured(),
            "status": "not_implemented",
            "message": f"金蝶资源 {provider_resource} 的连接层已预留，等待接入真实接口规范。",
            "items": [],
        }

