#!/usr/bin/env python3
"""Focused regression tests for the Codex hook protocol adapter."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).with_name("codex-adapter.py")
SPEC = importlib.util.spec_from_file_location("codex_adapter", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class AdapterTests(unittest.TestCase):
    def test_extracts_every_patch_target_once(self) -> None:
        payload = {
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: work/a.md\n*** Move to: work/b.md\n*** Add File: docs/c.md\n*** Update File: work/a.md\n*** End Patch"
            }
        }
        self.assertEqual(MODULE.patch_paths(payload), ["work/a.md", "docs/c.md", "work/b.md"])

    def test_malformed_payload_fails_open(self) -> None:
        with patch.object(sys, "stdin", io.StringIO("not json")):
            self.assertEqual(MODULE.load_payload(), {})

    def test_file_payload_preserves_session_and_projects_only_target_text(self) -> None:
        payload = {
            "session_id": "session",
            "tool_input": {"command": "unused"},
        }
        translated = MODULE.file_payload(
            payload, "work/a.md", "Add", "*** Add File: work/a.md\n+source_id: own"
        )
        self.assertEqual(translated["session_id"], "session")
        self.assertEqual(translated["tool_input"]["file_path"], "work/a.md")
        self.assertEqual(translated["tool_input"]["content"], "source_id: own")

    def test_multifile_patch_does_not_share_citations(self) -> None:
        payload = {
            "tool_input": {
                "command": "*** Begin Patch\n*** Add File: work/a.md\n+source_id: registered\n*** Add File: work/b.md\n+uncited\n*** End Patch"
            }
        }
        contents = [
            MODULE.file_payload(payload, path, action, section, source_path)["tool_input"]["content"]
            for path, action, section, source_path in MODULE.patch_targets(payload)
        ]
        self.assertEqual(contents, ["source_id: registered", "uncited"])

    def test_projection_removes_deleted_citation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.md"
            target.write_text("title\nsource_id: registered\n", encoding="utf-8")
            projected = MODULE.projected_text(
                str(target), "Update", "*** Update File: artifact.md\n@@\n-source_id: registered\n+replacement"
            )
        self.assertNotIn("source_id: registered", projected)
        self.assertIn("replacement", projected)

    def test_move_projects_source_content_at_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.md"
            source.write_text("source_id: registered\n", encoding="utf-8")
            payload = {
                "tool_input": {
                    "command": f"*** Begin Patch\n*** Update File: {source}\n*** Move to: work/destination.md\n*** End Patch"
                }
            }
            path, action, section, source_path = MODULE.patch_targets(payload)[0]
            translated = MODULE.file_payload(payload, path, action, section, source_path)
        self.assertEqual(path, "work/destination.md")
        self.assertEqual(translated["tool_input"]["content"], "source_id: registered")

    def test_stop_yield_emits_valid_empty_json(self) -> None:
        completed = MODULE.subprocess.CompletedProcess([], 0, stdout="", stderr="")
        output = io.StringIO()
        with patch.object(sys, "stdout", output):
            self.assertEqual(MODULE.emit(completed, "Stop"), 0)
        self.assertEqual(json.loads(output.getvalue()), {})

    def test_stop_block_strips_claude_specific_context(self) -> None:
        body = {
            "decision": "block",
            "reason": "retry",
            "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": "claude"},
        }
        completed = MODULE.subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(body), stderr=""
        )
        output = io.StringIO()
        with patch.object(sys, "stdout", output):
            self.assertEqual(MODULE.emit(completed, "Stop"), 0)
        self.assertEqual(json.loads(output.getvalue()), {"decision": "block", "reason": "retry"})

    def test_probe_requires_temp_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            forbidden = Path(directory).parent / "not-authorized-probe"
            with patch.dict(MODULE.os.environ, {"VAULT_HOOK_PROBE_DIR": str(forbidden)}):
                MODULE.record_probe({"hook_event_name": "Stop"}, "direct", "menu")
            self.assertFalse(forbidden.exists())

    def test_direct_git_guard_blocks_broad_staging(self) -> None:
        payload = {
            "session_id": "fixture-session",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "git add -A"},
        }
        result = subprocess.run(
            [sys.executable, str(PATH), "direct", "git-scope-guard.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=MODULE.ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("broad staging", result.stderr)

    def test_patch_outside_prose_roots_yields(self) -> None:
        payload = {
            "session_id": "fixture-session",
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: /private/tmp/probe.txt\n@@\n-before\n+after\n*** End Patch"
            },
        }
        result = subprocess.run(
            [sys.executable, str(PATH), "patch-pre"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=MODULE.ROOT / "docs",
            check=False,
        )
        self.assertEqual(result.returncode, 0)


    def test_direct_incident_gate_blocks(self) -> None:
        inc_dir = MODULE.ROOT / ".agents" / "incidents"
        inc_dir.mkdir(parents=True, exist_ok=True)
        inc_file = inc_dir / "INC-7777-codex-test.md"
        inc_file.write_text(
            "---\n"
            "id: INC-7777\n"
            "trigger_class: bash_command\n"
            "activation_predicate:\n"
            "  token: 'forbidden_codex_token'\n"
            "status: active\n"
            "---\n",
            encoding="utf-8",
        )
        try:
            payload = {
                "session_id": "fixture-session",
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "sh forbidden_codex_token.sh"},
            }
            result = subprocess.run(
                [sys.executable, str(PATH), "direct", "incident-gate.py"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=MODULE.ROOT,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Blocked by incident gate [INC-7777]", result.stderr)
        finally:
            inc_file.unlink(missing_ok=True)

    def test_patch_pre_dispatches_discussion_intake_gate(self) -> None:
        payload = {
            "session_id": "fixture-session",
            "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Add File: work/drafts/sample.md\n+# Draft content\n*** End Patch"
            },
        }
        result = subprocess.run(
            [sys.executable, str(PATH), "patch-pre"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=MODULE.ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Blocked by discussion intake discipline", result.stderr)

    def test_patch_post_dispatches_artifact_preview_gate(self) -> None:
        payload = {
            "session_id": "fixture-session",
            "hook_event_name": "PostToolUse",
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Add File: README.md\n+# New preview test\n*** End Patch"
            },
        }
        result = subprocess.run(
            [sys.executable, str(PATH), "patch-post"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=MODULE.ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Artifact preview generated:", result.stderr)

    def test_patch_pre_gates_write_and_edit_payloads(self) -> None:
        inputs = {
            "Write": {"file_path": "docs/design/ADAPTER-PROBE-NO-WRITE.md", "content": "candidate"},
            "Edit": {"path": "docs/design/README.md", "old_string": "a", "new_string": "b"},
        }
        for tool_name, tool_input in inputs.items():
            calls = []
            payload = {"tool_name": tool_name, "tool_input": tool_input}
            with patch.object(
                MODULE, "run_hook", lambda script, p, args=None: calls.append((script, p["tool_input"]["file_path"]))
            ):
                self.assertEqual(MODULE.patch_pre(payload), 0)
            path = tool_input.get("file_path") or tool_input["path"]
            self.assertIn(("goal-contract-gate.py", path), calls, tool_name)
            self.assertIn(("incident-gate.py", path), calls, tool_name)

    def test_patch_post_runs_reminders_for_write(self) -> None:
        calls = []
        payload = {"tool_name": "Write", "tool_input": {"file_path": "docs/design/x.md", "content": "c"}}
        with patch.object(MODULE, "run_hook", lambda script, p, args=None: calls.append(script)):
            self.assertEqual(MODULE.patch_post(payload), 0)
        self.assertEqual(["frontmatter-reminder.py", "artifact-preview-gate.py"], calls)


if __name__ == "__main__":
    unittest.main()
