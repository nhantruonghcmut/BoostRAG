"""Structural chunker — giữ ngữ cảnh hierarchical (I., 1., a)).

Xem `docs/RAG_PIPELINE.md` §1.3 cho algorithm chi tiết.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.rag.ingestion.parsers import ParsedDocument


@dataclass(frozen=True)
class Chunk:
    """Một chunk text sẵn sàng embed."""

    chunk_id: str
    document_id: str
    text: str
    page_number: int | None
    section_path: list[str]
    heading_context: str
    char_start: int
    char_end: int
    token_count: int


@runtime_checkable
class Chunker(Protocol):
    """Protocol cho chunking strategy."""

    def chunk(self, parsed: ParsedDocument, document_id: str) -> list[Chunk]: ...


# Hierarchical marker patterns (order matters for detection)
_ROMAN_RE = re.compile(r"^([IVXLC]+)\.\s+(.+)$")
_NUMERIC_RE = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)$")
_LETTER_LOWER_RE = re.compile(r"^([a-z])[\.\)]\s+(.+)$")
_LETTER_UPPER_RE = re.compile(r"^([A-Z])\.\s+(.+)$")
_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_BULLET_RE = re.compile(r"^[\*\-•]\s+(.+)$")


def _marker_level(line: str) -> tuple[int, str] | None:
    """Detect hierarchical marker — return (level, full_heading_text) or None."""
    stripped = line.strip()
    if not stripped:
        return None

    m = _MD_HEADING_RE.match(stripped)
    if m:
        return len(m.group(1)), stripped

    m = _ROMAN_RE.match(stripped)
    if m:
        return 1, stripped

    m = _NUMERIC_RE.match(stripped)
    if m:
        depth = m.group(1).count(".") + 1
        return depth + 1, stripped

    m = _LETTER_LOWER_RE.match(stripped)
    if m:
        return 4, stripped

    m = _LETTER_UPPER_RE.match(stripped)
    if m:
        return 3, stripped

    if _BULLET_RE.match(stripped):
        return None

    return None


def _count_tokens(text: str) -> int:
    """Approximate token count — fallback word-based split."""
    if not text.strip():
        return 0
    return len(text.split())


def _render_heading_context(section_path: list[str]) -> str:
    return " > ".join(section_path)


def _split_text(
    text: str, chunk_size: int, chunk_overlap: int
) -> list[tuple[str, int, int]]:
    """Recursive split by separators — return (text, char_start, char_end)."""
    separators = ["\n\n", "\n", ". ", " ", ""]
    if _count_tokens(text) <= chunk_size:
        return [(text, 0, len(text))]

    for sep in separators:
        if sep and sep not in text:
            continue
        parts = text.split(sep) if sep else list(text)
        if len(parts) <= 1 and sep != "":
            continue

        chunks: list[tuple[str, int, int]] = []
        current = ""
        current_start = 0
        offset = 0

        for i, part in enumerate(parts):
            piece = part if sep == "" else (part + sep if i < len(parts) - 1 else part)
            candidate = current + piece
            if _count_tokens(candidate) <= chunk_size or not current:
                current = candidate
            else:
                start = current_start
                end = start + len(current)
                chunks.append((current.strip(), start, end))
                overlap_text = current
                if chunk_overlap > 0:
                    words = overlap_text.split()
                    overlap_words = (
                        words[-chunk_overlap:] if len(words) > chunk_overlap else words
                    )
                    overlap_text = " ".join(overlap_words)
                current_start = end - len(overlap_text)
                current = overlap_text + piece
            offset += len(piece)

        if current.strip():
            start = current_start
            end = start + len(current)
            chunks.append((current.strip(), start, end))

        if chunks:
            return chunks

    mid = len(text) // 2
    return [(text[:mid].strip(), 0, mid), (text[mid:].strip(), mid, len(text))]


class StructuralChunker:
    """Default chunker giữ ngữ cảnh hierarchical."""

    chunk_size: int = 800
    chunk_overlap: int = 100

    def chunk(self, parsed: ParsedDocument, document_id: str) -> list[Chunk]:
        """Chunk parsed document với section_path tracking."""
        all_chunks: list[Chunk] = []
        global_offset = 0

        for page in parsed.pages:
            lines = page.text.splitlines()
            section_stack: list[tuple[int, str]] = []
            paragraph_lines: list[str] = []
            paragraph_start = global_offset

            def flush_paragraph() -> None:
                nonlocal paragraph_start, global_offset
                if not paragraph_lines:
                    return
                para_text = "\n".join(paragraph_lines).strip()
                if not para_text:
                    paragraph_lines.clear()
                    return

                section_path = [title for _, title in section_stack]
                heading_context = _render_heading_context(section_path)

                for sub_text, rel_start, rel_end in _split_text(
                    para_text,
                    self.chunk_size,
                    self.chunk_overlap,
                ):
                    if not sub_text.strip():
                        continue
                    abs_start = paragraph_start + rel_start
                    abs_end = paragraph_start + rel_end
                    all_chunks.append(
                        Chunk(
                            chunk_id=str(uuid.uuid4()),
                            document_id=document_id,
                            text=sub_text,
                            page_number=page.page_number,
                            section_path=list(section_path),
                            heading_context=heading_context,
                            char_start=abs_start,
                            char_end=abs_end,
                            token_count=_count_tokens(sub_text),
                        ),
                    )

                global_offset = paragraph_start + len(para_text)
                paragraph_lines.clear()
                paragraph_start = global_offset

            for line in lines:
                marker = _marker_level(line)
                if marker is not None:
                    flush_paragraph()
                    level, heading_text = marker
                    while section_stack and section_stack[-1][0] >= level:
                        section_stack.pop()
                    section_stack.append((level, heading_text))
                    paragraph_lines.append(line)
                else:
                    paragraph_lines.append(line)

            flush_paragraph()
            global_offset += 1

        if not all_chunks and parsed.pages:
            combined = "\n\n".join(p.text for p in parsed.pages if p.text.strip())
            if combined.strip():
                for sub_text, rel_start, rel_end in _split_text(
                    combined,
                    self.chunk_size,
                    self.chunk_overlap,
                ):
                    all_chunks.append(
                        Chunk(
                            chunk_id=str(uuid.uuid4()),
                            document_id=document_id,
                            text=sub_text,
                            page_number=parsed.pages[0].page_number,
                            section_path=[],
                            heading_context="",
                            char_start=rel_start,
                            char_end=rel_end,
                            token_count=_count_tokens(sub_text),
                        ),
                    )

        return all_chunks
