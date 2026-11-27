#!/usr/bin/env python3
"""Convert a registered raw-KB scanned/image PDF to Markdown through native
Poppler and Tesseract tools after pdf-read reports partial extraction."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REQUIRED_TOOLS = ("pdftotext", "pdftoppm", "tesseract")
INSTALL_PROPOSALS = {
    "pdftotext": "brew install poppler",
    "pdftoppm": "brew install poppler",
    "tesseract": "brew install tesseract",
}
PROVENANCE_CLASSES = ("user-provided", "agent-acquired")
DEFAULT_TIMEOUT_SECONDS = 300
MIN_NATIVE_PAGE_CHARACTERS = 100


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


def doctor(vault: Path, timeout: int) -> dict[str, object]:
    if timeout < 1:
        raise AdapterError("invalid_timeout", "timeout must be a positive number of seconds.")
    if not vault.resolve().is_dir():
        raise AdapterError("invalid_vault", f"Vault is not a directory: {vault}")
    found = {tool: shutil.which(tool) for tool in REQUIRED_TOOLS}
    missing = [tool for tool, path in found.items() if not path]
    if missing:
        raise AdapterError(
            "tool_unavailable",
            "One or more OCR tools are not available on PATH; installation requires explicit owner approval.",
            missing_tools=missing,
            install_proposal=" && ".join(INSTALL_PROPOSALS[tool] for tool in missing),
        )
    return {
        "status": "ready",
        "tools": {tool: str(Path(path).resolve()) for tool, path in found.items()},
    }


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


def markdown_document(body: str, source_id: str, source_relative: Path, source_digest: str, page_count: int) -> str:
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
        "  - ocr-derivative",
        f"source_id: {yaml_string(source_id)}",
        f"source_path: {yaml_string(source_relative.as_posix())}",
        f"source_sha256: {source_digest}",
        "parser: pdftotext+pdftoppm+tesseract",
        "pdf_type: \"scanned\"",
        f"page_count: {page_count}",
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
    source_digest = sha256(source)
    with tempfile.TemporaryDirectory() as work:
        completed = run(["pdftotext", "-layout", str(source), "-"], args.timeout)
        if completed.returncode != 0:
            raise AdapterError("conversion_failed", "pdftotext failed.", stderr=completed.stderr.strip())
        pages = completed.stdout.split("\f")
        if pages and not pages[-1].strip():
            pages.pop()
        if not pages:
            raise AdapterError("conversion_failed", "Native extraction returned no pages.")

        ocr_pages: list[int] = []
        for index, page in enumerate(pages, start=1):
            if sum(1 for character in page if not character.isspace()) >= MIN_NATIVE_PAGE_CHARACTERS:
                continue
            prefix = Path(work) / f"page-{index}"
            rendered = run(
                [
                    "pdftoppm",
                    "-f",
                    str(index),
                    "-l",
                    str(index),
                    "-r",
                    "150",
                    "-png",
                    "-singlefile",
                    str(source),
                    str(prefix),
                ],
                args.timeout,
            )
            if rendered.returncode != 0:
                raise AdapterError(
                    "conversion_failed",
                    f"pdftoppm failed on page {index}.",
                    stderr=rendered.stderr.strip(),
                )
            image = prefix.with_suffix(".png")
            if not image.is_file():
                raise AdapterError("conversion_failed", f"pdftoppm did not render page {index}.")
            recognized = run(["tesseract", str(image), "stdout"], args.timeout)
            if recognized.returncode != 0:
                raise AdapterError(
                    "conversion_failed",
                    f"tesseract failed on page {index}.",
                    stderr=recognized.stderr.strip(),
                )
            if not recognized.stdout.strip():
                raise AdapterError("conversion_failed", f"OCR extraction returned empty text for page {index}.")
            pages[index - 1] = recognized.stdout
            ocr_pages.append(index)

    if not any(page.strip() for page in pages):
        raise AdapterError("conversion_failed", "OCR extraction returned empty text.")
    page_count = len(pages)
    marked = "\n\n".join(f"<!-- Page {index} -->\n\n{page.strip()}" for index, page in enumerate(pages, start=1))
    if sha256(source) != source_digest:
        raise AdapterError("source_changed", "Source PDF changed during conversion; no derivative was created.")
    document = markdown_document(marked, args.source_id.strip(), source_relative, source_digest, page_count)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.pdf-ocr-", dir=output.parent)
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
        "tool": "pdftotext+pdftoppm+tesseract",
        "tools": ready["tools"],
        "ocr_pages": ocr_pages,
        "source_id": args.source_id.strip(),
        "source_path": source_relative.as_posix(),
        "source_sha256": source_digest,
        "derivative_path": output_relative.as_posix(),
        "derivative_sha256": sha256(output),
        "pdf_type": "scanned",
        "page_count": page_count,
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
