from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import time
from typing import Any

import requests


WORKFLOW_ID = "operations_listing_launch"
DEFAULT_INPUT = (
    "SKU: LATENCY-BENCH-STEEL-BOTTLE-750; product: 750 ml stainless steel insulated water bottle; "
    "material: 304 stainless steel; size: 750 ml; marketplace: Amazon US; "
    "audience: commuters and outdoor users; selling points: leak-resistant lid, double-wall insulation, "
    "replaceable straw; compliance: do not claim medical benefits or unverified insulation duration. "
    "Generate a listing draft for internal review only."
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def summarize_ms(values: list[int]) -> dict[str, float]:
    seconds = [value / 1000 for value in values]
    return {
        "avg_seconds": round(statistics.mean(seconds), 3) if seconds else 0,
        "p50_seconds": round(percentile(seconds, 0.50), 3),
        "p95_seconds": round(percentile(seconds, 0.95), 3),
        "p99_seconds": round(percentile(seconds, 0.99), 3),
        "max_seconds": round(max(seconds), 3) if seconds else 0,
    }


def login(session: requests.Session, base_url: str, username: str, password: str) -> str:
    response = session.post(
        f"{base_url}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_json(session: requests.Session, base_url: str, path: str, token: str, timeout: int) -> dict[str, Any]:
    response = session.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def run_sample(
    session: requests.Session,
    base_url: str,
    operations_token: str,
    admin_token: str,
    input_text: str,
    timeout: int,
    index: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    response = session.post(
        f"{base_url}/ai-workflows/{WORKFLOW_ID}/run",
        headers={"Authorization": f"Bearer {operations_token}"},
        json={"input_text": input_text},
        timeout=timeout,
    )
    http_duration_ms = round((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    result = response.json()
    run_id = result.get("run_id")
    draft = result.get("platform_draft") or {}
    draft_id = draft.get("id")
    if not run_id or not draft_id:
        raise ValueError(f"sample {index}: missing run_id or platform draft")

    draft_detail = get_json(session, base_url, f"/platform-drafts/{draft_id}", operations_token, timeout)
    run_detail = get_json(session, base_url, f"/run-records/{run_id}", admin_token, timeout)
    saved_draft = draft_detail["item"]
    saved_run = run_detail["run"]
    steps = result.get("steps") or []
    content = saved_draft.get("content") if isinstance(saved_draft.get("content"), dict) else {}
    full_package = str(content.get("full_listing_package") or "")
    amazon_listing = content.get("amazon_listing") if isinstance(content.get("amazon_listing"), dict) else {}
    quality_ok = (
        len(full_package) >= 200
        and "Title" in full_package
        and "Five Bullet Points" in full_package
        and bool(str(amazon_listing.get("title") or "").strip())
    )
    success = (
        result.get("status") == "succeeded"
        and result.get("workflow", {}).get("id") == WORKFLOW_ID
        and saved_run.get("status") == "succeeded"
        and saved_run.get("app_id") == WORKFLOW_ID
        and saved_draft.get("source_run_id") == run_id
        and saved_draft.get("status") == "pending_review"
        and saved_draft.get("writeback_status") == "draft_saved"
        and saved_draft.get("metadata", {}).get("amazon_upload_status") == "waiting_confirmation"
        and not draft_detail.get("executions")
        and quality_ok
        and {step.get("step_name") for step in steps} >= {"ai_generate_decision", "save_platform_draft"}
        and all(step.get("status") == "succeeded" for step in steps)
    )
    return {
        "index": index,
        "success": success,
        "http_duration_ms": http_duration_ms,
        "run_duration_ms": saved_run.get("duration_ms"),
        "run_id": run_id,
        "draft_id": draft_id,
        "draft_status": saved_draft.get("status"),
        "amazon_upload_status": saved_draft.get("metadata", {}).get("amazon_upload_status"),
        "quality_ok": quality_ok,
        "steps": [
            {"name": step.get("step_name"), "status": step.get("status"), "duration_ms": step.get("duration_ms")}
            for step in steps
        ],
    }


def main() -> None:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    base_url = args.api_base_url.rstrip("/")
    session = requests.Session()
    operations_token = login(session, base_url, args.username, args.password)
    admin_token = login(session, base_url, args.admin_username, args.admin_password)
    samples: list[dict[str, Any]] = []

    for index in range(1, args.count + 1):
        try:
            sample = run_sample(
                session, base_url, operations_token, admin_token,
                args.input_text, args.timeout, index,
            )
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            sample = {"index": index, "success": False, "error": type(error).__name__}
        samples.append(sample)
        print(json.dumps({key: sample.get(key) for key in ("index", "success", "http_duration_ms", "run_id", "draft_id", "error") if key in sample}, ensure_ascii=False), flush=True)

    successful = [sample for sample in samples if sample["success"]]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_label": args.run_label,
        "scenario": "operations_listing_launch_fixed_input",
        "configuration": {
            "api_base_url": base_url,
            "model": args.model,
            "input_text": args.input_text,
            "count": args.count,
            "timing_scope": "workflow POST only; draft and run-record verification excluded",
            "side_effect": "creates pending_review platform drafts and run records; does not upload or publish",
        },
        "summary": {
            "samples": len(samples),
            "successes": len(successful),
            "http": summarize_ms([sample["http_duration_ms"] for sample in successful]),
            "run_record": summarize_ms([sample["run_duration_ms"] for sample in successful if isinstance(sample.get("run_duration_ms"), int)]),
        },
        "samples_detail": samples,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": len(successful) == args.count, "output": str(output), "summary": report["summary"]}, ensure_ascii=False))
    if len(successful) != args.count:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the real Listing draft workflow with fixed input")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--run-label", default="baseline-optimized")
    parser.add_argument("--api-base-url", default=os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001"))
    parser.add_argument("--username", default="operations_demo")
    parser.add_argument("--password", default="Operations123456")
    parser.add_argument("--admin-username", default="admin_demo")
    parser.add_argument("--admin-password", default="Admin123456")
    parser.add_argument("--input-text", default=DEFAULT_INPUT)
    parser.add_argument("--model", default=os.getenv("BAILIAN_CHAT_MODEL", "configured in API"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default="data/latency-benchmarks/listing-baseline-optimized.json")
    return parser.parse_args()


if __name__ == "__main__":
    main()
