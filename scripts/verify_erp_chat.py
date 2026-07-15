import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.getenv("VERIFY_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


CASES = [
    {
        "label": "operations_sales_order",
        "username": "operations_demo",
        "password": "Operations123456",
        "message": "帮我查一下 Amazon 订单 AMZ-DE-305-7712468-1290045 的销售订单",
        "status": 200,
        "contains": ["销售订单", "AMZ-DE-305-7712468-1290045", "引用 ERP 记录"],
    },
    {
        "label": "service_delivery",
        "username": "employee_demo",
        "password": "Employee123456",
        "message": "帮我查一下 AMZ-DE-305-7712468-1290045 的物流",
        "status": 200,
        "contains": ["物流/出库单", "DHL-DE-AMZ-2026071502", "引用 ERP 记录"],
    },
    {
        "label": "service_issue",
        "username": "employee_demo",
        "password": "Employee123456",
        "message": "帮我查一下 AMZ-US-112-4589012-7783401 的售后工单",
        "status": 200,
        "contains": ["售后工单", "退款咨询", "引用 ERP 记录"],
    },
    {
        "label": "finance_invoice",
        "username": "finance_demo",
        "password": "Finance123456",
        "message": "帮我查一下 AMZ-JP-250-6630188-4402197 的销售发票",
        "status": 200,
        "contains": ["销售发票", "AMZ-JP-250-6630188-4402197", "引用 ERP 记录"],
    },
    {
        "label": "service_forbidden_salary",
        "username": "employee_demo",
        "password": "Employee123456",
        "message": "帮我查一下 AMZ-JP-250-6630188-4402197 的工资单",
        "status": 403,
        "contains": ["客服岗位无权查询"],
    },
]


def main() -> None:
    failures = []

    for case in CASES:
        token = _login(case["username"], case["password"])
        status, payload = _chat(token, case["message"])
        body = json.dumps(payload, ensure_ascii=False)
        ok = status == case["status"] and all(
            expected in body for expected in case["contains"]
        )

        print(
            json.dumps(
                {
                    "label": case["label"],
                    "ok": ok,
                    "status": status,
                    "intent": payload.get("intent"),
                    "answer_preview": (payload.get("answer") or payload.get("detail") or "")[:160],
                },
                ensure_ascii=False,
            )
        )

        if not ok:
            failures.append(case["label"])

    if failures:
        raise SystemExit(f"ERP chat verification failed: {', '.join(failures)}")


def _login(username: str, password: str) -> str:
    body = urlencode({"username": username, "password": password}).encode()
    request = Request(
        f"{BASE_URL}/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def _chat(token: str, message: str) -> tuple[int, dict]:
    request = Request(
        f"{BASE_URL}/chat",
        data=json.dumps({"message": message}, ensure_ascii=False).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


if __name__ == "__main__":
    main()
