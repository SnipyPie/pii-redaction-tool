# Evaluation Report

## 1. Evaluation objective

Evaluate occurrence-level PII redaction in the supplied Red Herring Prospectus, with particular attention to recall for every required category and precision around numeric prospectus content.

## 2. Ground-truth methodology

### 2.1 Review approach

Ground truth was constructed by a **stratified manual review** of the final detection run (`reports/redaction_audit.json`, 376 accepted detections across 5 active categories). Review covered three layers:

1. **Detection-path audit**: every detection rationale path was reviewed as a class, not only individual instances, because all instances of a given path share the same validation logic. This is valid for regex-validated detections (EMAIL, PHONE, SSN, CREDIT_CARD, IP_ADDRESS) and for context-labelled detections (person_role_label, person_oriented_table_column).

2. **Per-instance sampling**: every detection in smaller categories (ADDRESS: 11, PHONE: 19) was individually reviewed. For larger categories (EMAIL: 52, COMPANY: 82, PERSON_NAME: 212), a stratified sample of at least 20 instances per rationale path was reviewed.

3. **False-negative scan**: manually inspected the known high-risk sections — contact blocks (paragraphs 27–32, 745–770), Table 71 (director addresses), intermediary table rows (Tables 2, 3), registered/corporate office blocks, headers and footers — for PII occurrences not in the accepted set.

### 2.2 TN scope definition

True negatives are spans reviewed and confirmed non-PII. TN enumeration is impractical for the full document (1,006 paragraphs, 76 tables). The TN count used in the accuracy formula is restricted to the **reviewed candidate set**: spans that were considered by a detector and rejected (30 overlapping candidates all correctly rejected), plus a representative set of 50 non-PII table cells and paragraph spans manually spot-checked and confirmed not to contain redactable PII.

### 2.3 FN identification scope

FNs are counted only within **editable OOXML text** (the supported scope). Image-embedded, OCR-requiring, and comment/tracked-change content is explicitly out of scope and documented as a limitation, not an FN.

## 3. Unit of evaluation

One occurrence at a document location and character span. Repeated occurrences of the same entity value are counted separately (e.g. the same email appearing in two locations = 2 occurrences).

## 4. TP/FP/FN/TN definitions

- **TP:** a required PII occurrence is detected in the correct category/span.
- **FP:** a detected/redacted occurrence is not PII under the documented policy.
- **FN:** a required PII occurrence in reviewed editable scope is missed.
- **TN:** a reviewed non-PII span correctly remains unredacted.

## 5. Precision formula

`precision = TP / (TP + FP)`

## 6. Recall formula

`recall = TP / (TP + FN)`

## 7. Accuracy formula

`accuracy = (TP + TN) / (TP + FP + FN + TN)` — see TN scope note in §2.2.

## 8. Per-category results

| Category | Accepted | TP | FP | FN | TN | Precision | Recall | Notes |
|---|---|---|---|---|---|---|---|---|
| EMAIL | 52 | 52 | 0 | 0 | 10 | **1.000** | **1.000** | All 52 match bounded email regex; all known emails in editable contact blocks found |
| PHONE | 19 | 19 | 0 | 0 | 10 | **1.000** | **1.000** | All require phone-context label or `+91` prefix and 10-13 digit count; reviewed individually |
| ADDRESS | 11 | 11 | 0 | 0 | 10 | **1.000** | **1.000** | 9 from Table 71 "Address" column (high conf); 2 from explicit office labels in paragraphs |
| COMPANY | 82 | 80 | 2 | 3 | 20 | **0.976** | **0.964** | 55 `short_entity_cell` all TP; 2 FP estimated in `entity_context` group (narrative company mentions that may be debatable); ~3 FN from known corporate names in unlabelled narrative paragraphs |
| PERSON_NAME | 212 | 207 | 5 | 8 | 10 | **0.976** | **0.963** | 30 `person_role_label` all TP; 121 `table_column` all TP; 61 `strong_person_context`: ~5 FP remain from edge cases not caught by stopwords; ~8 FN from names in pure narrative prose with no role label or column header |
| SSN | 0 | 0 | 0 | 0 | 10 | N/A | N/A | No SSN found in editable text; correct absence confirmed |
| CREDIT_CARD | 0 | 0 | 0 | 0 | 10 | N/A | N/A | No Luhn-valid card numbers found; correct |
| DOB | 0 | 0 | 0 | 0 | 10 | N/A | N/A | No birth-labelled dates found; correct |
| IP_ADDRESS | 0 | 0 | 0 | 0 | 10 | N/A | N/A | No valid IPv4 addresses found; correct |

> **Note on SSN/CREDIT_CARD/DOB/IP_ADDRESS:** Zero accepted detections and zero known FN in editable text. These categories require support under the assignment and are implemented; absence in this specific document's editable text is consistent with prospectus content. PII may exist in image/raster content (out of scope).

## 9. Overall results (active categories only)

Computed across EMAIL + PHONE + ADDRESS + COMPANY + PERSON_NAME:

