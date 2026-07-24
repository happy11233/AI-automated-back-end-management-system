from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.db import close_pool, open_pool  # noqa: E402
from app.rag.ingest import ensure_rag_document_scope_schema  # noqa: E402
from app.rag.retriever import _load_keyword_corpus, build_metadata_filter  # noqa: E402


DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)


def main() -> None:
    marker = f"RAG-FIELD-SENS-{int(time.time())}-{uuid4().hex[:8]}"

    open_pool()
    try:
        ensure_rag_document_scope_schema()
        document_ids = seed_scope_documents(marker)

        common_source = f"verify-rag-field-sensitivity/{marker}/common"
        operations_listing_source = f"verify-rag-field-sensitivity/{marker}/operations-listing"
        customer_after_sales_source = f"verify-rag-field-sensitivity/{marker}/customer-after-sales"
        finance_salary_source = f"verify-rag-field-sensitivity/{marker}/finance-salary"
        finance_restricted_source = f"verify-rag-field-sensitivity/{marker}/finance-restricted-unscoped"

        no_position_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position=None,
        )
        operations_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
        )
        customer_service_chunks = _load_keyword_corpus(
            role="employee",
            department="客服部",
            position="customer_service",
        )
        finance_chunks = _load_keyword_corpus(
            role="employee",
            department="财务部",
            position="finance",
        )
        operations_internal_only_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
            max_sensitivity_level="internal",
        )
        operations_wrong_field_chunks = _load_keyword_corpus(
            role="employee",
            department="运营部",
            position="operations",
            field_scope="finance_salary",
        )
        finance_confidential_cap_chunks = _load_keyword_corpus(
            role="employee",
            department="财务部",
            position="finance",
            max_sensitivity_level="confidential",
        )
        admin_chunks = _load_keyword_corpus(
            role="admin",
            department="管理部",
            position=None,
        )
        vector_filter = build_metadata_filter(
            role="employee",
            department="运营部",
            position="operations",
        )

        assert has_source(no_position_chunks, common_source), summarize_chunks(no_position_chunks)
        assert not has_source(no_position_chunks, operations_listing_source), summarize_chunks(no_position_chunks)
        assert not has_source(no_position_chunks, finance_salary_source), summarize_chunks(no_position_chunks)

        assert has_source(operations_chunks, common_source), summarize_chunks(operations_chunks)
        assert has_source(operations_chunks, operations_listing_source), summarize_chunks(operations_chunks)
        assert not has_source(operations_chunks, customer_after_sales_source), summarize_chunks(operations_chunks)
        assert not has_source(operations_chunks, finance_salary_source), summarize_chunks(operations_chunks)
        assert not has_source(operations_chunks, finance_restricted_source), summarize_chunks(operations_chunks)

        assert has_source(customer_service_chunks, common_source), summarize_chunks(customer_service_chunks)
        assert has_source(customer_service_chunks, customer_after_sales_source), summarize_chunks(customer_service_chunks)
        assert not has_source(customer_service_chunks, operations_listing_source), summarize_chunks(customer_service_chunks)
        assert not has_source(customer_service_chunks, finance_salary_source), summarize_chunks(customer_service_chunks)

        assert has_source(finance_chunks, common_source), summarize_chunks(finance_chunks)
        assert has_source(finance_chunks, finance_salary_source), summarize_chunks(finance_chunks)
        assert has_source(finance_chunks, finance_restricted_source), summarize_chunks(finance_chunks)
        assert not has_source(finance_chunks, operations_listing_source), summarize_chunks(finance_chunks)
        assert not has_source(finance_chunks, customer_after_sales_source), summarize_chunks(finance_chunks)

        assert has_source(operations_internal_only_chunks, common_source), summarize_chunks(operations_internal_only_chunks)
        assert not has_source(operations_internal_only_chunks, operations_listing_source), summarize_chunks(operations_internal_only_chunks)
        assert has_source(operations_wrong_field_chunks, common_source), summarize_chunks(operations_wrong_field_chunks)
        assert not has_source(operations_wrong_field_chunks, finance_salary_source), summarize_chunks(operations_wrong_field_chunks)
        assert has_source(finance_confidential_cap_chunks, common_source), summarize_chunks(finance_confidential_cap_chunks)
        assert not has_source(finance_confidential_cap_chunks, finance_salary_source), summarize_chunks(finance_confidential_cap_chunks)

        assert has_source(admin_chunks, operations_listing_source), summarize_chunks(admin_chunks)
        assert has_source(admin_chunks, customer_after_sales_source), summarize_chunks(admin_chunks)
        assert has_source(admin_chunks, finance_salary_source), summarize_chunks(admin_chunks)
        assert has_source(admin_chunks, finance_restricted_source), summarize_chunks(admin_chunks)

        vector_filter_text = json.dumps(vector_filter, ensure_ascii=False)
        assert "field_scope" in vector_filter_text, vector_filter
        assert "sensitivity_level" in vector_filter_text, vector_filter
        assert "operations_listing" in vector_filter_text, vector_filter
        assert "confidential" in vector_filter_text, vector_filter

        print(
            json.dumps(
                {
                    "ok": True,
                    "marker": marker,
                    "seeded_document_ids": document_ids,
                    "no_position_sources": source_list(no_position_chunks),
                    "operations_sources": source_list(operations_chunks),
                    "customer_service_sources": source_list(customer_service_chunks),
                    "finance_sources": source_list(finance_chunks),
                    "admin_sources": source_list(admin_chunks),
                    "vector_filter": vector_filter,
                    "note": "real PostgreSQL RAG keyword filtering plus vector metadata filter inspection; no mock/stub/fake/monkeypatch",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup_scope_documents(marker)
        close_pool()


def seed_scope_documents(marker: str) -> list[str]:
    import psycopg

    embedding = "[" + ",".join(["0.001"] * 1024) + "]"
    documents = [
        {
            "title": f"{marker} 通用知识",
            "source": f"verify-rag-field-sensitivity/{marker}/common",
            "department": None,
            "position_scope": None,
            "field_scope": None,
            "sensitivity_level": None,
            "content": f"{marker} 通用知识：所有员工都可以查看基础流程入口。",
        },
        {
            "title": f"{marker} 运营 Listing 保密规则",
            "source": f"verify-rag-field-sensitivity/{marker}/operations-listing",
            "department": "运营部",
            "position_scope": "operations",
            "field_scope": "operations_listing",
            "sensitivity_level": "confidential",
            "content": f"{marker} 运营 Listing 保密规则：新品标题测试词只能给运营岗位使用。",
        },
        {
            "title": f"{marker} 客服售后保密规则",
            "source": f"verify-rag-field-sensitivity/{marker}/customer-after-sales",
            "department": "客服部",
            "position_scope": "customer_service",
            "field_scope": "customer_after_sales",
            "sensitivity_level": "confidential",
            "content": f"{marker} 客服售后保密规则：客户沟通记录只能给客服岗位使用。",
        },
        {
            "title": f"{marker} 财务工资受限规则",
            "source": f"verify-rag-field-sensitivity/{marker}/finance-salary",
            "department": "财务部",
            "position_scope": "finance",
            "field_scope": "finance_salary",
            "sensitivity_level": "restricted",
            "content": f"{marker} 财务工资受限规则：工资字段只能给财务岗位使用。",
        },
        {
            "title": f"{marker} 财务受限通用规则",
            "source": f"verify-rag-field-sensitivity/{marker}/finance-restricted-unscoped",
            "department": None,
            "position_scope": None,
            "field_scope": None,
            "sensitivity_level": "restricted",
            "content": f"{marker} 财务受限通用规则：利润率和完整付款明细只能给财务岗位使用。",
        },
    ]

    document_ids: list[str] = []
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for item in documents:
                cur.execute(
                    """
                    INSERT INTO documents (
                        title,
                        source,
                        visibility,
                        department,
                        position_scope,
                        field_scope,
                        sensitivity_level,
                        content_hash,
                        version,
                        status
                    )
                    VALUES (%s, %s, 'employee', %s, %s, %s, %s, %s, 1, 'active')
                    RETURNING id;
                    """,
                    (
                        item["title"],
                        item["source"],
                        item["department"],
                        item["position_scope"],
                        item["field_scope"],
                        item["sensitivity_level"],
                        f"verify-{marker}-{item['source']}",
                    ),
                )
                document_id = str(cur.fetchone()[0])
                document_ids.append(document_id)
                parent_id = str(uuid4())
                chunk_id = str(uuid4())
                metadata = {
                    "document_id": document_id,
                    "title": item["title"],
                    "source": item["source"],
                    "visibility": "employee",
                    "department": item["department"],
                    "position_scope": item["position_scope"],
                    "status": "active",
                    "parent_index": 0,
                    "chunk_id": chunk_id,
                    "parent_chunk_id": parent_id,
                    "chunk_index": 0,
                }
                if item["field_scope"]:
                    metadata["field_scope"] = item["field_scope"]
                if item["sensitivity_level"]:
                    metadata["sensitivity_level"] = item["sensitivity_level"]

                cur.execute(
                    """
                    INSERT INTO document_parent_chunks (
                        id,
                        document_id,
                        parent_index,
                        content,
                        metadata
                    )
                    VALUES (%s, %s, 0, %s, %s::jsonb);
                    """,
                    (
                        parent_id,
                        document_id,
                        item["content"],
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO document_chunks (
                        id,
                        document_id,
                        parent_chunk_id,
                        chunk_index,
                        content,
                        embedding,
                        embedding_model,
                        metadata
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        0,
                        %s,
                        %s::vector,
                        'text-embedding-v4',
                        %s::jsonb
                    );
                    """,
                    (
                        chunk_id,
                        document_id,
                        parent_id,
                        item["content"],
                        embedding,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
        conn.commit()

    return document_ids


def cleanup_scope_documents(marker: str) -> None:
    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM documents
                WHERE source LIKE %s;
                """,
                (f"verify-rag-field-sensitivity/{marker}/%",),
            )
        conn.commit()


def has_source(chunks: list[dict[str, Any]], source: str) -> bool:
    return any(chunk.get("source") == source for chunk in chunks)


def source_list(chunks: list[dict[str, Any]]) -> list[str]:
    return [str(chunk.get("source") or "") for chunk in chunks if chunk.get("source")]


def summarize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source": chunk.get("source"),
            "department": chunk.get("department"),
            "position_scope": chunk.get("position_scope"),
            "field_scope": chunk.get("field_scope"),
            "sensitivity_level": chunk.get("sensitivity_level"),
        }
        for chunk in chunks
    ]


if __name__ == "__main__":
    main()
