from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


API_BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")

ACCOUNTS = {
    "finance": ("finance_demo", "Finance123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
}


def main() -> None:
    wait_for_api()
    tokens = {name: login(*account)["access_token"] for name, account in ACCOUNTS.items()}

    hello = post_json(tokens["finance"], "/chat", {"message": "你好"}, timeout=120)
    assert hello["intent"] == "chitchat", hello
    assert_no_raw_model_error(hello)
    hello_stream = post_sse(tokens["finance"], "/chat/stream", {"message": "你好"}, timeout=120)
    assert hello_stream.get("intent") == "chitchat", hello_stream
    assert_no_raw_model_error(hello_stream)

    denied = post_json(tokens["finance"], "/chat", {"message": "帮我生成listing文案并保存草稿"}, timeout=60)
    assert denied["intent"] == "permission_denied", denied
    assert "财务岗位没有权限" in denied["answer"], denied
    assert "运营岗位" in denied["answer"], denied

    clarification = post_json(tokens["finance"], "/chat", {"message": "导出excel表"}, timeout=60)
    assert clarification["intent"] == "ask_clarification", clarification
    assert "哪一类财务 Excel" in clarification["answer"], clarification

    salary = post_json(
        tokens["finance"],
        "/chat",
        {"message": "把这个月所有员工的工资表导出excel给我"},
        timeout=180,
    )
    assert salary["intent"] == "finance_salary_export", salary
    assert salary["attachments"], salary
    assert salary["attachments"][0]["filename"].endswith(".xlsx"), salary

    operations_thread = post_json(tokens["operations"], "/threads", {}, timeout=30)["item"]
    forbidden = get_json(
        tokens["customer_service"],
        f"/threads/{operations_thread['id']}/messages",
        timeout=30,
        expected_status=403,
    )
    assert "权限" in json.dumps(forbidden, ensure_ascii=False), forbidden

    customer_threads = get_json(tokens["customer_service"], "/threads", timeout=30)["items"]
    assert all(item["id"] != operations_thread["id"] for item in customer_threads), customer_threads[:3]

    print(json.dumps({
        "ok": True,
        "hello_intent": hello["intent"],
        "hello_stream_intent": hello_stream["intent"],
        "denied_answer": denied["answer"],
        "clarification": clarification["answer"],
        "salary_attachment": salary["attachments"][0]["filename"],
        "thread_isolation_checked": operations_thread["id"],
        "note": "real API, real auth, real chat/stream/automation paths; no mock/stub/fake",
    }, ensure_ascii=False, indent=2))


def wait_for_api() -> None:
    for _ in range(30):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"API 不可用：{API_BASE_URL}")


def login(username: str, password: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
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
    if response.status_code != expected_status:
        raise AssertionError(f"{path} expected {expected_status}, got {response.status_code}: {response.text[:1000]}")
    return response.json()


def get_json(token: str, path: str, timeout: int = 60, expected_status: int = 200) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}{path}",
        headers=auth_headers(token),
        timeout=timeout,
    )
    if response.status_code != expected_status:
        raise AssertionError(f"{path} expected {expected_status}, got {response.status_code}: {response.text[:1000]}")
    return response.json()


def post_sse(token: str, path: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
        stream=True,
        timeout=timeout,
    )
    response.raise_for_status()
    done_payload: dict[str, Any] | None = None
    current_event = ""
    current_data = ""
    for raw_line in response.iter_lines(decode_unicode=True):
        line = raw_line or ""
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            current_data = line.split(":", 1)[1].strip()
        elif line == "" and current_event:
            if current_event == "error":
                raise AssertionError(current_data)
            if current_event == "done":
                done_payload = json.loads(current_data)
                break
            current_event = ""
            current_data = ""
    assert done_payload, "stream did not emit done"
    return done_payload


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_no_raw_model_error(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    forbidden = [
        "InternalError.Algo.InvalidParameter",
        "response_format",
        "json_object",
        "Error code: 400",
    ]
    for item in forbidden:
        assert item not in text, payload


if __name__ == "__main__":
    main()
