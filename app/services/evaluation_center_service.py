from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = PROJECT_ROOT / "eval"
REPORT_LIMIT = 8


DATASETS = [
    {
        "id": "rag_smoke",
        "name": "RAG 基础问答评测集",
        "category": "RAG",
        "path": EVAL_DIR / "rag_eval_set.jsonl",
        "report_path": EVAL_DIR / "rag_eval_report.json",
        "description": "覆盖退款规则、发货退款、特殊退款审批和拒答样本。",
        "runner": "scripts/evaluate_rag.py",
        "can_run": True,
    },
    {
        "id": "rag_rules_large",
        "name": "公司规则类 RAG 大样本评测集",
        "category": "RAG",
        "path": EVAL_DIR / "rule_rag_eval_set.jsonl",
        "report_path": EVAL_DIR / "rule_rag_eval_report.json",
        "description": "从公司规则类 DOCX 文档生成的大样本评测集，用于压力评测规则检索命中率。",
        "runner": "scripts/evaluate_rag.py",
        "can_run": True,
    },
]

REGRESSION_SUITES = [
    {
        "id": "erp_chat_accuracy",
        "name": "ERP 对话准确性回归",
        "category": "ERP",
        "command": ".venv/bin/python scripts/verify_erp_chat.py",
        "description": "使用真实登录、真实 ERPNext 和真实 /chat，验证运营、客服、财务 ERP 对话返回正确引用。",
        "case_count": 5,
    },
    {
        "id": "position_permission_refusal",
        "name": "岗位权限拒答回归",
        "category": "权限拒答",
        "command": ".venv/bin/python scripts/verify_position_permissions.py",
        "description": "使用真实后端验证跨岗位自动化、ERP、AI 对话、Excel、管理员接口和 ERP 详情权限。",
        "case_count": 20,
    },
    {
        "id": "release_ready",
        "name": "发布前稳定化回归",
        "category": "发布闸门",
        "command": ".venv/bin/python scripts/verify_release_ready.py",
        "description": "覆盖 ERP 概览金额、记录详情权限、AI 对话 ERP 引用和管理员审计筛选。",
        "case_count": 4,
    },
    {
        "id": "automation_flow_output_contract",
        "name": "自动化流程输出契约检查",
        "category": "自动化输出",
        "command": ".venv/bin/python scripts/verify_automation_flows.py",
        "description": "检查流程配置来源、schema、允许资源、审批策略和敏感字段不泄露。",
        "case_count": 4,
    },
]


def build_evaluation_center() -> dict[str, Any]:
    datasets = [_dataset_item(item) for item in DATASETS]
    reports = [_report_summary(item) for item in DATASETS if item["report_path"].exists()]
    regression_suites = [_regression_suite_item(item) for item in REGRESSION_SUITES]

    total_cases = sum(item["case_count"] for item in datasets) + sum(
        item["case_count"] for item in regression_suites
    )
    pass_rates = [
        report["pass_rate"]
        for report in reports
        if report["pass_rate"] is not None
    ]

    return {
        "summary": {
            "dataset_count": len(datasets),
            "report_count": len(reports),
            "regression_suite_count": len(regression_suites),
            "total_cases": total_cases,
            "average_pass_rate": round(sum(pass_rates) / len(pass_rates), 4) if pass_rates else 0.0,
        },
        "datasets": datasets,
        "reports": reports,
        "regression_suites": regression_suites,
        "release_gates": _release_gates(reports, regression_suites),
    }


def run_rag_evaluation(
    *,
    dataset_id: str = "rag_smoke",
    top_k: int = 5,
) -> dict[str, Any]:
    dataset = _find_dataset(dataset_id)
    if not dataset["can_run"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该评测集暂不支持在线运行")

    if not dataset["path"].exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评测集文件不存在")

    from scripts.evaluate_rag import evaluate_cases, load_eval_cases, write_json_report

    cases = load_eval_cases(dataset["path"])
    summary = evaluate_cases(cases=cases, top_k=top_k)

    write_json_report(summary, dataset["report_path"])
    return {
        "dataset": _dataset_item(dataset),
        "report": _build_report_payload(dataset, summary),
    }


def _dataset_item(item: dict[str, Any]) -> dict[str, Any]:
    case_count, positive_count, refusal_count = _count_jsonl_cases(item["path"])
    report = _load_report(item["report_path"])
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "description": item["description"],
        "path": _display_path(item["path"]),
        "report_path": _display_path(item["report_path"]),
        "runner": item["runner"],
        "case_count": case_count,
        "positive_cases": positive_count,
        "refusal_cases": refusal_count,
        "has_report": report is not None,
        "can_run": item["can_run"],
        "updated_at": _mtime_iso(item["path"]),
        "report_updated_at": _mtime_iso(item["report_path"]),
    }


