"""JSON audit serialization with PII-safe original-value hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections import Counter

from .models import AcceptedDetection, RejectedCandidate, Replacement

SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_audit(path: Path, input_path: Path, output_path: Path | None, accepted: list[AcceptedDetection], replacement_values: dict[str, Replacement], rejected: list[RejectedCandidate], warnings: list[str]) -> dict[str, object]:
    counts = Counter(detection.candidate.category for detection in accepted)
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "input": {"path": str(input_path), "sha256": sha256_file(input_path)},
        "output": None if output_path is None else {"path": str(output_path), "sha256": sha256_file(output_path)},
        "detected": [
            {
                "id": detection.detection_id,
                "category": detection.candidate.category,
                "original_sha256": sha256_text(detection.candidate.normalized_value),
                "replacement": replacement_values[detection.detection_id].value,
                "location": detection.candidate.location.coordinates(),
                "span": {"start": detection.candidate.start, "end": detection.candidate.end},
                "confidence": detection.candidate.confidence,
                "validation": list(detection.candidate.rationale),
            }
            for detection in accepted
        ],
        "skipped_candidates": [
            {
                "category": item.candidate.category,
                "original_sha256": sha256_text(item.candidate.normalized_value),
                "location": item.candidate.location.coordinates(),
                "reason": item.reason,
            }
            for item in rejected
        ],
        "warnings": warnings,
        "counts_by_category": dict(sorted(counts.items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
