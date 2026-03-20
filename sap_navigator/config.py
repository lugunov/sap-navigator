from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _resolve_path(env_name: str, default: str) -> Path:
    raw = os.getenv(env_name, default)
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path


@dataclass(slots=True)
class AppConfig:
    knowledge_dir: Path = _resolve_path("SAPA_KNOWLEDGE_DIR", "knowledge-base")
    vector_dir: Path = _resolve_path("SAPA_VECTOR_DIR", ".data/chroma")
    collection_name: str = os.getenv("SAPA_COLLECTION", "sap_tm_knowledge")
    llm_provider: str = os.getenv("SAPA_LLM_PROVIDER", "ollama")
    llm_model: str = os.getenv("SAPA_LLM_MODEL", "qwen2.5:7b-instruct")
    llm_base_url: str = os.getenv("SAPA_LLM_BASE_URL", "http://127.0.0.1:11434")
    llm_api_key: str = os.getenv("SAPA_LLM_API_KEY", "")
    embed_provider: str = os.getenv("SAPA_EMBED_PROVIDER", "ollama")
    embed_model: str = os.getenv("SAPA_EMBED_MODEL", "nomic-embed-text")
    embed_base_url: str = os.getenv("SAPA_EMBED_BASE_URL", "http://127.0.0.1:11434")
    embed_api_key: str = os.getenv("SAPA_EMBED_API_KEY", "")
    chunk_size: int = int(os.getenv("SAPA_CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(os.getenv("SAPA_CHUNK_OVERLAP", "220"))
    retrieval_k: int = int(os.getenv("SAPA_RETRIEVAL_K", "6"))


def get_config() -> AppConfig:
    return AppConfig()
