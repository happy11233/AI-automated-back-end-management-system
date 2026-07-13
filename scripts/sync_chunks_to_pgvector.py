from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db import close_pool, fetch_all, open_pool
from app.rag.vector_store import vector_store


def parse_vector(value: str) -> list[float]:
    return [
        float(item)
        for item in value.strip("[]").split(",")
        if item
    ]


def main() -> None:
    open_pool()

    rows = fetch_all(
        """
        SELECT
            c.id,
            c.content,
            c.embedding,
            c.metadata,
            c.parent_chunk_id,
            c.document_id,
            c.chunk_index,
            d.title,
            d.source,
            d.visibility,
            d.department
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        ORDER BY c.created_at;
        """
    )

    ids = []
    texts = []
    embeddings = []
    metadatas = []

    for row in rows:
        chunk_id = str(row[0])
        metadata = row[3] or {}
        metadata.update({
            "chunk_id": chunk_id,
            "parent_chunk_id": str(row[4]) if row[4] else None,
            "document_id": str(row[5]),
            "chunk_index": row[6],
            "title": row[7],
            "source": row[8],
            "visibility": row[9],
            "department": row[10],
        })

        ids.append(chunk_id)
        texts.append(row[1])
        embeddings.append(parse_vector(row[2]))
        metadatas.append(metadata)

    if ids:
        vector_store.add_embeddings(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    close_pool()
    print(f"同步完成：{len(ids)} 个 chunk 写入 PGVector")


if __name__ == "__main__":
    main()
