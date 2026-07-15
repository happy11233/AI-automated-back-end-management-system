from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.security import get_current_user, require_admin
from app.erp.base import ERPProviderError
from app.erp.diagnostics import build_erp_diagnostics
from app.erp.providers import get_active_provider, list_providers
from app.erp.resources import (
    ERP_RESOURCE_CATALOG,
    list_resource_definitions,
    provider_fields_for,
    provider_resource_for,
    resolve_resource_name,
)
from app.permissions import (
    POSITION_LABELS,
    all_erp_scopes,
    ensure_erp_resource_allowed,
    erp_scopes_for_position,
    is_valid_position,
)
from app.services.logging_service import write_audit_log


router = APIRouter(
    prefix="/erp",
    tags=["erp"],
)


class ERPProviderItem(BaseModel):
    provider: str
    label: str
    description: str
    active: bool
    configured: bool


class ERPProvidersResponse(BaseModel):
    active_provider: str
    items: list[ERPProviderItem]


class ERPResourceItem(BaseModel):
    resource: str
    label: str
    description: str
    provider_refs: dict[str, str]


class ERPScopesResponse(BaseModel):
    provider: str
    provider_label: str
    position: str | None
    position_label: str
    resources: list[ERPResourceItem]


class ERPStatusResponse(BaseModel):
    provider: str
    provider_label: str
    ok: bool
    configured: bool
    status: str
    message: str
    detail: Any = None


class ERPQueryRequest(BaseModel):
    resource: str = Field(min_length=1, max_length=80)
    query: str | None = Field(default=None, max_length=200)
    filters: dict[str, Any] | list[Any] | None = None
    limit: int = Field(default=10, ge=1, le=100)


class ERPQueryResponse(BaseModel):
    ok: bool
    configured: bool
    status: str
    provider: str
    provider_label: str
    resource: str
    resource_label: str
    provider_resource: str
    message: str
    items: list[dict[str, Any]]
    raw: dict[str, Any] | None = None


class ERPDashboardMetric(BaseModel):
    title: str
    value: str | int | float
    suffix: str = ""
    description: str = ""
    status: str = "default"


class ERPDashboardSection(BaseModel):
    resource: str
    resource_label: str
    title: str
    ok: bool
    status: str
    message: str
    total_count: int
    amount_total: float | None = None
    amount_label: str | None = None
    items: list[dict[str, Any]]


class ERPDashboardOverviewResponse(BaseModel):
    provider: str
    provider_label: str
    role: str
    position: str | None
    position_label: str
    market: str
    market_label: str
    store: str
    store_label: str
    date_range: str
    date_range_label: str
    title: str
    message: str
    metrics: list[ERPDashboardMetric]
    sections: list[ERPDashboardSection]


class ERPRecordDetailResponse(BaseModel):
    ok: bool
    provider: str
    provider_label: str
    resource: str
    resource_label: str
    provider_resource: str
    record_id: str
    message: str
    item: dict[str, Any] | None = None


DASHBOARD_OVERVIEW_RESOURCES: dict[str, list[str]] = {
    "operations": ["Sales Order", "Item", "Item Price"],
    "customer_service": ["Delivery Note", "Issue", "Customer"],
    "finance": ["Sales Invoice", "Payment Entry", "GL Entry"],
}

DASHBOARD_MARKETS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "全部站点",
        "markers": [],
    },
    "us": {
        "label": "美国站",
        "markers": ["AMZ-US", "US Store", "Amazon US", "1ZAMZUS"],
    },
    "de": {
        "label": "德国站",
        "markers": ["AMZ-DE", "DE Store", "Amazon DE", "DHL-DE"],
    },
    "jp": {
        "label": "日本站",
        "markers": ["AMZ-JP", "JP Store", "Amazon JP", "YAMATO-JP"],
    },
}

DASHBOARD_STORES: dict[str, dict[str, Any]] = {
    "all": {
        "label": "全部店铺",
        "markers": [],
    },
    "us_store": {
        "label": "US Store",
        "markers": ["US Store", "Amazon US", "AMZ-US", "1ZAMZUS"],
    },
    "de_store": {
        "label": "DE Store",
        "markers": ["DE Store", "Amazon DE", "AMZ-DE", "DHL-DE"],
    },
    "jp_store": {
        "label": "JP Store",
        "markers": ["JP Store", "Amazon JP", "AMZ-JP", "YAMATO-JP"],
    },
}

GLOBAL_DASHBOARD_RESOURCES = {"Item", "Item Price", "GL Entry", "Payment Entry"}

