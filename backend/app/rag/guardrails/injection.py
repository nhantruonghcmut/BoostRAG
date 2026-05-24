"""Prompt injection detection + input sanitization (Layer 1)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns phổ biến — case-insensitive
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
            re.IGNORECASE,
        ),
    ),
    (
        "role_override",
        re.compile(
            r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are)|switch\s+to\s+role)",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_reveal",
        re.compile(
            r"(reveal|show|print|output|repeat)\s+(your\s+)?(system\s+)?prompt",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_dan",
        re.compile(r"\bDAN\b|\bjailbreak\b|\bdeveloper\s+mode\b", re.IGNORECASE),
    ),
    (
        "xml_escape",
        re.compile(r"</?\s*user_query\s*>|</?\s*system\s*>|</?\s*document_content\s*>", re.IGNORECASE),
    ),
    (
        "instruction_injection",
        re.compile(
            r"(\[INST\]|\[/INST\]|<<SYS>>|<\|im_start\|>|<\|im_end\|>)",
            re.IGNORECASE,
        ),
    ),
]

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EXCESSIVE_NEWLINES_RE = re.compile(r"\n{4,}")


@dataclass(frozen=True)
class InjectionResult:
    """Kết quả kiểm tra injection."""

    is_injection: bool
    matched_patterns: list[str]
    sanitized_text: str


def sanitize_input(text: str, *, max_length: int = 8000) -> str:
    """Strip control chars, normalize whitespace, truncate.

    Args:
        text: Raw user input.
        max_length: Hard cap on input length.

    Returns:
        Sanitized string safe to wrap in XML tags.
    """
    cleaned = text.strip()
    cleaned = _CONTROL_CHARS_RE.sub("", cleaned)
    cleaned = _EXCESSIVE_NEWLINES_RE.sub("\n\n\n", cleaned)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def detect_injection(text: str) -> InjectionResult:
    """Detect known injection patterns in sanitized text.

    Args:
        text: Input (should be sanitized first).

    Returns:
        InjectionResult with matched pattern names.
    """
    sanitized = sanitize_input(text)
    matched: list[str] = []
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(sanitized):
            matched.append(name)
    return InjectionResult(
        is_injection=len(matched) > 0,
        matched_patterns=matched,
        sanitized_text=sanitized,
    )
