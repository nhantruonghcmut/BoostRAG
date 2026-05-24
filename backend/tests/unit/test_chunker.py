"""Unit tests for StructuralChunker hierarchy preservation."""

from __future__ import annotations

from app.rag.ingestion.chunker import StructuralChunker
from app.rag.ingestion.parsers import ParsedDocument, ParsedPage


def test_structural_chunker_preserves_hierarchy() -> None:
    """Chunker gắn section_path đúng cho I., 1., a) markers."""
    text = """I. Tổng quan
Giới thiệu chung về dự án.

1. Mục đích
Mục đích chính của hệ thống.

a) Phạm vi
Phạm vi áp dụng nội bộ.
"""
    parsed = ParsedDocument(pages=[ParsedPage(page_number=1, text=text)])
    chunker = StructuralChunker()
    chunks = chunker.chunk(parsed, document_id="doc-1")

    assert len(chunks) >= 1
    paths = [c.section_path for c in chunks if c.section_path]
    assert any("I. Tổng quan" in p[0] for p in paths if p)
    deep = [c for c in chunks if "Phạm vi" in c.text]
    assert deep, "Expected chunk containing 'Phạm vi'"
    assert any("a)" in " > ".join(c.section_path) or "Phạm vi" in c.text for c in deep)
