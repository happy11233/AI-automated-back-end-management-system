from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
import os
from decimal import Decimal
import sys
from typing import Any

import psycopg


DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag_user:rag_password@127.0.0.1:5433/rag_agent",
)


def main() -> None:
    args = parse_args()
    since = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days else None
    params: list[Any] = [since] if since else []
    scope = "all" if since is None else f"last_{args.days}d"
    canonical = """
        NOT EXISTS (
            SELECT 1
            FROM automation_runs parent
            WHERE parent.metadata->'automation'->>'run_id' = r.id::text
        )
    """
    run_where = f"WHERE r.duration_ms IS NOT NULL AND {canonical}"
    if since:
        run_where += " AND r.started_at >= %s"

    with psycopg.connect(args.database_url) as connection:
        run_types = query_rows(
            connection,
            f"""
            SELECT
                r.run_type,
                max(r.app_name) AS app_name,
                count(*) AS samples,
                round(avg(r.duration_ms) / 1000.0, 3) AS avg_seconds,
                round((percentile_cont(0.50) WITHIN GROUP (ORDER BY r.duration_ms) / 1000.0)::numeric, 3) AS p50_seconds,
                round((percentile_cont(0.95) WITHIN GROUP (ORDER BY r.duration_ms) / 1000.0)::numeric, 3) AS p95_seconds,
                round((percentile_cont(0.99) WITHIN GROUP (ORDER BY r.duration_ms) / 1000.0)::numeric, 3) AS p99_seconds,
                round((max(r.duration_ms) / 1000.0)::numeric, 3) AS max_seconds
            FROM automation_runs r
            {run_where}
            GROUP BY r.run_type
            ORDER BY p95_seconds DESC, samples DESC;
            """,
            params,
        )
        steps = query_rows(
            connection,
            f"""
            SELECT
                s.step_name,
                s.provider,
                count(*) AS samples,
                round(avg(s.duration_ms) / 1000.0, 3) AS avg_seconds,
                round((percentile_cont(0.95) WITHIN GROUP (ORDER BY s.duration_ms) / 1000.0)::numeric, 3) AS p95_seconds,
                round((max(s.duration_ms) / 1000.0)::numeric, 3) AS max_seconds
            FROM automation_run_steps s
            JOIN automation_runs r ON r.id = s.run_id
            {run_where}
              AND s.duration_ms IS NOT NULL
            GROUP BY s.step_name, s.provider
            ORDER BY p95_seconds DESC, samples DESC
            LIMIT 30;
            """,
            params,
        )
        overall = query_rows(
            connection,
            f"""
            SELECT
                count(*) AS samples,
                round(avg(r.duration_ms) / 1000.0, 3) AS avg_seconds,
                round((percentile_cont(0.50) WITHIN GROUP (ORDER BY r.duration_ms) / 1000.0)::numeric, 3) AS p50_seconds,
                round((percentile_cont(0.95) WITHIN GROUP (ORDER BY r.duration_ms) / 1000.0)::numeric, 3) AS p95_seconds,
                round((percentile_cont(0.99) WITHIN GROUP (ORDER BY r.duration_ms) / 1000.0)::numeric, 3) AS p99_seconds
            FROM automation_runs r
            {run_where};
            """,
            params,
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "definition": "唯一端到端运行；父对话包裹的子运行不重复计入。",
        "overall": overall[0] if overall else {},
        "run_types": run_types,
        "steps": steps,
    }
    if args.format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(("group", "name", "provider", "samples", "avg_seconds", "p50_seconds", "p95_seconds", "p99_seconds", "max_seconds"))
        write_csv_row(writer, "overall", "all", "", payload["overall"])
        for item in run_types:
            write_csv_row(writer, "run_type", item["run_type"], "", item)
        for item in steps:
            write_csv_row(writer, "step", item["step_name"], item["provider"], item)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def write_csv_row(writer: Any, group: str, name: str, provider: str, item: dict[str, Any]) -> None:
    writer.writerow((
        group, name, provider, item["samples"], item["avg_seconds"],
        item.get("p50_seconds"), item["p95_seconds"], item.get("p99_seconds"), item.get("max_seconds"),
    ))


def query_rows(connection, query: str, params: list[Any]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(query, tuple(params))
        columns = [description.name for description in cursor.description]
        return [
            {
                key: float(value) if isinstance(value, Decimal) else value
                for key, value in zip(columns, row)
            }
            for row in cursor.fetchall()
        ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="输出 automation_runs 的分类型延迟基线")
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="只统计最近 N 天；默认 0 表示全部时间",
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="PostgreSQL 连接串，默认读取 DATABASE_URL",
    )
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    return parser.parse_args()


if __name__ == "__main__":
    main()
