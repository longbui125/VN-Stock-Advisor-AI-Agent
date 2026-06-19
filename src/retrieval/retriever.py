from __future__ import annotations

import re
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from src.embeddings.embedder import get_embeddings
from src.utils.helpers import get_default_symbols, get_env, load_config


class EmptyRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        return []


class QdrantRetriever(BaseRetriever):
    collection_name: str
    url: str
    k: int = 8

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        from qdrant_client import QdrantClient
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        embeddings = get_embeddings()
        vector = embeddings.embed_query(query)
        client = QdrantClient(url=self.url, check_compatibility=False)

        if not client.collection_exists(self.collection_name):
            return []

        symbol = _extract_single_symbol(query)
        query_filter = (
            Filter(must=[FieldCondition(key="symbol", match=MatchValue(value=symbol))])
            if symbol
            else None
        )

        try:
            points = client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=self.k,
                with_payload=True,
            )
        except AttributeError:
            result = client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=query_filter,
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


def get_retriever(collection_name: str | None = None):
    return QdrantRetriever(
        collection_name=collection_name or get_env("QDRANT_COLLECTION", "vn_stock_text_chunks"),
        url=get_env("QDRANT_URL", "http://localhost:6333"),
        k=int(get_env("QDRANT_TOP_K", "8")),
    )


def _extract_single_symbol(query: str) -> str | None:
    symbols = [token for token in _query_tokens(query) if token in _known_symbols()]
    unique_symbols = sorted(set(symbols))
    if len(unique_symbols) == 1:
        return unique_symbols[0]
    return None


def _query_tokens(query: str) -> list[str]:
    return re.findall(r"\b[A-Z]{2,10}\b", query.upper())


@lru_cache(maxsize=1)
def _known_symbols() -> set[str]:
    try:
        config = load_config()
        symbols = set(get_default_symbols(config, "vnstock_market"))
        symbols.update(get_default_symbols(config, "vnstock_company_text"))
        return symbols
    except Exception:
        return {"VCB", "FPT", "HPG", "VNM", "MWG", "TCB", "SSI"}
