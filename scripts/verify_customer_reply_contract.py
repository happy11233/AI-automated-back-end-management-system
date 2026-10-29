"""Deterministic parsing/dispatch checks; not a model or channel acceptance test."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.customer_reply_contract import (
    apply_customer_reply_review, can_auto_write_customer_reply,
    customer_reply_external_content, parse_customer_reply,
)


class ReplyContractVerification(unittest.TestCase):
    def test_customer_text_is_separate(self):
        parsed = parse_customer_reply(json.dumps({
            "customer_reply": "Thank you.", "internal_note": "内部核实记录",
            "needs_human_review": False,
        }))
        content = customer_reply_external_content({
            **parsed, "reply_draft": parsed["customer_reply"],
            "handoff_reason": "内部原因", "metadata": {"secret": "internal"},
        })
        self.assertEqual(content["reply_draft"], "Thank you.")
        self.assertNotIn("internal_note", content)
        self.assertNotIn("handoff_reason", content)
        self.assertNotIn("metadata", content)

    def test_invalid_outputs_never_become_customer_text(self):
        for raw in [
            "1. 客户回复正文：Hello\n2. 客服内部处理建议：内部记录",
            '"hello"', '[]', '{}',
            '{"customer_reply":"Hello","internal_note":"x","needs_human_review":"false"}',
            '{"customer_reply":"Hello","internal_note":"x","needs_human_review":false,"extra":1}',
            '{"customer_reply":"Hello","customer_reply":"Internal","internal_note":"","needs_human_review":false}',
            '{"customer_reply":" ","internal_note":"x","needs_human_review":false}',
            json.dumps({"customer_reply": "Hello\nInternal note: staff investigation", "internal_note": "", "needs_human_review": False}),
            json.dumps({"customer_reply": "您好\n2. 客服内部处理建议：核实订单", "internal_note": "", "needs_human_review": False}),
        ]:
            with self.subTest(raw=raw):
                parsed = parse_customer_reply(raw)
                self.assertEqual(parsed["customer_reply"], "")
                self.assertTrue(parsed["needs_human_review"])
                self.assertEqual(parsed["reply_unparsed_output"], raw)

    def test_fenced_json_is_unambiguous(self):
        raw = '{"customer_reply":"Hello","internal_note":"","needs_human_review":false}'
        self.assertEqual(parse_customer_reply("```json\n" + raw + "\n```")["customer_reply"], "Hello")
        self.assertEqual(parse_customer_reply("prefix " + raw)["reply_parse_status"], "invalid")

    def test_automation_requires_all_conditions(self):
        reply = parse_customer_reply('{"customer_reply":"Hello","internal_note":"","needs_human_review":false}')
        ready = {"status": "auto_reply_ready", "decision": "low_risk_auto_reply_ready", "handoff_reason": ""}
        self.assertTrue(can_auto_write_customer_reply({"risk_level": "low"}, ready, reply))
        for risk in ("medium", "high"):
            self.assertFalse(can_auto_write_customer_reply({"risk_level": risk}, ready, reply))
        for changed in ({"needs_human_review": True}, {"reply_parse_status": "invalid"}, {"customer_reply": ""}):
            self.assertFalse(can_auto_write_customer_reply({"risk_level": "low"}, ready, {**reply, **changed}))
        draft = {"status": "drafted", "decision": "draft_only", "handoff_reason": "缺订单"}
        self.assertEqual(apply_customer_reply_review(draft, reply), draft)
        self.assertFalse(can_auto_write_customer_reply({"risk_level": "low"}, draft, reply))
        self.assertEqual(apply_customer_reply_review(ready, {**reply, "needs_human_review": True})["status"], "drafted")
        self.assertEqual(apply_customer_reply_review(ready, parse_customer_reply("invalid"))["status"], "drafted")

    def test_legacy_or_empty_body_cannot_dispatch(self):
        for content in ({"reply_draft": "legacy mixed text"}, {"reply_draft": "", "reply_parse_status": "validated"}):
            with self.subTest(content=content), self.assertRaises(ValueError):
                customer_reply_external_content(content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
