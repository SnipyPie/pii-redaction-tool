"""Deterministic, non-identifying replacement generation."""

from __future__ import annotations

from datetime import date
import hashlib
from typing import Callable

from .models import Replacement

FIRST_NAMES = ("Aarav", "Diya", "Ishaan", "Kavya", "Rohan", "Meera", "Vihaan", "Anaya")
LAST_NAMES = ("Mehta", "Shah", "Kapoor", "Iyer", "Rao", "Nair", "Gupta", "Bose")


def luhn_check_digit(prefix: str) -> str:
    total = 0
    for index, character in enumerate(reversed(prefix), start=1):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return str((10 - total % 10) % 10)


class EntityStore:
    """Maps one normalized entity to one stable fake value for a run."""

    def __init__(self) -> None:
        self._mapping: dict[tuple[str, str], Replacement] = {}
        self._next_index: dict[str, int] = {}

    def replacement_for(self, category: str, normalized_original: str) -> Replacement:
        key = (category, normalized_original)
        if key not in self._mapping:
            index = self._next_index.get(category, 0) + 1
            self._next_index[category] = index
            self._mapping[key] = Replacement(category, normalized_original, self._make(category, index))
        return self._mapping[key]

    def _make(self, category: str, index: int) -> str:
        if category == "PERSON_NAME":
            return f"{FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]} {LAST_NAMES[(index - 1) % len(LAST_NAMES)]}"
        if category == "EMAIL":
            return f"user{index:03d}@example.test"
        if category == "PHONE":
            return f"+91 90000 {index:05d}"
        if category == "COMPANY":
            return f"Example Company {index:03d} Pvt. Ltd."
        if category == "ADDRESS":
            return f"{100 + index} Example Road, Example Nagar, Pune - 400001, Maharashtra, India"
        if category == "SSN":
            return f"900-01-{index:04d}"
        if category == "CREDIT_CARD":
            prefix = f"41111111111{index:03d}"  # 15 digits before Luhn check digit.
            number = prefix + luhn_check_digit(prefix)
            return " ".join(number[offset : offset + 4] for offset in range(0, 16, 4))
        if category == "DOB":
            return date(1980 + index % 25, (index - 1) % 12 + 1, (index - 1) % 27 + 1).strftime("%d %B %Y")
        if category == "IP_ADDRESS":
            return f"192.0.2.{index % 254 + 1}"
        raise ValueError(f"Unsupported PII category: {category}")
