from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.feishu.client import get_feishu_client
from app.json_utils import dumps_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
TICKETS_FILE = DATA_DIR / "tickets.jsonl"

mcp = FastMCP(
    "company-ticket-system",
    instructions="创建和查询外部工单系统里的工单。",
)


@mcp.tool()
def create_ticket(
    title: str,
    description: str,
    priority: str = "normal",
    requester: str | None = None,
    source: str = "rag-agent",
) -> dict:
    """创建一条外部工单，适合人工处理、审批、售后跟进等场景。"""
    feishu_result = _create_feishu_ticket(
        title=title,
        description=description,
        priority=priority,
        requester=requester,
        source=source,
    )
    if feishu_result is not None:
        return feishu_result

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ticket = {
        "ticket_id": f"TICKET-{uuid4().hex[:10].upper()}",
        "title": title.strip()[:120],
        "description": description.strip(),
        "priority": priority,
        "requester": requester,
        "source": source,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with TICKETS_FILE.open("a", encoding="utf-8") as file:
        file.write(dumps_json(ticket) + "\n")

    return {
        "created": True,
        **ticket,
        "message": f"已创建外部工单：{ticket['ticket_id']}",
    }


@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """根据工单号查询工单详情。"""
    feishu_result = _get_feishu_ticket(ticket_id)
    if feishu_result is not None:
        return feishu_result

    if not TICKETS_FILE.exists():
        return {
            "found": False,
            "message": f"没有找到工单：{ticket_id}",
        }

    with TICKETS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            ticket = json.loads(line)
            if ticket.get("ticket_id") == ticket_id:
                return {
                    "found": True,
                    **ticket,
                }

    return {
        "found": False,
        "message": f"没有找到工单：{ticket_id}",
    }


def _is_feishu_ticket_configured() -> bool:
    client = get_feishu_client()
    return bool(
        client.is_configured
        and settings.feishu_bitable_app_token
        and settings.feishu_bitable_table_id
    )


def _create_feishu_ticket(
    title: str,
    description: str,
    priority: str,
    requester: str | None,
    source: str,
) -> dict | None:
    if not _is_feishu_ticket_configured():
        return None

    client = get_feishu_client()
    ticket_id = f"TICKET-{uuid4().hex[:10].upper()}"
    created_at = datetime.now(timezone.utc).isoformat()
    fields = {
        settings.feishu_ticket_id_field: ticket_id,
        settings.feishu_ticket_title_field: title.strip()[:120],
        settings.feishu_ticket_description_field: description.strip(),
        settings.feishu_ticket_priority_field: priority,
        settings.feishu_ticket_requester_field: requester or "",
        settings.feishu_ticket_source_field: source,
        settings.feishu_ticket_status_field: "open",
        settings.feishu_ticket_created_at_field: created_at,
    }

    record = client.create_bitable_record(
        app_token=settings.feishu_bitable_app_token or "",
        table_id=settings.feishu_bitable_table_id or "",
        fields=fields,
    )

    return {
        "created": True,
        "ticket_id": ticket_id,
        "title": title.strip()[:120],
        "description": description.strip(),
        "priority": priority,
        "requester": requester,
        "source": source,
        "status": "open",
        "created_at": created_at,
        "provider": "feishu",
        "record_id": record.get("record_id"),
        "message": f"已创建飞书工单：{ticket_id}",
    }


def _get_feishu_ticket(ticket_id: str) -> dict | None:
    if not _is_feishu_ticket_configured():
        return None

    client = get_feishu_client()
    records = client.list_bitable_records(
        app_token=settings.feishu_bitable_app_token or "",
        table_id=settings.feishu_bitable_table_id or "",
    )

    for record in records:
        fields = record.get("fields", {})
        if fields.get(settings.feishu_ticket_id_field) != ticket_id:
            continue

        return {
            "found": True,
            "ticket_id": ticket_id,
            "title": fields.get(settings.feishu_ticket_title_field),
            "description": fields.get(settings.feishu_ticket_description_field),
            "priority": fields.get(settings.feishu_ticket_priority_field),
            "requester": fields.get(settings.feishu_ticket_requester_field),
            "source": fields.get(settings.feishu_ticket_source_field),
            "status": fields.get(settings.feishu_ticket_status_field),
            "created_at": fields.get(settings.feishu_ticket_created_at_field),
            "provider": "feishu",
            "record_id": record.get("record_id"),
        }

    return {
        "found": False,
        "provider": "feishu",
        "message": f"没有找到飞书工单：{ticket_id}",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
