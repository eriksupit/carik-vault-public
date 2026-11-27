#!/usr/bin/env python3
"""Behavior tests for the native Poppler/Tesseract OCR adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


SCRIPT = Path(__file__).with_name("pdf_ocr.py")
SOURCE_ID = "SRC-TEST"


class PdfOcrTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.source = self.root / "raw-kb" / "user-provided" / "brief.pdf"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"fake-pdf")
        self.output = self.source.with_suffix(".md")
        self.environment = os.environ.copy()
        self.environment["PATH"] = f"{self.bin}{os.pathsep}{self.environment['PATH']}"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def executable(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(
            "#!/usr/bin/env python3\n" + textwrap.dedent(body),
            encoding="utf-8",
        )
        path.chmod(0o755)

    def run_adapter(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            text=True,
            capture_output=True,
            check=False,
            env=self.environment,
        )

    def install_native_tools(self) -> None:
        self.executable(
            "pdftotext",
            """
            import sys
            sparse_two = "header" + (" \\n" * 60) + "footer"
            sparse_four = "chart" + (" \\n" * 60) + "legend"
            sys.stdout.write(("native page 1 " * 10) + "\\f" + sparse_two + "\\f" + ("native page 3 " * 10) + "\\f" + sparse_four + "\\f")
            """,
        )
        self.executable(
            "pdftoppm",
            """
            import pathlib
            import sys
            page = sys.argv[sys.argv.index("-f") + 1]
            pathlib.Path(sys.argv[-1] + ".png").write_text(page)
            """,
        )
        self.executable(
            "tesseract",
            """
            import pathlib
            import sys
            page = pathlib.Path(sys.argv[1]).read_text()
            print(f"OCR page {page}")
            """,
        )

    def test_doctor_accepts_native_tools_without_ocrmypdf(self) -> None:
        self.install_native_tools()

        completed = self.run_adapter("doctor", "--vault", str(self.root))

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(set(payload["tools"]), {"pdftotext", "pdftoppm", "tesseract"})

    def test_ingest_ocrs_sparse_pages_in_source_order_and_preserves_markers(self) -> None:
        self.install_native_tools()

        completed = self.run_adapter(
            "ingest",
            "--vault",
            str(self.root),
            "--source",
            str(self.source.relative_to(self.root)),
            "--output",
            str(self.output.relative_to(self.root)),
            "--source-id",
            SOURCE_ID,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "converted")
        self.assertEqual(payload["source_id"], SOURCE_ID)
        self.assertEqual(payload["tool"], "pdftotext+pdftoppm+tesseract")
        self.assertEqual(payload["page_count"], 4)
        self.assertEqual(payload["ocr_pages"], [2, 4])
        markdown = self.output.read_text(encoding="utf-8")
        self.assertIn("parser: pdftotext+pdftoppm+tesseract", markdown)
        self.assertEqual(
            [line for line in markdown.splitlines() if line.startswith("<!-- Page ")],
            ["<!-- Page 1 -->", "<!-- Page 2 -->", "<!-- Page 3 -->", "<!-- Page 4 -->"],
        )
        self.assertIn("native page 1", markdown)
        self.assertIn("OCR page 2", markdown)
        self.assertIn("native page 3", markdown)
        self.assertIn("OCR page 4", markdown)

    def test_ingest_rejects_an_unreadable_sparse_page(self) -> None:
        self.install_native_tools()
        self.executable("tesseract", 'print("")')

        completed = self.run_adapter(
            "ingest",
            "--vault",
            str(self.root),
            "--source",
            str(self.source.relative_to(self.root)),
            "--output",
            str(self.output.relative_to(self.root)),
            "--source-id",
            SOURCE_ID,
        )

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "conversion_failed")
        self.assertIn("page 2", payload["message"])
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
