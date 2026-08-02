from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from langchain_core.documents import Document

SKIP_METADATA_KEYS = {
    "type",
    "angle",
    "bbox",
    "score",
    "block_tags",
    "content_tags",
    "format",
    "url",
    "children",
    "level",
    "sub_type",
    "subtype",
    "index",
    "page_idx",
    "page",
}

NOISY_BLOCK_TYPES = {
    "page_header",
    "page_footer",
    "page_number",
    "page_aside_text",
    "header",
    "footer",
    "aside_text",
}

CONTENT_FIELDS_BY_TYPE = {
    "title": ("title_content",),
    "paragraph": ("paragraph_content",),
    "equation": ("math_content",),
    "image": ("image_body", "image_caption", "image_footnote"),
    "table": ("table_body", "table_caption", "table_footnote"),
    "chart": ("chart_body", "chart_caption", "chart_footnote"),
    "code": ("code_content", "code_body", "code_caption", "code_footnote", "code_language"),
    "algorithm": ("algorithm_content", "algorithm_caption", "algorithm_footnote"),
    "list": ("list_items",),
    "index": ("list_items",),
    "page_footnote": ("page_footnote_content",),
}

CONTENT_LIST_TYPE_ALIASES = {
    "doc_title": "title",
    "heading": "title",
    "paragraph": "text",
    "text": "text",
    "equation_interline": "equation",
    "interline_equation": "equation",
    "formula": "equation",
    "seal": "image",
    "figure": "image",
    "footnote": "footnote",
    "page_footnote": "footnote",
}


class MinerUUnavailableError(RuntimeError):
    pass


class MinerUParseError(RuntimeError):
    pass


class MinerUPDFLoader:
    def __init__(
        self,
        file_path: str,
        *,
        command: str = "mineru",
        backend: str = "pipeline",
        timeout_seconds: int = 180,
        model_source: str | None = None,
    ):
        self.file_path = file_path
        self.command = command
        self.backend = backend
        self.timeout_seconds = timeout_seconds
        self.model_source = model_source

    def load(self) -> list[Document]:
        command_parts = shlex.split(self.command)
        if not command_parts:
            raise MinerUUnavailableError("MinerU 命令不能为空")

        executable = shutil.which(command_parts[0])
        if not executable:
            raise MinerUUnavailableError(f"没有找到 MinerU 命令：{command_parts[0]}")

        with TemporaryDirectory(prefix="mineru-rag-") as output_dir:
            command = [
                executable,
                *command_parts[1:],
                "-p",
                self.file_path,
                "-o",
                output_dir,
            ]
            if self.backend:
                command.extend(["-b", self.backend])

            env = os.environ.copy()
            if self.model_source:
                env["MINERU_MODEL_SOURCE"] = self.model_source

            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    env=env,
                    text=True,
                    timeout=max(1, int(self.timeout_seconds)),
                )
            except subprocess.TimeoutExpired as error:
                raise MinerUParseError(
                    f"MinerU 解析超时，已超过 {self.timeout_seconds} 秒"
                ) from error

            if result.returncode != 0:
                message = (result.stderr or result.stdout or "").strip()
                raise MinerUParseError(f"MinerU 解析失败：{message[-800:]}")

            documents = load_mineru_output_documents(
                output_dir=Path(output_dir),
                source_path=Path(self.file_path),
            )
            if not documents:
                raise MinerUParseError("MinerU 没有输出可入库的文本内容")

            return documents


def load_mineru_output_documents(
    *,
    output_dir: Path,
    source_path: Path,
) -> list[Document]:
    content_list_file = _select_content_list_file(output_dir, source_path.stem)
    if content_list_file:
        documents = _documents_from_content_list(
            _load_json(content_list_file),
            source_path=source_path,
            output_file=content_list_file,
        )
        if documents:
            return documents

    markdown_file = _select_markdown_file(output_dir, source_path.stem)
    if markdown_file:
        content = markdown_file.read_text(encoding="utf-8", errors="ignore").strip()
        if content:
            return [
                Document(
                    page_content=content,
                    metadata={
                        "source": str(source_path),
                        "parser": "mineru",
                        "parser_output": "markdown",
                        "mineru_output_file": str(markdown_file),
                    },
                )
            ]

    return []


