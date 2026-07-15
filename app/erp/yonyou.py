from typing import Any

from app.erp.base import ERPProvider


class YonyouProvider(ERPProvider):
    provider_id = "yonyou"
    provider_label = "用友"
    description = "用友 YonBIP/U8C OpenAPI 适配器预留"

    def __init__(
        self,
        base_url: str | None,
        tenant_id: str | None,
        app_key: str | None,
        app_secret: str | None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.tenant_id = tenant_id or ""
        self.app_key = app_key or ""
        self.app_secret = app_secret or ""

    def is_configured(self) -> bool:
        return bool(self.base_url and self.tenant_id and self.app_key and self.app_secret)

    def health_check(self) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "configured": False,
                "status": "not_configured",
                "message": "用友适配器已预留，请配置 ERP_YONYOU_BASE_URL、ERP_YONYOU_TENANT_ID、ERP_YONYOU_APP_KEY、ERP_YONYOU_APP_SECRET。",
            }

        return {
            "ok": False,
            "configured": True,
            "status": "not_implemented",
            "message": "用友连接参数已存在，真实鉴权和业务查询将在拿到接口规范后接入。",
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
            "message": f"用友资源 {provider_resource} 的连接层已预留，等待接入真实接口规范。",
            "items": [],
        }

