# Technical Design: DOCX PII Redaction Tool

## Scope and design principles

This design implements the assignment described in `input/Agenda.txt`, using `input/Red Herring Prospectus.docx` as the primary input. It prioritizes deterministic, explainable detection over broad unvalidated matching. The implementation will use Python standard-library facilities plus `python-docx`; no NLP/NER model is planned because the prospectus contains strong structural cues (labels, tables, contact blocks, legal entity suffixes) that can be handled more precisely with context-aware rules.

The first version will redact editable DOCX text. It will report, rather than claim to redact, PII that could be embedded in raster images or unsupported OOXML structures.

## 1. CLI interface

Command:

```text
python -m src.redactor [INPUT_DOCX] [options]
```

Arguments and options:

| Argument/option | Default | Behavior |
| --- | --- | --- |
| `INPUT_DOCX` | `input/Red Herring Prospectus.docx` | Source DOCX. Positional argument is optional so the supplied assignment input works without arguments. |
| `--output PATH` | `output/redacted_prospectus.docx` | Destination DOCX. Parent directory is created if needed. The command refuses to overwrite unless `--overwrite` is supplied. |
| `--audit PATH` | `reports/redaction_audit.json` | JSON audit report containing detections, replacements, locations, confidence, warnings, and run summary. |
| `--overwrite` | false | Permit replacement of an existing output or audit file. |
| `--dry-run` | false | Detect and write the audit only; do not create a redacted DOCX. |
| `--categories LIST` | all required categories | Comma-separated subset of required category names for controlled testing. It cannot silently introduce unsupported categories. |
| `--verbose` | false | Print summary counts and warnings to stderr without exposing original PII values in normal output. |

Exit status is `0` on success, `2` for invalid CLI/input/output usage, and `1` for processing failures. Default paths keep the supplied source untouched and place generated artifacts in the existing `output/` and `reports/` directories.

## 2. Project architecture

Planned module tree (created only during implementation):

```text
src/
  __init__.py
  redactor.py             # CLI parsing and orchestration
  models.py               # Typed records: Location, Detection, Replacement, RunSummary
  detectors.py            # Category-specific detection and validation functions
  entity_store.py         # Deterministic original-to-fake replacement registry
  docx_io.py              # DOCX traversal, OOXML text-node edits, save/open checks
  audit.py                # JSON-safe audit serialization and run warnings
  evaluation.py           # Metric calculation over reviewed ground truth
tests/
  test_detectors.py
  test_entity_store.py
  test_docx_io.py
  test_evaluation.py
  test_redactor.py        # CLI/end-to-end tests
```

`redactor.py` orchestrates four separate phases: (1) extract text locations, (2) detect and validate candidates, (3) assign replacements, and (4) apply approved replacements and write the audit. Detectors must not edit DOCX XML; writers must not decide whether text is PII.

## 3. PII detection architecture

Each detector returns `Detection` records with a category, normalized value, exact source span, context, confidence (`high`, `medium`, or `low`), and validation rationale. The orchestration layer resolves overlaps with this priority: `EMAIL`, `IP_ADDRESS`, `SSN`, `CREDIT_CARD`, `PHONE`, `DOB`, `ADDRESS`, `COMPANY`, `PERSON_NAME`. Higher-specificity spans win; the audit records dropped overlaps.

