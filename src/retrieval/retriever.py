from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.embeddings.embedder import HashingEmbeddings
from src.utils.helpers import get_env


class EmptyRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        return []


class QdrantHashRetriever(BaseRetriever):
    collection_name: str
    url: str
    k: int = 4
    dimensions: int = 384

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        try:
            from qdrant_client import QdrantClient

            embeddings = HashingEmbeddings(dimensions=self.dimensions)
            vector = embeddings.embed_query(query)
            client = QdrantClient(url=self.url, check_compatibility=False)

            if not client.collection_exists(self.collection_name):
                return []

            try:
                points = client.search(
                    collection_name=self.collection_name,
                    query_vector=vector,
                    limit=self.k,
                    with_payload=True,
                )
            except AttributeError:
                result = client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    limit=self.k,
                    with_payload=True,
                )
                points = result.points

            documents = []
            for point in points:
                payload = dict(point.payload or {})
                text = payload.pop("text", "")
                if text:
                    documents.append(Document(page_content=text, metadata=payload))
            return documents
        except Exception:
            return []


def get_retriever(collection_name: str | None = None):
    return QdrantHashRetriever(
        collection_name=collection_name or get_env("QDRANT_COLLECTION", "vn_stock_text_chunks"),
        url=get_env("QDRANT_URL", "http://localhost:6333"),
        k=4,
        dimensions=int(get_env("HASH_EMBEDDING_DIMENSIONS", "384")),
    )
