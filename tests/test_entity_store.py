from __future__ import annotations

import unittest

from src.entity_store import EntityStore


def luhn_valid(value: str) -> bool:
    digits = [int(char) for char in value if char.isdigit()]
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


class EntityStoreTests(unittest.TestCase):
    def test_repeat_is_stable_and_distinct_is_different(self) -> None:
        store = EntityStore()
        first = store.replacement_for("EMAIL", "jane@example.com").value
        self.assertEqual(first, store.replacement_for("EMAIL", "jane@example.com").value)
        self.assertNotEqual(first, store.replacement_for("EMAIL", "john@example.com").value)

    def test_safe_formats(self) -> None:
        store = EntityStore()
        self.assertTrue(store.replacement_for("EMAIL", "x").value.endswith("@example.test"))
        self.assertTrue(luhn_valid(store.replacement_for("CREDIT_CARD", "x").value))
        self.assertTrue(store.replacement_for("IP_ADDRESS", "x").value.startswith("192.0.2."))
        self.assertNotIn("original", store.replacement_for("COMPANY", "original").value.lower())
