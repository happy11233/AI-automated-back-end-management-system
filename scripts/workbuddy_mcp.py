"""WorkBuddy MCP bridge to the authenticated project API, using stdlib only."""

from __future__ import annotations

import base64
import http.client
import json
import os
import subprocess
import sys
import time
from urllib.parse import urlencode, urlsplit

API_URL = os.environ.get("COMPANY_RAG_MCP_API_URL", "http://127.0.0.1:8001").rstrip("/")
USERNAME = os.environ.get("COMPANY_RAG_MCP_USERNAME", "").strip()
TOKEN = ""
TOKEN_EXPIRY = 0.0


def api_url():
    url = urlsplit(API_URL)
    if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
        raise ValueError("API URL 只能包含协议、主机和端口")
    if url.scheme == "https" and url.hostname:
        return url
    if url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}:
        return url
    raise ValueError("API URL 必须为 HTTPS 或本机 HTTP 回环地址")


def password():
    if not USERNAME:
        raise RuntimeError("请先在 .workbuddy/mcp.json 配置 COMPANY_RAG_MCP_USERNAME")
    try:
        found = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", "company-rag-workbuddy", "-a", USERNAME, "-w"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("无法读取 macOS 钥匙串") from exc
    if found.returncode or not found.stdout.strip():
        raise RuntimeError("钥匙串中没有该项目账号密码；请按照 WORKBUDDY_MCP.md 添加")
    return found.stdout.rstrip("\n")


def request(method, path, *, params=None, data=None, token="", timeout=15):
    url = api_url()
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("请求路径无效")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None
    if data is not None:
        if path == "/auth/login":
            body = urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
    connection = (http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection)(
        url.hostname, url.port, timeout=timeout
    )
    try:
        connection.request(method, path + ("?" + urlencode(params) if params else ""), body=body, headers=headers)
        response = connection.getresponse()
        status, raw = response.status, response.read(4_000_001)
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        raise RuntimeError("项目 API 连接失败：" + type(exc).__name__) from exc
    finally:
        connection.close()
    if len(raw) > 4_000_000:
        raise RuntimeError("项目 API 响应过大")
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError("项目 API 返回非 JSON 响应") from exc
    if not 200 <= status < 300:
        detail = str(payload.get("detail", ""))[:250] if isinstance(payload, dict) and status < 500 else ""
        raise RuntimeError("项目 API HTTP " + str(status) + ("：" + detail if detail else ""))
    if not isinstance(payload, dict):
        raise RuntimeError("项目 API 响应格式错误")
    return payload


def auth_request(method, path, **kwargs):
    global TOKEN, TOKEN_EXPIRY
    if not TOKEN or time.time() >= TOKEN_EXPIRY - 60:
        login = request("POST", "/auth/login", data={"username": USERNAME, "password": password()})
        TOKEN = login.get("access_token", "")
        if not TOKEN:
            raise RuntimeError("项目登录响应缺少 access_token")
        try:
            part = TOKEN.split(".")[1]
            TOKEN_EXPIRY = float(json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))).get("exp", 0))
        except (IndexError, ValueError, TypeError):
            TOKEN_EXPIRY = 0
    # Do not retry a POST if the response times out: it may have succeeded.
    return request(method, path, token=TOKEN, **kwargs)


def safe_id(value):
    if not isinstance(value, str) or not value or not all(
        char.isascii() and (char.isalnum() or char in "_-") for char in value
    ):
        raise ValueError("标识只能包含英文字母、数字、下划线或连字符")
    return value


def project_health():
    """Check API liveness and dependency readiness without login."""
    result = {"api_url": API_URL, "username_configured": bool(USERNAME)}
    for name, path in (("health", "/health"), ("ready", "/ready")):
        try:
            result[name] = {"ok": True, **request("GET", path, timeout=5)}
        except RuntimeError as exc:
            result[name] = {"ok": False, "error": str(exc)}
    return result


def list_ai_workflows():
    """List workflows visible to the current project's user."""
    data = auth_request("GET", "/ai-workflows")
    keys = ("id", "name", "position_label", "scenario", "input_placeholder", "executable",
            "requires_approval", "approval_policy", "entry_label", "entry_view")
    items = []
    for workflow in data.get("items", []):
        item = {key: workflow.get(key) for key in keys}
        item["workbuddy_can_run"] = bool(workflow.get("executable") and not workflow.get("requires_approval"))
        items.append(item)
    return {"items": items}


def get_ai_workflow(workflow_id):
    """Get a workflow's inputs, entry point and approval policy."""
    return auth_request("GET", "/ai-workflows/" + safe_id(workflow_id))


