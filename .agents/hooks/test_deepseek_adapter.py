#!/usr/bin/env python3
"""Unit tests for deepseek-adapter.py lifecycle translations."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
VAULT_ROOT = HOOKS_DIR.parent.parent
ADAPTER = HOOKS_DIR / "deepseek-adapter.py"


def run_adapter(mode: str, payload: dict, env_extra: dict | None = None) -> tuple[int, dict, str]:
    """Helper to run deepseek-adapter.py with JSON payload on stdin."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(VAULT_ROOT)
    env.setdefault("DSH_SESSION_ID", "test-dsh-session")
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(ADAPTER), mode],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=VAULT_ROOT,
        env=env,
    )
    parsed = {}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            pass
    return proc.returncode, parsed, proc.stderr


def stripped_env() -> dict:
    env = os.environ.copy()
    for marker in ("DSH_SESSION_ID", "DSH_HOME", "DSH_SESSION_JSONL"):
        env.pop(marker, None)
    return env


class TestDeepseekAdapter(unittest.TestCase):
    def test_inert_without_dsh_markers(self):
        """DeepSeek-keyed: refuses to act when no DSH environment marker is present."""
        env = stripped_env()
        env["CLAUDE_PROJECT_DIR"] = str(VAULT_ROOT)
        proc = subprocess.run(
            [sys.executable, str(ADAPTER), "pre-prompt"],
            input=json.dumps({"session_id": "x", "prompt": "halo"}),
            text=True,
            capture_output=True,
            cwd=VAULT_ROOT,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")

    def test_pre_prompt_injects_governance(self):
        payload = {"session_id": "test-session-123", "prompt": "kerjakan riset ini"}
        rc, out, _ = run_adapter("pre-prompt", payload)
        self.assertEqual(rc, 0)
        self.assertIn("injectSteps", out)
        steps = out["injectSteps"]
        self.assertGreaterEqual(len(steps), 1)
        self.assertIn("Governance active", steps[0]["ephemeralMessage"])
        self.assertIn("Goal Contract", steps[0]["ephemeralMessage"])

    def test_pre_tool_allows_safe_read(self):
        payload = {
            "session_id": "test-session-123",
            "tool_name": "read",
            "tool_input": {"file_path": str(VAULT_ROOT / "SCOPE.md")},
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_denies_write_without_goal_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                json.dumps({"type": "user/message", "content": "tolong tulis dokumennya"}) + "\n",
                encoding="utf-8",
            )
            payload = {
                "session_id": "test-session-123",
                "tool_name": "write",
                "tool_input": {"file_path": str(VAULT_ROOT / "docs" / "test.md"), "content": "# Test"},
            }
            rc, out, _ = run_adapter("pre-tool", payload, env_extra={"DSH_SESSION_JSONL": str(transcript_path)})
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "deny")
            self.assertIn("Goal Contract missing", out.get("reason", ""))

    def test_pre_tool_allows_write_with_goal_contract_in_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                json.dumps({"type": "assistant/message", "content": "## Goal Contract\n- **Objective:** Test\n- **Completion condition:** tests pass"}) + "\n",
                encoding="utf-8",
            )
            payload = {
                "session_id": "test-session-123",
                "tool_name": "write",
                "tool_input": {"file_path": str(VAULT_ROOT / "docs" / "test.md"), "content": "# Test"},
            }
            rc, out, _ = run_adapter("pre-tool", payload, env_extra={"DSH_SESSION_JSONL": str(transcript_path)})
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_denies_broad_git_add(self):
        payload = {
            "session_id": "test-session-123",
            "tool_name": "bash",
            "tool_input": {"command": "git add ."},
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("broad staging", out.get("reason", ""))

    def test_pre_tool_denies_write_outside_user_path(self):
        # Sensitive external paths remain hard-denied under interactive-approval mode
        payload = {
            "session_id": "test-session-123",
            "tool_name": "write",
            "tool_input": {
                "file_path": str(Path.home() / ".ssh" / "id_rsa"),
                "content": "x",
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("outside the vault", out.get("reason", ""))

    def test_pre_tool_allows_read_outside_user_path(self):
        payload = {
            "session_id": "test-session-123",
            "tool_name": "read",
            "tool_input": {"file_path": str(Path.home() / "Downloads" / "reference.md")},
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_denies_shell_write_outside_vault(self):
        payload = {
            "session_id": "test-session-123",
            "tool_name": "bash",
            "tool_input": {"command": f"rm -rf {Path.home()}/.ssh"},
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("outside the vault", out.get("reason", ""))

    def test_pre_tool_delegates_ordinary_external_write_to_user_approval(self):
        payload = {
            "session_id": "test-session-123",
            "tool_name": "write",
            "tool_input": {
                "file_path": str(Path.home() / "Documents" / "external-project" / "notes.md"),
                "content": "x",
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_dispatches_discussion_intake_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                json.dumps({"type": "assistant/message", "content": "## Goal Contract\nObjective: test\nCompletion condition: test"}) + "\n",
                encoding="utf-8",
            )
            payload = {
                "session_id": "test-session-intake",
                "tool_name": "write",
                "tool_input": {"file_path": "work/drafts/sample.md", "content": "# Draft"},
            }
            rc, out, _ = run_adapter("pre-tool", payload, env_extra={"DSH_SESSION_JSONL": str(transcript_path)})
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "deny")
            self.assertIn("Blocked by discussion intake discipline", out.get("reason", ""))

    def test_pre_tool_dispatches_incident_gate(self):
        inc_dir = VAULT_ROOT / ".agents" / "incidents"
        inc_dir.mkdir(parents=True, exist_ok=True)
        inc_file = inc_dir / "INC-6666-dsh-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-6666\n"
            "trigger_class: bash_command\n"
            "activation_predicate:\n"
            "  token: 'forbidden_dsh_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8",
        )
        try:
            payload = {
                "session_id": "test-session-inc",
                "tool_name": "bash",
                "tool_input": {"command": "sh forbidden_dsh_token.sh"},
            }
            rc, out, _ = run_adapter("pre-tool", payload)
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "deny")
            self.assertIn("Blocked by incident gate [INC-6666]", out.get("reason", ""))
        finally:
            inc_file.unlink(missing_ok=True)

    def test_post_tool_dispatches_artifact_preview_gate(self):
        payload = {
            "session_id": "test-session-preview",
            "tool_name": "write",
            "tool_input": {"file_path": "README.md", "content": "# Test preview"},
        }
        rc, out, _ = run_adapter("post-tool", payload)
        self.assertEqual(rc, 0)
        self.assertIn("Artifact preview generated:", out.get("reminder", ""))

    def test_stop_token_incident_does_not_block_turn_end(self):
        inc_dir = VAULT_ROOT / ".agents" / "incidents"
        inc_dir.mkdir(parents=True, exist_ok=True)
        inc_file = inc_dir / "INC-6667-dsh-stop-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-6667\n"
            "trigger_class: stop_token\n"
            "activation_predicate:\n"
            "  token: 'forbidden_dsh_stop_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8",
        )
        try:
            payload = {
                "session_id": f"test-dsh-inc-stop-{os.getpid()}",
                "last_assistant_message": "forbidden_dsh_stop_token message",
            }
            rc, out, _ = run_adapter("stop", payload)
            self.assertEqual(rc, 0)
            self.assertNotEqual(out.get("decision"), "continue")
        finally:
            inc_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