def _regression_suite_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "description": item["description"],
        "command": item["command"],
        "case_count": item["case_count"],
        "real_services": ["真实后端", "真实登录", "真实权限", "真实 ERPNext"],
    }


def _report_summary(item: dict[str, Any]) -> dict[str, Any]:
    report = _load_report(item["report_path"])
    if report is None:
        return {
            "dataset_id": item["id"],
            "dataset_name": item["name"],
            "metrics": {},
            "counts": {},
            "pass_rate": None,
            "failed_cases": [],
            "updated_at": None,
        }

    return _build_report_payload(item, report)


def _build_report_payload(item: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    metrics = report.get("metrics") or {}
    counts = report.get("counts") or {}
    positive_results = report.get("positive_results") or []
    refusal_results = report.get("refusal_results") or []
    failed_cases = _failed_cases(positive_results, refusal_results)
    pass_rate = _pass_rate(positive_results, refusal_results)
    return {
        "dataset_id": item["id"],
        "dataset_name": item["name"],
        "metrics": metrics,
        "counts": counts,
        "pass_rate": pass_rate,
        "failed_cases": failed_cases,
        "updated_at": _mtime_iso(item["report_path"]),
    }


def _failed_cases(
    positive_results: list[dict[str, Any]],
    refusal_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for item in positive_results:
        if item.get("hit"):
            continue
        failures.append({
            "id": item.get("id"),
            "type": "retrieval",
            "question_preview": _preview(item.get("question")),
            "reason": "未命中期望证据",
            "score": item.get("recall"),
            "first_relevant_rank": item.get("first_relevant_rank"),
        })

    for item in refusal_results:
        if item.get("correct"):
            continue
        failures.append({
            "id": item.get("id"),
            "type": "refusal",
            "question_preview": _preview(item.get("question")),
            "reason": "拒答判断失败",
            "score": 1 if item.get("refused") else 0,
            "first_relevant_rank": None,
        })

    return failures[:REPORT_LIMIT]


def _release_gates(
    reports: list[dict[str, Any]],
    regression_suites: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gates = []
    for report in reports:
        pass_rate = report.get("pass_rate") or 0
        gates.append({
            "id": f"report-{report['dataset_id']}",
            "name": f"{report['dataset_name']} 通过率",
            "status": "passed" if pass_rate >= 0.95 else "warning",
            "threshold": ">= 95%",
            "actual": f"{pass_rate * 100:.1f}%",
        })

    for suite in regression_suites:
        gates.append({
            "id": f"suite-{suite['id']}",
            "name": suite["name"],
            "status": "ready",
            "threshold": "必须真实运行通过",
            "actual": suite["command"],
        })

    return gates


def _count_jsonl_cases(path: Path) -> tuple[int, int, int]:
    if not path.exists():
        return 0, 0, 0

    total = 0
    positive = 0
    refusal = 0
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            total += 1
            item = json.loads(line)
            if item.get("should_refuse"):
                refusal += 1
            else:
                positive += 1

    return total, positive, refusal


def _load_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_dataset(dataset_id: str) -> dict[str, Any]:
    for item in DATASETS:
        if item["id"] == dataset_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评测集不存在")


def _pass_rate(
    positive_results: list[dict[str, Any]],
    refusal_results: list[dict[str, Any]],
) -> float:
    total = len(positive_results) + len(refusal_results)
    if total == 0:
        return 0.0

    positive_passed = sum(1 for item in positive_results if item.get("hit"))
    refusal_passed = sum(1 for item in refusal_results if item.get("correct"))
    return round((positive_passed + refusal_passed) / total, 4)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(
        path.stat().st_mtime,
        tz=timezone.utc,
    ).isoformat()


def _preview(value: Any, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