DASHBOARD_AMOUNT_FIELDS: dict[str, tuple[str, ...]] = {
    "Sales Order": ("grand_total",),
    "Sales Invoice": ("grand_total",),
    "Sales Invoice summary": ("grand_total",),
    "Delivery Note": ("grand_total",),
    "Payment Entry": ("paid_amount", "received_amount", "paid_amount_after_tax"),
    "Purchase Invoice": ("grand_total", "outstanding_amount"),
    "Item Price": ("price_list_rate",),
    "GL Entry": ("debit", "credit"),
}

DASHBOARD_DATE_RANGES: dict[str, dict[str, Any]] = {
    "all": {
        "label": "全部时间",
        "days": None,
    },
    "today": {
        "label": "今天",
        "days": 1,
    },
    "7d": {
        "label": "近 7 天",
        "days": 7,
    },
    "30d": {
        "label": "近 30 天",
        "days": 30,
    },
}


@router.get("/providers", response_model=ERPProvidersResponse)
def get_erp_providers(current_user: dict = Depends(get_current_user)):
    provider = get_active_provider()
    return {
        "active_provider": provider.provider_id,
        "items": list_providers(),
    }


@router.get("/status", response_model=ERPStatusResponse)
def get_erp_status(current_user: dict = Depends(get_current_user)):
    provider = get_active_provider()
    result = provider.health_check()

    return {
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "ok": bool(result.get("ok")),
        "configured": bool(result.get("configured")),
        "status": str(result.get("status") or "unknown"),
        "message": str(result.get("message") or ""),
        "detail": result.get("detail"),
    }


@router.get("/diagnostics")
def get_erp_diagnostics(current_user: dict = Depends(require_admin)):
    return build_erp_diagnostics()


@router.get("/dashboard-overview", response_model=ERPDashboardOverviewResponse)
def get_erp_dashboard_overview(
    market: str = Query(default="all", pattern="^(all|us|de|jp)$"),
    store: str = Query(default="all", pattern="^(all|us_store|de_store|jp_store)$"),
    date_range: str = Query(default="all", pattern="^(all|today|7d|30d)$"),
    current_user: dict = Depends(get_current_user),
):
    provider = get_active_provider()
    role = str(current_user.get("role") or "employee")
    position = current_user.get("position")
    market_config = DASHBOARD_MARKETS.get(market, DASHBOARD_MARKETS["all"])
    market_label = str(market_config["label"])
    store_config = DASHBOARD_STORES.get(store, DASHBOARD_STORES["all"])
    store_label = str(store_config["label"])
    date_range_config = DASHBOARD_DATE_RANGES.get(date_range, DASHBOARD_DATE_RANGES["all"])
    date_range_label = str(date_range_config["label"])

    if role == "admin":
        health = provider.health_check()
        ok = bool(health.get("ok"))
        metrics = [
            {
                "title": "ERP 连接",
                "value": str(health.get("status") or "unknown"),
                "description": str(health.get("message") or ""),
                "status": "success" if ok else "warning",
            },
            {
                "title": "可用 Provider",
                "value": len(list_providers()),
                "suffix": "个",
                "description": "ERPNext、金蝶、用友适配层",
                "status": "processing",
            },
            {
                "title": "岗位 ERP 资源",
                "value": len(all_erp_scopes()),
                "suffix": "类",
                "description": "平台已纳入权限控制的资源",
                "status": "processing",
            },
        ]
        response = {
            "provider": provider.provider_id,
            "provider_label": provider.provider_label,
            "role": role,
            "position": position,
            "position_label": "管理员",
            "market": market,
            "market_label": market_label,
            "store": store,
            "store_label": store_label,
            "date_range": date_range,
            "date_range_label": date_range_label,
            "title": "平台运行概览",
            "message": "管理员首页展示平台连接状态，不直接展开岗位业务数据。",
            "metrics": metrics,
            "sections": [],
        }
        _write_dashboard_overview_audit(current_user, response)
        return response

    if not is_valid_position(position):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前账号未绑定岗位，无法查看 ERP 工作台概览。",
        )

    resources = DASHBOARD_OVERVIEW_RESOURCES.get(str(position), [])
    sections = []
    for resource in resources:
        ensure_erp_resource_allowed(current_user, resource)
        sections.append(
            _query_dashboard_section(
                provider=provider,
                resource=resource,
                market=market,
                market_config=market_config,
                store=store,
                store_config=store_config,
                date_range=date_range,
                date_range_config=date_range_config,
            )
        )

    metrics = [
        {
            "title": section["resource_label"],
            "value": section["total_count"],
            "suffix": "条",
            "description": section["message"],
            "status": "success" if section["ok"] else "warning",
        }
        for section in sections
    ]
    for section in sections:
        if section.get("amount_total") is None:
            continue
        metrics.append(
            {
                "title": section.get("amount_label") or f"{section['resource_label']}金额",
                "value": section["amount_total"],
                "suffix": "元",
                "description": f"{section['resource_label']}当前筛选范围金额合计",
                "status": "processing",
            }
        )
    position_label = POSITION_LABELS.get(str(position), "未绑定岗位")
    response = {
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "role": role,
        "position": position,
        "position_label": position_label,
        "market": market,
        "market_label": market_label,
        "store": store,
        "store_label": store_label,
        "date_range": date_range,
        "date_range_label": date_range_label,
        "title": f"{position_label}数据概览",
        "message": f"已按{position_label}岗位权限加载 {market_label} / {store_label} / {date_range_label} ERP 工作台概览。",
        "metrics": metrics,
        "sections": sections,
    }
    _write_dashboard_overview_audit(current_user, response)
    return response


