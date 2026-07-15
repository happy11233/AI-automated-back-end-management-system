import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


ACCOUNTS = {
    "admin": ("admin_demo", "Admin123456"),
    "operations": ("operations_demo", "Operations123456"),
    "customer_service": ("employee_demo", "Employee123456"),
    "finance": ("finance_demo", "Finance123456"),
}


def main() -> None:
    tokens = {
        key: _login(username, password)
        for key, (username, password) in ACCOUNTS.items()
    }

    checks = [
        _check_dashboard_store_and_amount(tokens["operations"]),
        _check_record_detail_permission(tokens["customer_service"]),
        _check_chat_references(tokens["finance"]),
        _check_audit_filters(tokens["admin"]),
    ]
    failures = [item["label"] for item in checks if not item["ok"]]

    for item in checks:
        print(json.dumps(item, ensure_ascii=False))

    if failures:
        raise SystemExit(f"Release readiness verification failed: {', '.join(failures)}")


def _check_dashboard_store_and_amount(token: str) -> dict:
    status, payload = _request_json(
        "/erp/dashboard-overview?market=de&store=de_store&date_range=30d",
        token=token,
        method="GET",
    )
    body = json.dumps(payload, ensure_ascii=False)
    metrics = payload.get("metrics") if isinstance(payload, dict) else []
    has_amount_metric = any(
        isinstance(item, dict)
        and item.get("title") in {"订单金额", "价格合计"}
        and item.get("value") is not None
        for item in metrics
    )
    ok = (
        status == 200
        and payload.get("store") == "de_store"
        and "DE Store" in body
        and "AMZ-DE" in body
        and has_amount_metric
    )
    return {
        "label": "dashboard_store_and_amount",
        "ok": ok,
        "status": status,
        "store": payload.get("store") if isinstance(payload, dict) else None,
        "metric_titles": [item.get("title") for item in metrics if isinstance(item, dict)],
    }


def _check_record_detail_permission(token: str) -> dict:
    ok_status, ok_payload = _request_json(
        "/erp/records/Delivery%20Note/DHL-DE-AMZ-2026071502",
        token=token,
        method="GET",
    )
    forbidden_status, forbidden_payload = _request_json(
        "/erp/records/GL%20Entry/AMZ-JP-250-6630188-4402197",
        token=token,
        method="GET",
    )
    ok = (
        ok_status == 200
        and ok_payload.get("resource") == "Delivery Note"
        and forbidden_status == 403
        and "客服岗位无权查询 ERP 资源" in json.dumps(forbidden_payload, ensure_ascii=False)
    )
    return {
        "label": "record_detail_permission",
        "ok": ok,
        "detail_status": ok_status,
        "forbidden_status": forbidden_status,
    }


def _check_chat_references(token: str) -> dict:
    status, payload = _request_json(
        "/chat",
        token=token,
        method="POST",
        payload={
            "message": "帮我查一下 AMZ-JP-250-6630188-4402197 的销售发票",
            "thread_id": "verify-release-ready-finance",
        },
        timeout=60,
    )
    references = payload.get("erp_references") if isinstance(payload, dict) else []
    answer = payload.get("answer") if isinstance(payload, dict) else ""
    ok = (
        status == 200
        and isinstance(references, list)
        and len(references) > 0
        and "引用 ERP 记录" in str(answer)
    )
    return {
        "label": "chat_references",
        "ok": ok,
        "status": status,
        "reference_count": len(references) if isinstance(references, list) else 0,
    }


def _check_audit_filters(token: str) -> dict:
    status, payload = _request_json(
        "/admin/audit-logs?action=erp&resource_type=erp&position=finance&limit=20",
        token=token,
        method="GET",
    )
    items = payload.get("items") if isinstance(payload, dict) else []
    ok = (
        status == 200
        and isinstance(items, list)
        and all(
            isinstance(item, dict)
            and item.get("resource_type") == "erp"
            and str(item.get("action", "")).startswith("erp")
            and (item.get("metadata") or {}).get("position") == "finance"
            for item in items
        )
    )
    return {
        "label": "audit_filters",
        "ok": ok,
        "status": status,
        "count": len(items) if isinstance(items, list) else 0,
    }


def _login(username: str, password: str) -> str:
    body = urlencode({"username": username, "password": password}).encode()
    status, payload = _request_json(
        "/auth/login",
        method="POST",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if status != 200:
        raise SystemExit(f"登录失败：{username}, status={status}, payload={payload}")

    token = payload.get("access_token")
    if not token:
        raise SystemExit(f"登录响应缺少 access_token：{username}")

    return str(token)


def _request_json(
    path: str,
    *,
    method: str,
    token: str | None = None,
    payload: dict | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> tuple[int, dict]:
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"

    data = body
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        request_headers["Content-Type"] = "application/json"

    request = Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"detail": raw}


if __name__ == "__main__":
    main()
