from __future__ import annotations

import re
from typing import Any

from app.erp.base import ERPProviderError
from app.erp.providers import get_active_provider
from app.erp.resources import (
    ERP_RESOURCE_CATALOG,
    match_resource_by_keywords,
    provider_fields_for,
    provider_resource_for,
)
from app.permissions import all_erp_scopes, erp_scopes_for_position, is_valid_position
from app.services.logging_service import write_audit_log


def build_erp_candidates(user_input: str, current_user: dict) -> list[str]:
    if current_user.get("role") == "admin":
        scopes = all_erp_scopes()
    else:
        position = current_user.get("position")
        if not is_valid_position(position):
            return []
        scopes = erp_scopes_for_position(position)

    matched_resource = match_resource_by_keywords(user_input, scopes)
    if matched_resource:
        return [matched_resource]

    return []


def summarize_erp_items(resource: str, items: list[dict[str, Any]]) -> str:
    definition = ERP_RESOURCE_CATALOG.get(resource, {})
    label = str(definition.get("label", resource))

    if not items:
        return f"未查到与“{label}”相关的数据。"

    lines = [f"已查到 {len(items)} 条{label}记录："]
    references = build_erp_references(resource, items)
    reference_map = {
        reference["record_id"]: index
        for index, reference in enumerate(references, start=1)
    }

    for index, item in enumerate(items[:5], start=1):
        parts = []
        for key in [
            "name",
            "customer",
            "customer_name",
            "item_name",
            "item_code",
            "po_no",
            "lr_no",
            "subject",
            "status",
            "priority",
            "grand_total",
            "outstanding_amount",
            "amount",
            "posting_date",
            "due_date",
            "description",
            "modified",
        ]:
            value = item.get(key)
            if value not in (None, "", []):
                parts.append(f"{key}={str(value)[:120]}")

        if not parts:
            parts.append(str(item)[:180])

        reference_no = reference_map.get(str(item.get("name") or item.get("po_no") or item.get("lr_no") or ""))
        prefix = f"[ERP-{reference_no}] " if reference_no else ""
        lines.append(f"{index}. {prefix}" + "；".join(parts))

    if references:
        lines.append("引用 ERP 记录：")
        for index, reference in enumerate(references, start=1):
            lines.append(
                f"[ERP-{index}] {reference['resource_label']} / {reference['record_id']}"
            )

    return "\n".join(lines)


