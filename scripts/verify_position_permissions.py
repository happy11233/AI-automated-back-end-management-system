import json
import os
import time
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openpyxl import Workbook


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

    cases = [
        {
            "label": "operations_cannot_use_customer_service_task",
            "fn": lambda: _request_json(
                "/automation/generate",
                token=tokens["operations"],
                method="POST",
                payload={
                    "task_id": "refund_script",
                    "input_text": "客户要求退款，请生成售后话术。",
                },
            ),
            "status": 403,
            "contains": ["无权使用该自动化任务"],
        },
        {
            "label": "customer_service_cannot_use_finance_task",
            "fn": lambda: _request_json(
                "/automation/generate",
                token=tokens["customer_service"],
                method="POST",
                payload={
                    "task_id": "salary_summary",
                    "input_text": "统计本月工资。",
                },
            ),
            "status": 403,
            "contains": ["无权使用该自动化任务"],
        },
        {
            "label": "finance_cannot_use_operations_task",
            "fn": lambda: _request_json(
                "/automation/generate",
                token=tokens["finance"],
                method="POST",
                payload={
                    "task_id": "listing",
                    "input_text": "为新品生成 Listing。",
                },
            ),
            "status": 403,
            "contains": ["无权使用该自动化任务"],
        },
        {
            "label": "customer_service_cannot_query_gl_entry",
            "fn": lambda: _request_json(
                "/erp/query",
                token=tokens["customer_service"],
                method="POST",
                payload={"resource": "GL Entry", "query": "Amazon", "limit": 1},
            ),
            "status": 403,
            "contains": ["客服岗位无权查询 ERP 资源"],
        },
        {
            "label": "operations_cannot_query_salary_slip",
            "fn": lambda: _request_json(
                "/erp/query",
                token=tokens["operations"],
                method="POST",
                payload={"resource": "Salary Slip", "query": "2026", "limit": 1},
            ),
            "status": 403,
            "contains": ["运营岗位无权查询 ERP 资源"],
        },
        {
            "label": "finance_cannot_query_customer_issue",
            "fn": lambda: _request_json(
                "/erp/query",
                token=tokens["finance"],
                method="POST",
                payload={"resource": "Issue", "query": "退款", "limit": 1},
            ),
            "status": 403,
            "contains": ["财务岗位无权查询 ERP 资源"],
        },
        {
            "label": "customer_service_cannot_chat_finance_report",
            "fn": lambda: _request_json(
                "/chat",
                token=tokens["customer_service"],
                method="POST",
                payload={"message": "帮我查看一下本月财务报表和利润"},
            ),
            "status": 403,
            "contains": ["客服岗位无权查询"],
        },
        {
            "label": "operations_cannot_chat_salary",
            "fn": lambda: _request_json(
                "/chat",
                token=tokens["operations"],
                method="POST",
                payload={"message": "帮我查一下员工工资和薪资明细"},
            ),
            "status": 403,
            "contains": ["运营岗位无权查询"],
        },
        {
            "label": "finance_cannot_chat_private_service_conversation",
            "fn": lambda: _request_json(
                "/chat",
                token=tokens["finance"],
                method="POST",
                payload={"message": "帮我查看客服私有会话和售后私聊"},
            ),
            "status": 403,
            "contains": ["财务岗位无权查询"],
        },
        {
            "label": "customer_service_cannot_transform_finance_excel",
            "fn": lambda: _request_bytes(
                "/automation/finance/excel-transform",
                token=tokens["customer_service"],
                method="POST",
                body=_build_excel_multipart_body(),
                headers={
                    "Content-Type": f"multipart/form-data; boundary={_excel_boundary()}",
                },
            ),
            "status": 403,
            "contains": ["只有财务岗位或管理员可以使用财务 Excel 生成功能"],
        },
        {
            "label": "customer_service_cannot_run_finance_reconciliation",
            "fn": lambda: _request_bytes(
                "/automation/finance/reconciliation",
                token=tokens["customer_service"],
                method="POST",
                body=_build_reconciliation_multipart_body(),
                headers={
                    "Content-Type": f"multipart/form-data; boundary={_reconciliation_boundary()}",
                },
            ),
            "status": 403,
            "contains": ["只有财务岗位或管理员可以使用财务对账自动化"],
        },
        {
            "label": "employee_cannot_access_admin_users",
            "fn": lambda: _request_json(
                "/admin/users",
                token=tokens["customer_service"],
                method="GET",
            ),
            "status": 403,
            "contains": ["需要管理员权限"],
        },
        {
            "label": "employee_cannot_access_erp_diagnostics",
            "fn": lambda: _request_json(
                "/erp/diagnostics",
                token=tokens["operations"],
                method="GET",
            ),
            "status": 403,
            "contains": ["需要管理员权限"],
        },
        {
            "label": "operations_dashboard_overview_only_operations_resources",
            "fn": lambda: _request_json(
                "/erp/dashboard-overview?market=all&date_range=all&store=all",
                token=tokens["operations"],
                method="GET",
            ),
            "status": 200,
            "contains": ["运营数据概览", "全部站点", "全部店铺", "全部时间", "Sales Order", "Item", "Item Price", "total_count", "amount_total"],
            "not_contains": ["Salary Slip", "Issue", "GL Entry"],
        },
        {
            "label": "operations_dashboard_overview_market_filter",
            "fn": lambda: _request_json(
                "/erp/dashboard-overview?market=de&date_range=30d&store=de_store",
                token=tokens["operations"],
                method="GET",
            ),
            "status": 200,
            "contains": ["德国站", "DE Store", "近 30 天", "AMZ-DE", "Sales Order", "total_count"],
            "not_contains": ["AMZ-US-112", "Salary Slip", "Issue", "GL Entry"],
        },
        {
            "label": "customer_service_dashboard_overview_only_service_resources",
            "fn": lambda: _request_json(
                "/erp/dashboard-overview?market=us&date_range=7d&store=us_store",
                token=tokens["customer_service"],
                method="GET",
            ),
            "status": 200,
            "contains": ["客服数据概览", "美国站", "US Store", "近 7 天", "Delivery Note", "Issue", "Customer", "total_count"],
            "not_contains": ["GL Entry", "Sales Invoice", "Salary Slip"],
        },
        {
            "label": "finance_dashboard_overview_only_finance_resources",
            "fn": lambda: _request_json(
                "/erp/dashboard-overview?market=jp&date_range=today&store=jp_store",
                token=tokens["finance"],
                method="GET",
            ),
            "status": 200,
            "contains": ["财务数据概览", "日本站", "JP Store", "今天", "Sales Invoice", "Payment Entry", "GL Entry", "total_count", "发票金额"],
            "not_contains": ["Issue", "Delivery Note", "Customer"],
        },
        {
            "label": "customer_service_can_open_delivery_detail",
            "fn": lambda: _request_json(
                "/erp/records/Delivery%20Note/DHL-DE-AMZ-2026071502",
                token=tokens["customer_service"],
                method="GET",
            ),
            "status": 200,
            "contains": ["物流/出库单", "DHL-DE-AMZ-2026071502", "item"],
        },
        {
            "label": "customer_service_cannot_open_finance_detail",
            "fn": lambda: _request_json(
                "/erp/records/GL%20Entry/AMZ-JP-250-6630188-4402197",
                token=tokens["customer_service"],
                method="GET",
            ),
            "status": 403,
            "contains": ["客服岗位无权查询 ERP 资源"],
        },
        {
            "label": "admin_can_list_all_automation_tasks",
            "fn": lambda: _request_json(
                "/automation/tasks",
                token=tokens["admin"],
                method="GET",
            ),
            "status": 200,
            "contains": ["listing", "refund_script", "salary_summary"],
        },
    ]

    failures = []
    for case in cases:
        status, payload = case["fn"]()
        body = _payload_to_text(payload)
        ok = status == case["status"] and all(
            expected in body for expected in case["contains"]
        ) and all(
            unexpected not in body for unexpected in case.get("not_contains", [])
        )

        print(
            json.dumps(
                {
                    "label": case["label"],
                    "ok": ok,
                    "status": status,
                    "preview": body[:180],
                },
                ensure_ascii=False,
            )
        )

        if not ok:
            failures.append(case["label"])

    if failures:
        raise SystemExit(
            f"Position permission verification failed: {', '.join(failures)}"
        )


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


