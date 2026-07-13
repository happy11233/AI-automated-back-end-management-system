from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.db import fetch_one
from app.json_utils import dumps_json
from app.llm import embed_texts
from app.rag.vector_store import vector_store

# 文档入库

def vector_to_sql(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=[
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        "；",
        "，",
        " ",
        "",
    ],
)

parent_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1600,
    chunk_overlap=200,
    separators=[
        "\n\n",
        "\n",
        "。",
        "！",
        "？",
        "；",
        "，",
        " ",
        "",
    ],
)


def create_document(
    title: str,
    source: str,
    visibility: str,
    department: str | None = None,
) -> str:
    row = fetch_one(
        """
        INSERT INTO documents (title, source, visibility, department)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        (title, source, visibility, department),
    )

    return str(row[0])


def create_parent_chunk(
    document_id: str,
    parent_index: int,
    content: str,
    metadata: dict,
) -> str:
    row = fetch_one(
        """
        INSERT INTO document_parent_chunks (
            document_id,
            parent_index,
            content,
            metadata
        )
        VALUES (%s, %s, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            document_id,
            parent_index,
            content,
            dumps_json(metadata),
        ),
    )

    return str(row[0])


def create_document_chunk(
    chunk_id: str,
    document_id: str,
    parent_chunk_id: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    metadata: dict,
) -> str:
    embedding_sql = vector_to_sql(embedding)

    row = fetch_one(
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
        VALUES (%s, %s, %s, %s, %s, %s::vector, %s, %s::jsonb)
        RETURNING id;
        """,
        (
            chunk_id,
            document_id,
            parent_chunk_id,
            chunk_index,
            content,
            embedding_sql,
            "text-embedding-v4",
            dumps_json(metadata),
        ),
    )

    return str(row[0])

def ingest_text_document(
    title: str,
    source: str,
    visibility: str,
    text: str,
    department: str | None = None,
) -> dict:
    document = Document(
        page_content=text,
        metadata={
            "source": source,
        },
    )

    return ingest_documents(
        title=title,
        source=source,
        visibility=visibility,
        department=department,
        raw_documents=[document],
    )


def ingest_documents(
    title: str,
    source: str,
    visibility: str,
    raw_documents: list[Document],
    department: str | None = None,
) -> dict:
    document_id = create_document(
        title=title,
        source=source,
        visibility=visibility,
        department=department,
    )

    parent_chunks = parent_text_splitter.split_documents(raw_documents)

    documents = []
    metadatas = []
    texts = []
    embeddings = []
    ids = []
    chunk_index = 0

    for parent_index, parent_chunk in enumerate(parent_chunks):
        parent_content = parent_chunk.page_content.strip()

        if not parent_content:
            continue

        parent_metadata = {
            **(parent_chunk.metadata or {}),
            "document_id": document_id,
            "title": title,
            "source": source,
            "visibility": visibility,
            "department": department,
            "parent_index": parent_index,
        }

        parent_chunk_id = create_parent_chunk(
            document_id=document_id,
            parent_index=parent_index,
            content=parent_content,
            metadata=parent_metadata,
        )

        child_chunks = text_splitter.split_documents([
            Document(
                page_content=parent_content,
                metadata=parent_metadata,
            )
        ])

        child_texts = [
            child_chunk.page_content.strip()
            for child_chunk in child_chunks
            if child_chunk.page_content.strip()
        ]

        if not child_texts:
            continue

        child_embeddings = embed_texts(child_texts)

        for child_text, child_embedding in zip(child_texts, child_embeddings):
            chunk_id = str(uuid4())
            metadata = {
                **parent_metadata,
                "chunk_id": chunk_id,
                "parent_chunk_id": parent_chunk_id,
                "chunk_index": chunk_index,
            }

            create_document_chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                parent_chunk_id=parent_chunk_id,
                chunk_index=chunk_index,
                content=child_text,
                embedding=child_embedding,
                metadata=metadata,
            )

            documents.append(
                Document(
                    page_content=child_text,
                    metadata=metadata,
                )
            )
            texts.append(child_text)
            embeddings.append(child_embedding)
            metadatas.append(metadata)
            ids.append(chunk_id)
            chunk_index += 1

    if not documents:
        raise ValueError("文档切分后没有可入库的文本内容")

    vector_store.add_embeddings(
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    return {
        "document_id": document_id,
        "parent_chunk_count": len(parent_chunks),
        "chunk_count": len(documents),
        "chunk_ids": ids,
    }
