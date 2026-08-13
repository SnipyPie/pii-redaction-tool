from __future__ import annotations

import unittest

from src.detectors import detect_locations, select_candidates
from src.models import TextLocation


def location(text: str, headers: str = "") -> TextLocation:
    return TextLocation("test", "paragraph", text, context=(("table_headers", headers),))


class DetectorTests(unittest.TestCase):
    def categories(self, text: str, headers: str = "") -> set[str]:
        accepted, _ = select_candidates(detect_locations([location(text, headers)]))
        return {item.candidate.category for item in accepted}

    def test_email(self) -> None:
        self.assertIn("EMAIL", self.categories("Write to jane.doe@example.com."))

    def test_phone_requires_context_without_country_prefix(self) -> None:
        self.assertIn("PHONE", self.categories("Telephone: 20 4505 3237"))
        self.assertNotIn("PHONE", self.categories("Capacity was 20 4505 3237 units."))

    def test_ssn_and_credit_card(self) -> None:
        categories = self.categories("SSN 123-45-6789 and card 4111 1111 1111 1111")
        self.assertIn("SSN", categories)
        self.assertIn("CREDIT_CARD", categories)

    def test_ip_validation(self) -> None:
        self.assertIn("IP_ADDRESS", self.categories("IP address: 192.168.0.1"))
        self.assertNotIn("IP_ADDRESS", self.categories("Version 999.999.999.999"))

    def test_dob_requires_birth_context(self) -> None:
        self.assertIn("DOB", self.categories("Date of Birth: 12 January 1985"))
        self.assertNotIn("DOB", self.categories("Dated December 10, 2025"))

    def test_person_requires_strong_context(self) -> None:
        self.assertIn("PERSON_NAME", self.categories("Contact Person: John Smith; Telephone: +91 90000 00001"))
        self.assertIn("PERSON_NAME", self.categories("Jane Doe", "Name | Designation | Address"))
        self.assertNotIn("PERSON_NAME", self.categories("This Red Herring Prospectus describes Market Growth."))

    def test_company_and_address_context(self) -> None:
        self.assertIn("COMPANY", self.categories("Example Holdings Private Limited"))
        self.assertIn("ADDRESS", self.categories("Registered Office: 10 Example Road, Example Nagar, Pune 400001, Maharashtra, India"))

    def test_numeric_protection(self) -> None:
        candidates = detect_locations([location("Telephone: 2022-2023; CIN U28129PN1979PLC141032; ₹ 1,000 million; 25%")])
        accepted, rejected = select_candidates(candidates)
        self.assertNotIn("PHONE", {item.candidate.category for item in accepted})
        self.assertTrue(all(item.reason for item in rejected))


class PersonNamePrecisionTests(unittest.TestCase):
    """Regression tests for the strong_person_context detection path.

    Each FP test captures an exact pattern observed in the Red Herring Prospectus
    that was incorrectly detected as a person name before the precision fix.
    Each TP test proves the corresponding legitimate names are still detected.
    """

    def _accepted_names(self, text: str) -> list[str]:
        """Return raw_value strings for all accepted PERSON_NAME detections."""
        locs = [location(text)]
        accepted, _ = select_candidates(detect_locations(locs))
        return [item.candidate.raw_value for item in accepted if item.candidate.category == "PERSON_NAME"]

    # --- False-positive regression tests ---

    def test_fp_materiality_policy_not_a_person(self) -> None:
        # "Materiality Policy" appeared near the word "Directors" in para 221,
        # causing it to be detected as a PERSON_NAME via strong_person_context.
        # "policy" and "materiality" are now stopwords.
        text = (
            "A summary of outstanding litigation proceedings involving our Directors, "
            "Promoters, and KMPs in accordance with the SEBI ICDR Regulations and the "
            "Materiality Policy adopted by our Board."
        )
        self.assertNotIn("Materiality Policy", self._accepted_names(text))

    def test_fp_certain_corporate_matters_not_a_person(self) -> None:
        # "Certain Corporate Matters" appeared near "Promoter Selling Shareholder"
        # in para 540 and was detected as a PERSON_NAME.
        # "corporate", "matters", and "certain" are now stopwords.
        text = (
            "For further details in relation to the personal guarantees, see "
            "History and Certain Corporate Matters — Guarantees provided to "
            "third parties by our Promoter Selling Shareholders."
        )
        self.assertNotIn("Certain Corporate Matters", self._accepted_names(text))

    def test_fp_sentence_boundary_period_not_a_person(self) -> None:
        # CONTEXTUAL_NAME_RE allows '.' in tokens (for initials like "A."), which
        # caused it to greedily match "Shetty. For" across a sentence boundary.
        # The trailing-period guard in _looks_like_person now blocks this.
        text = (
            "We are led by our Individual Promoters Rakhi Girija Shetty. "
            "For further details, see Our Promoters."
        )
        names = self._accepted_names(text)
        self.assertNotIn("Rakhi Girija Shetty. For", names)

    def test_fp_our_promoter_singular_not_a_person(self) -> None:
        # "Our Promoter" appeared as a 2-word title-case sequence in several
        # paragraphs.  Adding "promoter" (singular) to PERSON_STOPWORDS fixes it.
        text = (
            "For further details, see Our Promoter and Our Director on page 269."
        )
        names = self._accepted_names(text)
        self.assertNotIn("Our Promoter", names)
        self.assertNotIn("Our Director", names)

    # --- Positive recall tests (must still detect legitimate names) ---

    def test_tp_kmp_names_detected_near_director_context(self) -> None:
        # Para 226 style: names of real KMPs/directors listed inline.
        # "key managerial personnel" is the trigger; names follow directly.
        text = (
            "Certain of our KMPs including, Kushal Subbayya Hegde, Rajesh Kushal Hegde, "
            "Rohit Kushal Hegde and Rakhi Girija Shetty are also our Executive Directors."
        )
        names = self._accepted_names(text)
        self.assertIn("Kushal Subbayya Hegde", names)
        self.assertIn("Rajesh Kushal Hegde", names)
        self.assertIn("Rakhi Girija Shetty", names)

    def test_tp_senior_management_names_detected(self) -> None:
        # Para 227 style: real KMP names listed by role abbreviation inline.
        text = (
            "Certain of our SMs including, Sandesh Bhagwat, CEO, Amod Joshi, CFO, "
            "Sarthak Malvadkar, CS and Compliance Officer, are also our KMPs."
        )
        names = self._accepted_names(text)
        self.assertIn("Sandesh Bhagwat", names)
        self.assertIn("Amod Joshi", names)

    def test_tp_director_in_form_filing_paragraph(self) -> None:
        # Para 442–444 style: director name mentioned after "director in relation to".
        # The word "director" in the sentence is the nearby context trigger.
        text = (
            "Form 32 along with corresponding challan for regularization as director "
            "in relation to Rajesh Kushal Hegde dated September 26, 1996."
        )
        names = self._accepted_names(text)
        self.assertIn("Rajesh Kushal Hegde", names)

