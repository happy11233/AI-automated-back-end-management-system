from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.qa import answer_question
from app.db import close_pool, open_pool


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> None:
    args = parse_args()
    open_pool()
    durations: list[float] = []
    samples: list[dict] = []
    for index in range(1, args.count + 1):
        started = time.perf_counter()
        result = answer_question(
            question=args.question,
            role=args.role,
            department=args.department,
            position=args.position,
            top_k=args.top_k,
            multi_query_count=args.multi_query_count,
            generate_answer=False,
        )
        duration = time.perf_counter() - started
        durations.append(duration)
        samples.append({
            "index": index,
            "duration_ms": round(duration * 1000),
            "chunk_count": len(result.get("chunks") or []),
            "citation_count": len(result.get("citations") or []),
        })
        print(json.dumps(samples[-1], ensure_ascii=False), flush=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": "rag_fixed_query_retrieval_only",
        "configuration": {
            "question": args.question,
            "role": args.role,
            "department": args.department,
            "position": args.position,
            "top_k": args.top_k,
            "multi_query_count": args.multi_query_count,
            "count": args.count,
        },
        "summary": {
            "samples": len(durations),
            "successful_samples": sum(item["chunk_count"] > 0 for item in samples),
            "avg_seconds": round(statistics.mean(durations), 3) if durations else 0,
            "p50_seconds": round(percentile(durations, 0.5), 3),
            "p95_seconds": round(percentile(durations, 0.95), 3),
            "p99_seconds": round(percentile(durations, 0.99), 3),
            "max_seconds": round(max(durations), 3) if durations else 0,
        },
        "samples": samples,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "summary": report["summary"]}, ensure_ascii=False))
    close_pool()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fixed-input RAG retrieval benchmark")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--question", default="订单已经发货但是还没签收，可以申请退款吗？")
    parser.add_argument("--role", default="employee")
    parser.add_argument("--department", default=None)
    parser.add_argument("--position", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--multi-query-count", type=int, default=1)
    parser.add_argument("--output", default="data/latency-benchmarks/rag-baseline-optimized.json")
    return parser.parse_args()


if __name__ == "__main__":
    main()
