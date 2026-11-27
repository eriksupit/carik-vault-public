#!/usr/bin/env python3
"""Tests for scripts/preview_artifact.py."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "preview_artifact.py"

class TestPreviewArtifact(unittest.TestCase):
    def test_markdown_compilation(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Sample Header\n\nSample paragraph with **bold** and `code` and [[target|alias]].")
            md_path = Path(f.name)
        out_file = ROOT / ".agents" / "previews" / f"{md_path.stem}.html"
        try:
            res = subprocess.run([sys.executable, str(SCRIPT), str(md_path)], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertIn("file://", res.stdout)
            self.assertTrue(out_file.is_file(), f"Output file missing: {out_file}")
            html_content = out_file.read_text(encoding="utf-8")
            self.assertIn("<h1>Sample Header</h1>", html_content)
            self.assertIn("<strong>bold</strong>", html_content)
            self.assertIn("alias", html_content)
        finally:
            md_path.unlink(missing_ok=True)
            if out_file.is_file():
                out_file.unlink()

    def test_canvas_compilation(self):
        canvas_json = '{"nodes": [{"id": "1", "type": "text", "text": "Card Content"}]}'
        with tempfile.NamedTemporaryFile(suffix=".canvas", mode="w", delete=False) as f:
            f.write(canvas_json)
            canvas_path = Path(f.name)
        out_file = ROOT / ".agents" / "previews" / f"{canvas_path.stem}.html"
        try:
            res = subprocess.run([sys.executable, str(SCRIPT), str(canvas_path)], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertTrue(out_file.is_file())
            html_content = out_file.read_text(encoding="utf-8")
            self.assertIn("Card Content", html_content)
            self.assertIn("canvas-card", html_content)
        finally:
            canvas_path.unlink(missing_ok=True)
            if out_file.is_file():
                out_file.unlink()

    def test_file_size_limit_pre_stat(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="wb", delete=False) as f:
            f.write(b"a" * (2 * 1024 * 1024 + 10))
            large_path = Path(f.name)
        try:
            res = subprocess.run([sys.executable, str(SCRIPT), str(large_path)], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0)
            self.assertIn("exceeds 2MB limit", res.stderr)
        finally:
            large_path.unlink(missing_ok=True)
    def test_cli_vault_argument(self):
        with tempfile.TemporaryDirectory() as custom_vault:
            vault_path = Path(custom_vault)
            with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
                f.write("# Vault Header\nContent")
                md_path = Path(f.name)
            try:
                res = subprocess.run(
                    [sys.executable, str(SCRIPT), str(md_path), "--vault", str(vault_path)],
                    capture_output=True, text=True, check=False
                )
                self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
                expected_out = vault_path / ".agents" / "previews" / f"{md_path.stem}.html"
                self.assertTrue(expected_out.is_file(), f"Custom vault preview missing: {expected_out}")
            finally:
                md_path.unlink(missing_ok=True)

    def test_cli_json_argument(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Header\nText")
            md_path = Path(f.name)
        out_file = ROOT / ".agents" / "previews" / f"{md_path.stem}.html"
        try:
            res = subprocess.run(
                [sys.executable, str(SCRIPT), str(md_path), "--json"],
                capture_output=True, text=True, check=False
            )
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            import json
            data = json.loads(res.stdout)
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("target"), str(md_path.resolve()))
            self.assertTrue(data.get("file_uri", "").startswith("file://"))
            self.assertEqual(data.get("html_path"), str(out_file.resolve()))
        finally:
            md_path.unlink(missing_ok=True)
            if out_file.is_file():
                out_file.unlink()

    def test_json_artifact_compilation(self):
        sample_json = '{"name": "test", "items": [1, 2, 3]}'
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(sample_json)
            json_path = Path(f.name)
        out_file = ROOT / ".agents" / "previews" / f"{json_path.stem}.html"
        try:
            res = subprocess.run([sys.executable, str(SCRIPT), str(json_path)], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertTrue(out_file.is_file())
            html_content = out_file.read_text(encoding="utf-8")
            self.assertIn("class=\"language-json\"", html_content)
            self.assertIn('&quot;name&quot;: &quot;test&quot;', html_content)
        finally:
            json_path.unlink(missing_ok=True)
            if out_file.is_file():
                out_file.unlink()

    def test_html_passthrough_compilation(self):
        sample_html = '<div class="custom-card"><p>Hello HTML</p></div>'
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
            f.write(sample_html)
            html_path = Path(f.name)
        out_file = ROOT / ".agents" / "previews" / f"{html_path.stem}.html"
        try:
            res = subprocess.run([sys.executable, str(SCRIPT), str(html_path)], capture_output=True, text=True, check=False)
            self.assertEqual(res.returncode, 0, f"Error: {res.stderr}")
            self.assertTrue(out_file.is_file())
            html_content = out_file.read_text(encoding="utf-8")
            self.assertIn("Hello HTML", html_content)
        finally:
            html_path.unlink(missing_ok=True)
            if out_file.is_file():
                out_file.unlink()

if __name__ == "__main__":
    unittest.main()
