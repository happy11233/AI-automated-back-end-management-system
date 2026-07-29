from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import asdict, dataclass
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_API_BASE_URL = "http://127.0.0.1:8001"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:5173"
PROJECT_NAME = "AI automated back-end management system"

DEMO_ACCOUNTS = {
    "admin": {
        "label": "管理员",
        "username": "admin_demo",
        "password": "Admin123456",
        "expected_role": "admin",
        "expected_position": None,
    },
    "operations": {
        "label": "运营",
        "username": "operations_demo",
        "password": "Operations123456",
        "expected_role": "employee",
        "expected_position": "operations",
    },
    "customer_service": {
        "label": "客服",
        "username": "employee_demo",
        "password": "Employee123456",
        "expected_role": "employee",
        "expected_position": "customer_service",
    },
    "finance": {
        "label": "财务",
        "username": "finance_demo",
        "password": "Finance123456",
        "expected_role": "employee",
        "expected_position": "finance",
    },
}


@dataclass
class CheckResult:
    label: str
    status: str
    detail: str
    status_code: int | None = None
    duration_ms: int | None = None


class DemoReadinessError(RuntimeError):
    pass


def main() -> None:
    args = parse_args()
    api_base_url = normalize_base_url(args.api_base_url or os.getenv("DEMO_API_BASE_URL") or DEFAULT_API_BASE_URL)
    frontend_url = normalize_base_url(args.frontend_url or os.getenv("DEMO_FRONTEND_URL") or DEFAULT_FRONTEND_URL)

    results: list[CheckResult] = []
    tokens: dict[str, str] = {}

    run_check(results, "API 健康检查", lambda: check_api_health(api_base_url))
    run_check(results, "Swagger 文档", lambda: check_swagger(api_base_url))
    if not args.skip_frontend:
        run_check(results, "前端页面", lambda: check_frontend(frontend_url))

    for account_key, account in DEMO_ACCOUNTS.items():
        run_check(
            results,
            f"{account['label']}账号登录",
            lambda account=account, account_key=account_key: login_account(api_base_url, account, tokens, account_key),
        )
        run_check(
            results,
            f"{account['label']}账号身份",
            lambda account=account, account_key=account_key: check_me(api_base_url, tokens[account_key], account),
        )

    run_check(results, "财务 ERP 状态", lambda: check_erp_status(api_base_url, tokens["finance"]))
    run_check(results, "财务 ERP 资源权限", lambda: check_erp_scopes(api_base_url, tokens["finance"]))
    run_check(results, "财务 AI 工作流列表", lambda: check_ai_workflows(api_base_url, tokens["finance"]))
    run_check(results, "财务生成文件中心", lambda: check_generated_files(api_base_url, tokens["finance"]))
    run_check(results, "管理员运行记录", lambda: check_admin_run_records(api_base_url, tokens["admin"]))

    for account_key in ("operations", "customer_service", "finance"):
        account = DEMO_ACCOUNTS[account_key]
        run_check(
            results,
            f"{account['label']}访问运行记录应被拒绝",
            lambda account_key=account_key, account=account: check_run_records_forbidden(
                api_base_url,
                tokens[account_key],
                account["label"],
            ),
        )

    summary = build_summary(api_base_url, frontend_url, results)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_human_summary(summary)

    if summary["failed"] > 0:
        raise SystemExit(1)


def parse_args():
    parser = ArgumentParser(description=f"{PROJECT_NAME} 公网演示健康检查")
    parser.add_argument("--api-base-url", default="", help="后端 API 地址，例如 http://127.0.0.1:8001")
    parser.add_argument("--frontend-url", default="", help="前端地址，例如 http://127.0.0.1:5173")
    parser.add_argument("--skip-frontend", action="store_true", help="只检查后端，不检查前端页面")
    parser.add_argument("--json", action="store_true", help="输出 JSON，方便接入脚本")
    return parser.parse_args()


def normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def run_check(results: list[CheckResult], label: str, action) -> None:
    started = time.monotonic()
    try:
        result = action()
        result.duration_ms = int((time.monotonic() - started) * 1000)
        results.append(result)
    except DemoReadinessError as error:
        results.append(CheckResult(
            label=label,
            status="fail",
            detail=str(error),
            duration_ms=int((time.monotonic() - started) * 1000),
        ))
    except Exception as error:
        results.append(CheckResult(
            label=label,
            status="fail",
            detail=f"{type(error).__name__}: {error}",
            duration_ms=int((time.monotonic() - started) * 1000),
        ))


