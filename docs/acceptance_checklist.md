# Assignment Acceptance Checklist

**Source authority:** `input/Agenda.txt`. Items marked **[Explicit]** are stated or directly required by the agenda. Items marked **[Observation]** come from the supplied prospectus. Items marked **[Recommendation]** are engineering planning only and are not assignment requirements.

**Status key:** `[x]` complete · `[~]` partially met / known limitation · `[ ]` not addressed

---

## 1. Functional Requirements

- [x] **[Explicit]** Provide a script, in a language of our choice, that reads the supplied source document and produces a redacted version.  
  _Implemented: `src/redactor.py` CLI; `python -m src.redactor` reads `input/Red Herring Prospectus.docx` and writes `output/redacted_prospectus.docx`._

- [x] **[Explicit]** Replace all detected PII with a fake alternative; examples given: real name → "John Doe", email → `john.doe@example.com`, Indian phone → a different Indian phone.  
  _Implemented: EMAIL replaced with `userNNN@example.test`, PHONE with sequential `+91 90000 0000N`, PERSON_NAME with synthetic names from `EntityStore`, COMPANY with `<COMPANY-N>`, ADDRESS with `<ADDRESS-N>`._

- [x] **[Explicit]** Detect and redact, at minimum, every PII category listed in Section 2.  
  _All nine categories are implemented, tested, and produce accepted or correctly-null detections on this document._

- [x] **[Explicit]** Make the decision for borderline identifiers explicit.  
  _Documented: CIN, DIN, PAN, registration numbers, fiscal years, financial figures, share counts, and percentage values are explicitly whitelisted and not redacted. Reasoning is documented in `README.md` and `docs/technical_design.md`._

- [~] **[Ambiguity]** The task text says "reads the ticket log" while the supplied source is a prospectus DOCX.  
  _The supplied DOCX is treated as the input. If the operator supplies a different file, it must be a DOCX with compatible structure._

---

## 2. Required PII Categories

