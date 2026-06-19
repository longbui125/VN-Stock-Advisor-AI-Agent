from langchain_core.embeddings import Embeddings

from src.utils.helpers import get_env


def get_embeddings() -> Embeddings:
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=get_env("OLLAMA_EMBED_MODEL", "bge-m3"),
        base_url=get_env("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