def check_api_health(api_base_url: str) -> CheckResult:
    status_code, payload, _ = request_json(f"{api_base_url}/health")
    if status_code != 200:
        raise DemoReadinessError(f"/health 返回 {status_code}")
    if payload.get("status") != "ok":
        raise DemoReadinessError(f"/health 内容异常：{payload}")
    return CheckResult("API 健康检查", "pass", "后端 API 正常", status_code)


def check_swagger(api_base_url: str) -> CheckResult:
    status_code, _, text = request_text(f"{api_base_url}/docs")
    if status_code != 200:
        raise DemoReadinessError(f"/docs 返回 {status_code}")
    if "swagger" not in text.lower() and "openapi" not in text.lower():
        return CheckResult("Swagger 文档", "warn", "接口文档可访问，但页面内容不像 Swagger", status_code)
    return CheckResult("Swagger 文档", "pass", "Swagger 文档可访问", status_code)


def check_frontend(frontend_url: str) -> CheckResult:
    status_code, _, text = request_text(frontend_url)
    if status_code != 200:
        raise DemoReadinessError(f"前端返回 {status_code}")
    lowered = text.lower()
    if "<html" not in lowered:
        return CheckResult("前端页面", "warn", "前端地址可访问，但返回内容不像 HTML", status_code)
    return CheckResult("前端页面", "pass", "前端页面可访问", status_code)


def login_account(api_base_url: str, account: dict[str, Any], tokens: dict[str, str], account_key: str) -> CheckResult:
    body = urlencode({
        "username": account["username"],
        "password": account["password"],
    }).encode("utf-8")
    status_code, payload, _ = request_json(
        f"{api_base_url}/auth/login",
        method="POST",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status_code != 200:
        raise DemoReadinessError(f"登录返回 {status_code}：{payload}")
    token = str(payload.get("access_token") or "")
    if not token:
        raise DemoReadinessError("登录成功但没有 access_token")
    tokens[account_key] = token
    return CheckResult(f"{account['label']}账号登录", "pass", f"{account['username']} 登录成功", status_code)


def check_me(api_base_url: str, token: str, account: dict[str, Any]) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/auth/me",
        headers=auth_headers(token),
    )
    if status_code != 200:
        raise DemoReadinessError(f"/auth/me 返回 {status_code}：{payload}")
    role = payload.get("role")
    position = payload.get("position")
    if role != account["expected_role"]:
        raise DemoReadinessError(f"角色不匹配：期望 {account['expected_role']}，实际 {role}")
    if account["expected_position"] is not None and position != account["expected_position"]:
        raise DemoReadinessError(f"岗位不匹配：期望 {account['expected_position']}，实际 {position}")
    return CheckResult(
        f"{account['label']}账号身份",
        "pass",
        f"role={role}, position={position or 'admin'}",
        status_code,
    )


def check_erp_status(api_base_url: str, token: str) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/erp/status",
        headers=auth_headers(token),
    )
    if status_code != 200:
        raise DemoReadinessError(f"/erp/status 返回 {status_code}：{payload}")
    provider_label = str(payload.get("provider_label") or payload.get("provider") or "ERP")
    status = str(payload.get("status") or "unknown")
    message = str(payload.get("message") or "")
    if not payload.get("ok"):
        return CheckResult(
            "财务 ERP 状态",
            "warn",
            f"{provider_label} 状态为 {status}：{message or '需要检查 ERPNext 配置'}",
            status_code,
        )
    return CheckResult("财务 ERP 状态", "pass", f"{provider_label} 连接正常：{status}", status_code)


def check_erp_scopes(api_base_url: str, token: str) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/erp/scopes",
        headers=auth_headers(token),
    )
    if status_code != 200:
        raise DemoReadinessError(f"/erp/scopes 返回 {status_code}：{payload}")
    resources = payload.get("resources") if isinstance(payload, dict) else []
    if not isinstance(resources, list) or not resources:
        raise DemoReadinessError("财务账号没有可用 ERP 资源")
    labels = [str(item.get("label") or item.get("resource")) for item in resources[:4] if isinstance(item, dict)]
    return CheckResult("财务 ERP 资源权限", "pass", f"可访问 {len(resources)} 类 ERP 资源：{', '.join(labels)}", status_code)


def check_ai_workflows(api_base_url: str, token: str) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/ai-workflows",
        headers=auth_headers(token),
    )
    if status_code != 200:
        raise DemoReadinessError(f"/ai-workflows 返回 {status_code}：{payload}")
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list) or not items:
        raise DemoReadinessError("财务账号没有可用 AI 工作流")
    names = [str(item.get("name") or item.get("id")) for item in items[:4] if isinstance(item, dict)]
    return CheckResult("财务 AI 工作流列表", "pass", f"可见 {len(items)} 个 AI 工作流：{', '.join(names)}", status_code)


