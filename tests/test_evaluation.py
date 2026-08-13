from __future__ import annotations

import unittest

from src.evaluation import calculate_metrics


class EvaluationTests(unittest.TestCase):
    def test_per_category_and_overall_metrics(self) -> None:
        results = calculate_metrics([
            {"category": "EMAIL", "outcome": "TP"},
            {"category": "EMAIL", "outcome": "FP"},
            {"category": "EMAIL", "outcome": "FN"},
            {"category": "EMAIL", "outcome": "TN"},
        ])
        self.assertEqual(0.5, results["EMAIL"].precision)
        self.assertEqual(0.5, results["EMAIL"].recall)
        self.assertEqual(0.5, results["OVERALL"].accuracy)
