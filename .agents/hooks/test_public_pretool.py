#!/usr/bin/env python3
"""Unit tests for .agents/hooks/public-pretool.py."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_HOOKS = Path(__file__).resolve().parent
HOOK_FILES = (
    "public-pretool.py",
    "interview_credential_redactor.py",
    "vault-boundary-guard.py",
    "git-scope-guard.py",
)

SECRET_SAMPLES = {
    "pem-private-key": (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIBVQIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEAtestsecretkey\n"
        "-----END PRIVATE KEY-----\n"
    ),
    "authorization-bearer": "Authorization: Bearer supersecret_bearer_token_987654321",
    "authorization-basic": "Authorization: Basic dXNlcjpzdXBlcnNlY3JldA==",
    "uri-userinfo": "https://alice:s3cr3tpass@example.com/db",
    "provider-token-prefix": "token is ghp_1234567890abcdefghij1234567890abcd",
    "environment-assignment": "OPENAI_API_KEY=real_live_secret_value_999",
    "cli-assignment": "mycli --api-key=cli_secret_value_888",
    "structured-secret-field": '{"api_key": "json_secret_value_777"}',
}


class TestPublicPretool(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="carik_public_pretool_"))
        hooks_dir = self.tmp / ".agents" / "hooks"
        hooks_dir.mkdir(parents=True)
        for name in HOOK_FILES:
            shutil.copy2(REPO_HOOKS / name, hooks_dir / name)
        self.entrypoint = hooks_dir / "public-pretool.py"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(
        self,
        payload: dict | bytes,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        env = os.environ.copy()
        for k in ("CLAUDE_PROJECT_DIR", "CODEX_SANDBOX", "CODEX_THREAD_ID"):
            env.pop(k, None)
        if env_overrides:
            for k, v in env_overrides.items():
                if v is None:
                    env.pop(k, None)
                else:
                    env[k] = v
        return subprocess.run(
            [sys.executable, str(self.entrypoint)],
            input=raw,
            capture_output=True,
            cwd=self.tmp,
            env=env,
            timeout=20,
            check=False,
        )

    def test_safe_write_exits_0(self) -> None:
        res = self._run({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(self.tmp / "notes" / "hello.md"),
                "content": "# Halo\nIni catatan biasa tanpa rahasia.\n",
            },
        })
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))

    def test_all_8_secret_families_blocked_without_leaking(self) -> None:
        for family, sample in SECRET_SAMPLES.items():
            with self.subTest(family=family):
                res = self._run({
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(self.tmp / "notes" / "secret.md"),
                        "content": sample,
                    },
                })
                self.assertEqual(res.returncode, 2)
                stderr_text = res.stderr.decode("utf-8", errors="strict")
                self.assertEqual(stderr_text.strip(), family)
                self.assertNotIn("secret", stderr_text.lower().replace(family, ""))
                self.assertNotIn("ghp_", stderr_text)
                self.assertNotIn("s3cr3tpass", stderr_text)
                self.assertEqual(res.stdout, b"")

    def test_edit_post_image_cross_boundary_secret_blocked(self) -> None:
        target = self.tmp / "notes" / "cfg.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Authorization: Bearer __PLACEHOLDER__", encoding="utf-8")
        res = self._run({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(target),
                "old_string": "__PLACEHOLDER__",
                "new_string": "real_leaked_token_123456789",
            },
        })
        self.assertEqual(res.returncode, 2)
        self.assertEqual(res.stderr.decode("utf-8").strip(), "authorization-bearer")
        self.assertNotIn("real_leaked_token", res.stderr.decode("utf-8"))

    def test_broken_utf8_stdin_and_target_fail_closed(self) -> None:
        res_stdin = self._run(b"\xff\xfe\xfd")
        self.assertEqual(res_stdin.returncode, 2)
        self.assertEqual(res_stdin.stderr.decode("utf-8").strip(), "scanner-failure")

        target = self.tmp / "notes" / "broken.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"prefix \xff\xfe suffix")
        res_edit = self._run({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(target),
                "old_string": "prefix",
                "new_string": "updated",
            },
        })
        self.assertEqual(res_edit.returncode, 2)
        self.assertEqual(res_edit.stderr.decode("utf-8").strip(), "scanner-failure")

    def test_antigravity_json_allow_and_deny(self) -> None:
        res_allow = self._run({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(self.tmp / "notes" / "ok.md"),
                    "CodeContent": "Aman dibaca.",
                },
            }
        })
        self.assertEqual(res_allow.returncode, 0)
        self.assertEqual(json.loads(res_allow.stdout.decode("utf-8")), {"decision": "allow"})

        res_deny = self._run({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(self.tmp / "notes" / "bad.md"),
                    "CodeContent": "OPENAI_API_KEY=sk_live_secret_abc12345",
                },
            }
        })
        self.assertEqual(res_deny.returncode, 2)
        out = json.loads(res_deny.stdout.decode("utf-8"))
        self.assertEqual(out, {"decision": "deny", "reason": "environment-assignment"})
        self.assertEqual(res_deny.stderr.decode("utf-8").strip(), "environment-assignment")

    def test_git_scope_dormant_without_dot_git_and_active_with_dot_git(self) -> None:
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "git add -A"},
        }
        # Without .git -> dormant -> exit 0
        res_no_git = self._run(payload)
        self.assertEqual(res_no_git.returncode, 0, res_no_git.stderr.decode("utf-8", "replace"))

        # With .git directory -> active -> exit 2
        (self.tmp / ".git").mkdir()
        res_with_git = self._run(payload)
        self.assertEqual(res_with_git.returncode, 2)

    def test_sensitive_external_paths_hard_blocked(self) -> None:
        home = Path.home()
        sensitive_paths = (
            home / ".ssh" / "id_rsa",
            home / ".aws" / "credentials",
            home / ".gnupg" / "secring.gpg",
            home / ".kube" / "config",
            home / ".config" / "gh" / "hosts.yml",
            home / ".gemini" / "settings.json",
            home / ".gemini" / "config" / "plugins" / "cfg.json",
            home / ".gemini" / "oauth_creds.json",
            home / ".codex" / "config.toml",
            home / ".claude" / "settings.json",
            home / "Library" / "LaunchAgents" / "com.carik.test.plist",
            home / ".netrc",
            home / ".zshrc",
            home / ".bashrc",
            home / "Documents" / ".env",
            home / "Documents" / ".env.local",
            self.tmp / ".agents" / "allow-external",
        )
        for target in sensitive_paths:
            with self.subTest(target=str(target)):
                res_claude = self._run(
                    {
                        "hook_event_name": "PreToolUse",
                        "tool_name": "Write",
                        "tool_input": {"file_path": str(target), "content": "hello"},
                    },
                    env_overrides={"CLAUDE_PROJECT_DIR": str(self.tmp)},
                )
                self.assertEqual(res_claude.returncode, 2)

                res_codex = self._run(
                    {
                        "tool_name": "Write",
                        "tool_input": {"file_path": str(target), "content": "hello"},
                    },
                    env_overrides={"CODEX_SANDBOX": "workspace-write"},
                )
                self.assertEqual(res_codex.returncode, 2)

                res_agy = self._run({
                    "toolCall": {
                        "name": "write_to_file",
                        "args": {"TargetFile": str(target), "CodeContent": "hello"},
                    }
                })
                self.assertEqual(res_agy.returncode, 2)
                self.assertEqual(json.loads(res_agy.stdout.decode("utf-8"))["decision"], "deny")

    def test_non_mutating_antigravity_and_codex_tools_allowed(self) -> None:
        agy_non_mutating = (
            ("search_web", {"query": "carik vault ~/.ssh"}),
            ("update_steps", {"steps": [{"title": "Periksa berkas", "status": "in_progress"}]}),
            ("ask_question", {"questions": [{"question": "Lanjut?", "options": ["Ya", "Tidak"]}]}),
            ("manage_task", {"Action": "list"}),
            ("schedule", {"Prompt": "cek", "DurationSeconds": 60}),
            ("read_url_content", {"Url": "https://example.com"}),
            ("list_resources", {}),
            ("read_resource", {"uri": "mcp://server/item"}),
        )
        for name, args in agy_non_mutating:
            with self.subTest(runtime="antigravity", tool=name):
                res = self._run({"toolCall": {"name": name, "args": args}})
                self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
                self.assertEqual(json.loads(res.stdout.decode("utf-8")), {"decision": "allow"})

        codex_non_mutating = (
            ("web_search", {"query": "python unittest"}),
            ("search_web", {"query": "obsidian markdown"}),
            ("update_steps", {"steps": []}),
            ("update_plan", {"plan": []}),
            ("request_user_input", {"questions": []}),
            ("list_resources", {}),
            ("read_resource", {"uri": "mcp://test"}),
        )
        for name, tinput in codex_non_mutating:
            with self.subTest(runtime="codex", tool=name):
                res = self._run(
                    {"tool_name": name, "tool_input": tinput},
                    env_overrides={"CODEX_SANDBOX": "workspace-write"},
                )
                self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
                self.assertEqual(res.stdout, b"")

    def test_apply_patch_boundary_and_credential_scanning(self) -> None:
        safe_patch = (
            "*** Begin Patch\n"
            "*** Add File: notes/patch-ok.md\n"
            "+# Catatan Aman\n"
            "+Isi biasa tanpa kredensial.\n"
            "*** End Patch\n"
        )
        for field in ("patch", "input", "command"):
            with self.subTest(field=field):
                res = self._run(
                    {"tool_name": "apply_patch", "tool_input": {field: safe_patch}},
                    env_overrides={"CODEX_SANDBOX": "workspace-write"},
                )
                self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))

        # Empty / targetless apply_patch fails closed
        res_empty = self._run({"tool_name": "apply_patch", "tool_input": {"patch": "*** Begin Patch\n*** End Patch\n"}})
        self.assertEqual(res_empty.returncode, 2)

        # Sensitive external target via apply_patch hard-denied across runtimes
        home = Path.home()
        for sensitive in (
            home / ".config" / "gh" / "hosts.yml",
            home / ".gemini" / "settings.json",
            home / ".codex" / "config.toml",
            home / "Library" / "LaunchAgents" / "com.evil.plist",
        ):
            bad_ext_patch = f"*** Begin Patch\n*** Add File: {sensitive}\n+data\n*** End Patch\n"
            res_sens = self._run(
                {"tool_name": "apply_patch", "tool_input": {"command": bad_ext_patch}},
                env_overrides={"CODEX_SANDBOX": "workspace-write"},
            )
            self.assertEqual(res_sens.returncode, 2, f"Expected exit 2 for {sensitive}")

        # Ordinary external target via apply_patch asks in Claude Code, delegates in Codex
        ordinary = home / "Documents" / "outside-patch-test.md"
        ord_patch = f"*** Begin Patch\n*** Add File: {ordinary}\n+Halo biasa\n*** End Patch\n"
        res_claude_ord = self._run(
            {"hook_event_name": "PreToolUse", "tool_name": "apply_patch", "tool_input": {"patch": ord_patch}},
            env_overrides={"CLAUDE_PROJECT_DIR": str(self.tmp)},
        )
        self.assertEqual(res_claude_ord.returncode, 0)
        self.assertEqual(json.loads(res_claude_ord.stdout.decode("utf-8"))["hookSpecificOutput"]["permissionDecision"], "ask")

        res_codex_ord = self._run(
            {"tool_name": "apply_patch", "tool_input": {"command": ord_patch}},
            env_overrides={"CODEX_SANDBOX": "workspace-write"},
        )
        self.assertEqual(res_codex_ord.returncode, 0)

        # All 8 secret families caught inside apply_patch (+ prefixed lines) without leaking
        for family, sample in SECRET_SAMPLES.items():
            plus_lines = "\n".join("+" + ln for ln in sample.splitlines())
            secret_patch = f"*** Begin Patch\n*** Add File: notes/sec.md\n{plus_lines}\n*** End Patch\n"
            with self.subTest(patch_secret=family):
                res_sec = self._run(
                    {"tool_name": "apply_patch", "tool_input": {"command": secret_patch}},
                    env_overrides={"CODEX_SANDBOX": "workspace-write"},
                )
                self.assertEqual(res_sec.returncode, 2)
                err = res_sec.stderr.decode("utf-8", errors="strict").strip()
                self.assertEqual(err, family)

        # Quoted unified diff targeting .agents/allow-external or external sensitive zone must fail closed (rc=2)
        for quoted_diff in (
            '--- /dev/null\n+++ "b/.agents/allow-external"\n@@ -0,0 +1 @@\n+/tmp/evil\n',
            "--- /dev/null\n+++ 'b/.agents/allow-external'\n@@ -0,0 +1 @@\n+/tmp/evil\n",
            '--- /dev/null\n+++ "b/\\056agents/allow-external"\n@@ -0,0 +1 @@\n+/tmp/evil\n',
            f'--- /dev/null\n+++ "b/{home / ".claude" / "settings.json"}"\n@@ -0,0 +1 @@\n+{{}}\n',
        ):
            with self.subTest(quoted_diff=quoted_diff.splitlines()[1]):
                res_qd = self._run(
                    {"tool_name": "apply_patch", "tool_input": {"patch": quoted_diff}},
                    env_overrides={"CODEX_SANDBOX": "workspace-write"},
                )
                self.assertEqual(res_qd.returncode, 2)

    def test_unrecognized_tool_and_missing_target_hard_denied_across_runtimes(self) -> None:
        outside = Path.home() / "Documents" / "outside-unknown-tool.txt"
        secret = "OPENAI_API_KEY=sk_live_secret_abc12345"
        # Unknown mutating tool in Codex, Claude Code, and Antigravity must hard-deny rc=2
        for env_ov in ({"CODEX_SANDBOX": "workspace-write"}, {"CLAUDE_PROJECT_DIR": str(self.tmp)}):
            res_unk = self._run(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "unknown_mutator",
                    "tool_input": {"file_path": str(outside), "content": secret},
                },
                env_overrides=env_ov,
            )
            self.assertEqual(res_unk.returncode, 2)
            res_no_name = self._run(
                {"tool_input": {"file_path": str(outside), "content": secret}},
                env_overrides=env_ov,
            )
            self.assertEqual(res_no_name.returncode, 2)
            res_no_target = self._run(
                {
                    "hook_event_name": "PreToolUse",
                    "tool_name": "Write",
                    "tool_input": {"destination_hint": str(outside), "content": "hi"},
                },
                env_overrides=env_ov,
            )
            self.assertEqual(res_no_target.returncode, 2)

        res_agy_unk = self._run({
            "toolCall": {"name": "unknown_mutator", "args": {"TargetFile": str(outside), "CodeContent": secret}}
        })
        self.assertEqual(res_agy_unk.returncode, 2)
        self.assertEqual(json.loads(res_agy_unk.stdout.decode("utf-8"))["decision"], "deny")

    def test_in_vault_claude_and_antigravity_brain_artifacts_allowed_while_gemini_creds_denied(self) -> None:
        home = Path.home()
        # In-vault .claude/settings.json remains allowed
        res_vault_claude = self._run({
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.tmp / ".claude" / "settings.json"), "content": "{}\n"},
        })
        self.assertEqual(res_vault_claude.returncode, 0)

        # Official Antigravity brain artifact paths are NOT hard-denied (rc=0 when clean, rc=2 if secret)
        for brain_path in (
            home / ".gemini" / "antigravity-cli" / "brain" / "conv-123" / "plan.md",
            home / ".gemini" / "antigravity" / "brain" / "conv-123" / "walkthrough.md",
        ):
            res_agy_brain = self._run({
                "toolCall": {
                    "name": "write_file",
                    "args": {"Path": str(brain_path), "Content": "# Rencana Kerja\nAman.\n"},
                }
            })
            self.assertEqual(res_agy_brain.returncode, 0, res_agy_brain.stderr.decode("utf-8", "replace"))
            self.assertEqual(json.loads(res_agy_brain.stdout.decode("utf-8")), {"decision": "allow"})

            res_brain_secret = self._run({
                "toolCall": {
                    "name": "write_file",
                    "args": {"Path": str(brain_path), "Content": "OPENAI_API_KEY=sk_live_secret_abc12345"},
                }
            })
            self.assertEqual(res_brain_secret.returncode, 2)

        # Traversal out of brain/ into .gemini/oauth_creds.json stays hard-denied rc=2
        traversal = home / ".gemini" / "antigravity" / "brain" / ".." / ".." / "oauth_creds.json"
        res_trav = self._run({
            "toolCall": {"name": "write_file", "args": {"Path": str(traversal), "Content": "{}"}}
        })
        self.assertEqual(res_trav.returncode, 2)

    def test_ordinary_external_path_claude_code_returns_ask(self) -> None:
        outside = Path.home() / "Documents" / "outside-carik-vault-test.txt"
        res = self._run(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(outside),
                    "content": "Halo dari luar vault.",
                },
            },
            env_overrides={"CLAUDE_PROJECT_DIR": str(self.tmp)},
        )
        self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace"))
        out = json.loads(res.stdout.decode("utf-8"))
        spec = out["hookSpecificOutput"]
        self.assertEqual(spec["hookEventName"], "PreToolUse")
        self.assertEqual(spec["permissionDecision"], "ask")
        self.assertIn(str(outside), spec["permissionDecisionReason"])

    def test_ordinary_external_path_with_secret_still_hard_blocked(self) -> None:
        outside = Path.home() / "Documents" / "outside-secret-test.txt"
        res = self._run(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(outside),
                    "content": "OPENAI_API_KEY=sk_live_secret_abc12345",
                },
            },
            env_overrides={"CLAUDE_PROJECT_DIR": str(self.tmp)},
        )
        self.assertEqual(res.returncode, 2)
        self.assertEqual(res.stderr.decode("utf-8").strip(), "environment-assignment")
        self.assertEqual(res.stdout, b"")

    def test_ordinary_external_path_antigravity_and_codex_delegate_to_native_permission(self) -> None:
        """Parity limit, by design: only Claude Code gets a hook-level `ask` for ordinary
        external folders. Antigravity App and Codex get `allow`/silence here, so their guard
        is the conversational permission gate in AGENTS.md plus the app's own permission
        prompt. Sensitive/credential zones stay a hard deny (exit 2) in every runtime."""
        outside = Path.home() / "Documents" / "outside-carik-vault-test.txt"
        res_agy = self._run({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(outside),
                    "CodeContent": "Aman untuk dialog izin native.",
                },
            }
        })
        self.assertEqual(res_agy.returncode, 0, res_agy.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(res_agy.stdout.decode("utf-8")), {"decision": "allow"})

        res_codex = self._run(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": str(outside),
                    "content": "Aman untuk sandbox native Codex.",
                },
            },
            env_overrides={"CODEX_SANDBOX": "workspace-write"},
        )
        self.assertEqual(res_codex.returncode, 0, res_codex.stderr.decode("utf-8", "replace"))
        self.assertEqual(res_codex.stdout, b"")

    def test_shell_launcher_fail_open_without_python3(self) -> None:
        cmd = (
            'command -v python3 >/dev/null 2>&1 || exit 0; '
            'for H in .agents/hooks/public-pretool.py hooks/public-pretool.py; '
            'do [ -f "$H" ] && exec python3 "$H"; done; exit 0'
        )
        env = os.environ.copy()
        env["PATH"] = "/nonexistent"
        res = subprocess.run(
            ["/bin/sh", "-c", cmd],
            input=b"{}",
            capture_output=True,
            cwd=self.tmp,
            env=env,
            timeout=10,
            check=False,
        )
        self.assertEqual(res.returncode, 0)

    def test_antigravity_launcher_with_cwd_dot_agents(self) -> None:
        """Regression test for P10 live bug: Antigravity App runs hooks with cwd=<root>/.agents (no .git)."""
        hooks_cfg = (
            Path(__file__).resolve().parents[2]
            / "work" / "build" / "carik-source" / ".agents" / "hooks.json"
        )
        cmd = json.loads(hooks_cfg.read_text(encoding="utf-8"))["vault-governance"]["PreToolUse"][0]["hooks"][0]["command"]
        dot_agents_cwd = self.tmp / ".agents"
        self.assertFalse((self.tmp / ".git").exists())

        safe_payload = json.dumps({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(self.tmp / "notes" / "ok-from-dot-agents.md"),
                    "CodeContent": "Aman dari cwd .agents.",
                },
            }
        }).encode("utf-8")
        res_allow = subprocess.run(
            ["/bin/sh", "-c", cmd],
            input=safe_payload,
            capture_output=True,
            cwd=dot_agents_cwd,
            timeout=20,
            check=False,
        )
        self.assertEqual(res_allow.returncode, 0, res_allow.stderr.decode("utf-8", "replace"))
        self.assertEqual(json.loads(res_allow.stdout.decode("utf-8")), {"decision": "allow"})

        secret_val = "ghp_1234567890abcdefghij1234567890abcd"
        secret_payload = json.dumps({
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(self.tmp / "notes" / "bad-from-dot-agents.md"),
                    "CodeContent": f"token: {secret_val}",
                },
            }
        }).encode("utf-8")
        res_deny = subprocess.run(
            ["/bin/sh", "-c", cmd],
            input=secret_payload,
            capture_output=True,
            cwd=dot_agents_cwd,
            timeout=20,
            check=False,
        )
        self.assertEqual(res_deny.returncode, 2)
        self.assertEqual(
            json.loads(res_deny.stdout.decode("utf-8")),
            {"decision": "deny", "reason": "provider-token-prefix"},
        )
        self.assertEqual(res_deny.stderr.decode("utf-8").strip(), "provider-token-prefix")
        self.assertNotIn(secret_val, res_deny.stdout.decode("utf-8") + res_deny.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