@router.get("/scopes", response_model=ERPScopesResponse)
def get_my_erp_scopes(current_user: dict = Depends(get_current_user)):
    provider = get_active_provider()
    role = current_user.get("role")
    position = current_user.get("position")

    if role == "admin":
        scopes = all_erp_scopes()
        position_label = "管理员"
    else:
        scopes = erp_scopes_for_position(position)
        position_label = POSITION_LABELS.get(position, "未绑定岗位")

    return {
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "position": position,
        "position_label": position_label,
        "resources": list_resource_definitions(scopes),
    }


@router.post("/query", response_model=ERPQueryResponse)
def query_erp(
    request: ERPQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    resource = resolve_resource_name(request.resource)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未知 ERP 资源，请从当前岗位允许的资源中选择。",
        )

    ensure_erp_resource_allowed(current_user, resource)

    provider = get_active_provider()
    provider_resource = provider_resource_for(resource, provider.provider_id)
    definition = ERP_RESOURCE_CATALOG[resource]

    if provider_resource is None:
        return _build_response(
            provider=provider,
            resource=resource,
            provider_resource="",
            status="unsupported_resource",
            ok=False,
            configured=provider.is_configured(),
            message=f"{provider.provider_label} 暂未映射资源 {resource}",
            items=[],
        )

    try:
        result = provider.query_resource(
            resource=resource,
            provider_resource=provider_resource,
            query=(request.query or "").strip() or None,
            filters=request.filters,
            fields=provider_fields_for(resource, provider.provider_id),
            limit=request.limit,
        )
    except ERPProviderError as error:
        result = {
            "ok": False,
            "configured": provider.is_configured(),
            "status": error.status,
            "message": error.message,
            "items": [],
        }

    response = _build_response(
        provider=provider,
        resource=resource,
        provider_resource=provider_resource,
        status=str(result.get("status") or "unknown"),
        ok=bool(result.get("ok")),
        configured=bool(result.get("configured")),
        message=str(result.get("message") or ""),
        items=result.get("items") if isinstance(result.get("items"), list) else [],
        raw=result.get("raw") if isinstance(result.get("raw"), dict) else None,
    )

    write_audit_log(
        user_id=current_user["id"],
        action="erp.query",
        resource_type="erp",
        resource_id=resource,
        metadata={
            "username": current_user["username"],
            "role": current_user["role"],
            "position": current_user.get("position"),
            "provider": provider.provider_id,
            "provider_resource": provider_resource,
            "query_preview": (request.query or "")[:200],
            "filters_preview": str(request.filters)[:500],
            "limit": request.limit,
            "status": response["status"],
            "ok": response["ok"],
            "result_count": len(response["items"]),
        },
    )

    return response