- [x] **[Explicit]** Full names. — **212 detected** (30 role-labelled, 121 table-column, 61 contextual-proximity)
- [x] **[Explicit]** Email addresses. — **52 detected** (all high confidence, verified 0 FP)
- [x] **[Explicit]** Phone numbers. — **19 detected** (all context-confirmed Indian numbers)
- [x] **[Explicit]** Company names. — **82 detected** (legal suffix + context)
- [x] **[Explicit]** Physical/mailing addresses. — **11 detected** (Table 71 director addresses + registered/corporate office blocks)
- [x] **[Explicit]** Social Security Numbers (SSNs). — **0 in editable text** (implemented; not present in this document's OOXML text)
- [x] **[Explicit]** Credit card numbers. — **0 in editable text** (Luhn-validated; none in document)
- [x] **[Explicit]** Dates of birth. — **0 in editable text** (explicit birth-label required; none found)
- [x] **[Explicit]** IP addresses. — **0 in editable text** (octet-validated; none in document)

---

## 3. Input Requirements

- [x] **[Explicit]** The redaction script reads `input/Red Herring Prospectus.docx`.  
  _Default input path; SHA-256 verified consistent across all runs._

- [x] **[Explicit]** The source document is a Red Herring Prospectus containing PII.  
  _Confirmed: document contains 52 email addresses, 19 phone numbers, 212 person names, 82 company names, 11 physical addresses in editable text._

- [~] **[Ambiguity]** CLI, encoding, non-DOCX support not specified in agenda.  
  _CLI documented in README. Only DOCX input is supported; other formats are not claimed._

---

## 4. Output Requirements

- [x] **[Explicit]** Produce a redacted output file in DOCX format.  
  _`output/redacted_prospectus.docx` — 1,879,643 bytes, opens cleanly, 1,006 paragraphs, 76 tables, 85 sections preserved._

- [x] **[Explicit]** Deliver the source code for the redaction script.  
  _`src/` package: `redactor.py`, `docx_io.py`, `detectors.py`, `models.py`, `entity_store.py`, `evaluation.py`._

- [x] **[Explicit]** Deliver a short README explaining the approach and tradeoffs/FP/FN.  
  _`README.md` — covers architecture, decisions, tradeoffs, and known limitations._

- [x] **[Explicit]** Explain the evaluation approach.  
  _`reports/evaluation_report.md` §2 describes the stratified review methodology._

- [x] **[Explicit]** Prepare an evaluation report with accuracy, precision, and recall numbers.  
  _`reports/evaluation_report.md` — overall precision 0.981, recall 0.971, accuracy 0.957; per-category table in §8._

---

## 5. Document Preservation Requirements

- [x] **[Explicit]** Deliverable must be a redacted DOCX file.  
  _Confirmed: `output/redacted_prospectus.docx` opens and is structurally valid._

- [x] **[Implicit]** Preserve document structure, styles, runs, tables, headers/footers, images.  
  _Run-level editing used; paragraph, table, header/footer, and section structure preserved. Fonts, bold, italic, and table formatting preserved. Images untouched (OCR not supported)._

- [~] **[Implicit]** Complex multi-run spans.  
  _Best-effort run-level span editing; edge cases with deeply fragmented runs may imperfectly preserve formatting in the redacted token only._

---

## 6. Evaluation Requirements

- [x] **[Explicit]** Evaluate recall: demonstrate whether all instances of each PII type were caught.  
  _Per-category recall in `reports/evaluation_report.md` §8. EMAIL: 1.000, PHONE: 1.000, ADDRESS: 1.000, COMPANY: 0.964, PERSON_NAME: 0.963._

- [x] **[Explicit]** Evaluate precision: demonstrate that non-PII is not unnecessarily redacted.  
  _Financial years, CINs, percentages, rupee amounts verified preserved post-redaction. EMAIL: 1.000, PHONE: 1.000, ADDRESS: 1.000, COMPANY: 0.976, PERSON_NAME: 0.976._

- [x] **[Explicit]** Include accuracy, precision, and recall in the evaluation report.  
  _Overall: precision 0.981, recall 0.971, accuracy 0.957._

- [x] **[Explicit]** Code quality: readability, structure, extensibility to new PII type.  
  _Each detector is a standalone function (`detect_<category>`); adding a new type requires only: (1) a new `detect_X` function, (2) registration in `detect_locations`, (3) a replacement pattern in `EntityStore`. Zero architectural changes._

- [x] **[Explicit]** Communication: README clarity.  
  _`README.md` covers approach, architecture, run instructions, tradeoffs, and known limitations._

---

## 7. Documentation Requirements

- [x] **[Explicit]** Short README with approach, tradeoffs, FP/FN observations.
- [x] **[Explicit]** State redaction approach (regex-based, NER, third-party library).  
  _Approach: rule-based, context-gated regex detection with no third-party ML/NER services._
- [x] **[Explicit]** State tradeoffs and observed FP/FN.  
  _README §4 and evaluation_report.md §10–11._
- [x] **[Explicit]** Explain evaluation approach.
- [x] **[Explicit]** Evaluation report with accuracy, precision, recall.

---

## 8. Testing Requirements

- [x] **[Explicit]** Evaluation sufficient to report accuracy, precision, recall, and per-category recall.  
  _23 automated unit/integration tests (pytest) + manual stratified review documented in evaluation_report.md._

- [x] **[Implicit]** Reviewable expected-result set before calculating metrics.  
  _Stratified review methodology described in §2 of evaluation_report.md. Detection-path audit + per-instance review of smaller categories._

- [x] **[Implicit]** Automated unit tests (not explicitly required, but implemented).  
  _23 tests across 5 test files; 23/23 passing; includes merged-cell regression (3 tests) and PERSON_NAME precision regression (7 tests)._

---

## 9. Assignment Constraints

- [x] **[Explicit]** Implementation language: Python (author's choice).
- [x] **[Explicit]** Cover all nine listed PII categories at minimum.
- [x] **[Explicit]** Borderline identifiers (CIN, DIN, PAN, registration numbers, financial figures) explicitly treated as non-PII and not redacted; disclosed in README and evaluation_report.md.
- [x] **[Explicit]** Final output is DOCX; source, documentation, and evaluation deliverables are included.

---

## 10. Prospectus-Specific Risks — Verification Status

- [x] **[Observation]** Large/complex document (1,006 paragraphs, 76 tables, 85 sections, 7 inline shapes).  
  _All OOXML locations traversed: paragraphs, tables (including merged cells), headers, footers, text boxes, nested tables._

- [x] **[Observation]** Full-name examples: Sarthak Malvadkar, Kushal Subbayya Hegde, Rakhi Girija Shetty, director rows in Table 71.  
  _All detected via `person_role_label` or `person_oriented_table_column` or `strong_person_context` with proximity gating._

- [x] **[Observation]** Email examples in contact/intermediary blocks.  
  _All 52 detected (100% recall on reviewed scope); merged-cell email confirmed detected and replaced._

- [x] **[Observation]** Phone regex risks matching financial years, dates, registration numbers, amounts.  
  _Protected numeric context check (`PROTECTED_CONTEXT`) prevents redaction of financial years, monetary amounts, CIN, DIN, ISIN, SEBI, registration numbers. Post-redaction verification confirmed all protected values intact._

- [x] **[Observation]** Company names pervasive; "Limited" suffix alone insufficient.  
  _Company detection requires legal suffix + (short entity cell ≤110 chars) OR (explicit entity context: registrar/banker/auditor/lead manager/company/entity/issuer)._

- [x] **[Observation]** Physical addresses in registered/corporate office blocks, Table 71.  
  _11 addresses detected: 9 from Table 71 "Address" column, 2 from explicit office-label paragraphs._

- [x] **[Observation]** No obvious SSN/CC/IP in editable text; DOB label not found.  
  _Correctly detected as zero. Implementations are tested and functional._

- [~] **[Observation]** Image/text-box/QR-code PII may exist in raster content.  
  _**Known limitation:** 8 image parts, OCR not implemented. PII in image-embedded text is not redacted. Documented warning emitted in every audit file._

- [x] **[Observation]** CIN/DIN/SEBI/financial figures are precision traps.  
  _Allowlist-based protection confirmed: all known identifier patterns preserved post-redaction._

---

## 11. Final Deliverables — Completion Status

- [x] **[Explicit]** Source code: `src/` package (6 modules, ~1,200 lines)
- [x] **[Explicit]** Redacted DOCX: `output/redacted_prospectus.docx` (1,879,643 bytes)
- [x] **[Explicit]** README: `README.md`
- [x] **[Explicit]** Evaluation approach: `reports/evaluation_report.md` §2
- [x] **[Explicit]** Evaluation report with metrics: `reports/evaluation_report.md` (precision 0.981, recall 0.971, accuracy 0.957)
- [x] **[Explicit]** Per-category recall evidence: evaluation_report.md §8 table
- [x] **[Recommendation]** Final DOCX verified: opens cleanly, contact blocks manually checked, merged-cell email confirmed replaced, protected numerics confirmed intact, Table 71 director data confirmed redacted

---

## Outstanding Limitations (not defects — documented and disclosed)

| # | Limitation | Impact | Mitigation |
|---|---|---|---|
| L1 | Image/OCR content not redacted (8 image parts) | PII in raster images not redacted | Manual review required for image pages |
| L2 | Unlabelled narrative names in unrestricted prose | ~8 estimated FN (by design, precision-first) | Add named-entity recognition model if higher recall required |
| L3 | Complex multi-run formatting edge cases | Redacted token formatting may be imperfect | Acceptable for legal review use case |
| L4 | Zero-category matches (SSN, CC, DOB, IP) | Not a defect; absent from this document | Implementations tested via unit tests |
| L5 | TN metric restricted to reviewed candidate set | Accuracy figure not computed over all tokens | Precision/recall are primary metrics |
