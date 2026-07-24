from argparse import ArgumentParser
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import http.client
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8001"
PROFILES = ("quick", "api", "release")
ALL_PROFILES = frozenset(PROFILES)
API_RELEASE_PROFILES = frozenset({"api", "release"})
QUICK_RELEASE_PROFILES = frozenset({"quick", "release"})
RELEASE_ONLY_PROFILE = frozenset({"release"})
WORKSPACE_NODE_MODULES = Path(
    "/Users/xiaoxiang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
)


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Step:
    label: str
    profiles: frozenset[str]
    action: Callable[[], None]


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    api_base_url = os.getenv("VERIFY_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
    python_bin = _python_bin()
    steps = [step for step in _build_steps(api_base_url, python_bin) if args.profile in step.profiles]

    if args.list:
        print(f"验证 profile：{args.profile}")
        for index, step in enumerate(steps, start=1):
            print(f"{index}. {step.label}")
        return

    print(f"验证 profile：{args.profile}（{len(steps)} 步）", flush=True)
    started_at = time.monotonic()

    for index, step in enumerate(steps, start=1):
        print(f"\n[{index}/{len(steps)}] {step.label}", flush=True)
        step_started_at = time.monotonic()
        try:
            step.action()
        except Exception as error:
            raise SystemExit(f"\n验证失败：{step.label}\n原因：{error}") from error
        print(f"通过：{step.label}（{time.monotonic() - step_started_at:.1f}s）", flush=True)

    print(f"\n全部验证通过（总耗时 {time.monotonic() - started_at:.1f}s）", flush=True)


def _parse_args(argv: Sequence[str] | None):
    parser = ArgumentParser(description="Company RAG Agent 分层验证入口")
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="release",
        help="quick=CI 快检；api=真实 API/数据库回归；release=发布前全量真实闸门（默认）",
    )
    parser.add_argument("--list", action="store_true", help="只列出当前 profile 会执行的步骤")
    return parser.parse_args(argv)


def _build_steps(api_base_url: str, python_bin: Path) -> list[Step]:
    return [
        Step(
            "后端 Python 语法编译",
            ALL_PROFILES,
            lambda: _run([str(python_bin), "-m", "compileall", "app", "scripts"]),
        ),
        Step(
            "数据库迁移静态检查",
            ALL_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_sql_migrations.py", "--mode", "static"]),
        ),
        Step(
            "Skill Registry 静态检查",
            ALL_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_skill_registry.py"]),
        ),
        Step(
            "数据库迁移真实 PostgreSQL 回放",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_sql_migrations.py", "--mode", "runtime"]),
        ),
        Step("API 健康检查", API_RELEASE_PROFILES, lambda: _check_api_health(api_base_url)),
        Step("ERP 管理员诊断", API_RELEASE_PROFILES, lambda: _check_erp_diagnostics(api_base_url)),
        Step(
            "ERP 对话权限回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_erp_chat.py"]),
        ),
        Step(
            "聊天 ReAct 守卫回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_chat_react_guardrails.py"]),
        ),
        Step(
            "岗位越权权限回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_position_permissions.py"]),
        ),
        Step(
            "管理员用户生命周期回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_admin_user_lifecycle.py"]),
        ),
        Step(
            "发布前稳定化回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_release_ready.py"]),
        ),
        Step(
            "AI 工作流真实执行回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_ai_workflows.py"]),
        ),
        Step(
            "客服自动化闭环回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_customer_service_automation.py"]),
        ),
        Step(
            "客服退款审批回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_customer_service_refund_approvals.py"]),
        ),
        Step(
            "业务闭环 owner 隔离回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_business_action_owner_isolation.py"]),
        ),
        Step(
            "平台草稿自动化回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_platform_draft_automation.py"]),
        ),
        Step(
            "自动化流程版本治理回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_automation_flow_versions.py"]),
        ),
        Step(
            "自动化运行记录版本引用回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_automation_run_flow_references.py"]),
        ),
        Step(
            "RAG 岗位 scope 隔离回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_rag_position_scope.py"]),
        ),
        Step(
            "RAG 站点店铺 scope 隔离回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_rag_business_scope.py"]),
        ),
        Step(
            "RAG 字段敏感级别 scope 隔离回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_rag_field_sensitivity_scope.py"]),
        ),
        Step(
            "RAG 用户团队授权隔离回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_rag_user_team_authorization.py"]),
        ),
        Step(
            "RAG 授权管理 API 与审计回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_rag_authorization_admin_api.py"]),
        ),
        Step(
            "RAG 授权命中拒绝审计回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_rag_authorization_audit.py"]),
        ),
        Step(
            "客服自动化收件箱前端回归",
            RELEASE_ONLY_PROFILE,
            lambda: _run_node(["node", "scripts/verify_customer_service_inbox_frontend.mjs"]),
        ),
        Step(
            "财务 Excel 生成回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_finance_excel_transform.py"]),
        ),
        Step(
            "财务工资导出回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_finance_salary_export.py"]),
        ),
        Step(
            "财务对账自动化回归",
            API_RELEASE_PROFILES,
            lambda: _run([str(python_bin), "scripts/verify_finance_reconciliation.py"]),
        ),
        Step("前端构建", QUICK_RELEASE_PROFILES, lambda: _run(["npm", "run", "build"], cwd=FRONTEND_DIR)),
        Step("前端权限可见性回归", RELEASE_ONLY_PROFILE, lambda: _check_frontend_permissions()),
        Step(
            "RAG 授权管理前端回归",
            RELEASE_ONLY_PROFILE,
            lambda: _run_node(["node", "scripts/verify_rag_authorization_frontend.mjs"]),
        ),
    ]


