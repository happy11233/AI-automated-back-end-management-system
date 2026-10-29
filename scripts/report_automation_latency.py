"""Read-only latency summary from local run, step, job and customer-message records."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import timedelta
from math import ceil
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import close_pool, fetch_all, open_pool


def percentile(values: list[int], fraction: float) -> str:
    if not values:
        return "-"
    ordered = sorted(values)
    seconds = ordered[max(0, ceil(len(ordered) * fraction) - 1)] / 1000
    return f"{seconds:.3f}" if seconds < 1 else f"{seconds:.2f}"


def show_groups(title: str, rows: list[tuple], key_columns: int = 1, *,
                use_duration: bool = False, complete_statuses: set[str] | None = None) -> None:
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(str(value or "-") for value in row[:key_columns])].append(row[key_columns:])
    print(f"\n## {title}")
    print(f"| 分组 | 总数 | 完成数 | 有效{'步骤计时' if use_duration else '墙钟'}样本 | P50 秒 | P95 秒 | duration_ms 零/缺失 | 未完成 |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key, records in sorted(groups.items()):
        index = 0 if use_duration else 1
        complete = [record for record in records
                    if complete_statuses is None or record[2] in complete_statuses]
        values = [int(record[index]) for record in complete
                  if record[index] is not None and record[index] > 0]
        missing_duration = sum(record[0] is None or record[0] <= 0 for record in records)
        unfinished = sum(record[1] is None or record[2] == "running" for record in records)
        print(f"| {' / '.join(key)} | {len(records)} | {len(complete)} | {len(values)} | {percentile(values, .5)} | "
              f"{percentile(values, .95)} | {missing_duration} | {unfinished} |")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    days = max(1, min(args.days, 365))
    since = timedelta(days=days)
    open_pool()
    try:
        runs = fetch_all("""SELECT app_id,COALESCE(NULLIF(flow_key,''),'(unlinked)'),duration_ms,
            CASE WHEN finished_at>=started_at THEN
              (EXTRACT(EPOCH FROM finished_at-started_at)*1000)::bigint END,status
            FROM automation_runs WHERE created_at>=now()-%s ORDER BY app_id,flow_key""", (since,))
        steps = fetch_all("""SELECT r.app_id,s.step_name,s.duration_ms,
            CASE WHEN s.finished_at>=s.started_at THEN
              (EXTRACT(EPOCH FROM s.finished_at-s.started_at)*1000)::bigint END,s.status
            FROM automation_run_steps s JOIN automation_runs r ON r.id=s.run_id
            WHERE r.created_at>=now()-%s ORDER BY r.app_id,s.step_name""", (since,))
        jobs = fetch_all("""SELECT kind,duration_ms,
            CASE WHEN finished_at>=created_at THEN
              (EXTRACT(EPOCH FROM finished_at-created_at)*1000)::bigint END,status
            FROM (SELECT kind,NULL::integer AS duration_ms,created_at,finished_at,status
                  FROM background_jobs WHERE created_at>=now()-%s) x""", (since,))
        messages = fetch_all("""SELECT channel,NULL::integer,
            CASE WHEN processed_at>=created_at THEN
              (EXTRACT(EPOCH FROM processed_at-created_at)*1000)::bigint END,status
            FROM customer_service_messages WHERE created_at>=now()-%s""", (since,))
        feedback = fetch_all("""SELECT category,NULL::integer,
            CASE WHEN completed_at>=created_at THEN
              (EXTRACT(EPOCH FROM completed_at-created_at)*1000)::bigint END,status
            FROM feedback_items WHERE created_at>=now()-%s""", (since,))
    finally:
        close_pool()

    print(f"# 自动化耗时记录（近 {days} 天）")
    print("单位为秒；P50/P95 只使用完成状态；应用、任务和消息使用数据库时间戳，步骤使用 duration_ms。")
    show_groups("AI 应用与工作流", runs, 2, complete_statuses={"succeeded"})
    show_groups("工作流步骤", steps, 2, use_duration=True, complete_statuses={"succeeded"})
    show_groups("后台任务创建至完成", jobs, complete_statuses={"succeeded"})
    show_groups("客服消息接收至处理", messages,
                complete_statuses={"drafted", "auto_reply_ready", "human_handoff", "closed"})
    show_groups("产品反馈提交至关闭（人工流程）", feedback, complete_statuses={"completed"})
    print("\n限制：数据包含本地测试记录；服务端时间不含客户端网络/排队前时间，"
          "客服 processed_at 也不一定代表对客户送达；不能据此声称真实客户端到端 SLA。")


if __name__ == "__main__":
    main()
