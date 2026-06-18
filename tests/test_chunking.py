from src.chunking.chunker import chunk_text


def test_chunk_text_keeps_metadata_and_indexes_chunks():
    chunks = chunk_text("a" * 1300, {"symbol": "FPT"}, chunk_size=500, chunk_overlap=50)

    assert len(chunks) >= 2
    assert chunks[0].metadata["symbol"] == "FPT"
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == list(range(len(chunks)))


def test_chunk_text_preserves_sections_and_adds_header():
    text = "\n".join(
        [
            "Ma co phieu: FPT",
            "business_model: Cong nghe. Vien thong. Giao duc.",
            "history: Thanh lap nam 1988. Niem yet nam 2006.",
            "website: https://fpt.com",
        ]
    )

    chunks = chunk_text(
        text,
        {"symbol": "FPT", "source": "vnstock_kbs", "document_type": "company_profile"},
        chunk_size=220,
        chunk_overlap=30,
    )

    assert chunks
    assert chunks[0].text.startswith("[Ma: FPT")
    assert "business_model:" in "\n".join(chunk.text for chunk in chunks)
    assert "history:" in "\n".join(chunk.text for chunk in chunks)
