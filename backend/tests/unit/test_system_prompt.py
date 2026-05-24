"""Unit tests for system prompt builder."""

from __future__ import annotations

from app.rag.guardrails.system_prompt import (
    build_system_prompt,
    format_context_block,
    wrap_user_query,
)


def test_wrap_user_query_xml() -> None:
    wrapped = wrap_user_query("Xin chào")
    assert wrapped.startswith("<user_query>")
    assert wrapped.endswith("</user_query>")
    assert "Xin chào" in wrapped


def test_format_context_block_document_tags() -> None:
    chunks = [
        {
            "citation_id": 1,
            "document_name": "Policy.pdf",
            "page_number": 5,
            "heading_context": "I. Overview",
            "text": "Employees get 12 days leave.",
        },
    ]
    block = format_context_block(chunks)
    assert "[1]" in block
    assert "<document_content>" in block
    assert "Policy.pdf" in block


def test_build_system_prompt_includes_context() -> None:
    prompt = build_system_prompt(
        numbered_context="[1] test",
        truncated_history="user: hi",
    )
    assert "BoostRAG Assistant" in prompt
    assert "[1] test" in prompt
    assert "IMMUTABLE" in prompt
