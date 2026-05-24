"""Unit tests for parser factory mime routing."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.rag.ingestion.parsers import (
    DocxParser,
    PDFParser,
    TxtParser,
    XlsxParser,
    get_parser,
    supported_mime_types,
)


def test_supported_mime_types_includes_expected() -> None:
    mimes = supported_mime_types()
    assert "application/pdf" in mimes
    assert "text/plain" in mimes


@pytest.mark.parametrize(
    ("mime", "expected_cls"),
    [
        ("application/pdf", PDFParser),
        ("text/plain", TxtParser),
        (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            DocxParser,
        ),
        (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            XlsxParser,
        ),
    ],
)
def test_get_parser_routes_by_mime(mime: str, expected_cls: type) -> None:
    parser = get_parser(mime)
    assert isinstance(parser, expected_cls)


def test_get_parser_unknown_mime_raises() -> None:
    with pytest.raises(ValidationError):
        get_parser("application/x-unknown")
