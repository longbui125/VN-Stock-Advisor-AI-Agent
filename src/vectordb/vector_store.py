from __future__ import annotations

import hashlib
import uuid
from typing import Iterable

from src.chunking.chunker import TextChunk
from src.embeddings.embedder import HashingEmbeddings
from src.utils.helpers import get_env


def delete_collection(
    collection_name: str = "vn_stock_text_chunks",
    qdrant_url: str | None = None,
) -> None:
    from qdrant_client import QdrantClient

    url = qdrant_url or get_env("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=url, check_compatibility=False)
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name=collection_name)


def upsert_text_chunks(
    chunks: Iterable[TextChunk],
    collection_name: str = "vn_stock_text_chunks",
    qdrant_url: str | None = None,
    embedding_dimensions: int | None = None,
) -> int:
    chunk_list = list(chunks)
    if not chunk_list:
        return 0

    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    url = qdrant_url or get_env("QDRANT_URL", "http://localhost:6333")
    dimensions = embedding_dimensions or int(get_env("HASH_EMBEDDING_DIMENSIONS", "384"))
    embeddings = HashingEmbeddings(dimensions=dimensions)
    vectors = embeddings.embed_documents([chunk.text for chunk in chunk_list])

    if not vectors:
        return 0

    client = QdrantClient(url=url, check_compatibility=False)
    vector_size = len(vectors[0])

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    points = []
    for chunk, vector in zip(chunk_list, vectors):
        points.append(
            PointStruct(
                id=_stable_chunk_id(chunk),
                vector=vector,
                payload={**chunk.metadata, "text": chunk.text},
            )
        )

    client.upsert(collection_name=collection_name, points=points)
    return len(points)


def _stable_chunk_id(chunk: TextChunk) -> str:
    raw = "|".join(
        [
            str(chunk.metadata.get("document_id", "")),
            str(chunk.metadata.get("symbol", "")),
            str(chunk.metadata.get("source", "")),
            str(chunk.metadata.get("chunk_index", "")),
            chunk.text,
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, digest))