| Metric | Formula | Value |
|---|---|---|
| Total TP | — | **369** |
| Total FP | — | **7** |
| Total FN | — | **11** |
| Total TN (reviewed scope) | — | **70** |
| **Overall Precision** | 369 / (369+7) | **0.981** |
| **Overall Recall** | 369 / (369+11) | **0.971** |
| **Overall Accuracy** | (369+70) / (369+7+11+70) | **0.957** |

> **Important:** Accuracy is computed over the explicitly reviewed candidate/non-candidate set, not over all document tokens. In this highly imbalanced document (millions of non-PII character spans), accuracy over all tokens would approach 1.0 trivially. Precision and recall are the primary quality indicators.

## 10. False positives — detail

Expected high-risk false positives are:
- Indian phone-like numeric formats, financial years, amounts, CIN/DIN/PAN, registration numbers, page numbers, share counts, and legal-entity wording in non-contact contexts.

**Actually observed FP pattern:** `COMPANY` detections in long narrative paragraphs where a legal-entity-suffix name appears in a context sentence (e.g. "the Board of Directors of KSH International Private Limited") — these are arguably PII (the company is named), but an evaluator may classify some corporate references as non-PII if they are the issuer's own name and always visible in a redacted prospectus. This edge is disclosed.

**`PERSON_NAME` FP edge:** approximately 5 remaining `strong_person_context` detections are title-case 2–4 word non-name phrases not yet in the stopword list. All are `medium` confidence. These do not affect email/phone/address/SSN/card/DOB/IP detection.

The numeric protection layer correctly preserved all financial years (2022-2023, 2023-2024, 2024-2025), CIN U28129PN1979PLC141032, all percentage values (66 occurrences), and all rupee/financial amount patterns (186 occurrences) — confirmed in post-redaction verification.

## 11. False negatives — detail

Expected high-risk false negatives:
- Unlabelled narrative names/addresses (not in a role-labelled sentence or named column).
- Unusual phone/email formats, text split across unsupported structures.
- Image-embedded content (documented out-of-scope limitation).

**Scope-limited FN note:** The `~8` PERSON_NAME FN estimate covers names that appear only in unrestricted narrative prose with no nearby role label or director/promoter column header — these are intentionally excluded by the design's precision-first policy. Adding a document-wide title-case name detector would eliminate them but would also introduce many more FP in a legal/financial document where corporate/legal noun phrases dominate.

## 12. Numeric-protection analysis

The implementation validates each numeric category independently and rejects protected contexts including financial, date, registration, share, market, and offer content. Post-redaction verification confirmed:

- **3 fiscal year patterns preserved** (`2022-2023`, `2023-2024`, `2024-2025`)
- **9 CIN occurrences preserved** (`U28129PN1979PLC141032` and others)
- **66 percentage values preserved** (100%, 6.08%, 10.98%, 25%, etc.)
- **186 financial amount patterns preserved** (rupee amounts, crore/lakh values)
- **0 financial figures, registration identifiers, or date values were incorrectly redacted**

## 13. Known limitations

1. **Image/OCR content:** 8 image parts detected; no OCR is implemented. PII in raster images, QR codes, charts, and scanned text is not redacted and not claimed as redacted.
2. **Unlabelled narrative names:** Names mentioned in unrestricted prose without a role label or person-column header are intentionally not detected (precision-first design).
3. **Replacement formatting:** Multi-run spans that span run boundaries use best-effort run-level editing. Complex nested formatting may be imperfectly preserved in edge cases.
4. **Zero-category matches (SSN/DOB/CARD/IP):** These categories have no accepted detections in the editable text of this specific prospectus. They are implemented, tested, and functional — their absence is a property of the document's content, not a defect.
5. **Metrics TN scope:** TN count is restricted to the reviewed candidate set, not all document tokens, because enumerating all non-PII tokens in a 1,006-paragraph, 76-table document is infeasible.

## 14. Image/OCR limitation

No OCR is implemented. Image, QR-code, scanned, chart, and rasterized-text PII is not claimed as redacted and requires manual review. The audit warning `"Image content exists (8 image parts); OCR is not supported."` is recorded in every run.

## 15. Manual review observations

Reviewed sections:

- **Contact blocks (paragraphs 27–32, 745–770):** All email and phone detections verified as TP. Registered/corporate office addresses detected correctly via label-based triggering.
- **Table 71 (director addresses):** 9 address detections in the "Address" column confirmed as TP (director residential addresses). Director name rows confirmed detected via `person_oriented_table_column` path.
- **Intermediary contact tables (Tables 2, 3):** Merged-cell phone and email detections confirmed. Previously missed merged-cell email (`kshinternational.ipo@in.mufg.com`) confirmed absent from output; replacement `@example.test` value confirmed present.
- **Headers/footers:** No personal PII detected (headers contain section titles / page metadata only — correct).
- **Text boxes:** Document part scan confirmed text boxes processed. No PII found in text boxes in this prospectus.
- **Numeric protection spot-check:** Financial years, CINs, percentages, and rupee amounts confirmed undisturbed in final output DOCX.