| Category | Detection and validation | Expected false positives / false negatives | Replacement strategy |
| --- | --- | --- | --- |
| `PERSON_NAME` | Detect labeled contact fields (`Contact Person`, `Director`, `Promoter`, `CEO`, `CFO`, `Company Secretary`, etc.) and name columns in identified people tables. Match 2-4 title-case tokens, allowing common initials and honorifics, but only in those contexts or after a role label. Normalize whitespace/case for repeat matching. | FP: company/trust names or legal headings in a name column. FN: a person mentioned only in unrestricted narrative prose, initials-only names, or non-Latin names. | Stable synthetic names from a fixed, bundled list, e.g. `Person 001` is avoided in favor of natural-looking `Aarav Mehta`; same normalized original gets the same fake name. |
| `EMAIL` | Standard bounded email regex; require a nonempty local part, a domain label and a 2+ character top-level domain. Preserve no surrounding punctuation. Normalize case for mapping. | FP: rare prose that resembles an email. FN: malformed/obfuscated emails such as `name (at) example dot com`. | `user001@example.test`, preserving neither original domain nor local-part data; same normalized email maps consistently. |
| `PHONE` | Indian/international-aware pattern requiring plausible digit count and formatting. Accept values with `+91`, optional `0`, parentheses, spaces or hyphens only when 10-13 digits remain after normalization. Prefer `Telephone`, `Tel`, `Mobile`, or contact-block context; permit a strong formatted number outside context. Reject date/year, money, and registration contexts. | FP: formatted account/order/reference numbers. FN: extensions, OCR-like corruption, or unusual separators. | Deterministic Indian-format number such as `+91 90000 00001`, preserving an explicit `+91` presentation when present; index increments per normalized number. |
| `COMPANY` | Use a deterministic legal-entity suffix vocabulary (`Limited`, `Private Limited`, `LLP`, `Inc.`, `Corporation`, etc.), known issuer/intermediary table labels, and organization/contact context. Capture the full title-case span before the suffix, including approved connectors such as `&`. Do not classify a single generic word or a heading merely because it contains `Company`. | FP: ordinary legal phrases ending in an entity-like word; organization names that are not treated as PII by an evaluator. FN: companies without a recognized suffix, abbreviations, or names split across runs/paragraphs. | `Example Company 001 Pvt. Ltd.`; preserve only the generic corporate type where practical, never the real name. Repeated normalized entities get the same replacement. |
| `ADDRESS` | Trigger on explicit labels (`Registered Office`, `Corporate Office`, `Address`) and address-table columns. Parse contiguous content containing at least two address signals: street/building/unit terms, locality/city/state, PIN/ZIP-like code, or `India`. Also scan contact blocks around a detected email/phone. | FP: business-location prose, venue descriptions, or legal registered-office references if the evaluator excludes corporate addresses. FN: unlabelled, abbreviated, or multi-paragraph addresses. | Stable synthetic Indian-style address by entity/index, e.g. `101 Example Road, Example Nagar, Pune - 400001, Maharashtra, India`; preserve line/semicolon segmentation where possible. |
| `SSN` | Strict US pattern `NNN-NN-NNNN`; reject known invalid groups (`000`, `666`, `9xx` prefix, `00`, `0000`). The agenda requires SSN support even though no example was found. | FP: a coincidental formatted number. FN: unhyphenated or foreign national identifiers, intentionally out of scope unless explicitly labeled. | `900-01-0001` style synthetic value satisfying formatting but not derived from original. |
| `CREDIT_CARD` | Identify 13-19 digit candidates with allowed spaces/hyphens, normalize digits, and require Luhn checksum validity. Reject candidates in explicit financial amount, share count, CIN/DIN, registration, or page contexts. | FP: a Luhn-valid non-card identifier. FN: masked cards, card numbers embedded in images, or invalid test numbers. | Deterministic Luhn-valid test-format number from a safe fixed prefix, rendered in four-digit groups; no original digits retained. |
| `DOB` | Require explicit birth context (`Date of Birth`, `DOB`, `born`, `birth date`) adjacent to a supported date format. A bare date is not a DOB. Parse only unambiguous textual dates or ISO/day-month-year forms with contextual label. | FP: incorporation/event date near an accidental `born` phrase. FN: DOB in a table without label, age-only statements, or unsupported locale formats. | Fixed but varied valid dates such as `12 January 1985`, mapped consistently per normalized original and formatted to match the source style where feasible. |
| `IP_ADDRESS` | Strict IPv4 regex with octets 0-255; exclude version numbers and dotted financial/table values by requiring normal word boundaries. IPv6 is not required by the agenda and will be reported as unsupported, not silently treated as IPv4. | FP: a syntactically valid dotted non-IP value. FN: IPv6, obfuscated IPs, and addresses in images. | Documentation-range IPv4 values from `192.0.2.0/24`, e.g. `192.0.2.1`, mapped consistently. |

Low-confidence candidates are recorded in the audit with `status: "skipped_low_confidence"` rather than redacted automatically. This is deliberate precision protection; the evaluation report will disclose resulting false negatives.

## 4. Numeric identifier protection

The prospectus contains abundant numeric values that must not be classified automatically as PII. Before phone, SSN, credit-card, DOB, or IP replacement, the validation layer applies these safeguards:

