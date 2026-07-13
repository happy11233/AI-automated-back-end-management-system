from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PATH = PROJECT_ROOT / "eval" / "source_documents" / "公司规则类RAG测试文档.docx"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "eval" / "rule_rag_eval_set.jsonl"
RULE_PATTERN = re.compile(
    r"(第\d+章.+?第\d+条（规则编号：(?P<rule_id>R\d{2}-\d{3}-\d{4})）：(?P<body>.+?)(?=第\d+章.+?第\d+条（规则编号：R\d{2}-\d{3}-\d{4}）：|$))",
    re.S,
)


def extract_docx_text(path: Path) -> str:
    with ZipFile(path) as docx_file:
        document_xml = docx_file.read("word/document.xml")

    root = ET.fromstring(document_xml)
    namespace = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    }
    paragraphs = []

    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [
            node.text
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        text = "".join(text_parts).strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


def extract_rules(text: str) -> list[dict]:
    rules = []

    for match in RULE_PATTERN.finditer(text):
        full_text = " ".join(match.group(1).split())
        body = " ".join(match.group("body").split())
        rule_id = match.group("rule_id")
        rules.append(
            {
                "rule_id": rule_id,
                "text": full_text,
                "body": body,
            }
        )

    return rules


def build_eval_cases(rules: list[dict], source_name: str, limit: int) -> list[dict]:
    selected_rules = spread_select(rules, limit)
    cases = []

    for index, rule in enumerate(selected_rules, start=1):
        rule_id = rule["rule_id"]
        body = rule["body"]
        situation = extract_between(body, "当出现“", "”")
        object_name = extract_between(body, "处理对象为“", "”")
        department = extract_between(body, "时，", "应指定")
        owner = extract_between(body, "应指定", "作为第一责任人")
        deadline = extract_between(body, "在", "完成登记")
        material = extract_between(body, "应形成《", "》")
        retention = extract_between(body, "保存不少于", "，")

        cases.append(
            {
                "id": f"rule_{index:03d}_{rule_id.lower()}",
                "question": f"规则编号 {rule_id} 中，出现{situation}且处理对象为{object_name}时，哪个部门负责、第一责任人是谁、处理时限是什么？",
                "role": "admin",
                "department": None,
                "should_refuse": False,
                "expected_evidence": [
                    {
                        "source": f"upload/{source_name}",
                        "keywords": [
                            rule_id,
                            situation,
                            object_name,
                            department,
                            owner,
                            deadline,
                        ],
                    }
                ],
            }
        )

        cases.append(
            {
                "id": f"rule_{index:03d}_{rule_id.lower()}_archive",
                "question": f"规则编号 {rule_id} 要形成什么过程材料，保存多久？",
                "role": "admin",
                "department": None,
                "should_refuse": False,
                "expected_evidence": [
                    {
                        "source": f"upload/{source_name}",
                        "keywords": [
                            rule_id,
                            material,
                            retention,
                        ],
                    }
                ],
            }
        )

    cases.extend(
        [
            {
                "id": "rule_negative_company_pet",
                "question": "公司规则类测试文档里，办公室宠物领养补贴标准是多少？",
                "role": "admin",
                "department": None,
                "should_refuse": True,
                "expected_evidence": [],
            },
            {
                "id": "rule_negative_secret_bonus",
                "question": "公司规则类测试文档里，董事长秘密奖金发放名单在哪里？",
                "role": "admin",
                "department": None,
                "should_refuse": True,
                "expected_evidence": [],
            },
        ]
    )

    return cases


def spread_select(items: list[dict], limit: int) -> list[dict]:
    if limit <= 0 or limit >= len(items):
        return items

    if limit == 1:
        return [items[0]]

    step = (len(items) - 1) / (limit - 1)
    return [items[round(index * step)] for index in range(limit)]


def extract_between(text: str, left: str, right: str) -> str:
    start = text.find(left)
    if start < 0:
        return ""

    start += len(left)
    end = text.find(right, start)
    if end < 0:
        return ""

    return text[start:end].strip()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从规则类 docx 文档自动生成 RAG 评测集")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=20, help="抽样规则条数；每条规则生成 2 道正样本题")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text = extract_docx_text(args.source)
    rules = extract_rules(text)

    if not rules:
        raise ValueError(f"没有从文档中解析到规则条款：{args.source}")

    cases = build_eval_cases(
        rules=rules,
        source_name=args.source.name,
        limit=args.limit,
    )
    write_jsonl(args.output, cases)

    print(f"解析规则条款：{len(rules)} 条")
    print(f"生成评测样本：{len(cases)} 条")
    print(f"输出文件：{args.output}")


if __name__ == "__main__":
    main()