def _select_content_list_file(output_dir: Path, source_stem: str) -> Path | None:
    candidates = [
        *output_dir.rglob("*_content_list_v2.json"),
        *output_dir.rglob("*_content_list.json"),
        *output_dir.rglob("content_list_v2.json"),
        *output_dir.rglob("content_list.json"),
    ]
    return _select_best_output_file(candidates, source_stem)


def _select_markdown_file(output_dir: Path, source_stem: str) -> Path | None:
    candidates = [
        path
        for path in output_dir.rglob("*.md")
        if not path.name.lower().startswith("readme")
    ]
    return _select_best_output_file(candidates, source_stem)


def _select_best_output_file(candidates: list[Path], source_stem: str) -> Path | None:
    existing = [path for path in candidates if path.exists() and path.is_file()]
    if not existing:
        return None

    def score(path: Path) -> tuple[int, int, float]:
        name = path.name.lower()
        stem = source_stem.lower()
        kind_priority = 2 if "content_list_v2" in name else 1 if "content_list" in name else 0
        name_match = 1 if stem and stem in name else 0
        return (kind_priority, name_match, path.stat().st_size, path.stat().st_mtime)

    return max(existing, key=score)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise MinerUParseError(f"MinerU 输出 JSON 解析失败：{path.name}") from error


def _documents_from_content_list(
    data: Any,
    *,
    source_path: Path,
    output_file: Path,
) -> list[Document]:
    items = _extract_content_items(data)
    documents: list[Document] = []
    buffer: list[str] = []
    buffer_items: list[dict[str, Any]] = []
    buffer_types: list[str] = []
    buffer_page_idxs: list[int] = []
    buffer_section_title: str | None = None
    buffer_section_level: int | None = None
    current_section_title: str | None = None
    current_section_level: int | None = None
    current_page_idx: int | None = None

    def flush() -> None:
        nonlocal buffer, buffer_items, buffer_types, buffer_page_idxs, buffer_section_title, buffer_section_level
        content = "\n\n".join(buffer).strip()
        if not content:
            buffer = []
            buffer_items = []
            buffer_types = []
            buffer_page_idxs = []
            return

        type_counts = Counter(t for t in buffer_types if t)
        page_idxs = [page_idx for page_idx in buffer_page_idxs if page_idx is not None]
        anchors = _dedupe_preserve_order(
            [
                str(item.get("anchor") or "").strip()
                for item in buffer_items
                if str(item.get("anchor") or "").strip()
            ]
        )
        text_levels = sorted(
            {
                int(level)
                for level in (
                    _to_int(item.get("text_level"))
                    or _to_int(item.get("level"))
                    or _to_int(item.get("section_level"))
                    for item in buffer_items
                )
                if level is not None
            }
        )
        bbox = next(
            (
                _normalize_bbox(item.get("bbox"))
                for item in buffer_items
                if _normalize_bbox(item.get("bbox")) is not None
            ),
            None,
        )
        primary_content_type = None
        if type_counts:
            primary_content_type = type_counts.most_common(1)[0][0]

        metadata: dict[str, Any] = {
            "source": str(source_path),
            "parser": "mineru",
            "parser_output": _mineru_output_kind(output_file),
            "mineru_output_file": str(output_file),
            "block_count": len(buffer_items),
            "content_types": sorted(type_counts),
            "primary_content_type": primary_content_type,
        }
        if page_idxs:
            page_idx_start = min(page_idxs)
            page_idx_end = max(page_idxs)
            metadata["page_idx"] = page_idx_start
            metadata["page_idx_start"] = page_idx_start
            metadata["page_idx_end"] = page_idx_end
            metadata["page_idx_count"] = len(set(page_idxs))
            metadata["page"] = page_idx_start + 1
            metadata["page_start"] = page_idx_start + 1
            metadata["page_end"] = page_idx_end + 1
            metadata["page_count"] = len(set(page_idxs))
        if buffer_section_title:
            metadata["section_title"] = buffer_section_title
        if buffer_section_level is not None:
            metadata["section_level"] = buffer_section_level
        if text_levels:
            metadata["text_levels"] = text_levels
        if anchors:
            metadata["anchors"] = anchors[:5]
        if bbox is not None:
            metadata["sample_bbox"] = bbox
        if type_counts.get("table"):
            metadata["has_table"] = True
        if type_counts.get("image"):
            metadata["has_image"] = True
        if type_counts.get("equation"):
            metadata["has_equation"] = True
        if type_counts.get("footnote") or type_counts.get("page_footnote"):
            metadata["has_footnote"] = True

        documents.append(Document(page_content=content, metadata=metadata))
        buffer = []
        buffer_items = []
        buffer_types = []
        buffer_page_idxs = []
        buffer_section_title = None
        buffer_section_level = None

    for index, item in enumerate(items):
        block_type = _block_type(item)
        item_metadata = _block_metadata(item, block_type=block_type)
        text = _block_to_markdown(item, block_type=block_type).strip()
        if not text:
            continue

        page_idx = item_metadata.get("page_idx")
        if block_type == "title":
            current_section_title = _clean_heading_text(text)
            current_section_level = _to_int(item_metadata.get("text_level"))

        should_flush = False
        if buffer and page_idx is not None and current_page_idx is not None and page_idx != current_page_idx:
            should_flush = True
        if buffer and block_type == "title":
            should_flush = True
        if buffer and sum(len(piece) for piece in buffer) + len(text) > 3200:
            should_flush = True

        if should_flush:
            flush()

        current_page_idx = page_idx if page_idx is not None else current_page_idx
        buffer.append(text)
        buffer_items.append(item_metadata)
        buffer_types.append(block_type or "unknown")
        if page_idx is not None:
            buffer_page_idxs.append(page_idx)
        if current_section_title and not buffer_section_title:
            buffer_section_title = current_section_title
        if current_section_level is not None and buffer_section_level is None:
            buffer_section_level = current_section_level

        if index == len(items) - 1:
            flush()

    flush()
    return documents