def _request_bytes(
    path: str,
    *,
    method: str,
    token: str,
    body: bytes,
    headers: dict[str, str],
    timeout: int = 30,
) -> tuple[int, bytes | dict]:
    request_headers = dict(headers)
    request_headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"detail": raw}


def _payload_to_text(payload: bytes | dict) -> str:
    if isinstance(payload, bytes):
        return payload[:300].decode("utf-8", errors="replace")

    return json.dumps(payload, ensure_ascii=False)


def _excel_boundary() -> str:
    return "----codex-position-permission-excel"


def _build_excel_multipart_body() -> bytes:
    boundary = _excel_boundary()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "工资测试"
    sheet.append(["员工", "工资"])
    sheet.append(["Alice", 10000])

    output = BytesIO()
    workbook.save(output)
    content = output.getvalue()

    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="instruction"\r\n\r\n',
        "统计工资。".encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        (
            'Content-Disposition: form-data; name="file"; '
            'filename="salary.xlsx"\r\n'
        ).encode(),
        b"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n",
        content,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks)


def _reconciliation_boundary() -> str:
    return "----codex-position-permission-reconciliation"


def _build_reconciliation_multipart_body() -> bytes:
    boundary = _reconciliation_boundary()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Amazon结算"
    sheet.append(["订单号", "SKU", "销售额"])
    sheet.append(["AMZ-PERM-001", "SKU-PERM", 100])

    output = BytesIO()
    workbook.save(output)
    content = output.getvalue()

    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="instruction"\r\n\r\n',
        "生成订单利润表。".encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="base_currency"\r\n\r\n',
        b"CNY",
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        (
            'Content-Disposition: form-data; name="files"; '
            'filename="amazon_settlement.xlsx"\r\n'
        ).encode(),
        b"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n",
        content,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks)


if __name__ == "__main__":
    main()
