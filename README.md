# PII Redaction Tool

This project redacts the PII categories required by the assignment from the supplied Red Herring Prospectus while producing a separate DOCX and a PII-safe JSON audit. It uses deterministic, context-aware rules rather than a heavyweight NLP model so that matching is explainable and numeric false positives can be controlled.

## Supported PII categories

`PERSON_NAME`, `EMAIL`, `PHONE`, `COMPANY`, `ADDRESS`, `SSN`, `CREDIT_CARD`, `DOB`, and `IP_ADDRESS`.

## Install and run locally

Use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### CLI
```powershell
.\.venv\Scripts\python.exe -m src.redactor --help
.\.venv\Scripts\python.exe -m src.redactor --verbose
```
The default command reads `input/Red Herring Prospectus.docx`, writes `output/redacted_prospectus.docx`, and writes `reports/redaction_audit.json`. Use `--output PATH`, `--audit PATH`, `--dry-run`, `--categories EMAIL,PHONE`, and `--overwrite` as needed. The input is never modified and output/audit files are not overwritten without `--overwrite`.

### FastAPI Server
You can run the application as a local HTTP API:
```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```
- **Health Check:** `GET http://127.0.0.1:8000/health` (Returns `{"status": "ok"}`)
- **Redact API:** `POST http://127.0.0.1:8000/redact` (Accepts a `file` form-data field containing a `.docx` upload, and returns the redacted `.docx` directly).

## Deployment

The application is deployed as a Web Service on Render at:
**https://pii-redaction-tool-u2sk.onrender.com/**

### How to verify the deployed API:
1. **Health Check:** Open [https://pii-redaction-tool-u2sk.onrender.com/health](https://pii-redaction-tool-u2sk.onrender.com/health) in a browser to confirm the service is running (`{"status": "ok"}`).
2. **Interactive UI:** Open [https://pii-redaction-tool-u2sk.onrender.com/docs](https://pii-redaction-tool-u2sk.onrender.com/docs) to access the interactive Swagger documentation automatically provided by FastAPI.
3. **Test Redaction:** In the Swagger UI at `/docs`, expand `POST /redact` → click **Try it out** → upload a `.docx` file → click **Execute**. You will be prompted to download the redacted `.docx` output.
4. **Note:** Visiting `https://pii-redaction-tool-u2sk.onrender.com/redact` directly in a browser sends a `GET` request. This will intentionally return `Method Not Allowed` because the endpoint requires a `POST` request with a file upload. Use the `/docs` UI or `curl` to test the endpoint.

The repository includes a `render.yaml` blueprint for automated deployment.

## Approach and tradeoffs

Detection is category-specific. Names require strong role/contact/table context; companies require legal-entity evidence plus context; addresses require labels/table columns and multiple address signals; DOB requires an explicit birth label. Emails, valid IPv4 values, SSNs, phones, and Luhn-valid cards use bounded validation. Numeric protection deliberately excludes financial years, ordinary dates, currency, percentages, shares, page numbers, CIN/DIN/PAN-like identifiers, registrations, and market/offer identifiers.

The same normalized PII value receives the same deterministic fake replacement within one run. The tool processes paragraphs, tables (including nested tables), headers, footers, and text boxes where editable OOXML text is available, preserving run formatting as far as practical. It does not OCR images, QR codes, scanned text, charts, comments, tracked deletions, or other unsupported embedded content; warnings are included in the audit.

## Evaluation and testing

Metrics are occurrence/span based: precision is `TP / (TP + FP)`, recall is `TP / (TP + FN)`, and accuracy is `(TP + TN) / (TP + FP + FN + TN)`. Accuracy is not the primary quality metric for this imbalanced document because true negatives are difficult to enumerate; the evaluation report explains the required reviewed ground-truth methodology. Do not interpret pending metrics as measured results.

Run tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Known false-positive risks are legal/corporate prose and identifier-like numbers. Known false-negative risks are unlabelled names/addresses, unusual formats, text in unsupported structures, and image-embedded PII.