def _extract_content_items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        if not data:
            return []

        if all(isinstance(item, list) for item in data):
            flattened: list[dict[str, Any]] = []
            for page_index, page_items in enumerate(data, start=1):
                flattened.extend(_flatten_items(page_items, inherited_page_idx=page_index - 1))
            return flattened

        flattened: list[dict[str, Any]] = []
        for index, item in enumerate(data):
            if isinstance(item, dict):
                page_idx = _mineru_page_idx(item)
                nested = _nested_content_items(item)
                if nested is not None:
                    flattened.extend(_flatten_items(nested, inherited_page_idx=page_idx if page_idx is not None else index))
                    continue
                flattened.append(_attach_page_index(item, page_idx))
            elif isinstance(item, list):
                flattened.extend(_flatten_items(item, inherited_page_idx=index))
        return flattened

    if not isinstance(data, dict):
        return []

    for key in ("content", "content_list", "items", "blocks", "pages"):
        value = data.get(key)
        if isinstance(value, list):
            return _flatten_items(value, inherited_page_idx=_mineru_page_idx(data))

    return _flatten_items([data], inherited_page_idx=_mineru_page_idx(data))


def _flatten_items(items: list[Any], inherited_page_idx: int | None = None) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            page_idx = _mineru_page_idx(item)
            if page_idx is None:
                page_idx = inherited_page_idx
            nested = _nested_content_items(item)
            if isinstance(nested, list):
                for child in _flatten_items(nested, inherited_page_idx=page_idx):
                    flattened.append(child)
                continue
            flattened.append(_attach_page_index(item, page_idx))
        elif isinstance(item, list):
            flattened.extend(_flatten_items(item, inherited_page_idx=inherited_page_idx))
    return flattened


