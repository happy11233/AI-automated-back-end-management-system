from langchain_core.tools import BaseTool

from app.tools.approval_tool import submit_approval_request
from app.tools.kb_tool import search_knowledge_base
from app.tools.order_tool import get_order_status


TOOLS: list[BaseTool] = [
    search_knowledge_base,
    get_order_status,
    submit_approval_request,
]


TOOLS_BY_NAME: dict[str, BaseTool] = {
    tool.name: tool
    for tool in TOOLS
}


def get_tool(name: str) -> BaseTool:
    return TOOLS_BY_NAME[name]


def list_tools() -> list[dict]:
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args_schema.model_json_schema()
            if tool.args_schema
            else None,
        }
        for tool in TOOLS
    ]