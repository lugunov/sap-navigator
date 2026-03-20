# SAP Navigator

Local RAG prototype for SAP consultants, architects, and developers, with the first domain focused on SAP Transportation Management (TM/TMS).

## What this prototype does

- Indexes local SAP knowledge sources into a persistent vector database
- Supports chat-style Q&A with cited source chunks
- Works well for SAP implementation knowledge such as process design, integration patterns, configuration guidance, and workshop notes
- Keeps everything local on your machine except the model provider you choose

## Recommended approach

### 1. Vector database

Use `Chroma` for the prototype.

Why:

- Very easy local setup
- Persistent on disk
- Good enough for a single-user workstation prototype
- Simple metadata filtering and collection management

When to change later:

- Move to `Qdrant` if you need multi-user access, a server deployment, hybrid search, or stronger operational controls

### 2. Embeddings

Best easy local option if you use LM Studio:

- `LM Studio` with an embedding model exposed through its local OpenAI-compatible API

Why:

- Fully local
- Easy to run
- Good enough for technical documentation

Alternative local option:

- `Ollama` + `nomic-embed-text`

Best quality/ease if cloud is acceptable:

- `OpenAI` + `text-embedding-3-small`

Why:

- Strong retrieval quality
- Very simple operationally
- Good cost/performance for a prototype

### 3. Chunking strategy

Use structure-aware chunks instead of raw fixed windows.

Recommended settings in this prototype:

- Chunk size: `1200` characters
- Overlap: `220` characters

Rules:

- Split on headings and paragraph boundaries first
- Preserve page or slide markers for citations
- Keep headings attached to the following content
- Use overlap to avoid breaking process steps and configuration explanations

This works well for SAP material because:

- SAP documentation is section-heavy
- Process explanations often span a few paragraphs
- Configuration notes frequently depend on the previous section

### 4. Source handling

Supported directly:

- `PDF`
- `DOCX`
- `PPTX`
- `TXT`
- `MD`
- `DOC` via conversion fallback using `textutil` or `LibreOffice`

Recommended workaround for OneNote:

- Export OneNote pages or sections to `PDF`, `DOCX`, or `Markdown`
- Put them into `knowledge-base/`

For personal knowledge:

- Keep short topic notes in Markdown files such as `knowledge-base/personal-notes/tm-charges.md`

## Architecture

```text
knowledge-base/ documents
        |
        v
 loaders (pdf/docx/pptx/txt/doc)
        |
        v
 structure-aware chunking
        |
        v
 embeddings (Ollama or OpenAI)
        |
        v
 Chroma persistent vector store
        |
        v
 Streamlit chat UI
        |
        v
 answer + cited source chunks
```

## Quick start

### 1. Create a virtual environment

Recommended Python version: `3.11` or `3.12`

Some ML-related packages may lag on very new Python versions, so avoid using the newest interpreter for the first setup.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure model providers

Copy `.env.example` to `.env`.

Default config in `.env.example` assumes `LM Studio`:

```bash
cp .env.example .env
```

In LM Studio:

- Start the local server
- Load one chat model
- Load one embedding model
- Copy the exact model identifiers into `.env`

LM Studio uses an OpenAI-compatible endpoint, so this prototype can call it directly.

If you prefer OpenAI:

- Set `SAPA_LLM_PROVIDER=openai`
- Set `SAPA_LLM_MODEL` to a chat model
- Set `SAPA_EMBED_PROVIDER=openai`
- Set `SAPA_EMBED_MODEL=text-embedding-3-small`
- Export `OPENAI_API_KEY`

If you prefer Ollama:

- Set `SAPA_LLM_PROVIDER=ollama`
- Set `SAPA_LLM_MODEL=qwen2.5:7b-instruct`
- Set `SAPA_LLM_BASE_URL=http://127.0.0.1:11434`
- Set `SAPA_EMBED_PROVIDER=ollama`
- Set `SAPA_EMBED_MODEL=nomic-embed-text`
- Set `SAPA_EMBED_BASE_URL=http://127.0.0.1:11434`

### 3. Add your SAP knowledge

Put source files into [`knowledge-base`](/Users/andrey.lugunov/dev/sap-navigator/knowledge-base).

Suggested structure:

```text
knowledge-base/
  tm-processes/
  integration/
  workshop-notes/
  personal-notes/
```

### 4. Build the index

```bash
python ingest.py
```

### 5. Start the chat UI

```bash
streamlit run app.py
```

## What to add next

- Metadata tags such as module, sub-process, release, and project
- Hybrid retrieval with keyword + vector search
- Reranking for better precision on long SAP documents
- Separate collections for TM, EWM, GTS, and cross-module integration
- User feedback capture for improving prompts and chunking

## Files

- UI: [`app.py`](/Users/andrey.lugunov/dev/sap-navigator/app.py)
- Indexer CLI: [`ingest.py`](/Users/andrey.lugunov/dev/sap-navigator/ingest.py)
- Core RAG logic: [`sap_navigator/rag.py`](/Users/andrey.lugunov/dev/sap-navigator/sap_navigator/rag.py)
- Document loaders: [`sap_navigator/loaders.py`](/Users/andrey.lugunov/dev/sap-navigator/sap_navigator/loaders.py)
- Chunking logic: [`sap_navigator/chunking.py`](/Users/andrey.lugunov/dev/sap-navigator/sap_navigator/chunking.py)
- Provider adapters: [`sap_navigator/providers.py`](/Users/andrey.lugunov/dev/sap-navigator/sap_navigator/providers.py)
- Vector store: [`sap_navigator/vector_store.py`](/Users/andrey.lugunov/dev/sap-navigator/sap_navigator/vector_store.py)
