from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import settings


def build_aiops_snapshot() -> dict[str, Any]:
    base_url = _normalized_base_url()
    poll_interval = max(60, settings.aiops_monitoring_poll_interval_seconds)
    snapshot = _empty_snapshot(base_url, poll_interval)

    if not base_url:
        return snapshot

    try:
        health = _get_json("/health")
        summary = _get_json("/api/v1/admin/dashboard/summary")
        incidents = _get_json("/api/v1/admin/incidents?limit=20&offset=0")
    except AIOpsBridgeError as error:
        snapshot["health"]["status"] = "failed"
        snapshot["health"]["message"] = str(error)
        snapshot["message"] = f"AIOps 服务暂不可达: {error}"
        return snapshot

    incident_items = [
        _normalize_incident(item)
        for item in incidents.get("items", [])
        if isinstance(item, dict)
    ]
    summary_payload = _normalize_summary(summary, poll_interval)
    health_status = "ok" if summary_payload["open_incident_count"] == 0 else "warning"
    snapshot.update(
        {
            "reachable": True,
            "status": health_status,
            "message": "AIOps 服务可用",
            "health": {
                "status": health.get("data", {}).get("status", "ok") if isinstance(health, dict) else "ok",
                "message": health.get("message", "AIOps 服务可用") if isinstance(health, dict) else "AIOps 服务可用",
                "checked_at": _now_iso(),
                "base_url": base_url,
            },
            "summary": summary_payload,
            "incidents": incident_items,
        }
    )
    snapshot["summary"]["repairable_count"] = sum(
        1 for item in incident_items if item["repair_available"]
    )
    if health_status == "warning":
        snapshot["message"] = "AIOps 已接入，但存在待处理事故"
    return snapshot


def get_aiops_incident_detail(incident_id: str) -> dict[str, Any]:
    detail = _get_json(f"/api/v1/admin/incidents/{quote(incident_id, safe='')}")
    return _normalize_detail(detail)


def repair_aiops_incident(
    incident_id: str,
    *,
    approved_by: str,
    reason: str,
) -> dict[str, Any]:
    payload = {
        "approved_by": approved_by,
        "reason": reason,
    }
    response = _request_json(
        "POST",
        f"/api/v1/admin/incidents/{quote(incident_id, safe='')}/repair",
        payload=payload,
    )
    if isinstance(response.get("detail"), dict):
        response["detail"] = _normalize_detail(response["detail"])
    return response


def _empty_snapshot(base_url: str | None, poll_interval: int) -> dict[str, Any]:
    return {
        "configured": bool(base_url),
        "reachable": False,
        "status": "disconnected",
        "message": "未配置 AIOps 服务地址",
        "base_url": base_url,
        "health": {
            "status": "disconnected",
            "message": "未配置 AIOps 服务地址",
            "checked_at": None,
            "base_url": base_url,
        },
        "summary": {
            "service_target_count": 0,
            "enabled_service_target_count": 0,
            "incident_count": 0,
            "open_incident_count": 0,
            "critical_open_incident_count": 0,
            "action_required_count": 0,
            "remediating_count": 0,
            "resolved_count": 0,
            "failed_count": 0,
            "last_incident_at": None,
            "scheduler_enabled": False,
            "default_inspection_interval_seconds": 86400,
            "storage_backend": "unknown",
            "poll_interval_seconds": poll_interval,
            "repairable_count": 0,
        },
        "incidents": [],
    }


def _normalize_summary(summary: dict[str, Any], poll_interval: int) -> dict[str, Any]:
    return {
        "service_target_count": int(summary.get("service_target_count") or 0),
        "enabled_service_target_count": int(summary.get("enabled_service_target_count") or 0),
        "incident_count": int(summary.get("incident_count") or 0),
        "open_incident_count": int(summary.get("open_incident_count") or 0),
        "critical_open_incident_count": int(summary.get("critical_open_incident_count") or 0),
        "action_required_count": int(summary.get("action_required_count") or 0),
        "remediating_count": int(summary.get("remediating_count") or 0),
        "resolved_count": int(summary.get("resolved_count") or 0),
        "failed_count": int(summary.get("failed_count") or 0),
        "last_incident_at": summary.get("last_incident_at"),
        "scheduler_enabled": bool(summary.get("scheduler_enabled")),
        "default_inspection_interval_seconds": int(
            summary.get("default_inspection_interval_seconds") or 86400
        ),
        "storage_backend": str(summary.get("storage_backend") or "unknown"),
        "poll_interval_seconds": poll_interval,
        "repairable_count": 0,
    }


def _normalize_incident(item: dict[str, Any]) -> dict[str, Any]:
    repair = item.get("repair") if isinstance(item.get("repair"), dict) else {}
    return {
        "incident_id": str(item.get("incident_id") or ""),
        "title": str(item.get("title") or item.get("summary") or ""),
        "service": str(item.get("service") or ""),
        "environment": str(item.get("environment") or ""),
        "namespace": str(item.get("namespace") or ""),
        "severity": str(item.get("severity") or ""),
        "severity_label": str(item.get("severity_label") or item.get("severity") or ""),
        "status": str(item.get("status") or ""),
        "status_label": str(item.get("status_label") or item.get("status") or ""),
        "alert_type": str(item.get("alert_type") or ""),
        "alert_type_label": str(item.get("alert_type_label") or item.get("alert_type") or ""),
        "summary": str(item.get("summary") or ""),
        "current_stage": str(item.get("current_stage") or ""),
        "current_stage_label": str(item.get("current_stage_label") or item.get("current_stage") or ""),
        "root_cause": item.get("root_cause"),
        "impact": item.get("impact"),
        "recommendation": item.get("recommendation"),
        "service_target_id": item.get("service_target_id"),
        "runtime_type": item.get("runtime_type"),
        "evidence_count": int(item.get("evidence_count") or 0),
        "action_count": int(item.get("action_count") or 0),
        "repair_available": bool(repair.get("available")),
        "repair_reason": repair.get("disabled_reason"),
        "latest_verification_status": item.get("latest_verification_status"),
        "latest_verification_summary": item.get("latest_verification_summary"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "detail_api": f"/monitoring-center/aiops/incidents/{quote(str(item.get('incident_id') or ''), safe='')}",
        "repair_api": f"/monitoring-center/aiops/incidents/{quote(str(item.get('incident_id') or ''), safe='')}/repair",
    }


def _normalize_detail(detail: dict[str, Any]) -> dict[str, Any]:
    if isinstance(detail.get("card"), dict):
        detail["card"] = _normalize_incident(detail["card"])
    return detail


def _normalized_base_url() -> str | None:
    raw = (settings.aiops_service_url or "").strip()
    if not raw:
        return None
    return raw.rstrip("/")


def _get_json(path: str) -> dict[str, Any]:
    return _request_json("GET", path)


def _request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url = _normalized_base_url()
    if not base_url:
        raise AIOpsBridgeError("AIOps 服务地址未配置")

    url = f"{base_url}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=settings.aiops_service_timeout_seconds) as response:
            body = response.read().decode("utf-8")
            if not body.strip():
                return {}
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                return parsed
            return {"data": parsed}
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="ignore") if error.fp else ""
        snippet = details.strip() or error.reason or "unknown error"
        raise AIOpsBridgeError(f"{error.code} {snippet}") from error
    except URLError as error:
        raise AIOpsBridgeError(str(error.reason)) from error
    except json.JSONDecodeError as error:
        raise AIOpsBridgeError(f"JSON 解析失败: {error}") from error


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AIOpsBridgeError(RuntimeError):
    pass
