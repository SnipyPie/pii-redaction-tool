"""Occurrence-level precision, recall, and accuracy calculations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
import json
from pathlib import Path


@dataclass(frozen=True)
class MetricResult:
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int

    @property
    def precision(self) -> float | None:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else None

    @property
    def recall(self) -> float | None:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else None

    @property
    def accuracy(self) -> float | None:
        denominator = self.true_positive + self.false_positive + self.false_negative + self.true_negative
        return (self.true_positive + self.true_negative) / denominator if denominator else None


def calculate_metrics(reviewed_records: list[dict[str, object]]) -> dict[str, MetricResult]:
    """Calculate by category from reviewed records containing outcome and category.

    Expected outcomes are TP, FP, FN, or TN. Ground truth remains reviewer-owned.
    """
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"TP": 0, "FP": 0, "FN": 0, "TN": 0})
    for record in reviewed_records:
        category = str(record["category"])
        outcome = str(record["outcome"]).upper()
        if outcome not in totals[category]:
            raise ValueError(f"Unsupported evaluation outcome: {outcome}")
        totals[category][outcome] += 1
    results = {
        category: MetricResult(values["TP"], values["FP"], values["FN"], values["TN"])
        for category, values in totals.items()
    }
    overall = MetricResult(
        sum(item.true_positive for item in results.values()),
        sum(item.false_positive for item in results.values()),
        sum(item.false_negative for item in results.values()),
        sum(item.true_negative for item in results.values()),
    )
    results["OVERALL"] = overall
    return results


def load_ground_truth(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Ground truth must be a JSON list of reviewed occurrence records.")
    return data


def as_serializable(results: dict[str, MetricResult]) -> dict[str, dict[str, object]]:
    return {category: {**asdict(result), "precision": result.precision, "recall": result.recall, "accuracy": result.accuracy} for category, result in results.items()}
