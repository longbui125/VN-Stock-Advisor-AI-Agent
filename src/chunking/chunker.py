from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    metadata: dict


def chunk_text(
    text: str,
    metadata: dict,
    chunk_size: int = 1400,
    chunk_overlap: int = 80,
) -> list[TextChunk]:
    clean_text = _normalize_text(text)
    if not clean_text:
        return []

    sections = _split_sections(clean_text)
    raw_chunks = _pack_sections(sections, chunk_size=chunk_size)

    chunks: list[TextChunk] = []
    for raw_chunk in raw_chunks:
        for piece in _split_oversized(raw_chunk, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
            if piece.strip():
                index = len(chunks)
                chunk_metadata = {**metadata, "chunk_index": index}
                chunks.append(TextChunk(text=_with_header(piece, chunk_metadata), metadata=chunk_metadata))

    return chunks


def _normalize_text(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        clean_line = " ".join(line.split())
        if clean_line:
            lines.append(clean_line)
    return "\n".join(lines)


def _split_sections(text: str) -> list[str]:
    lines = text.split("\n")
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if _is_section_start(line) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("\n".join(current).strip())

    return [section for section in sections if section]


def _is_section_start(line: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_ ]{1,48}:\s+", line))


def _pack_sections(sections: list[str], chunk_size: int) -> list[str]:
    chunks: list[str] = []
    current = ""

    for section in sections:
        if not current:
            current = section
            continue

        candidate = f"{current}\n\n{section}"
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            current = section

    if current:
        chunks.append(current)

    return chunks


def _split_oversized(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            end = _best_breakpoint(text, start, end)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = _next_start(text, end, chunk_overlap)

    return chunks


def _best_breakpoint(text: str, start: int, end: int) -> int:
    window_start = max(start + int((end - start) * 0.55), start)
    candidates = [
        text.rfind("\n- ", window_start, end),
        text.rfind("; ", window_start, end),
        text.rfind(". ", window_start, end),
        text.rfind(", ", window_start, end),
        text.rfind(" ", window_start, end),
    ]
    breakpoint = max(candidates)
    if breakpoint <= start:
        return end
    return breakpoint + 1


def _next_start(text: str, end: int, chunk_overlap: int) -> int:
    start = max(0, end - chunk_overlap)
    while start < end and start < len(text) and text[start].isalnum():
        start += 1
    return start


def _with_header(text: str, metadata: dict) -> str:
    header_parts = [
        f"Ma: {metadata.get('symbol', '')}",
        f"Loai tai lieu: {metadata.get('document_type', '')}",
        f"Nguon: {metadata.get('source', '')}",
        f"Chunk: {metadata.get('chunk_index', '')}",
    ]
    title = metadata.get("title")
    if title:
        header_parts.insert(1, f"Tieu de: {title}")
    return f"[{' | '.join(str(part) for part in header_parts if part)}]\n{text.strip()}"
