"""No-login protocol smoke check for the WorkBuddy MCP project config."""

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = json.loads((ROOT / ".workbuddy/mcp.json").read_text())["mcpServers"]["company-rag-agent"]


def exchange(proc, identifier, method, params=None):
    request = {"jsonrpc": "2.0", "id": identifier, "method": method}
    if params is not None:
        request["params"] = params
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    response = json.loads(proc.stdout.readline())
    assert response["id"] == identifier and "result" in response, response
    return response["result"]


def main():
    env = {**os.environ, **SERVER.get("env", {})}
    with subprocess.Popen([SERVER["command"], *SERVER["args"]], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, text=True, env=env) as proc:
        try:
            init = exchange(proc, 1, "initialize", {"protocolVersion": "2024-11-05",
                                                    "capabilities": {}, "clientInfo": {"name": "smoke-check", "version": "1"}})
            tools = exchange(proc, 2, "tools/list")
            health = exchange(proc, 3, "tools/call", {"name": "project_health", "arguments": {}})
            print("server:", init["serverInfo"]["name"])
            print("tools:", [tool["name"] for tool in tools["tools"]])
            print("health:", health["content"][0]["text"])
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)


if __name__ == "__main__":
    main()
