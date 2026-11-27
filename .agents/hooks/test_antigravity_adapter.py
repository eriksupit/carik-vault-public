#!/usr/bin/env python3
"""Unit tests for antigravity-adapter.py lifecycle translations."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
VAULT_ROOT = HOOKS_DIR.parent.parent
ADAPTER = HOOKS_DIR / "antigravity-adapter.py"


def run_adapter(mode: str, payload: dict, env: dict | None = None) -> tuple[int, dict, str]:
    """Helper to run antigravity-adapter.py with JSON payload on stdin."""
    proc = subprocess.run(
        [sys.executable, str(ADAPTER), mode],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=VAULT_ROOT,
        env={**os.environ, **env} if env else None,
    )
    parsed = {}
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            pass
    return proc.returncode, parsed, proc.stderr


class TestAntigravityAdapter(unittest.TestCase):
    def test_pre_invocation_injects_governance(self):
        payload = {
            "conversationId": "test-session-123",
            "workspacePaths": [str(VAULT_ROOT)],
            "modelName": "gemini-3.7-flash",
        }
        rc, out, _ = run_adapter("pre-invocation", payload)
        self.assertEqual(rc, 0)
        self.assertIn("injectSteps", out)
        steps = out["injectSteps"]
        self.assertGreaterEqual(len(steps), 1)
        self.assertIn("Governance active", steps[0]["ephemeralMessage"])

    def test_pre_tool_allows_safe_command(self):
        payload = {
            "conversationId": "test-session-123",
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status", "Cwd": str(VAULT_ROOT)},
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_denies_broad_git_add(self):
        payload = {
            "conversationId": "test-session-123",
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git add .", "Cwd": str(VAULT_ROOT)},
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("broad staging", out.get("reason", ""))

    def test_pre_tool_denies_write_outside_user_path(self):
        # Sensitive external paths remain hard-denied under interactive-approval mode
        payload = {
            "conversationId": "test-session-123",
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(Path.home() / ".ssh" / "id_rsa"),
                    "CodeContent": "x",
                },
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("outside the vault", out.get("reason", ""))

    def test_pre_tool_delegates_ordinary_external_write_to_native_approval(self):
        payload = {
            "conversationId": "test-session-123",
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": str(Path.home() / "Documents" / "external-project" / "notes.md"),
                    "CodeContent": "x",
                },
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_allows_read_outside_user_path(self):
        payload = {
            "conversationId": "test-session-123",
            "toolCall": {
                "name": "view_file",
                "args": {"AbsolutePath": str(Path.home() / "Downloads" / "reference.md")},
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

    def test_pre_tool_denies_mutation_without_goal_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                json.dumps({"type": "PLANNER_RESPONSE", "content": "I will edit the file now."}) + "\n",
                encoding="utf-8",
            )
            payload = {
                "conversationId": "test-session-123",
                "transcriptPath": str(transcript_path),
                "toolCall": {
                    "name": "write_to_file",
                    "args": {"TargetFile": str(VAULT_ROOT / "docs" / "test.md"), "CodeContent": "# Test"},
                },
            }
            rc, out, _ = run_adapter("pre-tool", payload)
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "deny")
            self.assertIn("Goal Contract missing", out.get("reason", ""))

    def test_pre_tool_does_not_record_view_file_as_skill_invocation(self):
        session_id = "test-telemetry-session"
        telemetry_file = VAULT_ROOT / ".agents" / "telemetry" / "skill-usage.jsonl"
        skill_path = str(VAULT_ROOT / ".agents" / "skills" / "anti-sycophancy" / "SKILL.md")
        payload = {
            "conversationId": session_id,
            "toolCall": {
                "name": "view_file",
                "args": {"AbsolutePath": skill_path},
            },
        }
        rc, out, _ = run_adapter("pre-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "allow")

        matched = []
        if telemetry_file.is_file():
            records = [json.loads(line) for line in telemetry_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            matched = [r for r in records if r.get("session_id") == session_id and r.get("skill") == "anti-sycophancy"]
        self.assertEqual(matched, [])

    def test_post_tool_runs_cleanly(self):
        payload = {
            "conversationId": "test-session-123",
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": str(VAULT_ROOT / "docs" / "test.md"), "CodeContent": "# Test"},
            },
        }
        rc, out, _ = run_adapter("post-tool", payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out, {})

    def test_pre_tool_dispatches_discussion_intake_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript_path = Path(tmp) / "transcript.jsonl"
            transcript_path.write_text(
                json.dumps({"type": "PLANNER_RESPONSE", "content": "## Goal Contract\nObjective: test\nCompletion condition: test"}) + "\n",
                encoding="utf-8",
            )
            payload = {
                "conversationId": "test-session-intake",
                "transcriptPath": str(transcript_path),
                "toolCall": {
                    "name": "write_to_file",
                    "args": {"TargetFile": "work/drafts/sample.md", "CodeContent": "# Draft"},
                },
            }
            rc, out, _ = run_adapter("pre-tool", payload)
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "deny")
            self.assertIn("Blocked by discussion intake discipline", out.get("reason", ""))

    def test_pre_tool_dispatches_incident_gate(self):
        inc_dir = VAULT_ROOT / ".agents" / "incidents"
        inc_dir.mkdir(parents=True, exist_ok=True)
        inc_file = inc_dir / "INC-8888-adapter-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-8888\n"
            "trigger_class: bash_command\n"
            "activation_predicate:\n"
            "  token: 'forbidden_adapter_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8",
        )
        try:
            payload = {
                "conversationId": "test-session-inc",
                "toolCall": {
                    "name": "run_command",
                    "args": {"CommandLine": "sh forbidden_adapter_token.sh"},
                },
            }
            rc, out, _ = run_adapter("pre-tool", payload)
            self.assertEqual(rc, 0)
            self.assertEqual(out.get("decision"), "deny")
            self.assertIn("Blocked by incident gate [INC-8888]", out.get("reason", ""))
        finally:
            inc_file.unlink(missing_ok=True)

    def test_post_tool_forwards_artifact_preview_stderr(self):
        payload = {
            "conversationId": "test-session-preview",
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": "README.md", "CodeContent": "# Test"},
            },
        }
        rc, out, err = run_adapter("post-tool", payload)
        self.assertEqual(rc, 0)
        self.assertIn("Artifact preview generated:", err)

    def test_stop_token_incident_does_not_block_turn_end(self):
        inc_dir = VAULT_ROOT / ".agents" / "incidents"
        inc_dir.mkdir(parents=True, exist_ok=True)
        inc_file = inc_dir / "INC-8889-stop-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-8889\n"
            "trigger_class: stop_token\n"
            "activation_predicate:\n"
            "  token: 'forbidden_adapter_stop_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8",
        )
        try:
            payload = {
                "conversationId": f"test-session-inc-stop-{os.getpid()}",
                "lastAssistantMessage": "forbidden_adapter_stop_token message",
            }
            rc, out, _ = run_adapter("stop", payload)
            self.assertEqual(rc, 0)
            self.assertNotEqual(out.get("decision"), "continue")
        finally:
            inc_file.unlink(missing_ok=True)


CONVERSATION_ID = "1e6c53c1-0000-4000-8000-000000000abc"
PREVIEW = (
    "Ringkasan.\n```text\nSUMMARY-FIRST PREVIEW path=\"docs/design/x.md\" operation=\"create\"\n"
    "# X\nIsi.\n```\n"
)


class TestAntigravityTranscriptResolution(unittest.TestCase):
    """Antigravity CLI sends conversationId but no transcriptPath; the adapter must find the log."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.root = tmp / "vault"
        self.root.mkdir()
        self.logs = tmp / "home" / ".gemini" / "antigravity-cli" / "brain" / CONVERSATION_ID / ".system_generated" / "logs"
        self.logs.mkdir(parents=True)
        self.env = {"HOME": str(tmp / "home"), "CLAUDE_PROJECT_DIR": str(self.root), "AGENT_PROJECT_DIR": str(self.root)}

    def tearDown(self):
        self._tmp.cleanup()

    def write_session(self, assistant_text: str, user_text: str) -> None:
        # Rows mirror the real Antigravity CLI schema: PreInvocation runs after
        # USER_INPUT is logged, and transcript.jsonl truncates long content.
        def rows(assistant: str) -> str:
            entries = [
                {"step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "<USER_REQUEST>\ntulis desain\n</USER_REQUEST>"},
                {"step_index": 1, "source": "SYSTEM_SDK", "type": "EPHEMERAL_MESSAGE", "content": "Governance active"},
                {"step_index": 2, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": assistant},
                {"step_index": 3, "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": f"<USER_REQUEST>\n{user_text}\n</USER_REQUEST>"},
            ]
            return "".join(json.dumps(e) + "\n" for e in entries)

        (self.logs / "transcript_full.jsonl").write_text(rows(assistant_text), encoding="utf-8")
        (self.logs / "transcript.jsonl").write_text(rows(assistant_text[:20]), encoding="utf-8")

    def test_pre_tool_goal_contract_gate_reads_resolved_transcript(self):
        self.write_session(PREVIEW, "ya, lanjut")
        payload = {
            "conversationId": CONVERSATION_ID,
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": str(self.root / "docs" / "x.md"), "CodeContent": "# X"}},
        }
        rc, out, _ = run_adapter("pre-tool", payload, self.env)
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "deny")
        self.assertIn("Goal Contract missing", out.get("reason", ""))

    def test_conversation_id_cannot_escape_brain_dir(self):
        self.write_session(PREVIEW, "ya, lanjut")
        payload = {
            "conversationId": f"../brain/{CONVERSATION_ID}",
            "toolCall": {"name": "write_to_file", "args": {"TargetFile": str(self.root / "docs" / "x.md"), "CodeContent": "# X"}},
        }
        rc, out, _ = run_adapter("pre-tool", payload, self.env)
        self.assertEqual(rc, 0)
        self.assertNotIn("Goal Contract missing", out.get("reason", ""))

    def test_pre_tool_allows_non_mutating_antigravity_tools(self):
        for tool_name, args in (
            ("search_web", {"query": "carik architecture"}),
            ("update_steps", {"steps": []}),
            ("ask_question", {"questions": []}),
        ):
            payload = {
                "conversationId": "test-non-mutating",
                "toolCall": {"name": tool_name, "args": args},
            }
            rc, out, _ = run_adapter("pre-tool", payload)
            self.assertEqual(rc, 0, tool_name)
            self.assertEqual(out.get("decision"), "allow", f"{tool_name}: {out}")


if __name__ == "__main__":
    unittest.main()
