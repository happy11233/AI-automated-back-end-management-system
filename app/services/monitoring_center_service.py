from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import fetch_all, fetch_one
from app.erp.providers import get_active_provider
from app.permissions import POSITION_LABELS
from app.services.connector_service import list_connectors
from app.services.evaluation_center_service import build_evaluation_center
from app.services.run_record_service import isoformat, sanitize_text


DATE_RANGE_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}


def build_monitoring_center(date_range: str = "30d") -> dict[str, Any]:
    normalized_range = date_range if date_range in {"7d", "30d", "90d", "all"} else "30d"
    since = _since_for_range(normalized_range)
    run_where, run_params = _time_scope("started_at", since)
    audit_where, audit_params = _time_scope("created_at", since)

    database = _database_health()
    run_summary = _run_summary(run_where, run_params)
    audit_summary = _audit_summary(audit_where, audit_params)
    connectors = _connectors_health()
    erp_health = _erp_health()
    evaluation = _evaluation_health()
    knowledge = _knowledge_stats()
    users = _user_stats()
    service_health = _service_health(
        database=database,
        erp_health=erp_health,
        connectors=connectors,
        evaluation=evaluation,
        run_summary=run_summary,
        audit_summary=audit_summary,
    )

    return {
        "scope": {
            "date_range": normalized_range,
            "date_range_label": _date_range_label(normalized_range),
            "since": isoformat(since),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "overall_status": _overall_status(service_health),
        "database": database,
        "run_summary": run_summary,
        "run_trend": _run_trend(run_where, run_params),
        "position_summary": _position_summary(run_where, run_params),
        "run_type_summary": _run_type_summary(run_where, run_params),
        "recent_issues": _recent_issues(run_where, run_params),
        "slow_runs": _slow_runs(run_where, run_params),
        "audit_summary": audit_summary,
        "audit_actions": _audit_actions(audit_where, audit_params),
        "connectors": connectors,
        "erp_health": erp_health,
        "evaluation": evaluation,
        "knowledge": knowledge,
        "users": users,
        "service_health": service_health,
    }


def _database_health() -> dict[str, Any]:
    row = fetch_one("SELECT now();")
    return {
        "status": "ok",
        "message": "数据库连接正常",
        "checked_at": isoformat(row[0]),
        "database_name": "PostgreSQL connected",
    }


def _run_summary(where_clause: str, params: list[Any]) -> dict[str, Any]:
    row = fetch_one(
        f"""
        SELECT
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            count(*) FILTER (WHERE status = 'running') AS running_runs,
            COALESCE(avg(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0)::int AS avg_duration_ms,
            COALESCE(
                percentile_disc(0.95) WITHIN GROUP (ORDER BY duration_ms)
                FILTER (WHERE duration_ms IS NOT NULL),
                0
            )::int AS p95_duration_ms,
            max(started_at) AS latest_run_at,
            count(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) AS active_users
        FROM automation_runs
        {where_clause};
        """,
        tuple(params),
    )
    total_runs = int(row[0] or 0)
    succeeded_runs = int(row[1] or 0)
    failed_runs = int(row[2] or 0)
    blocked_runs = int(row[3] or 0)
    running_runs = int(row[4] or 0)
    completed_runs = succeeded_runs + failed_runs + blocked_runs

    return {
        "total_runs": total_runs,
        "succeeded_runs": succeeded_runs,
        "failed_runs": failed_runs,
        "blocked_runs": blocked_runs,
        "running_runs": running_runs,
        "success_rate": _ratio(succeeded_runs, completed_runs),
        "failure_rate": _ratio(failed_runs, completed_runs),
        "blocked_rate": _ratio(blocked_runs, completed_runs),
        "avg_duration_ms": int(row[5] or 0),
        "p95_duration_ms": int(row[6] or 0),
        "latest_run_at": isoformat(row[7]),
        "active_users": int(row[8] or 0),
    }


def _run_trend(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            date_trunc('day', started_at)::date AS day,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            count(*) FILTER (WHERE status = 'running') AS running_runs
        FROM automation_runs
        {where_clause}
        GROUP BY date_trunc('day', started_at)::date
        ORDER BY day ASC
        LIMIT 120;
        """,
        tuple(params),
    )
    return [
        {
            "date": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
            "total_runs": int(row[1] or 0),
            "succeeded_runs": int(row[2] or 0),
            "failed_runs": int(row[3] or 0),
            "blocked_runs": int(row[4] or 0),
            "running_runs": int(row[5] or 0),
        }
        for row in rows
    ]


def _position_summary(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            COALESCE(position, 'platform') AS position,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            COALESCE(avg(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0)::int AS avg_duration_ms
        FROM automation_runs
        {where_clause}
        GROUP BY COALESCE(position, 'platform')
        ORDER BY total_runs DESC, position ASC
        LIMIT 8;
        """,
        tuple(params),
    )
    return [
        {
            "position": row[0],
            "position_label": _position_label(row[0]),
            "total_runs": int(row[1] or 0),
            "succeeded_runs": int(row[2] or 0),
            "failed_runs": int(row[3] or 0),
            "blocked_runs": int(row[4] or 0),
            "success_rate": _ratio(int(row[2] or 0), int(row[1] or 0) - int(row[4] or 0)),
            "avg_duration_ms": int(row[5] or 0),
        }
        for row in rows
    ]


def _run_type_summary(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            run_type,
            max(app_name) AS app_name,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            COALESCE(avg(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0)::int AS avg_duration_ms,
            max(started_at) AS latest_run_at
        FROM automation_runs
        {where_clause}
        GROUP BY run_type
        ORDER BY total_runs DESC, max(started_at) DESC
        LIMIT 10;
        """,
        tuple(params),
    )
    return [
        {
            "run_type": row[0],
            "label": _run_type_label(row[0]),
            "app_name": row[1],
            "total_runs": int(row[2] or 0),
            "succeeded_runs": int(row[3] or 0),
            "failed_runs": int(row[4] or 0),
            "blocked_runs": int(row[5] or 0),
            "success_rate": _ratio(int(row[3] or 0), int(row[2] or 0) - int(row[5] or 0)),
            "avg_duration_ms": int(row[6] or 0),
            "latest_run_at": isoformat(row[7]),
        }
        for row in rows
    ]


def _recent_issues(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT id, status, run_type, app_id, app_name, position, duration_ms, started_at
        FROM automation_runs
        {where_clause}
          AND status IN ('failed', 'blocked')
        ORDER BY started_at DESC
        LIMIT 12;
        """,
        tuple(params),
    )
    return [
        {
            "id": str(row[0]),
            "status": row[1],
            "run_type": row[2],
            "run_type_label": _run_type_label(row[2]),
            "app_id": row[3],
            "app_name": row[4],
            "position": row[5],
            "position_label": _position_label(row[5]),
            "duration_ms": row[6],
            "occurred_at": isoformat(row[7]),
            "summary": "权限拦截" if row[1] == "blocked" else "运行失败，详见运行记录",
        }
        for row in rows
    ]


def _slow_runs(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT id, status, run_type, app_id, app_name, position, duration_ms, started_at
        FROM automation_runs
        {where_clause}
          AND duration_ms IS NOT NULL
        ORDER BY duration_ms DESC, started_at DESC
        LIMIT 10;
        """,
        tuple(params),
    )
    return [
        {
            "id": str(row[0]),
            "status": row[1],
            "run_type": row[2],
            "run_type_label": _run_type_label(row[2]),
            "app_id": row[3],
            "app_name": row[4],
            "position": row[5],
            "position_label": _position_label(row[5]),
            "duration_ms": row[6],
            "started_at": isoformat(row[7]),
        }
        for row in rows
    ]


def _audit_summary(where_clause: str, params: list[Any]) -> dict[str, Any]:
    row = fetch_one(
        f"""
        SELECT
            count(*) AS total_events,
            count(*) FILTER (
                WHERE action ILIKE '%%blocked%%'
                   OR action ILIKE '%%denied%%'
                   OR action ILIKE '%%permission%%'
            ) AS security_events,
            count(*) FILTER (WHERE action ILIKE '%%approval%%') AS approval_events,
            count(*) FILTER (WHERE action ILIKE '%%user%%') AS user_admin_events,
            max(created_at) AS latest_event_at
        FROM audit_logs
        {where_clause};
        """,
        tuple(params),
    )
    return {
        "total_events": int(row[0] or 0),
        "security_events": int(row[1] or 0),
        "approval_events": int(row[2] or 0),
        "user_admin_events": int(row[3] or 0),
        "latest_event_at": isoformat(row[4]),
    }


def _audit_actions(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT action, resource_type, count(*) AS count, max(created_at) AS last_seen_at
        FROM audit_logs
        {where_clause}
        GROUP BY action, resource_type
        ORDER BY count DESC, max(created_at) DESC
        LIMIT 12;
        """,
        tuple(params),
    )
    return [
        {
            "action": row[0],
            "resource_type": row[1],
            "count": int(row[2] or 0),
            "last_seen_at": isoformat(row[3]),
        }
        for row in rows
    ]


def _connectors_health() -> dict[str, Any]:
    payload = list_connectors()
    items = [
        {
            "id": item["id"],
            "label": item["label"],
            "category": item["category"],
            "active": item["active"],
            "configured": item["configured"],
            "status": item["status"],
            "health_status": item["health_status"],
            "health_message": _safe_message(item.get("health_message")),
            "supports_real_health_check": item["supports_real_health_check"],
            "position_scope_labels": item["position_scope_labels"],
            "last_checked_at": item["last_checked_at"],
        }
        for item in payload["items"]
    ]
    return {
        "summary": payload["summary"],
        "items": items,
    }


def _erp_health() -> dict[str, Any]:
    provider = get_active_provider()
    health = provider.health_check()
    return {
        "provider": provider.provider_id,
        "provider_label": provider.provider_label,
        "configured": bool(health.get("configured")),
        "ok": bool(health.get("ok")),
        "status": str(health.get("status") or "unknown"),
        "message": _safe_message(health.get("message")),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _evaluation_health() -> dict[str, Any]:
    payload = build_evaluation_center()
    gates = payload["release_gates"]
    gate_statuses = [item["status"] for item in gates]
    reports = payload["reports"]
    latest_report_at = max(
        [item["updated_at"] for item in reports if item.get("updated_at")],
        default=None,
    )
    return {
        "summary": payload["summary"],
        "release_gates": gates,
        "latest_report_at": latest_report_at,
        "status": "failed" if "failed" in gate_statuses else "warning" if "warning" in gate_statuses else "ok",
    }


def _knowledge_stats() -> dict[str, Any]:
    document_row = fetch_one(
        """
        SELECT
            count(*) AS total_documents,
            count(*) FILTER (WHERE status = 'active') AS active_documents,
            max(updated_at) AS latest_document_at
        FROM documents;
        """
    )
    chunk_row = fetch_one(
        """
        SELECT
            count(*) AS child_chunks,
            count(DISTINCT document_id) AS indexed_documents,
            max(created_at) AS latest_chunk_at
        FROM document_chunks;
        """
    )
    parent_row = fetch_one("SELECT count(*) FROM document_parent_chunks;")
    return {
        "total_documents": int(document_row[0] or 0),
        "active_documents": int(document_row[1] or 0),
        "latest_document_at": isoformat(document_row[2]),
        "child_chunks": int(chunk_row[0] or 0),
        "indexed_documents": int(chunk_row[1] or 0),
        "latest_chunk_at": isoformat(chunk_row[2]),
        "parent_chunks": int(parent_row[0] or 0),
    }


def _user_stats() -> dict[str, Any]:
    rows = fetch_all(
        """
        SELECT role, COALESCE(position, 'platform') AS position, count(*) AS count
        FROM users
        GROUP BY role, COALESCE(position, 'platform')
        ORDER BY role ASC, position ASC;
        """
    )
    items = [
        {
            "role": row[0],
            "position": row[1],
            "position_label": _position_label(row[1]),
            "count": int(row[2] or 0),
        }
        for row in rows
    ]
    return {
        "total_users": sum(item["count"] for item in items),
        "items": items,
    }


def _service_health(
    *,
    database: dict[str, Any],
    erp_health: dict[str, Any],
    connectors: dict[str, Any],
    evaluation: dict[str, Any],
    run_summary: dict[str, Any],
    audit_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    connector_summary = connectors["summary"]
    connector_warning = connector_summary["needs_config"] + connector_summary["pending"]
    return [
        {
            "id": "api",
            "name": "API 服务",
            "status": "ok",
            "message": "后端健康检查可用",
            "metric": "HTTP /health",
        },
        {
            "id": "database",
            "name": "PostgreSQL",
            "status": database["status"],
            "message": database["message"],
            "metric": database["database_name"],
        },
        {
            "id": "erp",
            "name": "ERP 连接",
            "status": "ok" if erp_health["ok"] else "warning" if erp_health["configured"] else "failed",
            "message": erp_health["message"],
            "metric": erp_health["provider_label"],
        },
        {
            "id": "connectors",
            "name": "连接器",
            "status": "warning" if connector_warning else "ok",
            "message": f"{connector_summary['healthy']} 个健康，{connector_warning} 个待处理",
            "metric": f"{connector_summary['configured']}/{connector_summary['total']}",
        },
        {
            "id": "automation",
            "name": "自动化执行",
            "status": "warning" if run_summary["failed_runs"] else "ok",
            "message": f"{run_summary['total_runs']} 次运行，失败 {run_summary['failed_runs']} 次",
            "metric": f"{round(run_summary['success_rate'] * 100, 1)}%",
        },
        {
            "id": "security",
            "name": "权限审计",
            "status": "warning" if audit_summary["security_events"] else "ok",
            "message": f"{audit_summary['security_events']} 条权限/拦截事件",
            "metric": str(audit_summary["total_events"]),
        },
        {
            "id": "evaluation",
            "name": "AI 评测",
            "status": evaluation["status"],
            "message": f"{evaluation['summary']['total_cases']} 个真实评测/回归样本",
            "metric": f"{round(evaluation['summary']['average_pass_rate'] * 100, 1)}%",
        },
    ]


def _overall_status(items: list[dict[str, Any]]) -> str:
    statuses = {item["status"] for item in items}
    if "failed" in statuses:
        return "failed"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _time_scope(column: str, since: datetime | None) -> tuple[str, list[Any]]:
    if not since:
        return "WHERE 1 = 1", []

    return f"WHERE {column} >= %s", [since]


def _since_for_range(date_range: str) -> datetime | None:
    if date_range == "all":
        return None

    return datetime.now(timezone.utc) - timedelta(days=DATE_RANGE_DAYS.get(date_range, 30))


def _date_range_label(date_range: str) -> str:
    labels = {
        "7d": "近 7 天",
        "30d": "近 30 天",
        "90d": "近 90 天",
        "all": "全部时间",
    }
    return labels.get(date_range, labels["30d"])


def _position_label(position: str | None) -> str:
    if not position:
        return "未绑定岗位"
    if position == "platform":
        return "平台"
    return POSITION_LABELS.get(position, position)


def _run_type_label(run_type: str) -> str:
    labels = {
        "automation_generate": "岗位文本自动化",
        "finance_excel_transform": "财务 Excel 自动化",
        "finance_reconciliation": "财务对账自动化",
        "erp_query": "ERP 查询",
        "chat": "AI 对话",
        "chat_stream": "流式 AI 对话",
        "agent_chat": "Agent 对话",
    }
    return labels.get(run_type, run_type)


def _safe_message(value: Any) -> str:
    text = sanitize_text(str(value or ""))
    patterns = [
        r"(?i)Authorization\s*[:=]\s*(?:Bearer|token|Basic)?\s+[^\s,;}\"]+",
        r"(?i)(?:Bearer|token|Basic)\s+[A-Za-z0-9._~+/=:-]+",
        r"(?i)(api[_-]?secret|api[_-]?key|password|passwd|token|jwt|secret)\s*[:=]\s*[^,\s;}\"]+",
        r"(?i)\"(api[_-]?secret|api[_-]?key|password|passwd|token|jwt|secret)\"\s*:\s*\"[^\"]+\"",
        r"(?i)(postgresql|postgres|mysql|mongodb|redis)://[^:@/\s]+:[^@/\s]+@",
        r"(?i)https?://[^:@/\s]+:[^@/\s]+@",
        r"(?i)\b[A-Z0-9_]*(?:SECRET|PASSWORD|TOKEN|JWT|API[_-]?KEY)[A-Z0-9_]*\b",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text)

    if "{" in text and "}" in text:
        text = "外部系统返回异常，原始响应已脱敏隐藏"

    return text[:300]


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0

    return round(numerator / denominator, 4)