def run_ai_workflow(workflow_id, input_text):
    """Run only a permitted workflow explicitly requested by the user."""
    workflow_id = safe_id(workflow_id)
    item = get_ai_workflow(workflow_id)["item"]
    if not item.get("executable"):
        raise ValueError("请使用该工作流专用页面：" + str(item.get("entry_label", "")))
    if item.get("requires_approval"):
        raise ValueError("此工作流需要审批，不能由 WorkBuddy MCP 直接运行")
    if not isinstance(input_text, str) or not input_text.strip() or len(input_text) > 10000:
        raise ValueError("任务内容必须为 1–10000 字符")
    return auth_request("POST", "/ai-workflows/" + workflow_id + "/run",
                        data={"input_text": input_text}, timeout=120)


def workflow_activity(workflow_id="", status=""):
    """Read recent activity scoped by backend user access."""
    if status and status not in {"running", "succeeded", "failed", "blocked"}:
        raise ValueError("status 参数无效")
    params = {}
    if workflow_id:
        params["workflow_id"] = safe_id(workflow_id)
    if status:
        params["status"] = status
    return auth_request("GET", "/ai-workflows/activity", params=params)


def list_agent_tasks(workflow_id="", limit=20):
    """Read task registrations accessible to the current user."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit 必须为 1–100 的整数")
    params = {"limit": limit}
    if workflow_id:
        params["workflow_id"] = safe_id(workflow_id)
    return auth_request("GET", "/agent-tasks", params=params)


def get_agent_task(task_id):
    """Read a task registration accessible to the current user."""
    return auth_request("GET", "/agent-tasks/" + safe_id(task_id))


TOOLS = {
    "project_health": (project_health, {}, "检查项目 API 存活及依赖就绪，无需登录"),
    "list_ai_workflows": (list_ai_workflows, {}, "列出当前账号可见的 AI 工作流及可执行标记"),
    "get_ai_workflow": (get_ai_workflow, {"workflow_id": "string"}, "查看工作流详情、输入和审批策略"),
    "run_ai_workflow": (run_ai_workflow, {"workflow_id": "string", "input_text": "string"},
                        "仅在用户明确要求时运行获授权且无需审批的工作流；会产生运行记录"),
    "workflow_activity": (workflow_activity, {"workflow_id": "string?", "status": "string?"},
                          "查看账号有权访问的近期工作流执行状态"),
    "list_agent_tasks": (list_agent_tasks, {"workflow_id": "string?", "limit": "integer?"},
                         "只读列出账号可见的任务登记"),
    "get_agent_task": (get_agent_task, {"task_id": "string"}, "只读查看账号可见的任务详情"),
}


def tools_list():
    result = []
    for name, (_, arguments, description) in TOOLS.items():
        properties = {}
        required = []
        for key, kind in arguments.items():
            optional = kind.endswith("?")
            properties[key] = {"type": kind.rstrip("?")}
            if key == "input_text":
                properties[key].update(minLength=1, maxLength=10000)
            if not optional:
                required.append(key)
        result.append({"name": name, "description": description,
                       "inputSchema": {"type": "object", "properties": properties,
                                       "required": required, "additionalProperties": False}})
    return result


def reply(identifier, result=None, error=None):
    output = {"jsonrpc": "2.0", "id": identifier}
    output["error" if error is not None else "result"] = error if error is not None else result
    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False, separators=(",", ":")).encode() + b"\n")
    sys.stdout.buffer.flush()


def main():
    for line in sys.stdin.buffer:
        message = None
        try:
            message = json.loads(line)
            if not isinstance(message, dict) or message.get("id") is None:
                continue
            identifier, method = message["id"], message.get("method")
            if method == "initialize":
                version = message.get("params", {}).get("protocolVersion", "2024-11-05")
                reply(identifier, {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                                   "serverInfo": {"name": "company-rag-agent", "version": "1.0.0"},
                                   "instructions": "先查看流程；只在用户明确要求时执行。审批及专用页面流程不提供执行入口。"})
            elif method == "ping":
                reply(identifier, {})
            elif method == "tools/list":
                reply(identifier, {"tools": tools_list()})
            elif method == "tools/call":
                params = message.get("params") or {}
                entry = TOOLS.get(params.get("name")) if isinstance(params, dict) else None
                if entry is None:
                    raise ValueError("未知 MCP 工具")
                function, schema, _ = entry
                arguments = params.get("arguments") or {}
                if not isinstance(arguments, dict) or any(key not in schema for key in arguments):
                    raise ValueError("工具参数无效")
                for key, kind in schema.items():
                    if not kind.endswith("?") and key not in arguments:
                        raise ValueError("缺少参数：" + key)
                output = function(**arguments)
                reply(identifier, {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False)}],
                                   "isError": False})
            else:
                reply(identifier, error={"code": -32601, "message": "Unknown method"})
        except Exception as exc:
            if isinstance(message, dict) and message.get("id") is not None:
                reply(message["id"], {"content": [{"type": "text", "text": str(exc)}], "isError": True})


if __name__ == "__main__":
    main()
