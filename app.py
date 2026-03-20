from __future__ import annotations

from dataclasses import replace

import streamlit as st

from sap_navigator.config import AppConfig, get_config
from sap_navigator.rag import answer_question, ensure_knowledge_dir, ingest_knowledge_base, build_store


st.set_page_config(page_title="SAP Navigator", page_icon=":package:", layout="wide")


def main() -> None:
    base_config = get_config()
    config = _render_sidebar(base_config)
    ensure_knowledge_dir(config.knowledge_dir)

    st.title("SAP Navigator")
    st.caption("Local RAG prototype for SAP TM/TMS consultants, architects, and developers.")

    stats = build_store(config).stats()
    if stats.chunk_count == 0:
        st.warning("No indexed knowledge found yet. Use the sidebar to build the local index first.")
    elif stats.metadata.get("embedding_signature") != f"{config.embed_provider}:{config.embed_model}":
        st.warning(
            "The current embedding settings do not match the indexed collection. Rebuild the index or switch back to the original embedding model."
        )

    _render_index_panel(config, stats.chunk_count)
    _render_chat(config, has_index=stats.chunk_count > 0)


def _render_sidebar(base_config: AppConfig) -> AppConfig:
    with st.sidebar:
        st.header("Runtime")
        provider_options = ["lmstudio", "ollama", "openai"]
        llm_provider = st.selectbox(
            "LLM Provider",
            provider_options,
            index=provider_options.index(base_config.llm_provider) if base_config.llm_provider in provider_options else 0,
        )
        llm_model = st.text_input("LLM Model", value=base_config.llm_model)
        llm_base_url = st.text_input("LLM Base URL", value=base_config.llm_base_url)
        llm_api_key = st.text_input("LLM API Key", value=base_config.llm_api_key, type="password")

        embed_provider = st.selectbox(
            "Embedding Provider",
            provider_options,
            index=provider_options.index(base_config.embed_provider) if base_config.embed_provider in provider_options else 0,
        )
        embed_model = st.text_input("Embedding Model", value=base_config.embed_model)
        embed_base_url = st.text_input("Embedding Base URL", value=base_config.embed_base_url)
        embed_api_key = st.text_input("Embedding API Key", value=base_config.embed_api_key, type="password")

        retrieval_k = st.slider("Top-K Retrieval", min_value=3, max_value=12, value=base_config.retrieval_k)
        chunk_size = st.slider("Chunk Size", min_value=600, max_value=2200, step=100, value=base_config.chunk_size)
        chunk_overlap = st.slider("Chunk Overlap", min_value=100, max_value=400, step=20, value=base_config.chunk_overlap)

        st.divider()
        st.caption("Direct OneNote parsing is not included in this prototype. Export OneNote pages to PDF, DOCX, or Markdown before indexing.")

    return replace(
        base_config,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        embed_provider=embed_provider,
        embed_model=embed_model,
        embed_base_url=embed_base_url,
        embed_api_key=embed_api_key,
        retrieval_k=retrieval_k,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def _render_index_panel(config: AppConfig, existing_chunk_count: int) -> None:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Knowledge Base")
        st.write(f"Folder: `{config.knowledge_dir}`")
        st.write(f"Indexed chunks: `{existing_chunk_count}`")
    with col2:
        if st.button("Rebuild Index", use_container_width=True):
            try:
                with st.spinner("Extracting documents and rebuilding the vector index..."):
                    report, stats = ingest_knowledge_base(config, reset=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Index rebuild failed: {exc}")
            else:
                st.success(
                    f"Indexed {len(report.loaded_documents)} documents into {stats.chunk_count} chunks. Skipped {len(report.skipped_files)} files."
                )
                if report.skipped_files:
                    with st.expander("Skipped files"):
                        for skipped in report.skipped_files:
                            st.write(f"- `{skipped.path}`: {skipped.reason}")


def _render_chat(config: AppConfig, *, has_index: bool) -> None:
    st.subheader("Chat")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    top_bar_left, top_bar_right = st.columns([4, 1])
    with top_bar_right:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("Sources"):
                    for source in message["sources"]:
                        st.markdown(source)

    if not has_index:
        st.info("Build the local index first, then start asking SAP TM/TMS questions.")

    prompt = st.chat_input(
        "Ask about SAP TM/TMS design, processes, integrations, or configuration.",
        disabled=not has_index,
    )
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages[:-1]]
    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching the knowledge base and preparing the answer..."):
                response = answer_question(config, prompt, history, top_k=config.retrieval_k)
        except Exception as exc:  # noqa: BLE001
            error_message = f"Answer generation failed: {exc}"
            st.error(error_message)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_message,
                    "sources": [],
                }
            )
            return

        st.markdown(response.answer)
        source_lines = [
            f"[S{index}] `{result.metadata.get('title', 'Unknown')}` - `{result.metadata.get('source_path', 'unknown')}`"
            for index, result in enumerate(response.results, start=1)
        ]
        with st.expander("Sources"):
            for index, result in enumerate(response.results, start=1):
                st.markdown(
                    f"**[S{index}] {result.metadata.get('title', 'Unknown')}**  \n"
                    f"`{result.metadata.get('source_path', 'unknown')}`  \n"
                    f"{result.content[:900]}..."
                )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response.answer,
            "sources": source_lines,
        }
    )


if __name__ == "__main__":
    main()
