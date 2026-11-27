#!/usr/bin/env python3
"""Safely convert a registered raw-KB PDF with a machine-level pdf2md CLI."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PDF_INSPECTOR_VERSION = "0.1.8"
INSTALL_PROPOSAL = f"cargo install pdf-inspector --version {PDF_INSPECTOR_VERSION} --locked"
REQUIRED_CAPABILITIES = ("--json", "--detect-only", "--raw", "--compact", "--pages")
EXTRACTION_OPTIONS = ("--raw", "--compact", "--pages")
FALLBACK_TOOL = "poppler-pdftotext"
FALLBACK_OPTIONS = ("-q", "-nopgbrk", "-f/-l per page")
PROVENANCE_CLASSES = ("user-provided", "agent-acquired")
DEFAULT_TIMEOUT_SECONDS = 120


class AdapterError(Exception):
    def __init__(self, status: str, message: str, **details: object) -> None:
        super().__init__(message)
        self.payload = {"status": status, "message": message, **details}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError) as error:
        raise AdapterError("conversion_failed", str(error)) from error


def cargo_version(cargo: str, timeout: int) -> str | None:
    completed = run([cargo, "install", "--list"], timeout)
    if completed.returncode != 0:
        return None
    match = re.search(r"^pdf-inspector v([^:]+):$", completed.stdout, re.MULTILINE)
    return match.group(1) if match else None


def doctor(vault: Path, timeout: int) -> dict[str, object]:
    if timeout < 1:
        raise AdapterError("invalid_timeout", "timeout must be a positive number of seconds.")
    if not vault.resolve().is_dir():
        raise AdapterError("invalid_vault", f"Vault is not a directory: {vault}")
    executable = shutil.which("pdf2md")
    if not executable:
        raise AdapterError(
            "tool_unavailable",
            "pdf2md is not available on PATH; installation requires explicit owner approval.",
            install_proposal=INSTALL_PROPOSAL,
        )
    cargo = shutil.which("cargo")
    installed = cargo_version(cargo, timeout) if cargo else None
    if installed != PDF_INSPECTOR_VERSION:
        raise AdapterError(
            "tool_version_mismatch",
            f"Expected pdf-inspector {PDF_INSPECTOR_VERSION}, found {installed or 'unknown'}.",
            expected_version=PDF_INSPECTOR_VERSION,
            detected_version=installed,
            install_proposal=INSTALL_PROPOSAL,
        )
    probe = run([executable], timeout)
    help_text = probe.stdout + probe.stderr
    missing = [flag for flag in REQUIRED_CAPABILITIES if flag not in help_text]
    if missing:
        raise AdapterError(
            "unsupported_capability",
            "Installed pdf2md lacks required CLI options.",
            missing_capabilities=missing,
        )
    fallback = poppler_extractor(timeout)
    return {
        "status": "ready",
        "tool": "pdf-inspector",
        "tool_version": PDF_INSPECTOR_VERSION,
        "executable": str(Path(executable).resolve()),
        "capabilities": list(REQUIRED_CAPABILITIES),
        "fallback_tool": FALLBACK_TOOL if fallback else None,
        "fallback_version": fallback[1] if fallback else None,
        "fallback_executable": fallback[0] if fallback else None,
    }


def poppler_extractor(timeout: int) -> tuple[str, str] | None:
    """Resolve the fallback extractor and its self-reported version, or None."""
    executable = shutil.which("pdftotext")
    if not executable:
        return None
    completed = run([executable, "-v"], timeout)
    match = re.search(r"pdftotext version (\S+)", completed.stdout + completed.stderr)
    if not match:
        return None
    return str(Path(executable).resolve()), match.group(1)


def fallback_body(executable: str, source: Path, page_count: int, timeout: int) -> str:
    """Extract page by page with poppler, emitting the same page markers as pdf2md.

    pdf-inspector 0.1.8 silently omits pages whose text it cannot map, which the
    marker check rejects. Poppler is asked for one page at a time so a dropped
    page is impossible: an empty page is reported as `partial_extraction`.
    """
    sections: list[str] = []
    empty: list[int] = []
    for page in range(1, page_count + 1):
        completed = run([executable, "-q", "-nopgbrk", "-f", str(page), "-l", str(page), str(source), "-"], timeout)
        if completed.returncode != 0:
            raise AdapterError(
                "conversion_failed",
                "Fallback PDF extraction failed.",
                page=page,
                stderr=completed.stderr.strip(),
            )
        text = completed.stdout.strip()
        if not text:
            empty.append(page)
        sections.append(f"<!-- Page {page} -->\n\n{text}")
    if empty:
        raise AdapterError(
            "partial_extraction",
            "Fallback extraction returned no text for one or more pages.",
            empty_pages=empty,
        )
    return "\n\n".join(sections)


def resolve_inside(vault: Path, value: str, status: str) -> tuple[Path, Path]:
    root = vault.resolve()
    supplied = Path(value)
    path = supplied.resolve() if supplied.is_absolute() else (root / supplied).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise AdapterError(status, f"Path escapes the vault: {value}") from error
    return path, relative


def provenance_class(relative: Path) -> str | None:
    parts = relative.parts
    if len(parts) >= 3 and parts[0] == "raw-kb" and parts[1] in PROVENANCE_CLASSES:
        return parts[1]
    return None


def validate_paths(vault: Path, source_value: str, output_value: str) -> tuple[Path, Path, Path, Path]:
    source, source_relative = resolve_inside(vault, source_value, "invalid_source")
    output, output_relative = resolve_inside(vault, output_value, "invalid_destination")
    source_class = provenance_class(source_relative)
    output_class = provenance_class(output_relative)
    if not source.is_file() or source.suffix.lower() != ".pdf" or not source_class:
        raise AdapterError("invalid_source", "Source must be an existing PDF in a raw-KB provenance directory.")
    if output.suffix.lower() != ".md" or not output_class or output_class != source_class:
        raise AdapterError("invalid_destination", "Output must be Markdown in the source provenance class.")
    if output.exists() or not output.parent.is_dir():
        raise AdapterError("invalid_destination", "Output must not exist and its parent directory must exist.")
    return source, source_relative, output, output_relative


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def atomic_publish(temporary: Path, output: Path) -> None:
    try:
        os.link(temporary, output)
    except FileExistsError as error:
        raise AdapterError("invalid_destination", "Output appeared during conversion and was not overwritten.") from error
    except OSError as error:
        raise AdapterError("conversion_failed", f"Could not publish Markdown derivative: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)


def markdown_document(
    body: str,
    source_id: str,
    source_relative: Path,
    source_digest: str,
    page_count: int,
    parser_name: str,
    parser_version: str,
    options: tuple[str, ...],
) -> str:
    today = date.today().isoformat()
    title = source_relative.stem.replace("-", " ").replace("_", " ").strip() or "PDF derivative"
    return "\n".join((
        "---",
        f"title: {yaml_string(title)}",
        f"date: {today}",
        f"updated: {today}",
        "type: source-derivative",
        "status: extracted",
        "tags:",
        "  - raw-kb",
        "  - pdf-derivative",
        f"source_id: {yaml_string(source_id)}",
        f"source_path: {yaml_string(source_relative.as_posix())}",
        f"source_sha256: {source_digest}",
        f"parser: {parser_name}",
        f"parser_version: {parser_version}",
        "pdf_type: text_based",
        f"page_count: {page_count}",
        "extraction_options:",
        *(f"  - {yaml_string(option)}" for option in options),
        "---",
        "",
        body.rstrip(),
        "",
    ))


def ingest(args: argparse.Namespace) -> dict[str, object]:
    vault = Path(args.vault).resolve()
    if not args.source_id.strip() or "\n" in args.source_id or "\x00" in args.source_id:
        raise AdapterError("invalid_source", "source-id must be a non-empty single line.")
    source, source_relative, output, output_relative = validate_paths(vault, args.source, args.output)
    ready = doctor(vault, args.timeout)
    executable = str(ready["executable"])
    source_digest = sha256(source)
    detected = run([executable, str(source), "--detect-only", "--json"], args.timeout)
    if detected.returncode != 0:
        raise AdapterError("conversion_failed", "PDF classification failed.", stderr=detected.stderr.strip())
    try:
        classification = json.loads(detected.stdout)
    except json.JSONDecodeError as error:
        raise AdapterError("conversion_failed", "PDF classification returned invalid JSON.") from error
    pdf_type = classification.get("pdf_type")
    ocr_pages = classification.get("pages_needing_ocr") or []
    encoding_issues = bool(classification.get("has_encoding_issues"))
    page_count = classification.get("page_count")
    if pdf_type in {"scanned", "image_based"}:
        raise AdapterError("ocr_required", "PDF requires OCR; no Markdown derivative was created.", pdf_type=pdf_type, pages_needing_ocr=ocr_pages)
    if pdf_type != "text_based" or ocr_pages or encoding_issues:
        raise AdapterError(
            "partial_extraction",
            "PDF cannot produce a complete native-text derivative.",
            pdf_type=pdf_type,
            pages_needing_ocr=ocr_pages,
            has_encoding_issues=encoding_issues,
        )
    if not isinstance(page_count, int) or page_count < 1:
        raise AdapterError("conversion_failed", "Classification returned an invalid page count.")
    expected_markers = list(range(1, page_count + 1))
    parser_name, parser_version, options = "pdf-inspector", PDF_INSPECTOR_VERSION, EXTRACTION_OPTIONS
    extracted = run([executable, str(source), *EXTRACTION_OPTIONS], args.timeout)
    body = extracted.stdout if extracted.returncode == 0 else ""
    markers = [int(value) for value in re.findall(r"<!-- Page (\d+) -->", body)]
    if not body.strip() or markers != expected_markers:
        fallback = poppler_extractor(args.timeout)
        if not fallback:
            raise AdapterError(
                "conversion_failed",
                "Primary extraction dropped pages and no fallback extractor is available.",
                page_markers=markers,
                fallback_proposal="install poppler (pdftotext)",
            )
        fallback_executable, fallback_version = fallback
        body = fallback_body(fallback_executable, source, page_count, args.timeout)
        markers = [int(value) for value in re.findall(r"<!-- Page (\d+) -->", body)]
        if markers != expected_markers:
            raise AdapterError("conversion_failed", "Markdown page markers do not match the detected page count.", page_markers=markers)
        parser_name, parser_version, options = FALLBACK_TOOL, fallback_version, FALLBACK_OPTIONS
    if sha256(source) != source_digest:
        raise AdapterError("source_changed", "Source PDF changed during conversion; no derivative was created.")
    document = markdown_document(
        body,
        args.source_id.strip(),
        source_relative,
        source_digest,
        page_count,
        parser_name,
        parser_version,
        options,
    )
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.pdf-ingest-", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(document)
        atomic_publish(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "status": "converted",
        "provenance_status": "provenance_incomplete",
        "tool": parser_name,
        "tool_version": parser_version,
        "executable": ready["executable"],
        "classifier": ready["tool"],
        "classifier_version": ready["tool_version"],
        "source_id": args.source_id.strip(),
        "source_path": source_relative.as_posix(),
        "source_sha256": source_digest,
        "derivative_path": output_relative.as_posix(),
        "derivative_sha256": sha256(output),
        "pdf_type": pdf_type,
        "page_count": page_count,
        "options": list(options),
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="operation", required=True)
    doctor_parser = subcommands.add_parser("doctor")
    doctor_parser.add_argument("--vault", required=True)
    doctor_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    ingest_parser = subcommands.add_parser("ingest")
    ingest_parser.add_argument("--vault", required=True)
    ingest_parser.add_argument("--source", required=True)
    ingest_parser.add_argument("--output", required=True)
    ingest_parser.add_argument("--source-id", required=True)
    ingest_parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        result = doctor(Path(args.vault), args.timeout) if args.operation == "doctor" else ingest(args)
    except AdapterError as error:
        print(json.dumps(error.payload, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