def _python_bin() -> Path:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python

    return Path(sys.executable)


def _run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd or ROOT_DIR, check=True)


def _run_node(command: list[str], cwd: Path | None = None) -> None:
    env = os.environ.copy()
    if WORKSPACE_NODE_MODULES.exists():
        env["NODE_PATH"] = str(WORKSPACE_NODE_MODULES)

    subprocess.run(command, cwd=cwd or ROOT_DIR, check=True, env=env)


def _check_frontend_permissions() -> None:
    _run_node(["node", "scripts/verify_frontend_permissions.mjs"])


def _check_api_health(api_base_url: str) -> None:
    last_error: Exception | None = None
    for _ in range(10):
        try:
            payload = _request_json(f"{api_base_url}/health", method="GET", timeout=8)
            break
        except (VerificationError, ConnectionResetError, http.client.RemoteDisconnected) as error:
            last_error = error
            time.sleep(1)
    else:
        raise VerificationError(f"API 健康检查失败：{last_error}") from last_error

    if payload.get("status") != "ok":
        raise VerificationError(f"/health 返回异常：{payload}")


def _check_erp_diagnostics(api_base_url: str) -> None:
    token = _login_admin(api_base_url)
    payload = _request_json(
        f"{api_base_url}/erp/diagnostics",
        method="GET",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )

    active_health = payload.get("active_health") or {}
    status = active_health.get("status")
    ok = bool(active_health.get("ok"))

    if not ok or status != "ok":
        message = active_health.get("message") or "未知 ERP 诊断错误"
        raise VerificationError(f"ERP 诊断未通过：status={status}, message={message}")

    detail = active_health.get("detail")
    if isinstance(detail, dict):
        logged_user = detail.get("user") or detail.get("message") or "unknown"
    else:
        logged_user = detail or "unknown"
    print(
        json.dumps(
            {
                "active_provider": payload.get("active_provider"),
                "status": status,
                "logged_user": logged_user,
            },
            ensure_ascii=False,
        )
    )


def _login_admin(api_base_url: str) -> str:
    username = os.getenv("VERIFY_ADMIN_USERNAME", "admin_demo")
    password = os.getenv("VERIFY_ADMIN_PASSWORD", "Admin123456")
    body = urlencode({"username": username, "password": password}).encode()
    payload = _request_json(
        f"{api_base_url}/auth/login",
        method="POST",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    token = payload.get("access_token")
    if not token:
        raise VerificationError("管理员登录成功响应中没有 access_token")

    return str(token)


def _request_json(
    url: str,
    *,
    method: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int,
) -> dict:
    request = Request(url, data=body, headers=headers or {}, method=method)

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise VerificationError(f"{url} 返回 HTTP {error.code}: {_preview(raw)}") from error
    except URLError as error:
        raise VerificationError(f"{url} 无法连接：{error.reason}") from error
    except TimeoutError as error:
        raise VerificationError(f"{url} 请求超时") from error

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise VerificationError(f"{url} 返回不是 JSON：{_preview(raw)}") from error

    if not isinstance(payload, dict):
        raise VerificationError(f"{url} 返回 JSON 不是对象：{payload!r}")

    return payload


def _preview(value: str, length: int = 300) -> str:
    return " ".join(value.split())[:length]


if __name__ == "__main__":
    main()
