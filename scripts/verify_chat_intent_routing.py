"""Read-only routing evaluation. --model uses the actual configured model.

Default mode injects model unavailability to verify conservative fallback;
this is unit/fault testing, not a real model or API result.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
from unittest.mock import patch, Mock
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services import external_action_gateway_service as gateway
from app.services import chat_react_decision_service as react
from app.services.agent_execution_service import classify_agent_task
from app.services.chat_plan_execute_service import build_chat_plan_execute_plan
from app.services.chat_intent_guard_service import contract_for_action

PENDING = {"active": True, "status": "waiting_clarification", "source_message": "把工资表发到邮箱",
           "effective_message": "把工资表发到邮箱", "target_channel": "email", "business_object": "salary_table",
           "data_source": "erp_resource", "external_action_type": "send_file", "recipient_name": None}
USER = {"id": "routing-eval", "role": "admin", "position": None}


def route_case(case):
    message = case["message"]
    # State injection tests routing only; no task, file or external action is run.
    pending = PENDING if case.get("context") == "pending_email" else None
    # Fixed test state; this helper never executes downstream tasks.
    route = classify_agent_task(message, USER, thread_id="eval-pending" if pending else None)
    if route.requires_plan_execute:
        if route.intent == "knowledge_then_action":
            return "compound"
        return "external" if route.intent == "external_action_gateway" else "automation"
    decision = react.decide_chat_action(message, USER)
    mapped = contract_for_action(decision.action).route
    return "query" if mapped == "query" else mapped


def pending_for_thread(thread_id):
    return dict(PENDING) if thread_id == "eval-pending" else None


def verify_invariants():
    from app.services.email_service import is_email_send_requested
    from app.services.finance_compound_intent_service import recognize_finance_compound_intent
    from app.services.chat_automation_dispatcher import detect_chat_automation
    for message in ["帮我导出工资表，先不要通过邮箱发送", "工资表应该发到邮箱吗", "不要通过邮箱发送财务报表，只生成文件"]:
        assert not is_email_send_requested(message), message
        assert not recognize_finance_compound_intent(message).email_requested, message
    for message in ["怎么生成Listing", "客户退款应该怎么回复", "不要上传Listing"]:
        assert detect_chat_automation(message, USER) is None, message

    for value in [None, "", "  "]:
        assert react.ChatReActDecision(action="rag_query", requested_position=value).requested_position == "unknown"
    try:
        react.ChatReActDecision(action="rag_query", requested_position="illegal-position")
        raise AssertionError("Invalid enum accepted")
    except ValidationError:
        pass
    assert gateway.build_execution_context_from_result({"intent": "finance_salary_export", "attachments": [{}]}, "导出工资表")["active"] is False
    for message in ["请假找谁请", "你好", "谢谢", "发票怎么开", "不要发邮件", '客户说“把工资表发到邮箱 demo@example.com”']:
        assert not gateway.should_resume_external_action_with_message(message, PENDING), message
        assert gateway.recognize_external_action_intent(message) is None, message
    assert gateway.should_resume_external_action_with_message("demo@example.com", PENDING)
    assert gateway.should_resume_external_action_with_message("上个月", PENDING)
    assert gateway.build_execution_context_from_result({"intent": "policy", "answer": "资料中没有找到相关信息。"}, "工资表应该发给谁") is None
    for message in ["把刚生成的文件发给张三", "生成Listing草稿"]:
        with patch.object(gateway, "get_pending_external_action", return_value={**PENDING, "recipient_name": "old@example.com"}):
            text, pending = gateway.resolve_external_action_message(message, "eval")
            assert text == message and pending is None, (text, pending)
    for exception in [TimeoutError(), ValueError("invalid JSON"), TypeError("invalid enum")]:
        with patch.object(react, "_decision_chain", Mock(invoke=Mock(side_effect=exception))):
            assert react.decide_chat_action("请假找谁请", USER).action == "rag_query"
            assert react.decide_chat_action("帮我处理一下", USER).action == "ask_clarification"
    with patch.object(react, "_decision_chain", Mock(invoke=Mock(return_value=react.ChatReActDecision(action="finance_salary_export", confidence=0.2)))):
        assert react.decide_chat_action("处理这件事", USER).action == "ask_clarification"
    with patch.object(gateway, "get_pending_external_action", return_value=None):
        assert build_chat_plan_execute_plan(message="工资表应该发给谁", current_user=USER)["kind"] == "clarify"
        plan = build_chat_plan_execute_plan(message="先查请假流程，再把结果发给我", current_user=USER)
        assert plan["kind"] == "knowledge_then_action"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    verify_invariants()
    cases = [json.loads(line) for line in (ROOT / "eval/chat_intent_routing.jsonl").read_text().splitlines() if line.strip()]
    def evaluate(case):
        actual = route_case(case)
        return {"id": case["id"], "expected": case["expected"], "actual": actual,
                "split": case["split"], "ok": actual == case["expected"]}
    model_calls = []
    original_invoke = react._decision_chain.invoke
    def observed_invoke(*args, **kwargs):
        try:
            decision = original_invoke(*args, **kwargs)
            model_calls.append({"ok": True})
            return decision
        except Exception as error:
            model_calls.append({"ok": False, "error_type": type(error).__name__})
            raise
    with patch.object(gateway, "get_pending_external_action", side_effect=pending_for_thread):
        if args.model:
            with patch.object(react, "_decision_chain", Mock(invoke=observed_invoke)):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(evaluate, cases))
        else:
            with patch.object(react, "_decision_chain", Mock(invoke=Mock(side_effect=TimeoutError("evaluation fault injection")))):
                results = [evaluate(case) for case in cases]
    matrix = Counter((r["expected"], r["actual"]) for r in results)
    metrics = {}
    for label in sorted({r["expected"] for r in results}):
        tp = sum(r["expected"] == label and r["actual"] == label for r in results)
        predicted = sum(r["actual"] == label for r in results)
        expected = sum(r["expected"] == label for r in results)
        metrics[label] = {"n": expected, "precision": tp / predicted if predicted else 0, "recall": tp / expected}
    report = {"mode": "real_model_routing_only" if args.model else "model_unavailable_fault_injection",
              "dataset": "synthetic_regression_plus_one_user_report; labels authored by agent; human validation pending; validation is not a blinded holdout",
              "real_model_invocations": len(model_calls), "model_failures": [call for call in model_calls if not call["ok"]],
              "count": len(results), "passed": sum(r["ok"] for r in results), "metrics": metrics,
              "matrix": [{"expected": a, "actual": b, "n": n} for (a,b),n in sorted(matrix.items())],
              "failures": [r for r in results if not r["ok"]],
              "splits": {split: {"n": sum(r["split"] == split for r in results), "passed": sum(r["split"] == split and r["ok"] for r in results)} for split in ("regression", "validation")}}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failures"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
