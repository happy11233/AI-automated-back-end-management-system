from langchain_core.documents import Document

from app.mcp_client import call_mcp_tool
from app.rag.ingest import ingest_documents, mark_missing_documents_deleted


def sync_document_system_to_rag(
    visibility: str,
    department: str | None = None,
) -> dict:
    documents = call_mcp_tool("document_system", "list_documents")
    synced_items = []
    active_sources = set()

    for item in documents:
        document_detail = call_mcp_tool(
            "document_system",
            "read_document",
            {
                "filename": item["filename"],
            },
        )

        content = document_detail["content"].strip()
        if not content:
            continue

        active_sources.add(document_detail["source"])
        result = ingest_documents(
            title=document_detail["title"],
            source=document_detail["source"],
            visibility=visibility,
            department=department,
            raw_documents=[
                Document(
                    page_content=content,
                    metadata={
                        "source": document_detail["source"],
                        "filename": document_detail["filename"],
                        "mcp_server": "document_system",
                        "provider": document_detail.get("provider", "local"),
                    },
                )
            ],
        )

        synced_items.append(
            {
                "filename": document_detail["filename"],
                "title": document_detail["title"],
                "source": document_detail["source"],
                **result,
            }
        )

    deleted_items = mark_missing_documents_deleted(
        active_sources=active_sources,
        source_prefixes=[
            "mcp://document-system/",
            "feishu://docx/",
        ],
        visibility=visibility,
        department=department,
    )

    return {
        "synced_count": len(synced_items),
        "created_count": _count_by_action(synced_items, "created"),
        "updated_count": _count_by_action(synced_items, "updated"),
        "skipped_count": _count_by_action(synced_items, "skipped"),
        "deleted_count": len(deleted_items),
        "items": synced_items,
        "deleted_items": deleted_items,
    }


def _count_by_action(items: list[dict], action: str) -> int:
    return sum(1 for item in items if item.get("update_action") == action)


def create_external_ticket(
    title: str,
    description: str,
    priority: str,
    requester: str | None,
    source: str = "rag-agent",
) -> dict:
    return call_mcp_tool(
        "ticket_system",
        "create_ticket",
        {
            "title": title,
            "description": description,
            "priority": priority,
            "requester": requester,
            "source": source,
        },
    )


def get_external_ticket(ticket_id: str) -> dict:
    return call_mcp_tool(
        "ticket_system",
        "get_ticket",
        {
            "ticket_id": ticket_id,
        },
    )
