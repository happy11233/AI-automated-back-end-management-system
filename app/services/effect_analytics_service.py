from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import fetch_all, fetch_one
from app.permissions import POSITION_LABELS
from app.services.run_record_service import isoformat, sanitize_metadata


SAVED_MINUTES_BY_RUN_TYPE = {
    "automation_generate": 12,
    "finance_excel_transform": 35,
    "finance_reconciliation": 60,
    "erp_query": 8,
    "chat": 10,
    "chat_stream": 10,
    "agent_chat": 12,
}
DEFAULT_SAVED_MINUTES = 8
DATE_RANGE_DAYS = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}


def build_effect_analytics(
    *,
    current_user: dict,
    date_range: str = "30d",
    position: str | None = None,
) -> dict[str, Any]:
    scoped_position = _resolve_position_filter(current_user, position)
    since = _since_for_range(date_range)
    run_where, run_params = _run_scope(current_user, since, scoped_position)
    audit_where, audit_params = _audit_scope(current_user, since, scoped_position)

    summary = _build_summary(run_where, run_params)
    status_distribution = _group_count(
        f"""
        SELECT status, count(*) AS count
        FROM automation_runs
        {run_where}
        GROUP BY status
        ORDER BY count DESC;
        """,
        tuple(run_params),
        key_name="status",
    )
    run_type_ranking = _run_type_ranking(run_where, run_params)
    position_ranking = _position_ranking(run_where, run_params)
    app_ranking = _app_ranking(run_where, run_params)
    trend = _trend(run_where, run_params)
    failure_reasons = _failure_reasons(run_where, run_params)
    audit_summary = _audit_summary(audit_where, audit_params)
    scoped_run_types = {item["run_type"] for item in run_type_ranking}
    estimate_model = [
        {
            "run_type": run_type,
            "saved_minutes_per_run": minutes,
            "description": _saved_minutes_description(run_type, minutes),
        }
        for run_type, minutes in sorted(SAVED_MINUTES_BY_RUN_TYPE.items())
        if current_user.get("role") == "admin" or run_type in scoped_run_types
    ]

    return {
        "scope": {
            "role": current_user.get("role"),
            "position": scoped_position,
            "position_label": _position_label(scoped_position),
            "date_range": date_range if date_range in {"all", *DATE_RANGE_DAYS.keys()} else "30d",
            "date_range_label": _date_range_label(date_range),
            "since": isoformat(since),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "summary": summary,
        "status_distribution": status_distribution,
        "trend": trend,
        "position_ranking": position_ranking,
        "app_ranking": app_ranking,
        "run_type_ranking": run_type_ranking,
        "failure_reasons": failure_reasons,
        "audit_summary": audit_summary,
        "estimate_model": estimate_model,
    }


def _build_summary(where_clause: str, params: list[Any]) -> dict[str, Any]:
    row = fetch_one(
        f"""
        SELECT
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            count(*) FILTER (WHERE status = 'running') AS running_runs,
            COALESCE(avg(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0) AS avg_duration_ms,
            COALESCE(sum(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0) AS total_duration_ms,
            COALESCE(sum(
                CASE
                    WHEN status = 'succeeded' THEN
                        CASE run_type
                            WHEN 'automation_generate' THEN {SAVED_MINUTES_BY_RUN_TYPE["automation_generate"]}
                            WHEN 'finance_excel_transform' THEN {SAVED_MINUTES_BY_RUN_TYPE["finance_excel_transform"]}
                            WHEN 'finance_reconciliation' THEN {SAVED_MINUTES_BY_RUN_TYPE["finance_reconciliation"]}
                            WHEN 'erp_query' THEN {SAVED_MINUTES_BY_RUN_TYPE["erp_query"]}
                            WHEN 'chat' THEN {SAVED_MINUTES_BY_RUN_TYPE["chat"]}
                            WHEN 'chat_stream' THEN {SAVED_MINUTES_BY_RUN_TYPE["chat_stream"]}
                            WHEN 'agent_chat' THEN {SAVED_MINUTES_BY_RUN_TYPE["agent_chat"]}
                            ELSE {DEFAULT_SAVED_MINUTES}
                        END
                    ELSE 0
                END
            ), 0) AS estimated_saved_minutes
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
    avg_duration_ms = int(row[5] or 0)
    total_duration_ms = int(row[6] or 0)
    estimated_saved_minutes = int(row[7] or 0)
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
        "avg_duration_ms": avg_duration_ms,
        "total_duration_ms": total_duration_ms,
        "estimated_saved_minutes": estimated_saved_minutes,
        "estimated_saved_hours": round(estimated_saved_minutes / 60, 1),
    }


def _run_type_ranking(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            run_type,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            COALESCE(avg(duration_ms) FILTER (WHERE duration_ms IS NOT NULL), 0) AS avg_duration_ms
        FROM automation_runs
        {where_clause}
        GROUP BY run_type
        ORDER BY total_runs DESC, run_type ASC
        LIMIT 12;
        """,
        tuple(params),
    )
    return [
        {
            "run_type": row[0],
            "label": _run_type_label(row[0]),
            "total_runs": int(row[1] or 0),
            "succeeded_runs": int(row[2] or 0),
            "failed_runs": int(row[3] or 0),
            "blocked_runs": int(row[4] or 0),
            "success_rate": _ratio(int(row[2] or 0), int(row[1] or 0) - int(row[4] or 0)),
            "avg_duration_ms": int(row[5] or 0),
        }
        for row in rows
    ]


def _position_ranking(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            COALESCE(position, 'platform') AS position,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            COALESCE(sum(
                CASE
                    WHEN status = 'succeeded' THEN
                        CASE run_type
                            WHEN 'automation_generate' THEN {SAVED_MINUTES_BY_RUN_TYPE["automation_generate"]}
                            WHEN 'finance_excel_transform' THEN {SAVED_MINUTES_BY_RUN_TYPE["finance_excel_transform"]}
                            WHEN 'finance_reconciliation' THEN {SAVED_MINUTES_BY_RUN_TYPE["finance_reconciliation"]}
                            WHEN 'erp_query' THEN {SAVED_MINUTES_BY_RUN_TYPE["erp_query"]}
                            WHEN 'chat' THEN {SAVED_MINUTES_BY_RUN_TYPE["chat"]}
                            WHEN 'chat_stream' THEN {SAVED_MINUTES_BY_RUN_TYPE["chat_stream"]}
                            WHEN 'agent_chat' THEN {SAVED_MINUTES_BY_RUN_TYPE["agent_chat"]}
                            ELSE {DEFAULT_SAVED_MINUTES}
                        END
                    ELSE 0
                END
            ), 0) AS saved_minutes
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
            "estimated_saved_minutes": int(row[5] or 0),
        }
        for row in rows
    ]