def build_erp_references(resource: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    definition = ERP_RESOURCE_CATALOG.get(resource, {})
    resource_label = str(definition.get("label", resource))
    references: list[dict[str, Any]] = []

    for item in items[:5]:
        record_id = _erp_reference_record_id(item)
        if not record_id:
            continue

        references.append(
            {
                "resource": resource,
                "resource_label": resource_label,
                "record_id": record_id,
                "title": _erp_reference_title(item, record_id),
                "provider": None,
                "provider_resource": None,
            }
        )

    return references


def _erp_reference_record_id(item: dict[str, Any]) -> str:
    for key in ["name", "po_no", "lr_no", "subject", "item_code"]:
        value = item.get(key)
        if value not in (None, "", []):
            return str(value)[:160]

    return ""


def _erp_reference_title(item: dict[str, Any], record_id: str) -> str:
    for key in ["customer", "customer_name", "item_name", "subject", "account", "party"]:
        value = item.get(key)
        if value not in (None, "", []):
            return f"{record_id} - {str(value)[:80]}"

    return record_id


def extract_erp_lookup_query(resource: str, text: str) -> str:
    amazon_order = re.search(r"\bAMZ-[A-Z]{2}-\d{3}-\d{7}-\d{7}\b", text, re.I)
    if amazon_order:
        return amazon_order.group(0).upper()

    tracking_no = re.search(
        r"\b(?:1Z[A-Z0-9]{10,}|DHL-[A-Z]{2}-AMZ-\d{10,}|YAMATO-[A-Z]{2}-\d{10,})\b",
        text,
        re.I,
    )
    if tracking_no:
        return tracking_no.group(0).upper()

    sku = re.search(r"\bAMZ-[A-Z0-9]+(?:-[A-Z0-9]+)+\b", text, re.I)
    if sku:
        return sku.group(0).upper()

    return text


def query_erp_for_current_user(
    user_input: str,
    current_user: dict,
    query: str | None = None,
    filters: dict[str, Any] | list[Any] | None = None,
    limit: int = 5,
    source: str = "chat",
    thread_id: str | None = None,
) -> dict[str, Any]:
    candidates = build_erp_candidates(user_input, current_user)
    if not candidates:
        result = {
            "ok": False,
            "status": "no_scope",
            "message": "我可以查询你岗位权限内的 ERP 数据，但这次没有识别出具体资源名称。你可以直接说明要查客户、订单、物流、工单、工资、发票里的哪一类。",
            "resource": None,
            "items": [],
        }
        _write_erp_audit(
            current_user=current_user,
            resource=None,
            query=query or user_input,
            result=result,
            source=source,
            thread_id=thread_id,
        )
        return result

    resource = candidates[0]
    provider = get_active_provider()
    provider_resource = provider_resource_for(resource, provider.provider_id)

    if provider_resource is None:
        result = {
            "ok": False,
            "status": "unsupported_resource",
            "message": f"{provider.provider_label} 暂未映射资源 {resource}",
            "resource": resource,
            "items": [],
        }
        _write_erp_audit(
            current_user=current_user,
            resource=resource,
            query=query or user_input,
            result=result,
            source=source,
            thread_id=thread_id,
        )
        return result

    lookup_query = extract_erp_lookup_query(resource, query or user_input)

    try:
        result = provider.query_resource(
            resource=resource,
            provider_resource=provider_resource,
            query=lookup_query,
            filters=filters,
            fields=provider_fields_for(resource, provider.provider_id),
            limit=limit,
        )
    except ERPProviderError as error:
        result = {
            "ok": False,
            "status": error.status,
            "message": error.message,
            "resource": resource,
            "provider": provider.provider_id,
            "provider_resource": provider_resource,
            "items": [],
        }
        _write_erp_audit(
            current_user=current_user,
            resource=resource,
            query=query or user_input,
            result=result,
            source=source,
            thread_id=thread_id,
        )
        return result

    result = {
        "ok": bool(result.get("ok")),
        "status": str(result.get("status") or "unknown"),
        "message": str(result.get("message") or ""),
        "resource": resource,
        "provider": provider.provider_id,
        "provider_resource": provider_resource,
        "items": result.get("items") if isinstance(result.get("items"), list) else [],
        "lookup_query": lookup_query,
        "raw": result.get("raw") if isinstance(result.get("raw"), dict) else None,
    }
    result["references"] = build_erp_references(resource, result["items"])
    for reference in result["references"]:
        reference["provider"] = provider.provider_id
        reference["provider_resource"] = provider_resource

    _write_erp_audit(
        current_user=current_user,
        resource=resource,
        query=query or user_input,
        result=result,
        source=source,
        thread_id=thread_id,
    )
    return result


def _write_erp_audit(
    current_user: dict,
    resource: str | None,
    query: str,
    result: dict[str, Any],
    source: str,
    thread_id: str | None = None,
) -> None:
    write_audit_log(
        user_id=current_user.get("id"),
        action=f"erp.{source}.query",
        resource_type="erp",
        resource_id=resource,
        metadata={
            "username": current_user.get("username"),
            "role": current_user.get("role"),
            "position": current_user.get("position"),
            "source": source,
            "thread_id": thread_id,
            "query_preview": query[:200],
            "lookup_query": result.get("lookup_query"),
            "status": result.get("status"),
            "ok": result.get("ok"),
            "provider": result.get("provider"),
            "provider_resource": result.get("provider_resource"),
            "result_count": len(result.get("items") or []),
        },
    )
