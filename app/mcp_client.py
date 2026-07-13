import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MCP_SERVERS = {
    "document_system": "app.mcp_servers.document_system",
    "ticket_system": "app.mcp_servers.ticket_system",
}


def call_mcp_tool(server_name: str, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
    return asyncio.run(call_mcp_tool_async(server_name, tool_name, arguments or {}))


async def call_mcp_tool_async(server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
    module_name = MCP_SERVERS.get(server_name)

    if module_name is None:
        raise ValueError(f"未知 MCP Server：{server_name}")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", module_name],
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return _extract_tool_result(result)


def _extract_tool_result(result: Any) -> Any:
    if getattr(result, "isError", False):
        raise RuntimeError(_content_to_text(result.content))

    structured_content = getattr(result, "structuredContent", None)
    if structured_content is not None:
        return _unwrap_structured_content(structured_content)

    content = getattr(result, "content", [])

    if len(content) == 1:
        item = content[0]

        if hasattr(item, "text"):
            return _parse_text_content(item.text)

    return [
        item.text if hasattr(item, "text") else str(item)
        for item in content
    ]


def _content_to_text(content: list[Any]) -> str:
    return "\n".join(
        item.text if hasattr(item, "text") else str(item)
        for item in content
    )


def _unwrap_structured_content(value: Any) -> Any:
    if isinstance(value, dict) and set(value.keys()) == {"result"}:
        return value["result"]

    return value


def _parse_text_content(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
