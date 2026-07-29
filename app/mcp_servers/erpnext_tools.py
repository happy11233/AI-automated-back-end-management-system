from typing import Any

from mcp.server.fastmcp import FastMCP

from app.erp.providers import get_active_provider
from app.erp.resources import provider_fields_for, provider_resource_for


mcp = FastMCP(
    "company-erpnext-tools",
    instructions="受控 ERPNext 工具。业务权限必须由后端 Skill Executor 在调用 MCP 前完成。",
)


@mcp.tool()
def health_check() -> dict[str, Any]:
    """检查当前 ERP Provider 是否已配置并可用。"""
    provider = get_active_provider()
    return provider.health_check()


@mcp.tool()
def query_salary_slips(
    start_date: str,
    end_date: str,
    limit: int = 80,
) -> dict[str, Any]:
    """按工资期间只读查询 Salary Slip。调用前必须确认财务岗位权限。"""
    provider = get_active_provider()
    provider_resource = provider_resource_for("Salary Slip", provider.provider_id)
    if provider_resource is None:
        return {
            "ok": False,
            "status": "not_supported",
            "message": f"{provider.provider_label} 暂未映射 Salary Slip。",
            "items": [],
        }

    bounded_limit = max(1, min(int(limit or 80), 200))
    filters = [
        ["start_date", ">=", start_date],
        ["end_date", "<=", end_date],
    ]
    return provider.query_resource(
        resource="Salary Slip",
        provider_resource=provider_resource,
        query=None,
        filters=filters,
        fields=provider_fields_for("Salary Slip", provider.provider_id),
        limit=bounded_limit,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