def _app_ranking(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            app_id,
            max(app_name) AS app_name,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs,
            max(started_at) AS last_run_at
        FROM automation_runs
        {where_clause}
        GROUP BY app_id
        ORDER BY total_runs DESC, max(started_at) DESC
        LIMIT 12;
        """,
        tuple(params),
    )
    return [
        {
            "app_id": row[0],
            "app_name": row[1],
            "total_runs": int(row[2] or 0),
            "succeeded_runs": int(row[3] or 0),
            "failed_runs": int(row[4] or 0),
            "blocked_runs": int(row[5] or 0),
            "success_rate": _ratio(int(row[3] or 0), int(row[2] or 0) - int(row[5] or 0)),
            "last_run_at": isoformat(row[6]),
        }
        for row in rows
    ]


def _trend(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            date_trunc('day', started_at)::date AS day,
            count(*) AS total_runs,
            count(*) FILTER (WHERE status = 'succeeded') AS succeeded_runs,
            count(*) FILTER (WHERE status = 'failed') AS failed_runs,
            count(*) FILTER (WHERE status = 'blocked') AS blocked_runs
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
        }
        for row in rows
    ]


def _failure_reasons(where_clause: str, params: list[Any]) -> list[dict[str, Any]]:
    rows = fetch_all(
        f"""
        SELECT
            status,
            COALESCE(NULLIF(error_message, ''), '未记录错误摘要') AS reason,
            count(*) AS count,
            max(started_at) AS last_seen_at
        FROM automation_runs
        {where_clause}
          AND status IN ('failed', 'blocked')
        GROUP BY status, COALESCE(NULLIF(error_message, ''), '未记录错误摘要')
        ORDER BY count DESC, max(started_at) DESC
        LIMIT 10;
        """,
        tuple(params),
    )
    return [
        {
            "status": row[0],
            "reason": row[1],
            "count": int(row[2] or 0),
            "last_seen_at": isoformat(row[3]),
        }
        for row in rows
    ]


def _audit_summary(where_clause: str, params: list[Any]) -> dict[str, Any]:
    total_row = fetch_one(
        f"""
        SELECT
            count(*) AS total_events,
            count(*) FILTER (
                WHERE action ILIKE '%%blocked%%' OR action ILIKE '%%denied%%' OR action ILIKE '%%permission%%'
            ) AS blocked_events,
            count(*) FILTER (
                WHERE action ILIKE '%%approval%%'
            ) AS approval_events
        FROM audit_logs
        {where_clause};
        """,
        tuple(params),
    )
    action_rows = fetch_all(
        f"""
        SELECT action, resource_type, count(*) AS count, max(created_at) AS last_seen_at
        FROM audit_logs
        {where_clause}
        GROUP BY action, resource_type
        ORDER BY count DESC, max(created_at) DESC
        LIMIT 10;
        """,
        tuple(params),
    )
    return {
        "total_events": int(total_row[0] or 0),
        "blocked_events": int(total_row[1] or 0),
        "approval_events": int(total_row[2] or 0),
        "top_actions": [
            {
                "action": row[0],
                "resource_type": row[1],
                "count": int(row[2] or 0),
                "last_seen_at": isoformat(row[3]),
            }
            for row in action_rows
        ],
    }


def _group_count(query: str, params: tuple[Any, ...], *, key_name: str) -> list[dict[str, Any]]:
    rows = fetch_all(query, params)
    return [{key_name: row[0], "count": int(row[1] or 0)} for row in rows]


def _run_scope(
    current_user: dict,
    since: datetime | None,
    position: str | None,
) -> tuple[str, list[Any]]:
    conditions = ["1 = 1"]
    params: list[Any] = []

    if since:
        conditions.append("started_at >= %s")
        params.append(since)

    if current_user.get("role") != "admin":
        conditions.append("user_id = %s")
        params.append(current_user.get("id"))
        conditions.append("position IS NOT DISTINCT FROM %s")
        params.append(current_user.get("position"))
    elif position:
        conditions.append("position = %s")
        params.append(position)

    return f"WHERE {' AND '.join(conditions)}", params


def _audit_scope(
    current_user: dict,
    since: datetime | None,
    position: str | None,
) -> tuple[str, list[Any]]:
    conditions = ["1 = 1"]
    params: list[Any] = []

    if since:
        conditions.append("created_at >= %s")
        params.append(since)

    if current_user.get("role") != "admin":
        conditions.append("user_id = %s")
        params.append(current_user.get("id"))
    elif position:
        conditions.append("metadata->>'position' = %s")
        params.append(position)

    return f"WHERE {' AND '.join(conditions)}", params


def _resolve_position_filter(current_user: dict, position: str | None) -> str | None:
    if current_user.get("role") != "admin":
        user_position = current_user.get("position")
        return str(user_position) if user_position else None

    if position in POSITION_LABELS:
        return position

    return None


def _since_for_range(date_range: str) -> datetime | None:
    if date_range == "all":
        return None

    days = DATE_RANGE_DAYS.get(date_range, 30)
    return datetime.now(timezone.utc) - timedelta(days=days)


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
        return "全部岗位"
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


def _saved_minutes_description(run_type: str, minutes: int) -> str:
    return f"{_run_type_label(run_type)}每次成功执行按保守 {minutes} 分钟估算。"


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)
