#!/usr/bin/env python3
"""Regression: stage-reset writes its manifest before moving, resumes idempotently, and verifies archived bytes."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_reset  # noqa: E402

FILES = {"work/build/app.py": "print('x')\n", "work/review/report.md": "# review\n", "work/verification/log.md": "ok\n"}


class StageResetApplyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "profile.json").write_text(
            json.dumps({"pipeline": ["research", "implementation-plan", "build", "verification", "review"]}), encoding="utf-8"
        )
        for rel, text in FILES.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")
        self.engine = stage_reset.StageResetEngine(self.root)
        self.plan = self.engine.plan("implementation-plan", "design invalidated")
        self.archive = self.root / "archive/runs" / f"{self.plan['run_id']}-{self.plan['from_stage']}-to-implementation-plan"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def assert_fully_archived(self) -> None:
        manifest = json.loads((self.archive / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(FILES), sorted(entry["path"] for entry in manifest))
        checksums = (self.archive / "CHECKSUMS.sha256").read_text(encoding="utf-8")
        for rel, text in FILES.items():
            digest = hashlib.sha256(text.encode()).hexdigest()
            self.assertFalse((self.root / rel).exists(), rel)
            self.assertEqual(text, (self.archive / rel).read_text(encoding="utf-8"))
            self.assertIn(f"{digest}  {rel}", checksums)
        self.assertFalse((self.root / ".agents/stage-reset-token.json").exists())

    def crash_on_second_move(self, first_move):
        calls = []

        def flaky(src, dst):
            calls.append(src)
            if len(calls) == 2:
                raise OSError("disk yanked")
            return first_move(src, dst)

        with mock.patch.object(stage_reset.shutil, "move", side_effect=flaky):
            with self.assertRaises(stage_reset.StageResetError):
                self.engine.apply(self.plan["plan_token"])

    def test_apply_archives_with_verified_manifest(self) -> None:
        result = self.engine.apply(self.plan["plan_token"])
        self.assertEqual(3, result["swept_files_count"])
        self.assert_fully_archived()

    def test_manifest_exists_before_first_move_and_resume_completes(self) -> None:
        self.crash_on_second_move(shutil.move)
        manifest = json.loads((self.archive / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(3, len(manifest))
        result = self.engine.apply(self.plan["plan_token"])
        self.assertEqual(3, result["swept_files_count"])
        self.assert_fully_archived()

    def test_resume_after_copy_without_source_removal(self) -> None:
        self.crash_on_second_move(lambda src, dst: shutil.copy2(src, dst))
        self.engine.apply(self.plan["plan_token"])
        self.assert_fully_archived()

    def test_resume_refuses_corrupted_archive_copy(self) -> None:
        self.crash_on_second_move(shutil.move)
        moved = next(rel for rel in sorted(FILES) if (self.archive / rel).is_file())
        (self.archive / moved).write_text("tampered\n", encoding="utf-8")
        with self.assertRaisesRegex(stage_reset.StageResetError, "does not match its manifest SHA-256"):
            self.engine.apply(self.plan["plan_token"])

    def test_modified_source_on_resume_is_never_deleted(self) -> None:
        self.crash_on_second_move(lambda src, dst: shutil.copy2(src, dst))
        copied = sorted(FILES)[0]
        self.assertTrue((self.archive / copied).is_file() and (self.root / copied).is_file())
        (self.root / copied).write_text("owner revised this after the crash\n", encoding="utf-8")
        with self.assertRaisesRegex(stage_reset.StageResetError, "changed since the manifest was written"):
            self.engine.apply(self.plan["plan_token"])
        self.assertEqual("owner revised this after the crash\n", (self.root / copied).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
