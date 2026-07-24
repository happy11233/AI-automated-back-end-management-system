from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.db import close_pool, open_pool
from app.rag.qa import answer_question
from app.rag.retriever import retrieve_chunks

#rag测试hit@k\recall@k,rrm
DEFAULT_DATASET_PATH = PROJECT_ROOT / "eval" / "rag_eval_set.jsonl"
REFUSAL_MARKERS = [
    "资料中没有找到相关信息",
    "没有找到相关信息",
]


@dataclass
class EvalCase:
    case_id: str
    question: str
    role: str
    department: str | None
    position: str | None
    market_scope: str | None
    store_scope: str | None
    field_scope: str | None
    max_sensitivity_level: str | None
    should_refuse: bool
    expected_evidence: list[dict[str, Any]]


def load_eval_cases(dataset_path: Path) -> list[EvalCase]:
    cases = []

    with dataset_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            raw_case = json.loads(line)
            case_id = raw_case.get("id") or f"line-{line_number}"
            should_refuse = bool(raw_case.get("should_refuse", False))
            expected_evidence = raw_case.get("expected_evidence", [])

            if not raw_case.get("question"):
                raise ValueError(f"{dataset_path}:{line_number} 缺少 question")

            if not should_refuse and not expected_evidence:
                raise ValueError(f"{dataset_path}:{line_number} 正样本缺少 expected_evidence")

            cases.append(
                EvalCase(
                    case_id=case_id,
                    question=raw_case["question"],
                    role=raw_case.get("role", "employee"),
                    department=raw_case.get("department"),
                    position=raw_case.get("position"),
                    market_scope=raw_case.get("market_scope"),
                    store_scope=raw_case.get("store_scope"),
                    field_scope=raw_case.get("field_scope"),
                    max_sensitivity_level=raw_case.get("max_sensitivity_level"),
                    should_refuse=should_refuse,
                    expected_evidence=expected_evidence,
                )
            )

    return cases


def evaluate_cases(cases: list[EvalCase], top_k: int) -> dict[str, Any]:
    positive_results = []
    refusal_results = []

    for case in cases:
        chunks = retrieve_chunks(
            query=case.question,
            role=case.role,
            top_k=top_k,
            department=case.department,
            position=case.position,
            market_scope=case.market_scope,
            store_scope=case.store_scope,
            field_scope=case.field_scope,
            max_sensitivity_level=case.max_sensitivity_level,
        )

        if case.should_refuse:
            refusal_results.append(evaluate_refusal_case(case, top_k))
            continue

        positive_results.append(
            evaluate_positive_case(
                case=case,
                chunks=chunks,
                top_k=top_k,
            )
        )

    return build_summary(
        positive_results=positive_results,
        refusal_results=refusal_results,
        top_k=top_k,
    )


