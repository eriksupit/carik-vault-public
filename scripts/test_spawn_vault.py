#!/usr/bin/env python3
"""Regression test suite for spawn_vault.py (Local Forge Vault Generator)."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent

import sys
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import spawn_vault
except ImportError:
    spawn_vault = None


class TestSpawnVault(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test-spawn-vault-"))

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_module_exists(self):
        self.assertIsNotNone(spawn_vault, "spawn_vault module must exist and be importable")

    def test_validate_target(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        # 1. Valid target: non-existent directory
        target_new = self.temp_dir / "new-vault"
        is_valid, err = spawn_vault.validate_target(target_new, VAULT_ROOT)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # 2. Valid target: empty existing directory
        target_empty = self.temp_dir / "empty-dir"
        target_empty.mkdir()
        is_valid, err = spawn_vault.validate_target(target_empty, VAULT_ROOT)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # 3. Invalid target: directory with existing files
        target_dirty = self.temp_dir / "dirty-dir"
        target_dirty.mkdir()
        (target_dirty / "stray.txt").write_text("hello", encoding="utf-8")
        is_valid, err = spawn_vault.validate_target(target_dirty, VAULT_ROOT)
        self.assertFalse(is_valid)
        self.assertIn("not empty", str(err).lower())

        # 4. Invalid target: self recursion (vault root itself)
        is_valid, err = spawn_vault.validate_target(VAULT_ROOT, VAULT_ROOT)
        self.assertFalse(is_valid)
        self.assertIn("cannot be vault root", str(err).lower())

        # 5. Invalid target: inside current vault (sub-directory recursion)
        target_inside = VAULT_ROOT / "work" / "nested-vault"
        is_valid, err = spawn_vault.validate_target(target_inside, VAULT_ROOT)
        self.assertFalse(is_valid)
        self.assertIn("inside vault", str(err).lower())

    def test_render_template(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        template = "# {{PROJECT_NAME}}\nDate: {{DATE}}\n"
        rendered = spawn_vault.render_template(template, "Buku Sejarah Rempah", "2026-10-26")
        self.assertIn("# Buku Sejarah Rempah", rendered)
        self.assertIn("Date: 2026-10-26", rendered)
        self.assertNotIn("{{PROJECT_NAME}}", rendered)
        self.assertNotIn("{{DATE}}", rendered)

    def test_spawn_vault_structure(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        target = self.temp_dir / "proyek-esai-baru"
        project_name = "Esai Nusantara"
        today_str = "2026-10-26"

        success, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name=project_name,
            vault_source=VAULT_ROOT,
            today=today_str,
        )
        self.assertTrue(success, f"spawn_vault failed: {msg}")

        # Check root files
        for fname in [
            "CARIK-CHARTER.md",
            "AGENTS.md",
            "README.md",
            "SCOPE.md",
            "WORKFLOW.md",
            "MULAI-DARI-SINI.md",
            "CREATIVE-LAW.md",
        ]:
            p = target / fname
            self.assertTrue(p.is_file(), f"Missing root file: {fname}")
            content = p.read_text(encoding="utf-8")
            self.assertNotIn("{{PROJECT_NAME}}", content)
            self.assertNotIn("{{DATE}}", content)
            if fname in ["AGENTS.md", "README.md", "SCOPE.md", "WORKFLOW.md", "MULAI-DARI-SINI.md", "CREATIVE-LAW.md"]:
                self.assertIn(project_name, content)

        # Check .obsidian identity files
        for obs_name in ["app.json", "appearance.json", "core-plugins.json"]:
            obs_file = target / ".obsidian" / obs_name
            self.assertTrue(obs_file.is_file(), f"Missing .obsidian file: {obs_name}")
            try:
                json.loads(obs_file.read_text(encoding="utf-8"))
            except Exception as e:
                self.fail(f"Invalid JSON in {obs_name}: {e}")

        # Default profile is app-build
        for sub in ["research", "implementation-plan", "build", "verification", "review"]:
            self.assertTrue((target / "work" / sub).is_dir(), f"Missing work/{sub}")

        self.assertTrue((target / "work" / "TODO.txt").is_file())
        self.assertTrue((target / "work" / "research" / "intake.md").is_file())

        # Check .agents directory
        agents_dir = target / ".agents"
        self.assertTrue(agents_dir.is_dir())
        self.assertTrue((agents_dir / "Context.md").is_file())
        self.assertTrue((agents_dir / "Lessons.md").is_file())
        self.assertTrue((agents_dir / "Memory.md").is_file())
        self.assertTrue((agents_dir / "policy.json").is_file())
        self.assertTrue((agents_dir / "skills.json").is_file())
        self.assertTrue((agents_dir / "hooks.json").is_file())

        # Check skills and hooks
        self.assertTrue((agents_dir / "skills" / "anti-sycophancy" / "SKILL.md").is_file())
        self.assertTrue((agents_dir / "hooks" / "vault-boundary-guard.py").is_file())
        self.assertTrue((agents_dir / "hooks" / "antigravity-adapter.py").is_file())

        # Check writing-style and scripts
        self.assertTrue((target / "writing-style" / "prose-writing-style.md").is_file())
        self.assertTrue((target / "scripts" / "prose_style_audit.py").is_file())
        self.assertTrue((target / "handoff" / "README.md").is_file())

    def test_spawned_vault_passes_continuity_integrity_gate(self):
        """A derived vault ships skills that run scripts/governance_store.py at closure
        and handoff; every gate command must succeed on a freshly spawned vault."""
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")
        import subprocess

        target = self.temp_dir / "gate-vault"
        success, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name="Gate Check",
            vault_source=VAULT_ROOT,
            today="2026-10-28",
        )
        self.assertTrue(success, f"spawn_vault failed: {msg}")
        self.assertIn("Governance Continuity Store", (target / "WORKFLOW.md").read_text(encoding="utf-8"))
        for command in ("rotate-anchors", "refresh-memory", "check", "archive-docs", "check-retention"):
            result = subprocess.run(
                [sys.executable, "scripts/governance_store.py", command],
                cwd=target, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, f"{command}: {result.stdout}{result.stderr}")

    def test_spawned_vault_inherits_core_governance_with_executors(self):
        """The harness-managed core block must reach a derived vault together with
        the hooks it says are wired; a rule without its executor is a dangling rule."""
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")
        import subprocess
        from distribute_governance import extract_managed_block

        target = self.temp_dir / "core-vault"
        success, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name="Core Check",
            vault_source=VAULT_ROOT,
            today="2026-11-12",
        )
        self.assertTrue(success, f"spawn_vault failed: {msg}")
        for doc in ("AGENTS.md", "WORKFLOW.md"):
            source_block = extract_managed_block((VAULT_ROOT / doc).read_text(encoding="utf-8"))
            self.assertTrue(source_block and source_block.strip(), f"{doc}: source vault has no core block")
            self.assertEqual(
                extract_managed_block((target / doc).read_text(encoding="utf-8")),
                source_block,
                f"{doc}: spawned core block differs from source",
            )
        result = subprocess.run(
            [sys.executable, "scripts/verify_activation.py", "."],
            cwd=target, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_dirty_state_leak(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        target = self.temp_dir / "clean-vault"
        success, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name="Clean Vault",
            vault_source=VAULT_ROOT,
        )
        self.assertTrue(success, f"spawn_vault failed: {msg}")

        # Child Context.md should NOT contain parent's old session logs
        context_text = (target / ".agents" / "Context.md").read_text(encoding="utf-8")
        self.assertNotIn("Orientation completed", context_text)
        self.assertNotIn("Adversarial Review", context_text)
        self.assertIn("Clean Vault", context_text)

        # Child Memory.md and Lessons.md should be clean
        memory_text = (target / ".agents" / "Memory.md").read_text(encoding="utf-8")
        self.assertIn("Clean Vault", memory_text)

        # Child pipeline stages must not inherit the parent's artifacts
        for stage in ("build", "verification", "review"):
            leaked = [f.name for f in (target / "work" / stage).iterdir() if f.name != ".gitkeep"]
            self.assertEqual(leaked, [], f"Leaked work/{stage}: {leaked}")

    def test_archive_zip_creation(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        zip_target = self.temp_dir / "archive-test.zip"
        success, msg = spawn_vault.spawn_vault(
            target_dir=self.temp_dir / "zip-vault-staging",
            project_name="Zip Vault",
            vault_source=VAULT_ROOT,
            archive_zip_path=zip_target,
        )
        self.assertTrue(success, f"spawn_vault with zip failed: {msg}")
        self.assertTrue(zip_target.is_file(), "Archive zip was not created")
        self.assertGreater(zip_target.stat().st_size, 1000, "Archive zip is suspiciously small")


    def test_allow_existing_preserves_raw_kb(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        target = self.temp_dir / "existing-raw-kb-vault"
        user_prov = target / "raw-kb" / "user-provided"
        user_prov.mkdir(parents=True)
        seed_file = user_prov / "handoff.pdf"
        seed_file.write_bytes(b"PDF-DATA-KEEP")

        # Without allow_existing -> rejected
        ok_default, _ = spawn_vault.spawn_vault(
            target_dir=target,
            project_name="Humas DKJ",
            vault_source=VAULT_ROOT,
        )
        self.assertFalse(ok_default)

        # With allow_existing=True -> succeeds and preserves raw-kb file
        ok_allow, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name="Humas DKJ",
            vault_source=VAULT_ROOT,
            allow_existing=True,
        )
        self.assertTrue(ok_allow, f"spawn_vault with allow_existing failed: {msg}")
        self.assertEqual(seed_file.read_bytes(), b"PDF-DATA-KEEP")
        self.assertTrue((target / "CARIK-CHARTER.md").is_file())
        self.assertTrue((target / "work" / "research").is_dir())

    def test_spawn_vault_app_build_profile(self):
        """Spawning without a profile defaults to app-build: a deterministic software-engineering
        vault with research/implementation-plan/build/verification/review stages,
        research/intake.md at research-pending, and passes all continuity & activation gates."""
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")
        import subprocess

        target = self.temp_dir / "proyek-coding-baru"
        project_name = "Layanan API Nusantara"
        today_str = "2026-11-16"

        success, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name=project_name,
            vault_source=VAULT_ROOT,
            today=today_str,
        )
        self.assertTrue(success, f"spawn_vault (app-build) failed: {msg}")

        # 1. Pipeline directories for app-build
        expected_stages = ["research", "implementation-plan", "build", "verification", "review"]
        for stage in expected_stages:
            self.assertTrue((target / "work" / stage).is_dir(), f"Missing work/{stage}")
        self.assertFalse((target / "work" / "inbox").exists(), "app-build must not create prose work/inbox")

        # 2. Entry artifact work/research/intake.md with status: research-pending
        intake = target / "work" / "research" / "intake.md"
        self.assertTrue(intake.is_file(), "Missing work/research/intake.md")
        intake_text = intake.read_text(encoding="utf-8")
        self.assertIn(project_name, intake_text)
        self.assertIn("status: research-pending", intake_text)

        # 3. Coding .gitignore and policy.json
        gitignore_text = (target / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("node_modules/", gitignore_text)
        self.assertIn(".venv/", gitignore_text)
        policy_data = json.loads((target / ".agents" / "policy.json").read_text(encoding="utf-8"))
        self.assertEqual(policy_data.get("evidence_bearing"), [])

        # 4. AGENTS.md carries CORE_GOVERNANCE
        agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("CORE_GOVERNANCE", agents_text)

        # 5. Continuity store and hook activation checks pass on spawned app-build vault
        for command in ("rotate-anchors", "refresh-memory", "check", "archive-docs", "check-retention"):
            res = subprocess.run(
                [sys.executable, "scripts/governance_store.py", command],
                cwd=target,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res.returncode, 0, f"{command}: {res.stdout}{res.stderr}")

        act_res = subprocess.run(
            [sys.executable, "scripts/verify_activation.py", "."],
            cwd=target,
            capture_output=True,
            text=True,
        )
        self.assertEqual(act_res.returncode, 0, act_res.stdout + act_res.stderr)

    def test_spawn_vault_unknown_profile_rejected(self):
        if spawn_vault is None:
            self.skipTest("spawn_vault not yet implemented")

        # 'carik' was retired with profiles/carik and templates/clean
        target = self.temp_dir / "retired-carik-vault"
        ok, msg = spawn_vault.spawn_vault(
            target_dir=target,
            project_name="Retired Profile",
            vault_source=VAULT_ROOT,
            profile="carik",
        )
        self.assertFalse(ok)
        self.assertIn("unknown profile", msg.lower())
        self.assertFalse(target.exists(), "rejected profile must leave no partial output")

    def _source_with_cache_litter(self) -> Path:
        """Copy of the vault's spawn inputs with planted __pycache__/.pyc/.DS_Store litter."""
        source = self.temp_dir / "source"
        top_level_skip = {".git", "work", "notes", "docs", "handoff", "raw-kb"}
        shutil.copytree(
            VAULT_ROOT,
            source,
            ignore=lambda d, names: [n for n in names if Path(d) == VAULT_ROOT and n in top_level_skip],
        )
        for litter_dir in (".agents/hooks", ".agents/skills/bootstrap/scripts", "profiles/app-build"):
            cache = source / litter_dir / "__pycache__"
            cache.mkdir(parents=True, exist_ok=True)
            (cache / "x.cpython-314.pyc").write_bytes(b"\0")
            (source / litter_dir / ".DS_Store").write_bytes(b"\0")
            (source / litter_dir / "stray.pyc").write_bytes(b"\0")
        return source

    def test_spawned_vault_is_complete_and_cache_free(self):
        target = self.temp_dir / "child"
        ok, msg = spawn_vault.spawn_vault(
            target_dir=target, project_name="Child", vault_source=self._source_with_cache_litter(), today="2026-11-25"
        )
        self.assertTrue(ok, msg)

        root_skills = {p.name for p in (VAULT_ROOT / ".agents/skills").iterdir() if p.is_dir()}
        child_skills = {p.name for p in (target / ".agents/skills").iterdir() if p.is_dir()}
        self.assertEqual(37, len(child_skills))
        self.assertEqual(root_skills, child_skills)

        litter = [str(p.relative_to(target)) for p in target.rglob("*") if p.name in ("__pycache__", ".DS_Store") or p.suffix == ".pyc"]
        self.assertEqual([], litter)

        self.assertIn(".agents/sessions/workers/", (target / ".gitignore").read_text(encoding="utf-8").splitlines())

        self.assertTrue((target / "CREATIVE-LAW.md").is_file())
        for workflow in ("WORKFLOW.md", "work/WORKFLOW.md"):
            text = (target / workflow).read_text(encoding="utf-8")
            self.assertIn("Intelligence-First", text, workflow)
            self.assertIn("[[CREATIVE-LAW]]", text, workflow)
            self.assertNotIn("](CREATIVE-LAW.md)", text, workflow)
            self.assertNotIn("](../CREATIVE-LAW.md)", text, workflow)
            self.assertNotIn("hooks-hardening-plan", text, workflow)

    def _run_cli(self, *args: str, extra_env: dict[str, str] | None = None):
        import subprocess

        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "VAULT_ALLOW_EXTERNAL": "", **(extra_env or {})}
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "spawn_vault.py"), *args], env=env, capture_output=True, text=True, timeout=120
        )

    def test_outside_home_paths_are_external_too(self):
        # The OS temp dir sits outside both the vault and the user's home on macOS/Linux.
        self.assertFalse(self.temp_dir.resolve().is_relative_to(Path.home().resolve()))
        result = self._run_cli("--target", str(self.temp_dir / "proj"))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("Ditolak", result.stderr)
        self.assertFalse((self.temp_dir / "proj").exists())

    def test_cli_external_target_with_zip_writes_only_zip(self):
        zip_out = self.temp_dir / "out" / "proj.zip"
        result = self._run_cli(
            "--target", str(self.temp_dir / "proj"), "--archive-zip", str(zip_out),
            extra_env={"VAULT_ALLOW_EXTERNAL": str(zip_out.parent)},
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse((self.temp_dir / "proj").exists())
        with zipfile.ZipFile(zip_out) as zf:
            self.assertIn("AGENTS.md", zf.namelist())

    def test_cli_refuses_external_zip_without_permission(self):
        result = self._run_cli("--target", str(self.temp_dir / "proj"), "--archive-zip", str(self.temp_dir / "x.zip"))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertFalse((self.temp_dir / "x.zip").exists())
        self.assertFalse((self.temp_dir / "proj").exists())

    def test_cli_external_target_with_explicit_permission(self):
        target = self.temp_dir / "proj"
        for args, env in ((("--allow-external",), None), ((), {"VAULT_ALLOW_EXTERNAL": str(self.temp_dir)})):
            with self.subTest(args=args, env=env):
                shutil.rmtree(target, ignore_errors=True)
                result = self._run_cli("--target", str(target), *args, extra_env=env)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertTrue((target / "AGENTS.md").is_file())


if __name__ == "__main__":
    unittest.main()