1. Use category-specific shape validation: phone digit count/context, SSN hyphen structure and invalid-group rejection, card Luhn validation, DOB birth-only context, and bounded IPv4 octets.
2. Exclude known identifier shapes: Indian CIN (`[LU]` plus company-code structure), DIN (typically eight digits in a director table), PAN-like values, SEBI registration numbers, firm/peer-review numbers, alphanumeric security/market codes, and dates/years.
3. Exclude numeric candidates in contexts containing `₹`, `%`, `million`, `Fiscal`, `FY`, `share`, `equity`, `face value`, `CIN`, `DIN`, `registration`, `page`, `Table`, `section`, `SEBI`, `ISIN`, or `offer`, unless a stronger category label explicitly overrides it.
4. Reject plain number sequences without a required category-specific format or contextual label. Never redact page numbers, percentages, financial amounts, or share counts as a side effect of a generic digit regex.
5. Record every rejected numeric candidate and its reason in the audit summary only when it was considered by a detector, enabling precision review without treating it as PII.

## 5. Name, company, and address detection details

The tool will not use NLP/NER in the first pass. A general NER model would add a heavyweight dependency, be difficult to validate on Indian legal/financial names, and could over-redact the dense legal and corporate prose. Deterministic structural rules are better aligned with the prospectus and rubric.

Name handling uses a configurable role-label set, person-specific table-column headers (`Name`, `Director`, `Contact Person`, `Designation`), and the nearby value. It maintains a conservative stoplist for institutional nouns (`Company`, `Bank`, `Trust`, `Limited`, `Exchange`) and only permits free-text name matching when a person role label supplies context.

Company handling uses a legal-suffix matcher plus structural context such as `Book Running Lead Manager`, `Registrar`, `Banker`, `Auditor`, or an organization cell. A table-row entity is captured as a single value rather than reconstructing it from all cell text. Names of trusts and group entities will be handled as `COMPANY` only if they are included by the chosen organization policy; the README and evaluation report will state that policy.

Address handling is field- and block-based, not a global street-address regex. Once an address label or address column is found, adjacent text continues until the next field label/paragraph boundary. Within narrative contact blocks, address signals must meet the two-signal rule described above. This avoids treating every comma-separated legal phrase as an address.

## 6. Replacement system

`entity_store.py` owns a per-run mapping keyed by `(category, normalized_original)`. It derives a replacement from a deterministic sequence and fixed safe vocabularies, then uses that mapping at every occurrence. The JSON audit stores a one-way digest of the normalized original plus the synthetic replacement; it will not store raw PII by default.

| Category | Replacement format |
| --- | --- |
| `PERSON_NAME` | `Aarav Mehta`, `Diya Shah`, etc., from fixed paired-name lists. |
| `EMAIL` | `userNNN@example.test`. |
| `PHONE` | `+91 90000 0NNNN` or a matching source-style rendering. |
| `COMPANY` | `Example Company NNN Pvt. Ltd.` or `Example Company NNN Limited`, retaining generic suffix class when known. |
| `ADDRESS` | `NNN Example Road, Example Nagar, Pune - 400001, Maharashtra, India`. |
| `SSN` | `900-01-NNNN` with valid nonzero groups. |
| `CREDIT_CARD` | A generated Luhn-valid 16-digit test-format number rendered as `4111 1111 1111 NNNN` only after final Luhn adjustment. |
| `DOB` | A valid synthetic date rendered in the input's detected style. |
| `IP_ADDRESS` | `192.0.2.N`, from documentation-only address space. |

Replacement text does not retain original characters, domains, digits, or street fragments. Replacement collisions are prevented within a category. Cross-category collisions are permitted only where semantically harmless; no original value is reused as a fake value.

## 7. DOCX processing and formatting preservation

`docx_io.py` will load a copy of the input with `python-docx`, enumerate editable text locations, apply span replacements, save to the requested path, and reopen the output as a structural sanity check.

Processing coverage and approach:

- **Normal paragraphs and runs:** build a logical paragraph text plus a character-to-run map. Apply replacements from right to left. For a match contained in one run, replace only that run substring. For a cross-run match, preserve the first affected run's character formatting for the replacement and remove only the matched text from subsequent runs. This avoids resetting an entire paragraph and retains non-PII styling as far as practical.
- **Tables and table cells:** recursively enumerate every table cell paragraph, including nested tables if present; carry table/row/cell coordinates in `Location`. Cell formatting and table geometry are not rebuilt.
- **Headers and footers:** enumerate each section's header and footer paragraphs and tables. Deduplicate linked header/footer parts by OOXML part identity so a shared header is not processed repeatedly.
- **Text boxes and other OOXML text:** scan `word/document.xml` plus header/footer XML parts for `w:txbxContent` and text nodes that `python-docx` does not expose. Use targeted lxml OOXML edits only for these nodes; preserve all surrounding XML and run properties. The audit marks these locations as OOXML text-box locations.
- **Images and drawings:** do not OCR or alter images in the first implementation. Emit an audit warning giving image-part count and the limitation.
- **Other unsupported content:** comments, footnotes/endnotes, tracked deletions, fields, embedded objects, charts, SmartArt, and external links are not claimed as fully redacted unless the implementation explicitly enumerates them. Their presence produces a warning in the audit.

