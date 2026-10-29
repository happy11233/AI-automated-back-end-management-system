"""Side-effect-free checks for customer intent, ERP priority and partial-source failure."""
from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph.intent import _classify_by_rules
from app.graph.workflow import risk_check
from app.services.chat_intent_guard_service import refund_case_kind
from app.services.chat_react_decision_service import decide_chat_action
from app.services import customer_service_automation_service as customer
from app.services.erp_service import build_erp_candidates


USER = {"id": "fixture", "role": "admin", "position": "customer_service"}


def message(text: str) -> dict:
    return {"id": "fixture", "message": text, "subject": "", "buyer_language": "auto",
            "order_no": "AMZ-001", "tracking_no": None, "sku": None}


def main():
    for text in ("Where is my order?", "订单物流到哪里了", "请查快递运单"):
        classification = customer.classify_customer_message(message(text))
        assert classification["intent"] == "logistics", (text, classification)
    assert customer.classify_customer_message(message("What is my order status?"))["intent"] == "order_status"
    assert customer.classify_customer_message(message("查询订单状态"))["intent"] == "order_status"

    assert build_erp_candidates("Where is my order?", USER,
                                allowed_resources=["Delivery Note", "Sales Order"],
                                preferred_resource="Delivery Note") == ["Delivery Note"]
    assert build_erp_candidates("订单状态", USER, allowed_resources=["Delivery Note"],
                                preferred_resource="Sales Order") == []
    with patch.object(customer, "query_erp_for_current_user", return_value={
        "ok": True, "resource": "Delivery Note", "items": [], "status": "ok",
    }) as query:
        result = customer._query_customer_erp(item=message("Where is my order?"),
                                              classification={"intent": "logistics"}, current_user=USER)
        assert query.call_args.kwargs["preferred_resource"] == "Delivery Note"
        assert result["resource_selection_confidence"] == 1.0
    with patch.object(customer, "query_erp_for_current_user") as query:
        ambiguous = customer._query_customer_erp(item=message("客户订单"),
                                                 classification={"intent": "general_question"},
                                                 current_user=USER)
        assert ambiguous["status"] == "needs_clarification"
        assert ambiguous["resource_selection_confidence"] == 0.5
        assert ambiguous["resource_candidates"] == ["Customer", "Sales Order"]
        assert not query.called
        assert customer.decide_customer_action(
            {"intent": "general_question", "risk_level": "low", "reason": "test"},
            ambiguous, {"citations": []})["status"] == "drafted"

    classification = {"intent": "logistics", "risk_level": "low", "reason": "test", "language": "English"}
    with patch.object(customer, "_query_customer_erp", side_effect=TimeoutError("erp down")), \
         patch.object(customer, "answer_question", return_value={"answer": "Policy source", "citations": [{"title": "policy"}]}):
        erp, erp_ms, rag, rag_ms = customer._fetch_customer_context(
            item=message("Where is my order?"), classification=classification, current_user=USER)
    assert erp["status"] == "source_unavailable" and erp["error_code"] == "TimeoutError"
    assert rag["answer"] == "Policy source" and erp_ms >= 0 and rag_ms >= 0
    assert customer.decide_customer_action(classification, erp, rag)["status"] == "drafted"

    with patch.object(customer, "_query_customer_erp", return_value={"ok": True, "items": [{"name": "DN-1"}]}), \
         patch.object(customer, "answer_question", side_effect=ConnectionError("rag down")):
        erp, _, rag, _ = customer._fetch_customer_context(
            item=message("Where is my order?"), classification=classification, current_user=USER)
    assert rag["status"] == "source_unavailable" and rag["error_code"] == "ConnectionError"
    assert customer.decide_customer_action(classification, erp, rag)["status"] == "drafted"
    assert customer.decide_customer_action({**classification, "risk_level": "high"}, erp, rag)["status"] == "human_handoff"
    assert customer.decide_customer_action(classification,
        {"status": "source_unavailable"}, {"status": "source_unavailable"})["status"] == "human_handoff"

    for text in ("订单能不能退款", "这个订单可以退吗", "Is this order refundable?"):
        assert refund_case_kind(text) == "eligibility", text
        assert _classify_by_rules(text) == "refund", text
        assert decide_chat_action(text, USER).action == "refund_request", text
        assert risk_check({"intent": "refund", "user_input": text,
                           "order_result": {"found": True, "refundable": True}})["risk_level"] == "low"
    assert refund_case_kind("退款多久到账") is None
    assert _classify_by_rules("退款多久到账") == "policy"
    assert risk_check({"intent": "refund", "user_input": "帮我申请退款",
                       "order_result": {"found": True, "refundable": True}})["risk_level"] == "high"
    print("customer routing/degradation checks passed: resource priority, source failures, refund eligibility")


if __name__ == "__main__":
    main()