def evaluate_positive_case(
    case: EvalCase,
    chunks: list[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    top_chunks = chunks[:top_k]
    matched_evidence_indexes = set()
    first_relevant_rank = None

    for rank, chunk in enumerate(top_chunks, start=1):
        for evidence_index, evidence in enumerate(case.expected_evidence):
            if evidence_matches_chunk(evidence, chunk):
                matched_evidence_indexes.add(evidence_index)

                if first_relevant_rank is None:
                    first_relevant_rank = rank

    expected_count = len(case.expected_evidence)
    matched_count = len(matched_evidence_indexes)

    return {
        "id": case.case_id,
        "question": case.question,
        "hit": 1 if matched_count > 0 else 0,
        "recall": matched_count / expected_count if expected_count else 0.0,
        "reciprocal_rank": 1 / first_relevant_rank if first_relevant_rank else 0.0,
        "first_relevant_rank": first_relevant_rank,
        "matched_evidence_count": matched_count,
        "expected_evidence_count": expected_count,
        "top_chunks": [summarize_chunk(chunk, rank) for rank, chunk in enumerate(top_chunks, start=1)],
    }


def evaluate_refusal_case(case: EvalCase, top_k: int) -> dict[str, Any]:
    result = answer_question(
        question=case.question,
        role=case.role,
        top_k=top_k,
        department=case.department,
        position=case.position,
        market_scope=case.market_scope,
        store_scope=case.store_scope,
        field_scope=case.field_scope,
        max_sensitivity_level=case.max_sensitivity_level,
    )
    answer = result["answer"]
    refused = is_refusal_answer(answer)

    return {
        "id": case.case_id,
        "question": case.question,
        "refused": refused,
        "correct": 1 if refused else 0,
        "answer": answer,
        "chunk_count": len(result.get("chunks", [])),
    }


def build_summary(
    positive_results: list[dict[str, Any]],
    refusal_results: list[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    positive_count = len(positive_results)
    refusal_count = len(refusal_results)

    hit_at_k = average([item["hit"] for item in positive_results])
    recall_at_k = average([item["recall"] for item in positive_results])
    mrr = average([item["reciprocal_rank"] for item in positive_results])
    refusal_accuracy = average([item["correct"] for item in refusal_results])

    return {
        "metrics": {
            f"hit@{top_k}": hit_at_k,
            f"Recall@{top_k}": recall_at_k,
            "MRR": mrr,
            "refusal_accuracy": refusal_accuracy,
        },
        "counts": {
            "total_cases": positive_count + refusal_count,
            "positive_cases": positive_count,
            "refusal_cases": refusal_count,
        },
        "positive_results": positive_results,
        "refusal_results": refusal_results,
    }


def evidence_matches_chunk(evidence: dict[str, Any], chunk: dict[str, Any]) -> bool:
    if evidence.get("chunk_id") and evidence["chunk_id"] not in chunk_id_candidates(chunk):
        return False

    if evidence.get("document_id") and evidence["document_id"] != str(chunk.get("document_id", "")):
        return False

    if evidence.get("source") and not text_matches(evidence["source"], chunk.get("source", "")):
        return False

    if evidence.get("title") and not text_matches(evidence["title"], chunk.get("title", "")):
        return False

    keywords = evidence.get("keywords") or []
    normalized_content = normalize_text(chunk.get("content", ""))
    for keyword in keywords:
        if normalize_text(str(keyword)) not in normalized_content:
            return False

    return True


def chunk_id_candidates(chunk: dict[str, Any]) -> set[str]:
    return {
        str(value)
        for value in [
            chunk.get("chunk_id"),
            chunk.get("child_chunk_id"),
            chunk.get("parent_chunk_id"),
        ]
        if value
    }


def text_matches(expected: str, actual: str) -> bool:
    expected_text = normalize_text(expected)
    actual_text = normalize_text(actual)
    return expected_text == actual_text or expected_text in actual_text


def is_refusal_answer(answer: str) -> bool:
    normalized_answer = normalize_text(answer)
    return any(normalize_text(marker) in normalized_answer for marker in REFUSAL_MARKERS)


def normalize_text(value: str) -> str:
    return "".join(str(value).lower().split())


def summarize_chunk(chunk: dict[str, Any], rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "chunk_id": chunk.get("chunk_id"),
        "child_chunk_id": chunk.get("child_chunk_id"),
        "document_id": chunk.get("document_id"),
        "title": chunk.get("title"),
        "source": chunk.get("source"),
        "score": chunk.get("score"),
        "retrieval_sources": chunk.get("retrieval_sources", []),
        "field_scope": chunk.get("field_scope"),
        "sensitivity_level": chunk.get("sensitivity_level"),
        "content_preview": chunk.get("content", "")[:120],
    }


def average(values: list[float | int]) -> float:
    if not values:
        return 0.0

    return sum(float(value) for value in values) / len(values)


def print_report(summary: dict[str, Any], top_k: int) -> None:
    metrics = summary["metrics"]
    counts = summary["counts"]

    print("RAG 评测结果")
    print("=" * 48)
    print(f"总样本数：{counts['total_cases']}")
    print(f"正样本数：{counts['positive_cases']}")
    print(f"拒答样本数：{counts['refusal_cases']}")
    print("-" * 48)
    print(f"hit@{top_k}: {metrics[f'hit@{top_k}']:.4f}")
    print(f"Recall@{top_k}: {metrics[f'Recall@{top_k}']:.4f}")
    print(f"MRR: {metrics['MRR']:.4f}")
    print(f"拒答准确率: {metrics['refusal_accuracy']:.4f}")
    print()

    if summary["positive_results"]:
        print("正样本明细")
        print("-" * 48)
        for item in summary["positive_results"]:
            status = "PASS" if item["hit"] else "FAIL"
            rank = item["first_relevant_rank"] or "-"
            print(
                f"[{status}] {item['id']} "
                f"hit={item['hit']} recall={item['recall']:.4f} rr={item['reciprocal_rank']:.4f} "
                f"first_rank={rank}"
            )

    if summary["refusal_results"]:
        print()
        print("拒答样本明细")
        print("-" * 48)
        for item in summary["refusal_results"]:
            status = "PASS" if item["correct"] else "FAIL"
            answer_preview = item["answer"].replace("\n", " ")[:80]
            print(
                f"[{status}] {item['id']} "
                f"refused={item['refused']} chunks={item['chunk_count']} answer={answer_preview}"
            )


def write_json_report(summary: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评测 RAG 检索和拒答效果")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="JSONL 评测集路径",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="计算 hit、Recall、MRR 时使用的召回数量",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="可选：把完整评测结果写入 JSON 文件",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_eval_cases(args.dataset)

    open_pool()
    try:
        summary = evaluate_cases(cases=cases, top_k=args.top_k)
    finally:
        close_pool()

    print_report(summary, top_k=args.top_k)

    if args.output:
        write_json_report(summary, args.output)
        print()
        print(f"完整 JSON 报告已写入：{args.output}")


if __name__ == "__main__":
    main()
