#!/usr/bin/env python3
"""Test verification for .agents/previews/style.css and gitignore hygiene."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
STYLE_FILE = ROOT / ".agents" / "previews" / "style.css"

class TestPreviewStyle(unittest.TestCase):
    def test_stylesheet_exists_and_contains_core_rules(self):
        self.assertTrue(STYLE_FILE.is_file(), f"Missing stylesheet at {STYLE_FILE}")
        content = STYLE_FILE.read_text(encoding="utf-8")
        self.assertIn(":root", content)
        self.assertIn("prefers-color-scheme: dark", content)
        self.assertIn("overflow-x: auto", content)
        self.assertIn("max-width:", content)

    def test_gitignore_ignores_html_previews(self):
        res = subprocess.run(
            ["git", "check-ignore", "-q", "--no-index", ".agents/previews/preview.html"], cwd=ROOT, check=False
        )
        self.assertEqual(res.returncode, 0, "generated HTML previews must be git-ignored")

if __name__ == "__main__":
    unittest.main()
