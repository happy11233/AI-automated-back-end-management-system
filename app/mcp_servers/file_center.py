from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "company-file-center",
    instructions="生成文件中心工具。真实文件权限必须由后端 /files 接口校验。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """返回文件中心工具健康状态。"""
    return {
        "ok": True,
        "status": "healthy",
        "message": "文件中心 MCP 可用；实际下载权限由 /files/{artifact_id}/download 校验。",
    }


@mcp.tool()
def get_generated_file_download_path(artifact_id: str) -> dict[str, Any]:
    """根据文件产物 ID 生成后端下载路径，不直接读取文件内容。"""
    value = str(artifact_id or "").strip()
    if not value:
        return {
            "ok": False,
            "status": "invalid_argument",
            "message": "artifact_id 不能为空。",
        }

    return {
        "ok": True,
        "status": "ready",
        "artifact_id": value,
        "download_path": f"/files/{value}/download",
        "permission_note": "调用方仍需携带用户登录态，后端会校验文件归属和岗位权限。",
    }


@mcp.tool()
def describe_generated_file_policy() -> dict[str, Any]:
    """说明生成文件中心的安全策略，供管理后台展示。"""
    return {
        "ok": True,
        "status": "ready",
        "rules": [
            "MCP 不直接返回文件内容。",
            "下载必须走后端 /files/{artifact_id}/download。",
            "普通用户只能下载自己岗位和自己账号生成的文件。",
            "过期文件会被后端文件中心清理。",
        ],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
