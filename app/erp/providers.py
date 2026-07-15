from app.config import settings
from app.erp.base import ERPProvider
from app.erp.erpnext import ERPNextProvider
from app.erp.kingdee import KingdeeProvider
from app.erp.yonyou import YonyouProvider


PROVIDER_ORDER = ["erpnext", "kingdee", "yonyou"]


def get_active_provider() -> ERPProvider:
    return get_provider(settings.erp_provider)


def get_provider(provider_id: str | None) -> ERPProvider:
    normalized = (provider_id or "erpnext").strip().lower()

    if normalized == "kingdee":
        return KingdeeProvider(
            base_url=settings.erp_kingdee_base_url,
            account_id=settings.erp_kingdee_account_id,
            app_id=settings.erp_kingdee_app_id,
            app_secret=settings.erp_kingdee_app_secret,
        )

    if normalized == "yonyou":
        return YonyouProvider(
            base_url=settings.erp_yonyou_base_url,
            tenant_id=settings.erp_yonyou_tenant_id,
            app_key=settings.erp_yonyou_app_key,
            app_secret=settings.erp_yonyou_app_secret,
        )

    return ERPNextProvider(
        base_url=settings.erp_base_url,
        api_key=settings.erp_api_key,
        api_secret=settings.erp_api_secret,
        timeout_seconds=settings.erp_timeout_seconds,
    )


def list_providers() -> list[dict]:
    active_provider = (settings.erp_provider or "erpnext").strip().lower()
    providers = [get_provider(provider_id) for provider_id in PROVIDER_ORDER]

    return [
        {
            "provider": provider.provider_id,
            "label": provider.provider_label,
            "description": provider.description,
            "active": provider.provider_id == active_provider,
            "configured": provider.is_configured(),
        }
        for provider in providers
    ]

