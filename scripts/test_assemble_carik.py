#!/usr/bin/env python3
"""Unit tests for scripts/assemble_carik.py reproducibility and package sterility."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
ASSEMBLER = ROOT / "scripts" / "assemble_carik.py"
TARGET = ROOT / "work" / "build" / "carik"
ZIP_OUT = ROOT / "work" / "build" / "carik-vault-release.zip"

FORBIDDEN_TOKENS = (
    "profiles/",
    ".git/",
    "pane-management",
    "deepseek-runner",
    "branch-scope",
    ".agents/skills/anti-translationese",
    "cvp-team",
    ".agents/sessions",
    "openai.yaml",
    "test_pdf_ocr.py",
    "test_resolve_handoff.py",
)


class TestAssembleCarik(unittest.TestCase):
    def _run_assemble(self) -> str:
        res = subprocess.run(
            [sys.executable, str(ASSEMBLER)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=60,
            check=True,
        )
        for line in res.stdout.splitlines():
            if line.startswith("ZIP_SHA256="):
                return line.split("=", 1)[1].strip()
        self.fail(f"Missing ZIP_SHA256 in output: {res.stdout}")

    def test_reproducible_zip_sha256_and_sterility(self) -> None:
        sha1 = self._run_assemble()
        sha2 = self._run_assemble()
        self.assertEqual(sha1, sha2, "ZIP SHA-256 must be 100% identical across consecutive builds")

        # Verify assembled tree sterility
        rel_paths = [p.relative_to(TARGET).as_posix() for p in TARGET.rglob("*")]
        for rp in rel_paths:
            for bad in FORBIDDEN_TOKENS:
                self.assertNotIn(bad, rp, f"Forbidden artifact in work/build/carik/: {rp}")

        # Verify exact 30 skills, 3 commands, 4 hooks, 3 scripts
        skills = sorted(
            d.name for d in (TARGET / ".agents/skills").iterdir()
            if d.is_dir() and (d / "SKILL.md").is_file()
        )
        self.assertEqual(len(skills), 30)
        self.assertIn("carik-guided-goal", skills)
        self.assertIn("scratchpad", skills)
        commands = sorted(p.name for p in (TARGET / ".agents/commands").iterdir() if p.is_file())
        self.assertEqual(commands, ["bootstrap.md", "orient.md", "sepakat-atau-debat.md"])
        hooks = sorted(p.name for p in (TARGET / ".agents/hooks").iterdir() if p.is_file())
        self.assertEqual(
            hooks,
            [
                "git-scope-guard.py",
                "interview_credential_redactor.py",
                "public-pretool.py",
                "vault-boundary-guard.py",
            ],
        )
        scripts = sorted(p.name for p in (TARGET / "scripts").iterdir() if p.is_file())
        self.assertEqual(scripts, ["governance_store.py", "skill_store.py", "sync-skills.py"])

        # Verify .obsidian identity files are valid JSON
        for name in ("app.json", "appearance.json", "core-plugins.json"):
            json.loads((TARGET / ".obsidian" / name).read_text(encoding="utf-8"))

        # Verify ZIP contents include dotfiles, empty dirs, and zero forbidden entries
        with zipfile.ZipFile(ZIP_OUT, "r") as zf:
            names = zf.namelist()
            for n in names:
                for bad in FORBIDDEN_TOKENS:
                    self.assertNotIn(bad, n, f"Forbidden artifact in ZIP: {n}")
            self.assertIn("carik-vault/.obsidian/app.json", names)
            self.assertIn("carik-vault/.agents/skills/manifest.json", names)
            self.assertIn("carik-vault/work/inbox/", names)
            self.assertIn("carik-vault/work/canon/", names)
            self.assertIn("carik-vault/.agents/skills/id-prose/scripts/fact_diff.py", names)
            self.assertIn("carik-vault/.agents/skills/id-prose/scripts/check_sentences.py", names)
            self.assertIn("carik-vault/.agents/skills/carik-guided-goal/SKILL.md", names)
            self.assertIn("carik-vault/.agents/skills/scratchpad/SKILL.md", names)

    def test_sync_skills_check_passes_inside_assembled_package(self) -> None:
        self._run_assemble()
        res = subprocess.run(
            [sys.executable, "-B", "scripts/sync-skills.py", "--check"],
            capture_output=True,
            text=True,
            cwd=TARGET,
            timeout=30,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("CHECK project=30 ", res.stdout)
        self.assertIn("errors=0", res.stdout)

    def test_public_pretool_hook_runs_inside_assembled_package(self) -> None:
        self._run_assemble()
        hook = TARGET / ".agents/hooks/public-pretool.py"
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(TARGET), "PYTHONDONTWRITEBYTECODE": "1"}

        def run(file_path: Path, content: str = "halo") -> subprocess.CompletedProcess[bytes]:
            payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": str(file_path), "content": content}}
            return subprocess.run([sys.executable, "-B", str(hook)], input=json.dumps(payload).encode(), capture_output=True, cwd=TARGET, env=env, timeout=30)

        self.assertEqual(0, run(TARGET / "work/inbox/catatan.md").returncode)
        self.assertEqual(2, run(Path.home() / ".ssh" / "id_rsa").returncode)
        secret = run(TARGET / "work/inbox/rahasia.md", "OPENAI_API_KEY=real_live_secret_value_999")
        self.assertEqual(2, secret.returncode)
        self.assertNotIn(b"real_live_secret_value_999", secret.stdout + secret.stderr)
        self.assertEqual([], [p for p in TARGET.rglob("__pycache__")])

    def test_shipped_launcher_commands_enforce_boundary(self) -> None:
        self._run_assemble()

        def commands(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "command":
                        yield value
                    else:
                        yield from commands(value)
            elif isinstance(node, list):
                for item in node:
                    yield from commands(item)

        def claude(path: Path) -> dict:
            return {"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"file_path": str(path), "content": "halo"}}

        def codex(path: Path) -> dict:
            return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "halo"}}

        def antigravity(path: Path) -> dict:
            return {"toolCall": {"name": "write_to_file", "args": {"TargetFile": str(path), "CodeContent": "halo"}}}

        # Antigravity App runs hooks with cwd=<vault>/.agents; the others run from the vault root.
        runtimes = (
            (".claude/settings.json", TARGET, claude),
            (".codex/hooks.json", TARGET, codex),
            (".agents/hooks.json", TARGET / ".agents", antigravity),
        )
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(TARGET), "PYTHONDONTWRITEBYTECODE": "1"}
        for config, cwd, payload in runtimes:
            launchers = list(commands(json.loads((TARGET / config).read_text(encoding="utf-8"))))
            self.assertEqual(1, len(launchers), config)
            for target, expected in ((TARGET / "work/inbox/catatan.md", 0), (Path.home() / ".ssh" / "id_ed25519", 2)):
                with self.subTest(config=config, target=str(target)):
                    res = subprocess.run(
                        ["/bin/sh", "-c", launchers[0]], input=json.dumps(payload(target)).encode(),
                        capture_output=True, cwd=cwd, env=env, timeout=30,
                    )
                    self.assertEqual(expected, res.returncode, res.stderr.decode("utf-8", "replace"))
        self.assertEqual([], list(TARGET.rglob("__pycache__")))

    def test_public_gitignore_and_participant_creative_law(self) -> None:
        self._run_assemble()
        ignored = (TARGET / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".agents/sessions/workers/", ignored)
        self.assertIn(".DS_Store", ignored)

        law = (TARGET / "CREATIVE-LAW.md").read_text(encoding="utf-8")
        for principle in ("Human-Sovereign, File-First, Intelligence-First", "Tiga Pilar", "Empat Pintu Tantangan", "## 3. Invarian Mutlak", "Zona Kerja Harian", "Zona Pendukung"):
            self.assertIn(principle, law)
        for dead in ("work/build/carik", "work/WORKFLOW.md", "docs/design/", "docs/plans/", "profiles/", "work/research/", "work/implementation-plan/", "perkakas pabrik", "rekayasa pabrik"):
            self.assertNotIn(dead, law)
        with zipfile.ZipFile(ZIP_OUT) as zf:
            self.assertEqual(law.encode("utf-8"), zf.read("carik-vault/CREATIVE-LAW.md"))
            self.assertIn("carik-vault/.gitignore", zf.namelist())

    def test_release_metadata_ownership_and_public_skill_overrides(self) -> None:
        self._run_assemble()
        meta = json.loads((TARGET / ".agents" / "carik-release.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["built_date"], "2026-11-26")
        self.assertIn("ATURAN-LOKAL.md", meta["protected_user_paths"])
        expected_docs = (
            "docs/01-CARA-KERJA-DAN-DIAGNOSIS.md",
            "docs/02-PANDUAN-HARNESS-POPULER.md",
            "docs/03-KATALOG-SKILL-VAULT.md",
        )
        for doc_path in expected_docs:
            self.assertIn(doc_path, meta["upstream_owned_paths"])
            self.assertTrue((TARGET / doc_path).is_file(), f"Missing assembled doc: {doc_path}")
        self.assertNotIn("docs/", meta["upstream_owned_paths"])

        with zipfile.ZipFile(ZIP_OUT) as zf:
            zip_meta = json.loads(zf.read("carik-vault/.agents/carik-release.json").decode("utf-8"))
            self.assertEqual(meta, zip_meta)
            for doc_path in expected_docs:
                self.assertIn(f"carik-vault/{doc_path}", zf.namelist())
                self.assertEqual((TARGET / doc_path).read_bytes(), zf.read(f"carik-vault/{doc_path}"))

        # Verify public skill overrides are free of factory jargon and obsolete path references
        for skill_name in ("orient", "backup-drive", "update-carik", "show-visual", "make-pdf", "scratchpad"):
            body = (TARGET / ".agents" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
            for bad_ref in (
                "work/review/",
                "allow-external",
                "VAULT_ALLOW_EXTERNAL",
                "gh api",
                "Worker Checkpoint",
                "pane-management",
                "deepseek-runner",
                "branch-scope",
                "docs/plans/",
                "sinkronkan dari pabrik",
            ):
                self.assertNotIn(bad_ref, body, f"Forbidden token {bad_ref!r} in public skill {skill_name}")

    def _import_assembler(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import assemble_carik
        finally:
            sys.path.pop(0)
        return assemble_carik

    def _sibling_staging_writable(self) -> bool:
        probe = TARGET.parent / ".carik.write-probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return True
        except PermissionError:
            return False

    def _arm_live_pair(self):
        """Assemble once, mark the live tree, and return the module plus the live ZIP hash."""
        self._run_assemble()
        marker = TARGET / ".live-tree-marker"
        marker.write_text("live", encoding="utf-8")
        self.addCleanup(marker.unlink, missing_ok=True)
        return self._import_assembler(), hashlib.sha256(ZIP_OUT.read_bytes()).hexdigest()

    def _arm_sibling_promotion_pair(self):
        """Return (assemble_carik, target_dir, zip_path, manifest_path, zip_before) on a writable parent."""
        assemble_carik = self._import_assembler()
        if self._sibling_staging_writable():
            _, zip_before = self._arm_live_pair()
            return assemble_carik, TARGET, ZIP_OUT, assemble_carik.DEFAULT_MANIFEST, zip_before

        tmp = tempfile.TemporaryDirectory(prefix="carik_promo_test_")
        self.addCleanup(tmp.cleanup)
        tmp_root = Path(tmp.name).resolve()
        (tmp_root / "work" / "build" / "carik-source").mkdir(parents=True)
        (tmp_root / "work" / "build" / "carik-source" / "README.md").write_text("# Test\n", encoding="utf-8")
        manifest = tmp_root / "work" / "build" / "carik-manifest.json"
        manifest.write_text(
            json.dumps({
                "schema_version": 1,
                "target_dir": "work/build/carik",
                "zip_output": "work/build/carik-vault-release.zip",
                "zip_prefix": "carik-vault",
                "zip_timestamp": [2026, 11, 26, 0, 0, 0],
                "files": [{"src": "work/build/carik-source/README.md", "dst": "README.md"}],
            }),
            encoding="utf-8",
        )
        p_root = mock.patch.object(assemble_carik, "ROOT", tmp_root)
        p_build = mock.patch.object(assemble_carik, "BUILD_ROOT", (tmp_root / "work" / "build").resolve())
        p_root.start()
        p_build.start()
        self.addCleanup(p_root.stop)
        self.addCleanup(p_build.stop)
        target_dir, zip_path, zip_before = assemble_carik.assemble(manifest)
        (target_dir / ".live-tree-marker").write_text("live", encoding="utf-8")
        return assemble_carik, target_dir, zip_path, manifest, zip_before

    def _assert_old_pair_intact(self, zip_before: str, target_dir: Path = TARGET, zip_out: Path = ZIP_OUT) -> None:
        self.assertEqual(zip_before, hashlib.sha256(zip_out.read_bytes()).hexdigest())
        self.assertTrue((target_dir / ".live-tree-marker").is_file(), "live carik/ must be the pre-build tree")
        leftovers = [
            p.name for p in target_dir.parent.iterdir()
            if p.name.endswith((".staging", ".old", ".zip.tmp", ".zip.old", ".promoting", ".promoting.tmp"))
        ]
        self.assertEqual([], leftovers)

    def _crash_on_zip_promotion(self, assemble_carik, error: BaseException):
        real_replace = os.replace

        def replace(src, dst):
            if Path(src).name.endswith(".zip.tmp"):
                raise error
            return real_replace(src, dst)

        return mock.patch.object(assemble_carik.os, "replace", side_effect=replace)

    def test_failed_zip_verification_leaves_live_outputs_untouched(self) -> None:
        assemble_carik, zip_before = self._arm_live_pair()
        with mock.patch.object(assemble_carik, "_verify_zip", side_effect=ValueError("forced")):
            with self.assertRaises(ValueError):
                assemble_carik.assemble()
        self._assert_old_pair_intact(zip_before)

    def test_error_between_tree_and_zip_promotion_rolls_back_both(self) -> None:
        assemble_carik, target_dir, zip_out, manifest, zip_before = self._arm_sibling_promotion_pair()
        with self._crash_on_zip_promotion(assemble_carik, OSError("disk full")):
            with self.assertRaises(OSError):
                assemble_carik.assemble(manifest)
        self._assert_old_pair_intact(zip_before, target_dir, zip_out)

    def test_hard_crash_between_tree_and_zip_promotion_recovers_old_pair(self) -> None:
        assemble_carik, target_dir, zip_out, manifest, zip_before = self._arm_sibling_promotion_pair()
        with self._crash_on_zip_promotion(assemble_carik, KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                assemble_carik.assemble(manifest)
        journal = target_dir.parent / ".carik.promoting"
        self.assertTrue(journal.is_file(), "a killed process leaves the promotion journal behind")
        self.assertFalse(zip_out.exists())
        self.assertFalse((target_dir / ".live-tree-marker").exists(), "new tree was promoted before the crash")
        assemble_carik._recover_promotion(
            target_dir, target_dir.parent / ".carik.old", zip_out, zip_out.with_name(zip_out.name + ".old"), journal
        )
        shutil.rmtree(target_dir.parent / ".carik.staging", ignore_errors=True)
        zip_out.with_name(zip_out.name + ".tmp").unlink(missing_ok=True)
        self._assert_old_pair_intact(zip_before, target_dir, zip_out)

    def test_tmp_fallback_rejects_symlink_targets(self) -> None:
        assemble_carik = self._import_assembler()
        tmp = tempfile.TemporaryDirectory(prefix="carik_sym_test_")
        self.addCleanup(tmp.cleanup)
        tmp_root = Path(tmp.name).resolve()
        (tmp_root / "work" / "build" / "carik-source").mkdir(parents=True)
        (tmp_root / "work" / "build" / "carik-source" / "README.md").write_text("# Test\n", encoding="utf-8")
        manifest = tmp_root / "work" / "build" / "carik-manifest.json"
        manifest.write_text(
            json.dumps({
                "schema_version": 1,
                "target_dir": "work/build/carik",
                "zip_output": "work/build/carik-vault-release.zip",
                "zip_prefix": "carik-vault",
                "zip_timestamp": [2026, 11, 26, 0, 0, 0],
                "files": [{"src": "work/build/carik-source/README.md", "dst": "README.md"}],
            }),
            encoding="utf-8",
        )
        outside_dir = tmp_root / "outside_dir"
        outside_dir.mkdir()
        (outside_dir / "keep.txt").write_text("safe", encoding="utf-8")
        outside_zip = tmp_root / "outside.zip"
        outside_zip.write_bytes(b"original-zip")

        with mock.patch.object(assemble_carik, "ROOT", tmp_root), mock.patch.object(
            assemble_carik, "BUILD_ROOT", (tmp_root / "work" / "build").resolve()
        ), mock.patch.object(assemble_carik, "_recover_promotion", side_effect=PermissionError("sandbox")):
            (tmp_root / "work" / "build" / "carik").symlink_to(outside_dir, target_is_directory=True)
            with self.assertRaises(ValueError):
                assemble_carik.assemble(manifest)
            self.assertEqual((outside_dir / "keep.txt").read_text(encoding="utf-8"), "safe")
            (tmp_root / "work" / "build" / "carik").unlink()

            (tmp_root / "work" / "build" / "carik-vault-release.zip").symlink_to(outside_zip)
            with self.assertRaises(ValueError):
                assemble_carik.assemble(manifest)
            self.assertEqual(outside_zip.read_bytes(), b"original-zip")

    def test_tmp_fallback_rolls_back_tree_and_zip_on_mid_write_failure(self) -> None:
        assemble_carik = self._import_assembler()
        tmp = tempfile.TemporaryDirectory(prefix="carik_rb_test_")
        self.addCleanup(tmp.cleanup)
        tmp_root = Path(tmp.name).resolve()
        (tmp_root / "work" / "build" / "carik-source").mkdir(parents=True)
        (tmp_root / "work" / "build" / "carik-source" / "README.md").write_text("# v1\n", encoding="utf-8")
        manifest = tmp_root / "work" / "build" / "carik-manifest.json"
        manifest.write_text(
            json.dumps({
                "schema_version": 1,
                "target_dir": "work/build/carik",
                "zip_output": "work/build/carik-vault-release.zip",
                "zip_prefix": "carik-vault",
                "zip_timestamp": [2026, 11, 26, 0, 0, 0],
                "empty_dirs": ["work/inbox"],
                "files": [{"src": "work/build/carik-source/README.md", "dst": "README.md"}],
            }),
            encoding="utf-8",
        )
        with mock.patch.object(assemble_carik, "ROOT", tmp_root), mock.patch.object(
            assemble_carik, "BUILD_ROOT", (tmp_root / "work" / "build").resolve()
        ):
            target_dir, zip_out, zip_before = assemble_carik.assemble(manifest)
            (target_dir / ".live-tree-marker").write_text("v1-live", encoding="utf-8")
            (tmp_root / "work" / "build" / "carik-source" / "README.md").write_text("# v2\n", encoding="utf-8")

            real_write_bytes = Path.write_bytes
            failed_once = {"done": False}

            def flaky_zip_write(self_path: Path, data: bytes):
                if self_path == zip_out and not failed_once["done"]:
                    failed_once["done"] = True
                    raise OSError("disk full during fallback zip write")
                return real_write_bytes(self_path, data)

            with mock.patch.object(
                assemble_carik, "_recover_promotion", side_effect=PermissionError("sandbox")
            ), mock.patch.object(Path, "write_bytes", flaky_zip_write):
                with self.assertRaises(OSError):
                    assemble_carik.assemble(manifest)

            self.assertEqual(zip_before, hashlib.sha256(zip_out.read_bytes()).hexdigest())
            self.assertEqual((target_dir / "README.md").read_text(encoding="utf-8"), "# v1\n")
            self.assertEqual((target_dir / ".live-tree-marker").read_text(encoding="utf-8"), "v1-live")
            self.assertTrue((target_dir / "work" / "inbox").is_dir())


if __name__ == "__main__":
    unittest.main()
