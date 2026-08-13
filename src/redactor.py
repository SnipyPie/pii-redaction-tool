"""CLI orchestration for conservative DOCX PII redaction."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .audit import write_audit
from .detectors import CATEGORIES, detect_locations, select_candidates
from .docx_io import apply_replacements, extract_locations, load_document, save_and_reopen
from .entity_store import EntityStore

DEFAULT_INPUT = Path("input/Red Herring Prospectus.docx")
DEFAULT_OUTPUT = Path("output/redacted_prospectus.docx")
DEFAULT_AUDIT = Path("reports/redaction_audit.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Redact supported PII from a DOCX without modifying the input.")
    parser.add_argument("input_docx", nargs="?", type=Path, default=DEFAULT_INPUT, help=f"Source DOCX (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"Redacted DOCX (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT, help=f"Audit JSON (default: {DEFAULT_AUDIT})")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output or audit file.")
    parser.add_argument("--dry-run", action="store_true", help="Detect and write audit JSON without creating DOCX output.")
    parser.add_argument("--categories", help="Comma-separated subset: " + ", ".join(CATEGORIES))
    parser.add_argument("--verbose", action="store_true", help="Print category counts and warnings without raw PII.")
    return parser


def _parse_categories(value: str | None) -> set[str]:
    if not value:
        return set(CATEGORIES)
    selected = {item.strip().upper() for item in value.split(",") if item.strip()}
    unknown = selected - set(CATEGORIES)
    if unknown:
        raise ValueError("Unsupported categories: " + ", ".join(sorted(unknown)))
    if not selected:
        raise ValueError("--categories must contain at least one supported category.")
    return selected


def _same_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def run(args: argparse.Namespace) -> tuple[dict[str, object], int]:
    input_path: Path = args.input_docx
    output_path: Path = args.output
    audit_path: Path = args.audit
    if not input_path.is_file():
        raise ValueError(f"Input DOCX does not exist: {input_path}")
    if _same_path(input_path, output_path):
        raise ValueError("Input and output paths must be different.")
    if not args.dry_run and output_path.exists() and not args.overwrite:
        raise ValueError(f"Output already exists (use --overwrite): {output_path}")
    if audit_path.exists() and not args.overwrite:
        raise ValueError(f"Audit already exists (use --overwrite): {audit_path}")
    categories = _parse_categories(args.categories)
    try:
        document = load_document(input_path)
    except Exception as exc:  # python-docx wraps malformed archive/XML errors variably.
        raise ValueError(f"Input is not a readable DOCX: {exc}") from exc
    bindings, warnings = extract_locations(document)
    accepted, rejected = select_candidates(detect_locations((binding.location for binding in bindings.values()), categories))
    store = EntityStore()
    replacement_values = {detection.detection_id: store.replacement_for(detection.candidate.category, detection.candidate.normalized_value) for detection in accepted}
    if not args.dry_run:
        warnings.extend(apply_replacements(bindings, ((detection, replacement_values[detection.detection_id].value) for detection in accepted)))
        try:
            save_and_reopen(document, output_path)
        except Exception as exc:
            raise RuntimeError(f"Could not save/reopen output DOCX: {exc}") from exc
    payload = write_audit(audit_path, input_path, None if args.dry_run else output_path, accepted, replacement_values, rejected, warnings)
    return payload, 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        payload, exit_code = run(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    except Exception as exc:
        print(f"Processing failure: {exc}", file=sys.stderr)
        return 1
    if args.verbose:
        print("Detection counts:", payload["counts_by_category"], file=sys.stderr)
        for warning in payload["warnings"]:
            print(f"Warning: {warning}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
