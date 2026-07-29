import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.erp.base import ERPProvider, ERPProviderError


class ERPNextProvider(ERPProvider):
    provider_id = "erpnext"
    provider_label = "ERPNext"
    description = "ERPNext/Frappe REST API 适配器"

    def __init__(
        self,
        base_url: str | None,
        api_key: str | None,
        api_secret: str | None,
        timeout_seconds: int = 8,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.api_secret)

    def health_check(self) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "ok": False,
                "configured": False,
                "status": "not_configured",
                "message": "ERPNext 未配置，请设置 ERP_BASE_URL、ERP_API_KEY、ERP_API_SECRET。",
            }

        try:
            result = self._get_json("/api/method/frappe.auth.get_logged_user", {})
        except ERPProviderError as error:
            return {
                "ok": False,
                "configured": True,
                "status": error.status,
                "message": error.message,
            }

        return {
            "ok": True,
            "configured": True,
            "status": "ok",
            "message": "ERPNext 连接正常",
            "detail": result.get("message"),
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
        if not self.is_configured():
            return {
                "ok": False,
                "configured": False,
                "status": "not_configured",
                "message": "ERPNext 未配置，已完成岗位权限校验，但没有发起外部 ERP 请求。",
                "items": [],
            }

        doctype = provider_resource
        params: dict[str, Any] = {
            "limit_page_length": limit,
            "fields": json.dumps(fields, ensure_ascii=False),
        }
        normalized_filters = self._build_filters(doctype, filters, query)
        if normalized_filters:
            params["filters"] = json.dumps(normalized_filters, ensure_ascii=False)
        normalized_or_filters = self._build_or_filters(doctype, filters, query)
        if normalized_or_filters:
            params["or_filters"] = json.dumps(normalized_or_filters, ensure_ascii=False)

        path = f"/api/resource/{quote(doctype, safe='')}"
        result = self._get_json(path, params)
        items = result.get("data", [])

        if not isinstance(items, list):
            items = []

        return {
            "ok": True,
            "configured": True,
            "status": "ok",
            "message": f"已查询 ERPNext {doctype}",
            "items": items,
            "raw": result,
        }

    def _build_filters(
        self,
        doctype: str,
        filters: dict[str, Any] | list[Any] | None,
        query: str | None,
    ) -> list[Any] | dict[str, Any] | None:
        if isinstance(filters, dict) and filters:
            return [[key, "=", value] for key, value in filters.items()]

        if isinstance(filters, list) and filters:
            return filters

        return None

    def _build_or_filters(
        self,
        doctype: str,
        filters: dict[str, Any] | list[Any] | None,
        query: str | None,
    ) -> list[list[str]] | None:
        if filters or not query:
            return None

        searchable_fields = {
            "Item": ["name", "item_name", "item_code"],
            "Item Price": ["name", "item_code", "price_list"],
            "Bin": ["name", "item_code", "warehouse"],
            "Customer": ["name", "customer_name"],
            "Sales Order": ["name", "customer", "customer_name", "po_no"],
            "Sales Invoice": ["name", "customer", "customer_name", "po_no"],
            "Delivery Note": ["name", "customer", "customer_name", "lr_no", "title"],
            "Issue": ["name", "subject", "customer", "description"],
            "GL Entry": ["name", "account", "voucher_no"],
            "Payment Entry": ["name", "party", "reference_no", "remarks"],
            "Salary Slip": ["name", "employee", "employee_name"],
            "Purchase Invoice": ["name", "supplier", "bill_no"],
        }.get(doctype, ["name"])

        return [[field, "like", f"%{query}%"] for field in searchable_fields]

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"token {self.api_key}:{self.api_secret}",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise ERPProviderError(
                f"ERPNext 返回 HTTP {error.code}: {body[:500]}",
                status="http_error",
            ) from error
        except URLError as error:
            raise ERPProviderError(
                f"ERPNext 连接失败: {error.reason}",
                status="connection_error",
            ) from error
        except TimeoutError as error:
            raise ERPProviderError("ERPNext 请求超时", status="timeout") from error

        if not body:
            return {}

        try:
            return json.loads(body)
        except json.JSONDecodeError as error:
            raise ERPProviderError("ERPNext 返回了非 JSON 响应", status="invalid_json") from error