@router.get("/records/{resource}/{record_id}", response_model=ERPRecordDetailResponse)
def get_erp_record_detail(
    resource: str,
    record_id: str,
    current_user: dict = Depends(get_current_user),
):
    resolved_resource = resolve_resource_name(resource)
    if resolved_resource is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未知 ERP 资源，请从当前岗位允许的资源中选择。",
        )

    ensure_erp_resource_allowed(current_user, resolved_resource)

    provider = get_active_provider()
    provider_resource = provider_resource_for(resolved_resource, provider.provider_id)
    definition = ERP_RESOURCE_CATALOG[resolved_resource]

    if provider_resource is None:
        return {
            "ok": False,
            "provider": provider.provider_id,
            "provider_label": provider.provider_label,
            "resource": resolved_resource,
            "resource_label": str(definition["label"]),
            "provider_resource": "",
            "record_id": record_id,
            "message": f"{provider.provider_label} 暂未映射资源 {resolved_resource}",
            "item": None,
        }

    lookup = record_id.strip()
    if not lookup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="记录 ID 不能为空。",
        )

    try:
        result = provider.query_resource(
            resource=resolved_resource,
            provider_resource=provider_resource,
            query=lookup,
            filters=None,
            fields=provider_fields_for(resolved_resource, provider.provider_id),
            limit=10,
        )
    except ERPProviderError as error:
        result = {
            "ok": False,
            "status": error.status,
            "message": error.message,
            "items": [],
        }

    items = result.get("items") if isinstance(result.get("items"), list) else []
    normalized_items = [item for item in items if isinstance(item, dict)]
    exact_item = _find_dashboard_record(normalized_items, lookup)
    item = exact_item or (normalized_items[0] if normalized_items else None)

    response = {
        "ok": bool(result.get("ok")) and item is not None,
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "resource": resolved_resource,
        "resource_label": str(definition["label"]),
        "provider_resource": provider_resource,
        "record_id": lookup,
        "message": "已加载 ERP 记录详情。" if item else str(result.get("message") or "未找到 ERP 记录。"),
        "item": item,
    }

    write_audit_log(
        user_id=current_user.get("id"),
        action="erp.record_detail",
        resource_type="erp",
        resource_id=resolved_resource,
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "provider": provider.provider_id,
            "provider_resource": provider_resource,
            "record_id": lookup,
            "ok": response["ok"],
        },
    )

    return response


def _query_dashboard_section(
    provider,
    resource: str,
    market: str,
    market_config: dict[str, Any],
    store: str,
    store_config: dict[str, Any],
    date_range: str,
    date_range_config: dict[str, Any],
) -> dict[str, Any]:
    provider_resource = provider_resource_for(resource, provider.provider_id)
    definition = ERP_RESOURCE_CATALOG[resource]
    resource_label = str(definition["label"])

    if provider_resource is None:
        return {
            "resource": resource,
            "resource_label": resource_label,
            "title": resource_label,
            "ok": False,
            "status": "unsupported_resource",
            "message": f"{provider.provider_label} 暂未映射资源 {resource}",
            "total_count": 0,
            "amount_total": None,
            "amount_label": None,
            "items": [],
        }

    try:
        result = provider.query_resource(
            resource=resource,
            provider_resource=provider_resource,
            query=_dashboard_market_query(resource, market),
            filters=None,
            fields=provider_fields_for(resource, provider.provider_id),
            limit=30,
        )
    except ERPProviderError as error:
        result = {
            "ok": False,
            "status": error.status,
            "message": error.message,
            "items": [],
        }

    items = result.get("items") if isinstance(result.get("items"), list) else []
    normalized_items = [item for item in items if isinstance(item, dict)]
    filtered_items = _filter_dashboard_items_by_market(
        resource=resource,
        items=normalized_items,
        market=market,
        market_config=market_config,
    )
    filtered_items = _filter_dashboard_items_by_store(
        resource=resource,
        items=filtered_items,
        store=store,
        store_config=store_config,
    )
    filtered_items = _filter_dashboard_items_by_date_range(
        items=filtered_items,
        date_range=date_range,
        date_range_config=date_range_config,
    )
    total_count = len(filtered_items)
    amount_total = _dashboard_amount_total(resource, filtered_items)
    amount_label = _dashboard_amount_label(resource)

    return {
        "resource": resource,
        "resource_label": resource_label,
        "title": resource_label,
        "ok": bool(result.get("ok")),
        "status": str(result.get("status") or "unknown"),
        "message": _dashboard_section_message(
            provider_message=str(result.get("message") or ""),
            market_label=str(market_config["label"]),
            store_label=str(store_config["label"]),
            date_range_label=str(date_range_config["label"]),
            total_count=total_count,
            global_resource=resource in GLOBAL_DASHBOARD_RESOURCES,
        ),
        "total_count": total_count,
        "amount_total": amount_total,
        "amount_label": amount_label,
        "items": filtered_items[:5],
    }


def _dashboard_market_query(resource: str, market: str) -> str | None:
    if market == "all" or resource in GLOBAL_DASHBOARD_RESOURCES:
        return None

    return f"AMZ-{market.upper()}"


def _filter_dashboard_items_by_market(
    resource: str,
    items: list[dict[str, Any]],
    market: str,
    market_config: dict[str, Any],
) -> list[dict[str, Any]]:
    if market == "all" or resource in GLOBAL_DASHBOARD_RESOURCES:
        return items

    markers = [str(item).lower() for item in market_config.get("markers", [])]
    if not markers:
        return items

    filtered = [
        item
        for item in items
        if any(marker in _dashboard_item_text(item) for marker in markers)
    ]
    return filtered


