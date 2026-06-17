from __future__ import annotations

import hashlib
import math
import re

from langchain_core.embeddings import Embeddings


class HashingEmbeddings(Embeddings):
    """Deterministic local embeddings for small RAG demos."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        features = _features(text)

        for feature in features:
            digest = hashlib.sha1(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def _features(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[\w]+", lowered, flags=re.UNICODE)
    features: list[str] = []

    for token in tokens:
        features.append(f"tok:{token}")
        if len(token) >= 4:
            for start in range(0, len(token) - 2):
                features.append(f"tri:{token[start:start + 3]}")

    for left, right in zip(tokens, tokens[1:]):
        features.append(f"bi:{left}_{right}")

    return features
