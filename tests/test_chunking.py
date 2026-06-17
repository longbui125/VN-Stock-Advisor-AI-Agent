from src.chunking.chunker import chunk_text


def test_chunk_text_keeps_metadata_and_indexes_chunks():
    chunks = chunk_text("a" * 1300, {"symbol": "FPT"}, chunk_size=500, chunk_overlap=50)

    assert len(chunks) == 3
    assert chunks[0].metadata["symbol"] == "FPT"
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == [0, 1, 2]
