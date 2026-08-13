"""Immutable records shared by extraction, detection, writing, and auditing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class TextLocation:
    key: str
    kind: str
    text: str
    section: int | None = None
    table: int | None = None
    row: int | None = None
    cell: int | None = None
    paragraph: int | None = None
    part: str | None = None
    context: tuple[tuple[str, str], ...] = ()

    def context_value(self, name: str) -> str:
        return dict(self.context).get(name, "")

    def coordinates(self) -> dict[str, object]:
        return {
            key: value
            for key, value in {
                "kind": self.kind,
                "section": self.section,
                "table": self.table,
                "row": self.row,
                "cell": self.cell,
                "paragraph": self.paragraph,
                "part": self.part,
            }.items()
            if value is not None
        }


@dataclass(frozen=True)
class CandidateSpan:
    category: str
    location: TextLocation
    start: int
    end: int
    raw_value: str
    normalized_value: str
    confidence: Confidence
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class AcceptedDetection:
    detection_id: str
    candidate: CandidateSpan


@dataclass(frozen=True)
class RejectedCandidate:
    candidate: CandidateSpan
    reason: str


@dataclass(frozen=True)
class Replacement:
    category: str
    normalized_original: str
    value: str


@dataclass(frozen=True)
class AuditRecord:
    detection: AcceptedDetection
    replacement: Replacement
    original_sha256: str


@dataclass(frozen=True)
class RunSummary:
    accepted: tuple[AcceptedDetection, ...] = ()
    rejected: tuple[RejectedCandidate, ...] = ()
    warnings: tuple[str, ...] = ()
    counts_by_category: dict[str, int] = field(default_factory=dict)
