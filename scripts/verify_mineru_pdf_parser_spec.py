from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.mineru_loader import load_mineru_output_documents


def main() -> None:
    sample = [
        {
            "type": "title",
            "content": {"title_content": "第一章 财务概览", "level": 1},
            "page_idx": 0,
            "bbox": [1, 2, 3, 4],
        },
        {
            "type": "paragraph",
            "content": {"paragraph_content": "本月收入增长明显。"},
            "page_idx": 0,
        },
        {
            "type": "table",
            "content": {"table_body": "收入|金额\nA|100", "table_caption": "收入明细"},
            "page_idx": 0,
        },
        {
            "type": "image",
            "content": {"image_caption": "销售趋势图"},
            "page_idx": 1,
        },
    ]

    with tempfile.TemporaryDirectory(prefix="mineru-verify-") as temp_dir:
        output_dir = Path(temp_dir)
        (output_dir / "sample_content_list_v2.json").write_text(
            json.dumps(sample, ensure_ascii=False),
            encoding="utf-8",
        )

        documents = load_mineru_output_documents(
            output_dir=output_dir,
            source_path=Path("sample.pdf"),
        )

    assert len(documents) == 2, documents
    first_doc, second_doc = documents

    assert "第一章 财务概览" in first_doc.page_content, first_doc.page_content
    assert "本月收入增长明显。" in first_doc.page_content, first_doc.page_content
    assert "表格：" in first_doc.page_content, first_doc.page_content
    assert first_doc.metadata["parser"] == "mineru", first_doc.metadata
    assert first_doc.metadata["parser_output"] == "content_list_v2", first_doc.metadata
    assert first_doc.metadata["page"] == 1, first_doc.metadata
    assert first_doc.metadata["has_table"] is True, first_doc.metadata

    assert "图片说明：销售趋势图" in second_doc.page_content, second_doc.page_content
    assert second_doc.metadata["page"] == 2, second_doc.metadata
    assert second_doc.metadata["has_image"] is True, second_doc.metadata

    print("mineru pdf parser spec checks passed")


if __name__ == "__main__":
    main()
