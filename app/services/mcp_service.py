from langchain_core.documents import Document

from app.mcp_client import call_mcp_tool
from app.rag.ingest import ingest_documents


def sync_document_system_to_rag(
    visibility: str,
    department: str | None = None,
) -> dict:
    documents = call_mcp_tool("document_system", "list_documents")
    synced_items = []

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

    return {
        "synced_count": len(synced_items),
        "items": synced_items,
    }


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