def _block_type(item: dict[str, Any]) -> str:
    raw_type = (
        item.get("type")
        or item.get("category")
        or item.get("category_type")
        or item.get("block_type")
        or ""
    )
    block_type = str(raw_type).lower().replace("-", "_").strip()
    sub_type = str(item.get("sub_type") or item.get("subtype") or "").lower().replace("-", "_").strip()

    if block_type in NOISY_BLOCK_TYPES:
        return "noise"

    block_type = CONTENT_LIST_TYPE_ALIASES.get(block_type, block_type)

    if block_type == "title" or _has_content_field(item, "title"):
        return "title"

    if block_type == "table" or _has_content_field(item, "table"):
        return "table"

    if block_type == "image" or _has_content_field(item, "image"):
        return "image"

    if block_type == "equation" or _has_content_field(item, "equation"):
        return "equation"

    if block_type == "code" or sub_type == "code" or _has_content_field(item, "code"):
        return "code"

    if block_type == "algorithm" or sub_type == "algorithm" or _has_content_field(item, "algorithm"):
        return "algorithm"

    if block_type in {"list", "index"} or "list" in sub_type or _has_content_field(item, "list"):
        return "list"

    if block_type == "footnote" or _has_content_field(item, "page_footnote"):
        return "footnote"

    if block_type == "text" or _has_content_field(item, "paragraph"):
        return "text"

    return block_type or "text"


def _block_to_markdown(item: dict[str, Any], *, block_type: str) -> str:
    if block_type == "noise":
        return ""

    text = _extract_text_content(item, block_type)

    if block_type == "title":
        heading = _clean_heading_text(text)
        level = _text_level(item) or 2
        level = max(1, min(6, level))
        return f'{"#" * level} {heading}' if heading else ""
    if block_type == "table":
        return f"表格：\n{text}" if text else ""
    if block_type == "image":
        return f"图片说明：{text}" if text else ""
    if block_type == "equation":
        return f"公式：{text}" if text else ""
    if block_type == "code":
        return f"代码：\n{text}" if text else ""
    if block_type == "algorithm":
        return f"算法：\n{text}" if text else ""
    if block_type == "footnote":
        return f"脚注：{text}" if text else ""
    return text


def _extract_text_content(item: dict[str, Any], block_type: str) -> str:
    for key in _content_fields_for_type(block_type):
        text = _stringify_content_value(_item_value_for_key(item, key))
        if text:
            return text

    content = _content_payload(item)
    if content:
        for key in ("content", "text", "html", "markdown", "md_content", "caption"):
            text = _stringify_content_value(content.get(key))
            if text:
                return text

    fallback_values = []
    for key, value in item.items():
        if key in SKIP_METADATA_KEYS or key in {"img_path", "image_path", "poly", "content"}:
            continue
        if isinstance(value, str):
            fallback_values.append(value)
    return "\n".join(part.strip() for part in fallback_values if part.strip()).strip()


def _text_level(item: dict[str, Any]) -> int | None:
    level = _to_int(item.get("text_level"))
    if level is not None:
        return level

    level = _to_int(item.get("level"))
    if level is not None:
        return level

    content = item.get("content")
    if isinstance(content, dict):
        return _to_int(content.get("level"))

    return None


def _block_metadata(item: dict[str, Any], *, block_type: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "block_type": block_type,
    }

    page_idx = _mineru_page_idx(item)
    if page_idx is not None:
        metadata["page_idx"] = page_idx
        metadata["page"] = page_idx + 1

    text_level = _text_level(item)
    if text_level is not None:
        metadata["text_level"] = text_level

    anchor = _extract_anchor(item)
    if anchor:
        metadata["anchor"] = anchor

    bbox = _normalize_bbox(item.get("bbox"))
    if bbox is not None:
        metadata["bbox"] = bbox

    sub_type = item.get("sub_type") or item.get("subtype")
    if isinstance(sub_type, str) and sub_type.strip():
        metadata["sub_type"] = sub_type.strip()

    score = item.get("score")
    if isinstance(score, (int, float)):
        metadata["score"] = score

    content_format = item.get("format")
    if isinstance(content_format, str) and content_format.strip():
        metadata["format"] = content_format.strip()

    return metadata