Formatting preservation is a best-effort engineering goal, not an explicit agenda requirement. Replacement lengths may change line breaks/pagination; the final verification will reopen the DOCX and inspect high-risk areas manually.

## 8. Detection versus replacement

The logical boundary is:

1. **Extraction:** produce immutable `TextLocation` records containing text and document coordinates.
2. **Detection:** run category-specific detectors over locations and return candidate spans.
3. **Validation/selection:** reject protected numeric values, resolve overlaps, and record rejected low-confidence candidates.
4. **Replacement assignment:** map accepted normalized entities to deterministic fakes without touching document content.
5. **Writing:** apply already-approved replacements by location/span and save a new DOCX.
6. **Audit/evaluation:** serialize the run and compare reviewed predictions against ground truth.

This permits detectors, validators, replacement consistency, OOXML edits, and metrics to be tested independently.

## 9. Audit and evaluation data

The default audit file is JSON with this shape:

```json
{
  "schema_version": 1,
  "input": {"path": "...", "sha256": "..."},
  "output": {"path": "...", "sha256": "..."},
  "detected": [
    {
      "id": "det-0001",
      "category": "EMAIL",
      "original_sha256": "...",
      "replacement": "user001@example.test",
      "location": {"kind": "table_cell", "table": 71, "row": 2, "cell": 4, "paragraph": 1},
      "start": 0,
      "end": 20,
      "confidence": "high",
      "validation": ["email_shape"]
    }
  ],
  "skipped": [{"category": "PHONE", "reason": "financial_year"}],
  "warnings": ["Images are not OCR processed"],
  "counts_by_category": {"EMAIL": 70}
}
```

Raw PII is excluded by default. A separate manually curated ground-truth JSON may store encrypted/locally controlled source references or exact spans for the evaluation run; it is an evaluation artifact, not a required public deliverable. Location, category, source hash, and span allow matching without manually reconstructing every internal operation.

## 10. Testing strategy

- **Detector unit tests:** positive and negative fixtures for all nine required categories, including boundary punctuation, malformed inputs, and normalization.
- **Numeric false-positive tests:** prospectus-like financial years, currency amounts, percentages, CIN/DIN/SEBI registration values, page numbers, share counts, and ISO/financial dates must not be classified as phone/SSN/card/DOB/IP.
- **Name/company/address tests:** role-labeled names, contact blocks, legal entity suffixes, director/address table cells, generic legal language, and bare dates.
- **False-negative tests where practical:** alternate Indian phone spacing, email punctuation, multi-run matches, address line breaks, and repeated entities.
- **Replacement tests:** same normalized entity yields the same fake replacement; separate entities do not collide; replacement formats validate (including Luhn for cards and IPv4 octets).
- **DOCX tests:** a synthetic DOCX with formatted multi-run paragraph, table cell, header/footer, and text box where practical; verify only target text changes and the output reopens.
- **End-to-end test:** run the CLI over a compact fixture DOCX, assert output and audit JSON exist, assert original PII is absent from editable text, and assert intended safe numeric values remain.
- **Prospectus run review:** manually inspect the high-risk contact sections, Table 71, other contact tables, and audit warnings before producing the final evaluation report.

## 11. Evaluation methodology

Ground truth will be created by exporting the tool's pre-replacement candidate locations and independently reviewing the prospectus by category. The reviewer will mark each candidate as true PII/non-PII and add missed PII discovered in high-risk regions (contact blocks, director/promoter lists, named-address tables, headers/text boxes). Ground truth must identify category and document location/span; repeated occurrences count separately for recall unless a documented entity-level metric is also supplied.

