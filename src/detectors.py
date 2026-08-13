"""Conservative, category-specific PII candidate detectors."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import re

from .models import AcceptedDetection, CandidateSpan, RejectedCandidate, TextLocation

CATEGORIES = (
    "PERSON_NAME", "EMAIL", "PHONE", "COMPANY", "ADDRESS", "SSN", "CREDIT_CARD", "DOB", "IP_ADDRESS"
)
PRIORITY = {category: index for index, category in enumerate((
    "EMAIL", "IP_ADDRESS", "SSN", "CREDIT_CARD", "PHONE", "DOB", "ADDRESS", "COMPANY", "PERSON_NAME"
))}

EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9_-])")
PHONE_RE = re.compile(r"(?<![A-Za-z0-9])(?:\+\s?91[\s-]?)?(?:\(?0?\d{2,4}\)?[\s-]?)?\d{3,5}[\s-]\d{4,6}(?![A-Za-z0-9])")
SSN_RE = re.compile(r"(?<!\d)(\d{3}-\d{2}-\d{4})(?!\d)")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
COMPANY_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&().,'-]*\s+){0,10}(?:Private\s+Limited|Pvt\.\s*Ltd\.?|Limited|Ltd\.?|LLP|Inc\.?|Corporation)\b"
)
ROLE_NAME_RE = re.compile(
    r"(?i)(?:contact\s+person|director|promoter|chief\s+executive\s+officer|CEO|chief\s+financial\s+officer|CFO|company\s+secretary|compliance\s+officer|chairman|managing\s+director|joint\s+managing\s+director|whole[- ]time\s+director|independent\s+director)\s*[:,-]\s*([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){1,3})"
)
DOB_RE = re.compile(
    r"(?i)\b(?:date\s+of\s+birth|d\.o\.b\.|dob|born|birth\s+date)\s*[:,-]?\s*"
    r"((?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:\d{1,2}\s+[A-Za-z]+\s+\d{4})|(?:[A-Za-z]+\s+\d{1,2},?\s+\d{4}))"
)

PERSON_STOPWORDS = {"bank", "limited", "company", "trust", "exchange", "securities", "private", "international", "india", "llp", "personnel", "managerial", "promoters", "directors", "shareholders", "offer", "prospectus", "management", "regulations", "factors", "market", "research", "report", "group", "members", "shares", "equity", "statutory", "regulatory", "financial", "business", "disclosures", "overview", "discussion", "analysis", "analytics", "contact", "person", "running", "services", "products", "officer", "selling", "shareholder", "committee", "panel", "enterprises", "industries", "solutions", "ventures", "holdings", "general", "trade", "act", "structure", "capital", "sale", "foreign", "technical", "central", "national", "regional", "global", "local", "executive", "independent", "whole", "policy", "materiality", "corporate", "matters", "certain", "history", "arrangements", "promoter", "director"}
PERSON_CONTEXT = ("promoter", "director", "contact person", "company secretary", "compliance officer", "chief executive", "chief financial", "key managerial personnel", "senior management")
CONTEXTUAL_NAME_RE = re.compile(r"\b([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){1,3})\b")
COMPANY_CONTEXT = ("registrar", "banker", "auditor", "lead manager", "book running", "company", "entity", "issuer", "underwriter")
ADDRESS_LABELS = ("registered office", "corporate office", "residential address", "contact address", "address")
ADDRESS_SIGNALS = ("road", "rd", "street", "marg", "lane", "floor", "flat", "tower", "building", "society", "nagar", "pune", "mumbai", "maharashtra", "india", "pin", "apartment")
PROTECTED_CONTEXT = ("₹", "%", "million", "fiscal", "financial year", "share", "equity", "cin", "din", "registration", "sebi", "isin", "page", "offer", "peer review", "firm registration")
CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def _candidate(category: str, location: TextLocation, start: int, end: int, normalized: str, confidence: str, *rationale: str) -> CandidateSpan:
    return CandidateSpan(category, location, start, end, location.text[start:end], normalized, confidence, tuple(rationale))


def _surrounding(location: TextLocation, start: int, end: int) -> str:
    return location.text[max(0, start - 45) : min(len(location.text), end + 45)].lower()


def _normalize_digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _luhn_valid(value: str) -> bool:
    digits = _normalize_digits(value)
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, character in enumerate(reversed(digits)):
        digit = int(character)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _phone_context(location: TextLocation, start: int, end: int) -> bool:
    return any(token in _surrounding(location, start, end) for token in ("telephone", "phone", "mobile", "tel", "contact"))


def _protected_numeric(location: TextLocation, start: int, end: int) -> str | None:
    nearby = _surrounding(location, start, end)
    value = location.text[start:end]
    if CIN_RE.search(value) or PAN_RE.search(value):
        return "known_identifier_shape"
    if re.fullmatch(r"20\d{2}[-/]20\d{2}", value.strip()):
        return "financial_year"
    if any(token in nearby for token in PROTECTED_CONTEXT):
        return "protected_numeric_context"
    if re.fullmatch(r"\d{1,4}", value.strip()):
        return "short_numeric_value"
    return None


def detect_email(location: TextLocation) -> list[CandidateSpan]:
    return [_candidate("EMAIL", location, match.start(), match.end(), match.group(0).lower(), "high", "bounded_email_shape") for match in EMAIL_RE.finditer(location.text)]


def detect_phone(location: TextLocation) -> list[CandidateSpan]:
    found: list[CandidateSpan] = []
    for match in PHONE_RE.finditer(location.text):
        raw = match.group(0)
        digits = _normalize_digits(raw)
        has_country = raw.lstrip().startswith("+")
        if not 10 <= len(digits) <= 13:
            continue
        if not has_country and not _phone_context(location, match.start(), match.end()):
            continue
        found.append(_candidate("PHONE", location, match.start(), match.end(), digits, "high" if _phone_context(location, match.start(), match.end()) else "medium", "plausible_indian_phone_digits"))
    return found


def detect_ssn(location: TextLocation) -> list[CandidateSpan]:
    found: list[CandidateSpan] = []
    for match in SSN_RE.finditer(location.text):
        first, middle, last = match.group(1).split("-")
        if first in {"000", "666"} or first.startswith("9") or middle == "00" or last == "0000":
            continue
        found.append(_candidate("SSN", location, match.start(1), match.end(1), match.group(1), "high", "strict_ssn_shape"))
    return found


def detect_credit_card(location: TextLocation) -> list[CandidateSpan]:
    return [
        _candidate("CREDIT_CARD", location, match.start(), match.end(), _normalize_digits(match.group(0)), "high", "luhn_valid_card_shape")
        for match in CARD_RE.finditer(location.text)
        if _luhn_valid(match.group(0))
    ]


def detect_ip_address(location: TextLocation) -> list[CandidateSpan]:
    found: list[CandidateSpan] = []
    for match in IP_RE.finditer(location.text):
        value = match.group(0)
        if all(0 <= int(octet) <= 255 for octet in value.split(".")):
            found.append(_candidate("IP_ADDRESS", location, match.start(), match.end(), value, "high", "valid_ipv4_octets"))
    return found


def detect_dob(location: TextLocation) -> list[CandidateSpan]:
    found: list[CandidateSpan] = []
    for match in DOB_RE.finditer(location.text):
        value = match.group(1)
        if _parse_date(value):
            start, end = match.start(1), match.end(1)
            found.append(_candidate("DOB", location, start, end, _normalize_text(value), "high", "explicit_birth_context", "parseable_date"))
    return found


def _parse_date(value: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%B %d %Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _looks_like_person(value: str) -> bool:
    words = re.findall(r"[A-Za-z]+", value)
    if not (2 <= len(words) <= 4):
        return False
    if any(word.lower() in PERSON_STOPWORDS for word in words):
        return False
    # Reject if any space-delimited token ends with a period: this prevents
    # CONTEXTUAL_NAME_RE from capturing across sentence boundaries, e.g.
    # "Shetty. For" where 'Shetty.' is a regex token ending with '.'.
    if any(token.endswith(".") for token in value.split()):
        return False
    return True


def detect_person_name(location: TextLocation) -> list[CandidateSpan]:
    found: list[CandidateSpan] = []
    for match in ROLE_NAME_RE.finditer(location.text):
        start, end = match.start(1), match.end(1)
        value = match.group(1).strip()
        if _looks_like_person(value):
            found.append(_candidate("PERSON_NAME", location, start, end, _normalize_text(value), "high", "person_role_label"))
    headers = location.context_value("table_headers").lower()
    if any(label in headers for label in ("name", "director", "promoter", "contact person")):
        value = location.text.strip()
        offset = location.text.find(value)
        if _looks_like_person(value):
            found.append(_candidate("PERSON_NAME", location, offset, offset + len(value), _normalize_text(value), "high", "person_oriented_table_column"))
    # This is intentionally context-gated: it is not a document-wide title-case rule.
    # It handles explicit promoter/director/management lists written as prose.
    # IMPORTANT: the context trigger must appear NEAR the candidate (within 100 chars)
    # to avoid matching corporate/financial boilerplate in long paragraphs that happen
    # to mention "promoter" or "director" somewhere far from the actual name.
    text_lower = location.text.lower()
    if any(token in text_lower for token in PERSON_CONTEXT):
        for match in CONTEXTUAL_NAME_RE.finditer(location.text):
            value = match.group(1)
            if not _looks_like_person(value):
                continue
            ms, me = match.start(1), match.end(1)
            window_start = max(0, ms - 100)
            window_end = min(len(location.text), me + 100)
            nearby = location.text[window_start:window_end].lower()
            if any(token in nearby for token in PERSON_CONTEXT):
                found.append(_candidate("PERSON_NAME", location, ms, me, _normalize_text(value), "medium", "strong_person_context"))
    return found


def detect_company(location: TextLocation) -> list[CandidateSpan]:
    found: list[CandidateSpan] = []
    context = (location.text + " " + location.context_value("table_headers")).lower()
    for match in COMPANY_RE.finditer(location.text):
        value = match.group(0).strip()
        short_entity_cell = len(location.text.strip()) <= 110 and len(value) >= 8
        if short_entity_cell or any(token in context for token in COMPANY_CONTEXT):
            found.append(_candidate("COMPANY", location, match.start(), match.end(), _normalize_text(value), "medium", "legal_suffix", "entity_context" if not short_entity_cell else "short_entity_cell"))
    return found


def detect_address(location: TextLocation) -> list[CandidateSpan]:
    text_lower = location.text.lower()
    headers = location.context_value("table_headers").lower()
    is_address_column = "address" in headers
    label_match = next((re.search(rf"(?i)\b{re.escape(label)}\s*:\s*", location.text) for label in ADDRESS_LABELS if re.search(rf"(?i)\b{re.escape(label)}\s*:\s*", location.text)), None)
    if not is_address_column and not label_match:
        return []
    start = label_match.end() if label_match else 0
    value = location.text[start:].strip()
    offset = start + len(location.text[start:]) - len(location.text[start:].lstrip())
    signals = sum(1 for signal in ADDRESS_SIGNALS if re.search(rf"\b{re.escape(signal)}\b", value.lower()))
    if signals < 2 and not re.search(r"\b\d{5,6}\b", value):
        return []
    return [_candidate("ADDRESS", location, offset, offset + len(value), _normalize_text(value), "high" if is_address_column else "medium", "address_context", f"address_signals:{signals}")]


DETECTOR_FUNCTIONS = {
    "PERSON_NAME": detect_person_name,
    "EMAIL": detect_email,
    "PHONE": detect_phone,
    "COMPANY": detect_company,
    "ADDRESS": detect_address,
    "SSN": detect_ssn,
    "CREDIT_CARD": detect_credit_card,
    "DOB": detect_dob,
    "IP_ADDRESS": detect_ip_address,
}


def detect_locations(locations: Iterable[TextLocation], categories: set[str] | None = None) -> list[CandidateSpan]:
    selected = set(CATEGORIES) if categories is None else categories
    candidates: list[CandidateSpan] = []
    for location in locations:
        for category in CATEGORIES:
            if category in selected:
                candidates.extend(DETECTOR_FUNCTIONS[category](location))
    return candidates


def select_candidates(candidates: Iterable[CandidateSpan]) -> tuple[list[AcceptedDetection], list[RejectedCandidate]]:
    accepted: list[AcceptedDetection] = []
    rejected: list[RejectedCandidate] = []
    occupied: dict[str, list[tuple[int, int]]] = {}
    ordered = sorted(candidates, key=lambda item: (item.location.key, item.start, -(item.end - item.start), PRIORITY[item.category]))
    for candidate in ordered:
        if candidate.category in {"PHONE", "CREDIT_CARD", "SSN"}:
            reason = _protected_numeric(candidate.location, candidate.start, candidate.end)
            if reason:
                rejected.append(RejectedCandidate(candidate, reason))
                continue
        spans = occupied.setdefault(candidate.location.key, [])
        if any(candidate.start < end and start < candidate.end for start, end in spans):
            rejected.append(RejectedCandidate(candidate, "overlaps_higher_priority_detection"))
            continue
        spans.append((candidate.start, candidate.end))
        accepted.append(AcceptedDetection(f"det-{len(accepted) + 1:04d}", candidate))
    return accepted, rejected
