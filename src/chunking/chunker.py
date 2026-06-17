from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    metadata: dict


def chunk_text(
    text: str,
    metadata: dict,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
) -> list[TextChunk]:
    clean_text = " ".join(text.split())
    if not clean_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 0

    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        chunk = clean_text[start:end]
        chunks.append(TextChunk(text=chunk, metadata={**metadata, "chunk_index": index}))
        index += 1
        if end == len(clean_text):
            break
        start = max(0, end - chunk_overlap)

    return chunks