def check_generated_files(api_base_url: str, token: str) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/files?limit=5",
        headers=auth_headers(token),
    )
    if status_code != 200:
        raise DemoReadinessError(f"/files 返回 {status_code}：{payload}")
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise DemoReadinessError("/files 返回结构异常")
    if not items:
        return CheckResult("财务生成文件中心", "warn", "文件中心可访问，但当前没有生成文件", status_code)
    return CheckResult("财务生成文件中心", "pass", f"文件中心可访问，已有 {len(items)} 个文件摘要", status_code)


def check_admin_run_records(api_base_url: str, token: str) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/run-records?limit=1",
        headers=auth_headers(token),
    )
    if status_code != 200:
        raise DemoReadinessError(f"管理员 /run-records 返回 {status_code}：{payload}")
    return CheckResult("管理员运行记录", "pass", "管理员可访问运行记录", status_code)


def check_run_records_forbidden(api_base_url: str, token: str, account_label: str) -> CheckResult:
    status_code, payload, _ = request_json(
        f"{api_base_url}/run-records?limit=1",
        headers=auth_headers(token),
        allow_http_error=True,
    )
    if status_code == 403:
        return CheckResult(f"{account_label}访问运行记录应被拒绝", "pass", "员工访问运行记录返回 403，权限闸门正常", status_code)
    raise DemoReadinessError(f"期望 403，实际 {status_code}：{payload}")


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def request_json(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    allow_http_error: bool = False,
) -> tuple[int, dict[str, Any], str]:
    status_code, raw = request_raw(
        url,
        method=method,
        body=body,
        headers=headers,
        allow_http_error=allow_http_error,
    )
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text) if text else {}
    except json.JSONDecodeError:
        payload = {"raw": text[:500]}
    return status_code, payload, text


def request_text(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    allow_http_error: bool = False,
) -> tuple[int, dict[str, Any], str]:
    status_code, raw = request_raw(
        url,
        method=method,
        body=body,
        headers=headers,
        allow_http_error=allow_http_error,
    )
    text = raw.decode("utf-8", errors="replace")
    return status_code, {}, text


def request_raw(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    allow_http_error: bool = False,
) -> tuple[int, bytes]:
    request = Request(
        url,
        data=body,
        method=method,
        headers=headers or {},
    )
    try:
        with urlopen(request, timeout=8) as response:
            return response.status, response.read()
    except HTTPError as error:
        if allow_http_error:
            return error.code, error.read()
        try:
            payload = error.read().decode("utf-8", errors="replace")
        except Exception:
            payload = ""
        raise DemoReadinessError(f"{url} 返回 HTTP {error.code} {payload[:300]}") from error
    except URLError as error:
        raise DemoReadinessError(f"{url} 无法访问：{error.reason}") from error


def build_summary(api_base_url: str, frontend_url: str, results: list[CheckResult]) -> dict[str, Any]:
    passed = sum(1 for item in results if item.status == "pass")
    warned = sum(1 for item in results if item.status == "warn")
    failed = sum(1 for item in results if item.status == "fail")
    return {
        "project": PROJECT_NAME,
        "api_base_url": api_base_url,
        "frontend_url": frontend_url,
        "ok": failed == 0,
        "passed": passed,
        "warned": warned,
        "failed": failed,
        "results": [asdict(item) for item in results],
    }


def print_human_summary(summary: dict[str, Any]) -> None:
    print(f"\n{summary['project']} 演示健康检查")
    print(f"API: {summary['api_base_url']}")
    print(f"前端: {summary['frontend_url']}")
    print(f"结果: {summary['passed']} 通过 / {summary['warned']} 警告 / {summary['failed']} 失败\n")

    icon_map = {
        "pass": "[通过]",
        "warn": "[警告]",
        "fail": "[失败]",
    }
    for item in summary["results"]:
        status = icon_map.get(item["status"], item["status"])
        duration = f"{item['duration_ms']}ms" if item.get("duration_ms") is not None else "-"
        print(f"{status} {item['label']}：{item['detail']}（{duration}）")

    if summary["failed"]:
        print("\n存在失败项，建议先修复后再公网演示。", file=sys.stderr)
    elif summary["warned"]:
        print("\n存在警告项，可以演示，但建议确认 ERPNext 或演示数据是否符合预期。")
    else:
        print("\n全部关键链路正常，可以进行面试演示。")


if __name__ == "__main__":
    main()
