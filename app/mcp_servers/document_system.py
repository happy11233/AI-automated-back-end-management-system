from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.feishu.client import get_configured_document_refs, get_feishu_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
SUPPORTED_SUFFIXES = {".md", ".txt"}

mcp = FastMCP(
    "company-document-system",
    instructions="读取公司文档系统中的知识库文档。",
)


def _safe_doc_path(filename: str) -> Path:
    path = (DOCS_DIR / filename).resolve()

    if DOCS_DIR.resolve() not in path.parents and path != DOCS_DIR.resolve():
        raise ValueError("非法文档路径")

    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("当前文档 MCP 只允许读取 .md 和 .txt 文件")

    return path


@mcp.tool()
def health_check() -> dict:
    """检查文档 MCP 是否可读取配置来源。"""
    feishu_client = get_feishu_client()
    feishu_refs = get_configured_document_refs()
    if feishu_client.is_configured and feishu_refs:
        return {
            "ok": True,
            "status": "healthy",
            "message": f"飞书文档 MCP 已配置，当前 {len(feishu_refs)} 个文档引用。",
            "provider": "feishu",
        }
    return {
        "ok": DOCS_DIR.exists(),
        "status": "healthy" if DOCS_DIR.exists() else "not_configured",
        "message": "本地 docs 目录可读取。" if DOCS_DIR.exists() else "本地 docs 目录不存在。",
        "provider": "local",
    }


@mcp.tool()
def list_documents() -> list[dict]:
    """列出公司文档系统中可同步到知识库的文档。"""
    feishu_client = get_feishu_client()
    feishu_refs = get_configured_document_refs()

    if feishu_client.is_configured and feishu_refs:
        return [
            {
                "filename": ref.document_id,
                "title": ref.title,
                "source": f"feishu://docx/{ref.document_id}",
                "file_type": "feishu_docx",
                "provider": "feishu",
            }
            for ref in feishu_refs
        ]

    documents = []

    if not DOCS_DIR.exists():
        return documents

    for path in sorted(DOCS_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue

        documents.append(
            {
                "filename": str(path.relative_to(DOCS_DIR)),
                "title": path.stem,
                "source": f"mcp://document-system/{path.relative_to(DOCS_DIR)}",
                "file_type": path.suffix.lower().lstrip("."),
                "provider": "local",
            }
        )

    return documents


@mcp.tool()
def read_document(filename: str) -> dict:
    """读取指定文档内容。filename 来自 list_documents 返回值。"""
    feishu_client = get_feishu_client()
    feishu_refs = get_configured_document_refs()
    feishu_ref = next(
        (ref for ref in feishu_refs if ref.document_id == filename),
        None,
    )

    if feishu_client.is_configured and feishu_ref is not None:
        return {
            "filename": filename,
            "title": feishu_ref.title,
            "source": f"feishu://docx/{filename}",
            "content": feishu_client.get_document_raw_content(filename),
            "provider": "feishu",
        }

    path = _safe_doc_path(filename)

    if not path.exists() or not path.is_file():
        raise ValueError(f"文档不存在：{filename}")

    return {
        "filename": filename,
        "title": path.stem,
        "source": f"mcp://document-system/{filename}",
        "content": path.read_text(encoding="utf-8"),
        "provider": "local",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
