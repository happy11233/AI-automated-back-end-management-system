from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.db import fetch_all, fetch_one, open_pool, pool


mcp = FastMCP(
    "company-postgres-readonly",
    instructions="Postgres 只读诊断工具。只允许管理员通过固定查询查看自动化运行状态。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """检查只读诊断查询是否可用。"""
    try:
        _ensure_pool_open()
        row = fetch_one("SELECT 1;")
    except Exception as error:
        return {
            "ok": False,
            "status": "unhealthy",
            "message": f"Postgres 只读诊断不可用：{error}",
        }
    return {
        "ok": bool(row and row[0] == 1),
        "status": "healthy",
        "message": "Postgres 只读诊断可用；不支持自由 SQL。",
        "free_sql_allowed": False,
    }


@mcp.tool()
def summarize_automation_runs(limit: int = 50) -> dict[str, Any]:
    """汇总最近自动化运行状态，只返回业务可视化字段。"""
    _ensure_pool_open()
    bounded_limit = _bounded_limit(limit)
    rows = fetch_all(
        """
        SELECT status, run_type, app_name, count(*) AS total
        FROM (
            SELECT status, run_type, app_name
            FROM automation_runs
            ORDER BY created_at DESC
            LIMIT %s
        ) recent
        GROUP BY status, run_type, app_name
        ORDER BY total DESC, app_name ASC;
        """,
        (bounded_limit,),
    )
    items = [
        {
            "状态": _status_label(row[0]),
            "类型": row[1],
            "应用": row[2],
            "次数": int(row[3] or 0),
        }
        for row in rows
    ]
    return {
        "ok": True,
        "status": "ready",
        "message": f"已汇总最近 {bounded_limit} 条自动化运行记录。",
        "summary_table": items,
        "free_sql_allowed": False,
    }


@mcp.tool()
def list_recent_failures(limit: int = 10) -> dict[str, Any]:
    """列出最近失败或阻断的自动化运行记录。"""
    _ensure_pool_open()
    bounded_limit = _bounded_limit(limit, default=10, maximum=50)
    rows = fetch_all(
        """
        SELECT id, run_type, app_name, status, username, position, error_message, created_at, finished_at
        FROM automation_runs
        WHERE status IN ('failed', 'blocked')
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (bounded_limit,),
    )
    items = [
        {
            "运行ID": str(row[0]),
            "类型": row[1],
            "应用": row[2],
            "状态": _status_label(row[3]),
            "用户": row[4],
            "岗位": _position_label(row[5]),
            "原因": str(row[6] or "")[:160],
            "开始时间": row[7].isoformat() if row[7] else None,
            "结束时间": row[8].isoformat() if row[8] else None,
        }
        for row in rows
    ]
    return {
        "ok": True,
        "status": "ready",
        "message": f"已列出最近 {len(items)} 条失败或阻断记录。",
        "items": items,
        "free_sql_allowed": False,
    }


@mcp.tool()
def get_run_diagnostics(run_id: str) -> dict[str, Any]:
    """按运行 ID 查看诊断摘要和步骤，不返回原始 payload。"""
    _ensure_pool_open()
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "run_id 不能为空。",
        }
    run = fetch_one(
        """
        SELECT id, run_type, app_name, status, username, position, input_preview,
               output_preview, error_message, duration_ms, created_at, finished_at
        FROM automation_runs
        WHERE id = %s
        LIMIT 1;
        """,
        (normalized_run_id,),
    )
    if run is None:
        return {
            "ok": False,
            "status": "not_found",
            "message": "未找到该运行记录。",
        }

    step_rows = fetch_all(
        """
        SELECT step_order, step_name, status, provider, output_preview, error_message, duration_ms
        FROM automation_run_steps
        WHERE run_id = %s
        ORDER BY step_order ASC, started_at ASC;
        """,
        (normalized_run_id,),
    )
    steps = [
        {
            "序号": int(row[0] or 0),
            "步骤": row[1],
            "状态": _status_label(row[2]),
            "执行方": row[3],
            "结果摘要": str(row[4] or row[5] or "")[:180],
            "耗时毫秒": row[6],
        }
        for row in step_rows
    ]
    return {
        "ok": True,
        "status": "ready",
        "message": "已生成运行诊断摘要。",
        "run": {
            "运行ID": str(run[0]),
            "类型": run[1],
            "应用": run[2],
            "状态": _status_label(run[3]),
            "用户": run[4],
            "岗位": _position_label(run[5]),
            "输入摘要": str(run[6] or "")[:180],
            "输出摘要": str(run[7] or "")[:180],
            "错误摘要": str(run[8] or "")[:180],
            "耗时毫秒": run[9],
            "开始时间": run[10].isoformat() if run[10] else None,
            "结束时间": run[11].isoformat() if run[11] else None,
        },
        "steps": steps,
        "free_sql_allowed": False,
    }


def _bounded_limit(value: int, *, default: int = 50, maximum: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _ensure_pool_open() -> None:
    if pool.closed:
        open_pool()


def _status_label(value: str | None) -> str:
    return {
        "running": "执行中",
        "succeeded": "成功",
        "failed": "失败",
        "blocked": "已阻断",
    }.get(str(value or ""), str(value or "未知"))


def _position_label(value: str | None) -> str:
    return {
        "operations": "运营",
        "customer_service": "客服",
        "finance": "财务",
    }.get(str(value or ""), str(value or ""))


if __name__ == "__main__":
    mcp.run(transport="stdio")
