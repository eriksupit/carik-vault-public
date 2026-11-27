"""Behaviour tests for update_carik.py. Run: python3 -m unittest test_update_carik.py -v"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_carik  # noqa: E402

SEEDS = ("SCOPE.md", ".agents/Memory.md", ".agents/Context.md", ".agents/Lessons.md")


def write(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def snapshot(root: Path) -> dict[str, tuple]:
    """Every entry under root: files by hash and mode, dirs, and symlinks by target."""
    out: dict[str, tuple] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                out[rel] = ("link", os.readlink(p))
            elif p.is_dir():
                out[rel] = ("dir",)
            else:
                out[rel] = ("file", hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mode & 0o777)
    return out


class UpdateCarikTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.release = self.make_release("rel", agents="AGENTS v2\n")
        self.target = self.root / "target"
        write(self.target / "AGENTS.md", "AGENTS v1\n")
        write(self.target / "SOURCES.md", "local sources\n")
        write(self.target / "ATURAN-LOKAL.md", "local rules\n")
        write(self.target / ".agents/skills/local-skill/SKILL.md", "local skill\n")

    def make_release(self, name: str, agents: str, owned_extra=(), skills_extra=(), ship_extra=True) -> Path:
        rel = self.root / name
        meta = {
            "schema_version": 1,
            "upstream_skills": ["alpha", *skills_extra],
            "upstream_owned_paths": ["AGENTS.md", "scripts/", ".agents/carik-release.json", *owned_extra],
        }
        write(rel / ".agents/carik-release.json", json.dumps(meta))
        write(rel / "AGENTS.md", agents)
        write(rel / "scripts/tool.py", "print('tool')\n", 0o755)
        write(rel / ".agents/skills/alpha/SKILL.md", "alpha\n")
        write(rel / "ATURAN-LOKAL.md", "release rules must never land\n")
        write(rel / "raw-kb/SOURCES.md", "release sources must never land\n")
        write(rel / "handoff/HANDOFF.md", "never\n")
        for seed in SEEDS:
            write(rel / seed, f"template {seed}\n")
        if ship_extra:
            for extra in owned_extra:
                write(rel / extra, "package claims this\n")
            for skill in skills_extra:
                write(rel / ".agents/skills" / skill / "SKILL.md", "package claims this skill\n")
        return rel

    def run_update(self, apply: bool = False, release: Path | None = None) -> dict:
        return update_carik.run_update(self.target, release or self.release, False, None, apply)

    def run_main(self, *args: str) -> tuple[int, dict]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = update_carik.main(list(args))
        return code, json.loads(buf.getvalue())

    def test_seeds_only_when_absent_and_never_protected_paths(self) -> None:
        result = self.run_update(apply=True)
        self.assertEqual(result["status"], "applied")
        for seed in SEEDS:
            self.assertIn(seed, result["added"])
            self.assertEqual((self.target / seed).read_text(), f"template {seed}\n")
        self.assertEqual((self.target / "ATURAN-LOKAL.md").read_text(), "local rules\n")
        self.assertFalse((self.target / "raw-kb").exists())
        self.assertFalse((self.target / "handoff").exists())

    def test_existing_seeds_are_kept(self) -> None:
        for seed in SEEDS:
            write(self.target / seed, f"custom {seed}\n")
        before = {s: (self.target / s).read_bytes() for s in SEEDS}
        result = self.run_update(apply=True)
        self.assertEqual(result["status"], "applied")
        self.assertFalse(set(SEEDS) & set(result["added"] + result["updated"]))
        self.assertEqual(before, {s: (self.target / s).read_bytes() for s in SEEDS})

    def test_idempotent(self) -> None:
        self.run_update(apply=True)
        again = self.run_update()
        self.assertEqual((again["counts"]["added"], again["counts"]["updated"]), (0, 0))

    def test_aturan_lokal_never_written_even_when_package_claims_it(self) -> None:
        claim = self.make_release("claim", "AGENTS v2\n", owned_extra=["ATURAN-LOKAL.md"])
        result = self.run_update(apply=True, release=claim)  # present, no target metadata
        self.assertNotIn("ATURAN-LOKAL.md", result["added"] + result["updated"])
        self.assertEqual((self.target / "ATURAN-LOKAL.md").read_text(), "local rules\n")
        (self.target / "ATURAN-LOKAL.md").unlink()
        result = self.run_update(apply=True, release=claim)  # absent
        self.assertNotIn("ATURAN-LOKAL.md", result["added"] + result["updated"])
        self.assertFalse((self.target / "ATURAN-LOKAL.md").exists())

    def assert_rejected_without_change(self, release: Path) -> None:
        before = snapshot(self.target)
        for apply in (False, True):
            result = self.run_update(apply=apply, release=release)
            self.assertEqual(result["status"], "rejected", result)
        self.assertEqual(before, snapshot(self.target))

    def test_package_claiming_existing_sources_is_rejected(self) -> None:
        self.run_update(apply=True)  # target now carries release metadata
        claim = self.make_release("claim", "AGENTS v3\n", owned_extra=["SOURCES.md"])
        self.assert_rejected_without_change(claim)
        self.assertEqual((self.target / "SOURCES.md").read_text(), "local sources\n")

    def test_package_claiming_existing_local_skill_is_rejected(self) -> None:
        self.run_update(apply=True)
        claim = self.make_release("claim", "AGENTS v3\n", skills_extra=["local-skill"])
        self.assert_rejected_without_change(claim)
        result = self.run_update(release=claim)
        self.assertIn(".agents/skills/local-skill/SKILL.md", result["reason"])

    def test_claim_without_file_then_file_is_rejected(self) -> None:
        self.run_update(apply=True)
        meta_before = (self.target / ".agents/carik-release.json").read_bytes()
        release_a = self.make_release("a", "AGENTS v3\n", owned_extra=["SOURCES.md"], ship_extra=False)
        self.assert_rejected_without_change(release_a)
        self.assertIn("SOURCES.md", self.run_update(release=release_a)["reason"])
        release_b = self.make_release("b", "AGENTS v4\n", owned_extra=["SOURCES.md"])
        self.assert_rejected_without_change(release_b)
        self.assertEqual((self.target / "SOURCES.md").read_text(), "local sources\n")
        self.assertEqual((self.target / ".agents/carik-release.json").read_bytes(), meta_before)

    def test_new_skill_claim_over_existing_local_folder_is_rejected(self) -> None:
        self.run_update(apply=True)
        claim = self.make_release("claim", "AGENTS v3\n", skills_extra=["local-skill"], ship_extra=False)
        self.assert_rejected_without_change(claim)
        self.assertIn(".agents/skills/local-skill/", self.run_update(release=claim)["reason"])

    def test_narrower_claim_inside_owned_folder_is_accepted(self) -> None:
        self.run_update(apply=True)  # target already owns scripts/ and has scripts/tool.py
        release = self.make_release("narrow", "AGENTS v3\n", owned_extra=["scripts/tool.py"], ship_extra=False)
        result = self.run_update(apply=True, release=release)
        self.assertEqual(result["status"], "applied", result)

    def test_new_owned_path_absent_from_target_is_accepted(self) -> None:
        self.run_update(apply=True)
        release = self.make_release("new", "AGENTS v3\n", owned_extra=["docs/guide.md"])
        result = self.run_update(apply=True, release=release)
        self.assertEqual(result["status"], "applied", result)
        self.assertIn("docs/guide.md", result["added"])
        self.assertEqual((self.target / "docs/guide.md").read_text(), "package claims this\n")

    def test_directory_symlink_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.target / "scripts").symlink_to(outside, target_is_directory=True)
        self.assert_rejected_without_change(self.release)
        self.assertEqual(list(outside.iterdir()), [])

    def test_file_symlink_is_rejected(self) -> None:
        outside = self.root / "outside.md"
        write(outside, "outside\n")
        (self.target / "AGENTS.md").unlink()
        (self.target / "AGENTS.md").symlink_to(outside)
        self.assert_rejected_without_change(self.release)
        self.assertEqual(outside.read_text(), "outside\n")

    def test_backup_path_symlink_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (self.target / "work").symlink_to(outside, target_is_directory=True)
        self.assert_rejected_without_change(self.release)
        self.assertEqual(list(outside.iterdir()), [])

    def test_rapid_applies_get_distinct_backups(self) -> None:
        first = self.run_update(apply=True)
        second = self.run_update(apply=True, release=self.make_release("rel2", "AGENTS v3\n"))
        self.assertEqual((first["status"], second["status"]), ("applied", "applied"))
        self.assertNotEqual(first["backup_dir"], second["backup_dir"])
        b1, b2 = self.target / first["backup_dir"], self.target / second["backup_dir"]
        self.assertEqual((b1 / "AGENTS.md").read_text(), "AGENTS v1\n")
        self.assertEqual((b2 / "AGENTS.md").read_text(), "AGENTS v2\n")
        self.assertEqual(set((b1 / "added.txt").read_text().split()), set(first["added"]))
        self.assertEqual((b2 / "added.txt").read_text(), "")

    def fail_third_target_write(self):
        """Patch os.open so the third updater target write (O_CREAT|O_TRUNC) fails."""
        real_open = os.open
        calls = {"n": 0}
        write_flags = os.O_CREAT | os.O_TRUNC

        def flaky(path, flags, *args, **kwargs):
            if flags & write_flags == write_flags:
                calls["n"] += 1
                if calls["n"] == 3:
                    raise OSError("disk full (simulated)")
            return real_open(path, flags, *args, **kwargs)

        return mock.patch.object(update_carik.os, "open", flaky)

    def test_failure_mid_write_restores_target(self) -> None:
        (self.target / "AGENTS.md").chmod(0o600)
        before = snapshot(self.target)
        with self.fail_third_target_write():
            result = self.run_update(apply=True)
        self.assertEqual(result["status"], "rolled_back", result)
        self.assertIn("disk full", result["reason"])
        self.assertEqual(before, snapshot(self.target))

    def test_failure_while_backing_up_restores_target(self) -> None:
        before = snapshot(self.target)
        with mock.patch.object(update_carik.shutil, "copy2", side_effect=OSError("backup disk full")):
            result = self.run_update(apply=True)
        self.assertEqual(result["status"], "rolled_back", result)
        self.assertIn("backup disk full", result["reason"])
        self.assertEqual(before, snapshot(self.target))  # partial backup folder removed too

    def test_directory_symlink_appearing_after_check_is_not_followed(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        real_apply = update_carik._apply_writes
        swapped = {}

        def swap_then_apply(target_root, *args):
            (target_root / "scripts").symlink_to(outside, target_is_directory=True)
            swapped["snap"] = snapshot(target_root)
            return real_apply(target_root, *args)

        with mock.patch.object(update_carik, "_apply_writes", swap_then_apply):
            result = self.run_update(apply=True)
        self.assertEqual(result["status"], "rolled_back", result)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(swapped["snap"], snapshot(self.target))

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW is POSIX-only")
    def test_final_symlink_blocked_by_nofollow_when_check_misses_it(self) -> None:
        outside = self.root / "outside.md"
        write(outside, "outside\n")
        (self.target / "AGENTS.md").unlink()
        (self.target / "AGENTS.md").symlink_to(outside)
        before = snapshot(self.target)
        with mock.patch.object(update_carik, "_has_symlink", return_value=False):
            result = self.run_update(apply=True)
        self.assertEqual(result["status"], "rolled_back", result)
        self.assertEqual(outside.read_text(), "outside\n")
        self.assertEqual(before, snapshot(self.target))

    def test_failed_rollback_keeps_backup_and_exits_nonzero(self) -> None:
        with self.fail_third_target_write(), mock.patch.object(
            Path, "unlink", side_effect=OSError("unlink refused")
        ):
            code, out = self.run_main("--target", str(self.target), "--source", str(self.release), "--apply")
        self.assertEqual((code, out["status"]), (1, "rollback_failed"), out)
        backup = self.target / out["backup_dir"]
        self.assertIn(out["backup_dir"], out["reason"])
        self.assertIn("added.txt", out["reason"])
        self.assertEqual((backup / "AGENTS.md").read_text(), "AGENTS v1\n")
        self.assertIn("SCOPE.md", (backup / "added.txt").read_text().split())

    def test_exit_codes(self) -> None:
        code, out = self.run_main("--target", str(self.target), "--source", str(self.release))
        self.assertEqual((code, out["status"]), (0, "dry-run"))
        self.run_update(apply=True)
        claim = self.make_release("claim", "AGENTS v3\n", owned_extra=["SOURCES.md"])
        code, out = self.run_main("--target", str(self.target), "--source", str(claim), "--apply")
        self.assertEqual((code, out["status"]), (1, "rejected"))
        bad_zip = self.root / "broken.zip"
        bad_zip.write_bytes(b"not a zip")
        code, out = self.run_main("--target", str(self.target), "--source", str(bad_zip))
        self.assertEqual((code, out["status"]), (1, "unavailable"))


if __name__ == "__main__":
    unittest.main()