def _filter_dashboard_items_by_store(
    resource: str,
    items: list[dict[str, Any]],
    store: str,
    store_config: dict[str, Any],
) -> list[dict[str, Any]]:
    if store == "all" or resource in GLOBAL_DASHBOARD_RESOURCES:
        return items

    markers = [str(item).lower() for item in store_config.get("markers", [])]
    if not markers:
        return items

    filtered = [
        item
        for item in items
        if any(marker in _dashboard_item_text(item) for marker in markers)
    ]
    return filtered


def _dashboard_item_text(item: dict[str, Any]) -> str:
    return " ".join(str(value) for value in item.values() if value is not None).lower()


def _filter_dashboard_items_by_date_range(
    items: list[dict[str, Any]],
    date_range: str,
    date_range_config: dict[str, Any],
) -> list[dict[str, Any]]:
    if date_range == "all":
        return items

    days = date_range_config.get("days")
    if not isinstance(days, int) or days <= 0:
        return items

    today = date.today()
    start_date = today - timedelta(days=days - 1)
    filtered = []
    for item in items:
        item_date = _dashboard_item_date(item)
        if item_date is None:
            continue
        if start_date <= item_date <= today:
            filtered.append(item)

    return filtered


def _dashboard_item_date(item: dict[str, Any]) -> date | None:
    for key in [
        "posting_date",
        "transaction_date",
        "modified",
        "creation",
        "due_date",
        "start_date",
        "end_date",
    ]:
        parsed = _parse_dashboard_date(item.get(key))
        if parsed is not None:
            return parsed

    return None


def _parse_dashboard_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _dashboard_amount_total(resource: str, items: list[dict[str, Any]]) -> float | None:
    fields = DASHBOARD_AMOUNT_FIELDS.get(resource)
    if not fields:
        return None

    total = 0.0
    matched = False
    for item in items:
        item_total = 0.0
        item_matched = False
        for field in fields:
            value = _parse_dashboard_amount(item.get(field))
            if value is None:
                continue
            item_total += value
            item_matched = True

        if item_matched:
            total += item_total
            matched = True

    if not matched:
        return None

    return round(total, 2)


def _dashboard_amount_label(resource: str) -> str | None:
    labels = {
        "Sales Order": "订单金额",
        "Sales Invoice": "发票金额",
        "Sales Invoice summary": "发票摘要金额",
        "Delivery Note": "出库金额",
        "Payment Entry": "收付款金额",
        "Purchase Invoice": "采购金额",
        "Item Price": "价格合计",
        "GL Entry": "借贷发生额",
    }
    return labels.get(resource)


def _parse_dashboard_amount(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "")
    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def _find_dashboard_record(items: list[dict[str, Any]], record_id: str) -> dict[str, Any] | None:
    lookup = record_id.strip().lower()
    if not lookup:
        return None

    for item in items:
        for key in ["name", "po_no", "lr_no", "subject", "item_code"]:
            value = item.get(key)
            if value is not None and str(value).strip().lower() == lookup:
                return item

    return None


def _dashboard_section_message(
    provider_message: str,
    market_label: str,
    store_label: str,
    date_range_label: str,
    total_count: int,
    global_resource: bool,
) -> str:
    scope = "全部站点 / 全部店铺" if global_resource else f"{market_label} / {store_label}"
    return f"{provider_message}；{scope} / {date_range_label}匹配 {total_count} 条。"


def _write_dashboard_overview_audit(
    current_user: dict,
    response: dict[str, Any],
) -> None:
    write_audit_log(
        user_id=current_user.get("id"),
        action="erp.dashboard_overview",
        resource_type="erp",
        resource_id=str(current_user.get("position") or current_user.get("role")),
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "provider": response.get("provider"),
            "market": response.get("market"),
            "store": response.get("store"),
            "date_range": response.get("date_range"),
            "section_resources": [
                section.get("resource")
                for section in response.get("sections", [])
                if isinstance(section, dict)
            ],
            "metric_count": len(response.get("metrics") or []),
        },
    )


def _build_response(
    provider,
    resource: str,
    provider_resource: str,
    status: str,
    ok: bool,
    configured: bool,
    message: str,
    items: list[Any],
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    definition = ERP_RESOURCE_CATALOG[resource]
    normalized_items = [item for item in items if isinstance(item, dict)]

    return {
        "ok": ok,
        "configured": configured,
        "status": status,
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "resource": resource,
        "resource_label": str(definition["label"]),
        "provider_resource": provider_resource,
        "message": message,
        "items": normalized_items,
        "raw": raw,
    }
