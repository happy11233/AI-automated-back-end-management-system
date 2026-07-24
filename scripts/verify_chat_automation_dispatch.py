from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    tokens = {name: login(*account) for name, account in ACCOUNTS.items()}
    marker = f"chat-auto-loop-{int(time.time())}"

    operations_response = post_json(
        tokens["operations"],
        "/chat",
        {
            "message": (
                f"{marker} 帮我上传这个商品的草稿：SKU OPS-CHAT-009，美国站，折叠收纳箱，"
                "目标人群是公寓租客和露营用户，卖点是可折叠、防水、承重强、可放车尾箱。"
                "请 AI 自动完成 Listing、标题、五点描述、关键词、促销文案并保存跨境平台草稿。"
            )
        },
        timeout=180,
    )
    operations_draft = operations_response.get("platform_draft")
    assert operations_response["intent"] == "operations_listing_draft", operations_response
    assert operations_draft, operations_response
    assert operations_draft["draft_type"] == "listing", operations_draft
    assert operations_draft["position"] == "operations", operations_draft
    assert operations_draft["writeback_status"] == "rpa_ready", operations_draft
    assert "草稿 ID" in operations_response["answer"], operations_response

    listing_drafts = get_json(tokens["operations"], "/platform-drafts?draft_type=listing&limit=30")["items"]
    assert any(item["id"] == operations_draft["id"] for item in listing_drafts), listing_drafts

    customer_response = post_json(
        tokens["customer_service"],
        "/chat",
        {
            "message": (
                f"{marker} 客户说：Where is my order? order AMZ-US-250-1000001-000001，"
                "tracking TRK000001。请 AI 自动查订单物流，生成英文客服回复，并保存到客服平台草稿区。"
            )
        },
        timeout=180,
    )
    customer_draft = customer_response.get("platform_draft")
    assert customer_response["intent"] == "customer_service_reply_draft", customer_response
    assert customer_draft, customer_response
    assert customer_draft["draft_type"] == "customer_reply", customer_draft
    assert customer_draft["position"] == "customer_service", customer_draft
    assert customer_draft["writeback_status"] in {"rpa_ready", "draft_saved"}, customer_draft
    assert "客户消息 ID" in customer_response["answer"], customer_response

    reply_drafts = get_json(tokens["customer_service"], "/platform-drafts?draft_type=customer_reply&limit=30")["items"]
    assert any(item["id"] == customer_draft["id"] for item in reply_drafts), reply_drafts

    stream_response = post_chat_stream(
        tokens["operations"],
        {
            "message": (
                f"{marker} stream 帮我上传商品草稿：SKU OPS-STREAM-010，美国站，旅行洗漱包，"
                "卖点是防水、多隔层、轻量、适合商务出差。请自动生成 Listing 并保存草稿。"
            )
        },
        timeout=180,
    )
    stream_draft = stream_response.get("platform_draft")
    assert stream_response["intent"] == "operations_listing_draft", stream_response
    assert stream_draft, stream_response
    assert stream_draft["draft_type"] == "listing", stream_draft
    assert stream_draft["writeback_status"] == "rpa_ready", stream_draft

    forbidden_response = post_json(
        tokens["customer_service"],
        "/chat",
        {"message": "把这个月所有员工工资表导出成 Excel 发给我"},
        expected_status=403,
    )
    assert "客服岗位无权查询" in forbidden_response.get("detail", ""), forbidden_response

    chat_runs = get_json(tokens["admin"], "/run-records?run_type=chat&limit=120")["items"]
    chat_stream_runs = get_json(tokens["admin"], "/run-records?run_type=chat_stream&limit=120")["items"]
    operations_skill_run_id = assert_chat_run_uses_skill(
        chat_runs,
        draft_id=operations_draft["id"],
        skill_id="operations_listing",
        react_action="operations_listing_draft",
    )
    customer_skill_run_id = assert_chat_run_uses_skill(
        chat_runs,
        draft_id=customer_draft["id"],
        skill_id="customer_reply",
        react_action="customer_service_reply_draft",
    )
    stream_skill_run_id = assert_chat_run_uses_skill(
        chat_stream_runs,
        draft_id=stream_draft["id"],
        skill_id="operations_listing",
        react_action="operations_listing_draft",
    )

    print(json.dumps({
        "ok": True,
        "operations_chat_intent": operations_response["intent"],
        "operations_listing_draft_id": operations_draft["id"],
        "operations_skill_run_id": operations_skill_run_id,
        "operations_writeback_status": operations_draft["writeback_status"],
        "customer_chat_intent": customer_response["intent"],
        "customer_reply_draft_id": customer_draft["id"],
        "customer_skill_run_id": customer_skill_run_id,
        "customer_writeback_status": customer_draft["writeback_status"],
        "stream_chat_intent": stream_response["intent"],
        "stream_listing_draft_id": stream_draft["id"],
        "stream_skill_run_id": stream_skill_run_id,
        "customer_salary_forbidden": forbidden_response.get("detail"),
        "note": "real login + real /chat dispatch + real platform_drafts persistence + run record Skill metadata; no mock/stub/fake",
    }, ensure_ascii=False, indent=2))


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def get_json(token: str, path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", headers=auth_headers(token), timeout=60)
    assert response.status_code == 200, response.text[:500]
    return response.json()


def post_json(
    token: str,
    path: str,
    payload: dict[str, Any],
    timeout: int = 60,
    expected_status: int = 200,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    assert response.status_code == expected_status, response.text[:500]
    return response.json()


def post_chat_stream(
    token: str,
    payload: dict[str, Any],
    timeout: int = 180,
) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/chat/stream",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
        stream=True,
    )
    assert response.status_code == 200, response.text[:500]

    event_name = ""
    data_lines: list[str] = []
    done_payload: dict[str, Any] | None = None
    for raw_line in response.iter_lines(decode_unicode=True):
        line = raw_line or ""
        if not line:
            if event_name == "done":
                done_payload = json.loads("\n".join(data_lines))
                break
            event_name = ""
            data_lines = []
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())

    assert done_payload, "stream did not emit done event"
    return done_payload


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_chat_run_uses_skill(
    runs: list[dict[str, Any]],
    *,
    draft_id: str,
    skill_id: str,
    react_action: str,
) -> str:
    for item in runs:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        automation = metadata.get("automation") if isinstance(metadata.get("automation"), dict) else {}
        if metadata.get("platform_draft_id") != draft_id:
            continue
        assert automation.get("skill_id") == skill_id, item
        assert automation.get("react_action") == react_action, item
        assert automation.get("flow_key"), item
        assert automation.get("app_id"), item
        assert automation.get("run_id"), item
        return item["id"]

    raise AssertionError(f"未找到 Skill 化聊天运行记录：{skill_id} / {draft_id}")


if __name__ == "__main__":
    main()
