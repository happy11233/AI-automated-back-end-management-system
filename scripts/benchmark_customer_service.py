from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time
from typing import Any
from uuid import uuid4

import requests


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> None:
    args = parse_args()
    base_url = args.api_base_url.rstrip("/")
    token = login(base_url, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}
    samples: list[dict[str, Any]] = []

    for index in range(1, args.count + 1):
        external_id = f"latency-benchmark-{args.run_label}-{index}-{uuid4().hex[:8]}"
        payload = {
            "channel": "manual",
            "external_id": external_id,
            "buyer_name": "Latency Benchmark",
            "buyer_language": "English",
            "marketplace": "Amazon US",
            "order_no": args.order_no,
            "subject": args.subject,
            "message": args.message,
            "metadata": {"benchmark": True, "run_label": args.run_label, "sample_index": index},
        }
        started = time.perf_counter()
        created = post(base_url, "/customer-service/messages", headers, payload, timeout=args.timeout)
        message_id = created["item"]["id"]
        result = post(base_url, f"/customer-service/messages/{message_id}/process", headers, {}, timeout=args.timeout)
        duration_ms = round((time.perf_counter() - started) * 1000)
        item = result["item"]
        samples.append({
            "index": index,
            "message_id": message_id,
            "run_id": result.get("run_id"),
            "duration_ms": duration_ms,
            "status": item.get("status"),
            "intent": item.get("intent"),
            "risk_level": item.get("risk_level"),
            "steps": [
                {"name": step.get("step_name"), "duration_ms": step.get("duration_ms")}
                for step in result.get("steps", [])
            ],
        })
        print(json.dumps({"sample": index, "duration_ms": duration_ms, "run_id": result.get("run_id")}, ensure_ascii=False), flush=True)

    durations = [sample["duration_ms"] / 1000 for sample in samples]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_label": args.run_label,
        "scenario": "customer_service_low_risk_fixed_input",
        "configuration": {
            "api_base_url": base_url,
            "model": os.getenv("BAILIAN_FAST_CHAT_MODEL", "configured in API"),
            "message": args.message,
            "order_no": args.order_no,
            "count": args.count,
        },
        "summary": {
            "samples": len(durations),
            "successes": sum(sample["status"] in {"auto_reply_ready", "drafted"} for sample in samples),
            "avg_seconds": round(statistics.mean(durations), 3) if durations else 0,
            "p50_seconds": round(percentile(durations, 0.50), 3),
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


def login(base_url: str, username: str, password: str) -> str:
    response = requests.post(
        f"{base_url}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def post(base_url: str, path: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    response = requests.post(
        f"{base_url}{path}",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a fixed-input real customer-service latency benchmark")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--run-label", default="baseline-optimized")
    parser.add_argument("--api-base-url", default=os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001"))
    parser.add_argument("--username", default="employee_demo")
    parser.add_argument("--password", default="Employee123456")
    parser.add_argument("--order-no", default="AMZ-US-001")
    parser.add_argument("--subject", default="Latency benchmark order status")
    parser.add_argument("--message", default="Where is my order? My order number is AMZ-US-001.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default="data/latency-benchmarks/customer-service-baseline-optimized.json")
    return parser.parse_args()


if __name__ == "__main__":
    main()