For each category and overall, calculate:

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
accuracy  = (TP + TN) / (TP + FP + FN + TN)
```

The evaluation report will state the unit of evaluation (occurrence/span), review scope, category counts, formula, and any ambiguous policy choice (notably order/ticket-like identifiers and whether organization names are treated as PII). It will report accuracy, precision, and recall as required, with no invented target threshold.

Accuracy is weak for this imbalanced document: there are vastly more non-PII text spans than PII spans, and “true negatives” are not naturally enumerable for free text. A high accuracy value could therefore coexist with poor PII recall. Precision and recall, including per-category counts, are the primary evidence; the report will explicitly state how TN was defined or that accuracy is calculated only over a reviewed candidate/non-candidate corpus.

## 12. Image-embedded text

The first implementation does not perform OCR and will not claim redaction of text inside the prospectus's embedded images, QR code, scanned graphics, charts, or rasterized text boxes. It will count image parts and emit an audit warning. Manual visual review is required for these parts. OCR is deferred because it would introduce a substantial dependency and a new redaction/rendering problem not required explicitly by Agenda.txt.

## 13. Error handling

| Condition | Planned behavior |
| --- | --- |
| Missing input file | Print a concise error, do not write output, exit `2`. |
| Invalid/non-DOCX input or unreadable ZIP/XML | Catch load/parse error, state that a valid DOCX is required, do not overwrite output, exit `2`. |
| Unsupported content | Process supported editable text, add explicit audit warnings for images/OCR and other unprocessed parts; do not claim complete coverage. |
| Output/audit path already exists | Fail safely unless `--overwrite` is supplied. Input and output resolving to the same path is always rejected. |
| Cannot create output parent / cannot save | Report filesystem error, retain input unchanged, exit `1`. |
| Malformed detector input | A detector returns no match or a skipped candidate with rationale; it must not raise on arbitrary text. Unexpected detector exceptions are isolated, captured in the audit, and cause failure only if a required detector cannot run. |
| Overlapping or cross-run spans | Resolve by category priority; log skipped overlap. If a mapping cannot be applied safely, leave the DOCX unchanged at that span and report a warning/error rather than corrupting text. |

## 14. Performance

The target is one large prospectus, not a batch-processing service. Load the DOCX once, traverse each editable text location once, use compiled regexes and small lookup sets, retain span offsets rather than duplicate full document strings, and edit spans right-to-left. No database, server, background queue, or model loading is needed. Audit data remains proportional to detections and warnings, not every character of the document.

## 15. Acceptance-test mapping

| Acceptance-checklist requirement | Planned implementation or verification |
| --- | --- |
| Script reads source document and produces redacted version | CLI defaults to the supplied DOCX; end-to-end test verifies a new DOCX is created. |
| Fake alternatives replace PII | `entity_store.py` deterministic category-specific fake formats; replacement tests validate no original fragments are retained. |
| All minimum PII categories | Nine detectors and category-level positive tests. |
| Order/ticket-like policy made explicit | README/evaluation report states numeric-identifier protection and policy; detector tests verify it. |
| DOCX redacted output | Default `--output` DOCX; save/reopen validation and end-to-end test. |
| Source code delivered | Maintainable `src/` module structure and documented CLI. |
| README describes approach and tradeoffs | README implementation task will state deterministic/context-aware approach, image limitation, and observed FP/FN. |
| Evaluation approach/report with accuracy, precision, recall | `evaluation.py`, reviewed ground truth, JSON/Markdown report generation plan, and formula documentation. |
| Recall for each PII type | Category-specific ground-truth review and per-category TP/FP/FN reporting. |
| Precision / avoid non-PII redaction | Numeric protection rules plus prospectus-like negative tests and reviewed false positives. |
| Code quality, readability, extensibility | Isolated detectors, typed records, no DOCX mutation inside detection, and unit tests. |
| README clarity | Concise run instructions, method, policy choices, limitations, and report location. |
| Existing DOCX structure risks | Traverse paragraphs, tables, headers, footers, text boxes; retain formatting by span-level run edits; warnings for unsupported content. |
| Image-embedded text limitation | Explicit audit warning and final manual review, with no unsupported OCR claim. |

## Unresolved decisions to confirm before implementation

1. Treat the agenda's “ticket log” reference as an apparent mismatch and implement DOCX prospectus input only.
2. Treat organizations/company names and business addresses as PII because Agenda.txt lists them, despite their public/prospectus nature.
3. Do not OCR images in the first version; disclose that limitation in README and report.
4. Use a manually reviewed occurrence-level ground truth for metrics; define/report an explicit TN strategy before publishing “accuracy.”
5. Do not redact CIN, DIN, SEBI/firm registration numbers, financial values, page numbers, share counts, ordinary dates, or market identifiers unless a future operator instruction expands scope.
