"""ACL filter dataclass + Qdrant filter conversion.

Mọi vector search bắt buộc dùng `ACLFilter` — xem `docs/SECURITY.md` mục 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ACLFilter:
    """User ACL constraints loaded fresh từ DB mỗi request."""

    max_level: int
    groups: list[str]

    def to_qdrant_filter(self) -> dict[str, Any]:
        """Convert sang Qdrant filter spec — mandatory cho mọi search.

        Returns:
            Filter dict với must/should/minimum_should_match theo spec.
        """
        should_clauses: list[dict[str, Any]] = [
            {"is_empty": {"key": "allowed_groups"}},
        ]
        if self.groups:
            should_clauses.append(
                {"key": "allowed_groups", "match": {"any": self.groups}},
            )

        return {
            "must": [
                {"key": "required_level", "range": {"lte": self.max_level}},
            ],
            "should": should_clauses,
            "minimum_should_match": 1,
        }
