from __future__ import annotations

import hashlib
import re

from sap_navigator.models import DocumentChunk, LoadedDocument


HEADING_PATTERN = re.compile(r"^(?:[A-Z][A-Za-z0-9 /,&()_-]{2,90}|[0-9]+(?:\.[0-9]+)*\s+.+)$")


def chunk_documents(
    documents: list[LoadedDocument],
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for document in documents:
        sections = _split_into_sections(document.content)
        chunk_bodies = _pack_sections(sections, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        for index, body in enumerate(chunk_bodies):
            chunk_id = _make_chunk_id(document.source_path, index, body)
            heading = _infer_heading(body)
            metadata: dict[str, str | int | float | bool] = {
                **document.metadata,
                "title": document.title,
                "source_type": document.source_type,
                "chunk_index": index,
                "heading": heading,
            }
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    source_path=document.source_path,
                    content=body,
                    metadata=metadata,
                )
            )
    return chunks


def _split_into_sections(text: str) -> list[str]:
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    sections: list[str] = []
    current_heading: str | None = None

    for part in parts:
        first_line = part.splitlines()[0].strip()
        if HEADING_PATTERN.match(first_line) and len(part.splitlines()) <= 3:
            current_heading = first_line
            sections.append(part)
            continue

        if current_heading and not part.startswith(current_heading):
            sections.append(f"{current_heading}\n{part}")
            continue

        sections.append(part)

    return sections


def _pack_sections(sections: list[str], *, chunk_size: int, chunk_overlap: int) -> list[str]:
    if not sections:
        return []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) > chunk_size:
            split_sections = _split_large_section(section, chunk_size)
        else:
            split_sections = [section]

        for piece in split_sections:
            piece_length = len(piece) + 2
            if current_parts and current_length + piece_length > chunk_size:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = _overlap_parts(current_parts, chunk_overlap)
                current_length = _joined_length(current_parts)

            current_parts.append(piece)
            current_length += piece_length

    if current_parts:
        chunks.append("\n\n".join(current_parts).strip())

    return [chunk for chunk in chunks if chunk]


def _split_large_section(section: str, chunk_size: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", section)
    if len(sentences) == 1:
        return [section[i : i + chunk_size] for i in range(0, len(section), chunk_size)]

    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            pieces.append(current.strip())
        current = sentence

    if current.strip():
        pieces.append(current.strip())

    return pieces


def _overlap_parts(parts: list[str], chunk_overlap: int) -> list[str]:
    overlap_parts: list[str] = []
    total = 0
    for part in reversed(parts):
        part_length = len(part) + 2
        if overlap_parts and total + part_length > chunk_overlap:
            break
        overlap_parts.insert(0, part)
        total += part_length
    return overlap_parts


def _joined_length(parts: list[str]) -> int:
    if not parts:
        return 0
    return sum(len(part) for part in parts) + (len(parts) - 1) * 2


def _make_chunk_id(source_path, index: int, body: str) -> str:
    digest = hashlib.sha1(f"{source_path}:{index}:{body}".encode("utf-8")).hexdigest()
    return digest[:20]


def _infer_heading(content: str) -> str:
    first_line = content.splitlines()[0].strip() if content else ""
    return first_line[:120]

