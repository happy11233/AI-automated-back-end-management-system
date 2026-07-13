from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from langchain_community.document_loaders import (
    CSVLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredExcelLoader,
)
from langchain_core.documents import Document


SUPPORTED_DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".xlsx", ".xls", ".csv"}


class UnsupportedDocumentTypeError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


def load_documents_from_bytes(filename: str, content: bytes) -> list[Document]:
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise UnsupportedDocumentTypeError(f"当前只支持 {supported} 文件")

    if not content:
        raise EmptyDocumentError("文件内容不能为空")

    temp_path = _write_temp_file(content, suffix)

    try:
        loader = _build_loader(temp_path, suffix)
        documents = loader.load()
        return _normalize_documents(documents, filename, suffix)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def _write_temp_file(content: bytes, suffix: str) -> str:
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content)
        return temp_file.name


def _build_loader(file_path: str, suffix: str):
    if suffix in {".txt", ".md"}:
        return TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)

    if suffix == ".pdf":
        return PyPDFLoader(file_path)

    if suffix == ".docx":
        return DocxTextLoader(file_path)

    if suffix == ".csv":
        return CSVLoader(file_path, encoding="utf-8", autodetect_encoding=True)

    if suffix in {".xlsx", ".xls"}:
        return UnstructuredExcelLoader(file_path, mode="elements")

    raise UnsupportedDocumentTypeError(f"不支持的文件类型：{suffix}")


class DocxTextLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> list[Document]:
        paragraphs = []

        with ZipFile(self.file_path) as docx_file:
            document_xml = docx_file.read("word/document.xml")

        root = ET.fromstring(document_xml)
        namespace = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        }

        for paragraph in root.findall(".//w:p", namespace):
            text_parts = [
                node.text
                for node in paragraph.findall(".//w:t", namespace)
                if node.text
            ]
            text = "".join(text_parts).strip()

            if text:
                paragraphs.append(text)

        content = "\n".join(paragraphs).strip()

        if not content:
            return []

        return [
            Document(
                page_content=content,
                metadata={
                    "source": self.file_path,
                },
            )
        ]


def _normalize_documents(
    documents: list[Document],
    filename: str,
    suffix: str,
) -> list[Document]:
    normalized_documents = []

    for index, document in enumerate(documents):
        content = document.page_content.strip()

        if not content:
            continue

        metadata = _sanitize_metadata(document.metadata or {})
        metadata.update(
            {
                "filename": filename,
                "file_type": suffix.lstrip("."),
                "loader_index": index,
            }
        )

        normalized_documents.append(
            Document(
                page_content=content,
                metadata=metadata,
            )
        )

    if not normalized_documents:
        raise EmptyDocumentError("文件解析后没有可入库的文本内容")

    return normalized_documents


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize_metadata_value(value) for key, value in metadata.items()}


def _sanitize_metadata_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return _sanitize_metadata(value)

    if isinstance(value, (list, tuple, set)):
        return [_sanitize_metadata_value(item) for item in value]

    return str(value)
