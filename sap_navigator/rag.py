from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sap_navigator.chunking import chunk_documents
from sap_navigator.config import AppConfig
from sap_navigator.loaders import load_documents
from sap_navigator.models import IngestionReport, RetrievalResult
from sap_navigator.providers import build_chat_provider, build_embedding_provider
from sap_navigator.vector_store import PersistentVectorStore, VectorStoreStats


SYSTEM_PROMPT = """You are SAP Navigator, an AI consultant assistant focused on SAP Transportation Management (TM/TMS).

Answer like an SAP consultant working on discovery, architecture, and implementation support.
Rules:
- Prefer the supplied knowledge context over model memory.
- If the context is incomplete, say so explicitly and separate assumptions from sourced facts.
- Do not invent SAP configuration paths, transaction codes, or standard behavior when the context does not support them.
- When recommending a solution, state whether it is likely SAP standard, integration design, or project-specific customization.
- Cite relevant context snippets using [S1], [S2], and so on.
"""


@dataclass(slots=True)
class ChatResponse:
    answer: str
    results: list[RetrievalResult]


def build_store(config: AppConfig) -> PersistentVectorStore:
    embedding_provider = build_embedding_provider(
        config.embed_provider,
        model=config.embed_model,
        base_url=config.embed_base_url,
        api_key=config.embed_api_key,
    )
    return PersistentVectorStore(
        vector_dir=config.vector_dir,
        collection_name=config.collection_name,
        embedding_provider=embedding_provider,
        embedding_signature=f"{config.embed_provider}:{config.embed_model}",
    )


def ingest_knowledge_base(config: AppConfig, *, reset: bool = True) -> tuple[IngestionReport, VectorStoreStats]:
    documents, skipped_files = load_documents(config.knowledge_dir)
    chunks = chunk_documents(
        documents,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    store = build_store(config)
    stats = store.replace_collection(chunks) if reset else store.upsert_chunks(chunks)
    return IngestionReport(loaded_documents=documents, skipped_files=skipped_files, chunks=chunks), stats


def answer_question(
    config: AppConfig,
    question: str,
    history: list[dict[str, str]] | None = None,
    *,
    top_k: int | None = None,
    temperature: float = 0.1,
) -> ChatResponse:
    store = build_store(config)
    results = store.search(question, top_k=top_k or config.retrieval_k)
    context = _format_context(results)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history[-6:])

    user_prompt = f"""Question:
{question}

Retrieved context:
{context}

Answer with concise SAP-focused guidance and cite supporting sources like [S1], [S2]."""
    messages.append({"role": "user", "content": user_prompt})

    chat_provider = build_chat_provider(
        config.llm_provider,
        model=config.llm_model,
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
    )
    answer = chat_provider.chat(messages, temperature=temperature)
    return ChatResponse(answer=answer, results=results)


def ensure_knowledge_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _format_context(results: list[RetrievalResult]) -> str:
    if not results:
        return "No indexed context was retrieved."

    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        source = result.metadata.get("source_path", "unknown")
        heading = result.metadata.get("heading", "")
        blocks.append(
            f"[S{index}] Source: {source}\nHeading: {heading}\nContent:\n{result.content}"
        )
    return "\n\n".join(blocks)