def _extract_anchor(item: dict[str, Any]) -> str | None:
    anchor = item.get("anchor")
    if isinstance(anchor, str):
        cleaned = anchor.strip()
        if cleaned:
            return cleaned

    content = item.get("content")
    if isinstance(content, dict):
        inner_anchor = content.get("anchor")
        if isinstance(inner_anchor, str):
            cleaned = inner_anchor.strip()
            if cleaned:
                return cleaned

    return None


def _normalize_bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list) or not value:
        return None

    normalized: list[float] = []
    for item in value:
        try:
            normalized.append(float(item))
        except (TypeError, ValueError):
            return None

    return normalized


def _mineru_output_kind(output_file: Path) -> str:
    name = output_file.name.lower()
    if "content_list_v2" in name:
        return "content_list_v2"
    if "content_list" in name:
        return "content_list"
    if name.endswith(".md"):
        return "markdown"
    return output_file.suffix.lstrip(".") or "unknown"


def _content_fields_for_type(block_type: str) -> tuple[str, ...]:
    fields = CONTENT_FIELDS_BY_TYPE.get(block_type, ())
    if fields:
        return fields + ("text", "md_content", "markdown", "html", "caption")
    return ("text", "content", "md_content", "markdown", "html", "caption")


def _has_content_field(item: dict[str, Any], block_type: str) -> bool:
    for key in _content_fields_for_type(block_type):
        if _stringify_content_value(_item_value_for_key(item, key)):
            return True
    return False


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _attach_page_index(item: dict[str, Any], page_idx: int | None) -> dict[str, Any]:
    if page_idx is None or _mineru_page_idx(item) is not None:
        return dict(item)

    normalized = dict(item)
    normalized["page_idx"] = page_idx
    normalized.setdefault("page", page_idx + 1)
    return normalized


def _nested_content_items(item: dict[str, Any]) -> list[Any] | None:
    for key in ("blocks", "items", "content", "pages"):
        value = item.get(key)
        if isinstance(value, list):
            return value
    return None


def _mineru_page_idx(item: dict[str, Any]) -> int | None:
    page_idx = _to_int(item.get("page_idx"))
    if page_idx is not None and page_idx >= 0:
        return page_idx

    for key in ("page", "page_no", "page_number"):
        page_number = _to_int(item.get(key))
        if page_number is not None and page_number > 0:
            return page_number - 1

    content = item.get("content")
    if isinstance(content, dict):
        nested_page_idx = _mineru_page_idx(content)
        if nested_page_idx is not None:
            return nested_page_idx

    return None


def _stringify_content_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        pieces: list[str] = []
        for item in value:
            text = _stringify_content_value(item)
            if text:
                pieces.append(text)
        return "\n".join(pieces).strip()
    if isinstance(value, dict):
        if "children" in value and isinstance(value.get("children"), list):
            child_text = _stringify_content_value(value.get("children"))
            if child_text:
                return child_text

        content_value = value.get("content")
        if isinstance(content_value, (str, int, float, bool, list, dict)):
            content_text = _stringify_content_value(content_value)
            if content_text:
                return content_text

        for key in ("text", "markdown", "html", "caption"):
            nested_text = _stringify_content_value(value.get(key))
            if nested_text:
                return nested_text

        pieces = []
        for key, nested in value.items():
            if key in SKIP_METADATA_KEYS or key in {"children", "url", "content"}:
                continue
            text = _stringify_content_value(nested)
            if text:
                pieces.append(text)
        return "\n".join(pieces).strip()
    return str(value).strip()


def _content_payload(item: dict[str, Any]) -> dict[str, Any] | None:
    content = item.get("content")
    if isinstance(content, dict):
        return content
    return None


def _item_value_for_key(item: dict[str, Any], key: str) -> Any:
    if key in item:
        return item.get(key)

    content = _content_payload(item)
    if content and key in content:
        return content.get(key)

    return None


def _page_number(item: dict[str, Any]) -> int | None:
    page_idx = _mineru_page_idx(item)
    if page_idx is None:
        return None
    return page_idx + 1


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_heading_text(text: str) -> str:
    return text.lstrip("#").strip()
