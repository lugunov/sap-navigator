from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class LoadedDocument:
    source_path: Path
    content: str
    source_type: str
    title: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SkippedFile:
    path: Path
    reason: str


@dataclass(slots=True)
class DocumentChunk:
    chunk_id: str
    source_path: Path
    content: str
    metadata: dict[str, str | int | float | bool]


@dataclass(slots=True)
class RetrievalResult:
    chunk_id: str
    content: str
    metadata: dict[str, str | int | float | bool]
    distance: float | None = None


@dataclass(slots=True)
class IngestionReport:
    loaded_documents: list[LoadedDocument]
    skipped_files: list[SkippedFile]
    chunks: list[DocumentChunk]

