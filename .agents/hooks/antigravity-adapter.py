#!/usr/bin/env python3
"""Translate Antigravity lifecycle hook envelopes to canonical vault shared hooks."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("hook_telemetry", Path(__file__).resolve().parent / "lib" / "telemetry.py")
_telemetry = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_telemetry)
record_skill_usage = _telemetry.record_skill_usage

ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS = Path(__file__).resolve().parent
TELEMETRY = ROOT / ".agents" / "telemetry" / "skill-usage.jsonl"
SKILL_PATH_PATTERN = re.compile(r"/skills/([^/]+)/SKILL\.md$")


def load_payload() -> dict:
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def project_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if "AGENT_PROJECT_DIR" not in env:
        env["AGENT_PROJECT_DIR"] = str(ROOT)
    if "CLAUDE_PROJECT_DIR" not in env:
        env["CLAUDE_PROJECT_DIR"] = str(ROOT)
    return env


def run_canonical_hook(script: str, payload: dict, args: list[str] | None = None) -> subprocess.CompletedProcess[str] | None:
    target = (HOOKS / script).resolve()
    if target.parent != HOOKS or not target.is_file():
        return None
    try:
        cmd = [sys.executable, str(target)]
        if args:
            cmd.extend(args)
        return subprocess.run(
            cmd,
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=project_env(),
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def record_skill_telemetry(session_id: str, skill_name: str) -> None:
    """Delegate to the single schema owner in lib/telemetry.py (never raises)."""
    try:
        record_skill_usage(ROOT, session_id, skill_name)
    except Exception:
        pass


def resolve_transcript_path(payload: dict) -> str:
    """Antigravity CLI omits transcriptPath; derive it from conversationId under ~/.gemini."""
    explicit = payload.get("transcriptPath")
    if explicit:
        return str(explicit)
    conversation_id = str(payload.get("conversationId") or "")
    if not re.fullmatch(r"[\w-]+", conversation_id):
        return ""
    logs = Path.home() / ".gemini" / "antigravity-cli" / "brain" / conversation_id / ".system_generated" / "logs"
    # transcript.jsonl truncates long content (truncated_fields); the full log is authoritative.
    for name in ("transcript_full.jsonl", "transcript.jsonl"):
        if (logs / name).is_file():
            return str(logs / name)
    return ""


def handle_pre_invocation(payload: dict) -> int:
    session_id = payload.get("conversationId", "unknown")
    prompt = payload.get("userMessage", "") or payload.get("prompt", "")

    # Run interview prompt hook
    interview_res = run_canonical_hook(
        "interview_session_hook.py",
        {"runtime": "antigravity", "session_id": session_id, "prompt": prompt},
        args=["prompt", "antigravity"],
    )
    interview_text = ""
    if interview_res and interview_res.stdout:
        try:
            parsed = json.loads(interview_res.stdout)
            if parsed.get("decision") == "block":
                interview_text = f"Interview continuity blocked: {parsed.get('reason', '')}"
        except (json.JSONDecodeError, ValueError):
            pass

    # Run governance-reminder
    gov_res = run_canonical_hook("governance-reminder.py", {"prompt": prompt, "session_id": session_id})
    gov_text = ""
    if gov_res and gov_res.stdout:
        try:
            gov_text = json.loads(gov_res.stdout).get("hookSpecificOutput", {}).get("additionalContext", "")
        except (json.JSONDecodeError, ValueError):
            pass

    combined = "\n\n".join(filter(None, [gov_text, interview_text]))
    if combined:
        sys.stdout.write(json.dumps({"injectSteps": [{"ephemeralMessage": combined}]}))
    else:
        sys.stdout.write(json.dumps({}))
    return 0


# Antigravity's tool vocabulary mapped to the canonical Claude-shaped names the
# shared hooks branch on. vault-boundary-guard.py decides read-versus-write from
# `tool_name`, so an adapter that drops the name puts every call in that guard's
# fail-closed branch. Adapters translate the envelope; the policy stays in the hook.
CANONICAL_TOOL = {
    "run_command": "Bash",
    "view_file": "Read",
    "read_file": "Read",
    "grep_search": "Grep",
    "list_dir": "Glob",
    # Non-filesystem Antigravity tools mapped to Read so vault-boundary-guard's read-only branch allows them without weakening fail-closed policy.
    "search_web": "Read",
    "update_steps": "Read",
    "ask_question": "Read",
    "write_to_file": "Write",
    "write_file": "Write",
    "replace_file_content": "Edit",
    "multi_replace_file_content": "Edit",
    "edit_file": "Edit",
}


def handle_pre_tool(payload: dict) -> int:
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}
    session_id = str(payload.get("conversationId", "unknown"))

    # Convert to Claude-shaped payload for canonical hooks
    translated_input: dict[str, str] = {}
    if tool_name == "run_command":
        translated_input["command"] = str(args.get("CommandLine", ""))
    elif tool_name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
        translated_input["file_path"] = str(args.get("TargetFile", ""))
        translated_input["content"] = str(args.get("CodeContent", ""))
        translated_input["new_string"] = str(args.get("ReplacementContent", ""))
    elif tool_name in ("write_file", "edit_file"):
        translated_input["file_path"] = str(args.get("Path", ""))
        translated_input["content"] = str(args.get("Content", ""))
        translated_input["target"] = str(args.get("Target", ""))
        translated_input["replacement"] = str(args.get("Replacement", ""))
    elif tool_name in ("view_file", "read_file"):
        translated_input["file_path"] = str(args.get("AbsolutePath", args.get("Path", "")))
    elif tool_name == "grep_search":
        translated_input["path"] = str(args.get("SearchPath", ""))
    elif tool_name == "list_dir":
        translated_input["path"] = str(args.get("DirectoryPath", ""))
    else:
        # Fallback mapping: capture any path or command arguments for unknown tools
        for k, v in args.items():
            if isinstance(v, str):
                if k in ("Path", "file_path", "target_file", "TargetFile", "destination", "path"):
                    translated_input["file_path"] = v
                elif k in ("command", "CommandLine", "cmd"):
                    translated_input["command"] = v
                else:
                    translated_input[k] = v

    transcript_path = resolve_transcript_path(payload)
    claude_payload = {
        "session_id": session_id,
        "tool_name": CANONICAL_TOOL.get(tool_name, tool_name),
        "tool_input": translated_input,
        "transcript_path": transcript_path,
    }

    # Dispatch PreToolUse gates
    gates = ["vault-boundary-guard.py", "incident-gate.py"]
    if tool_name == "run_command":
        gates.append("git-scope-guard.py")
    elif tool_name in ("write_to_file", "replace_file_content", "multi_replace_file_content", "write_file", "edit_file"):
        gates.extend(["goal-contract-gate.py", "discussion-intake-gate.py", "artifact-research-gate.py", "prose-language-gate.py"])

    for gate in gates:
        gate_args = ["--interactive-approval", "--runtime=antigravity"] if gate == "vault-boundary-guard.py" else None
        res = run_canonical_hook(gate, claude_payload, args=gate_args)
        if res is not None and res.returncode != 0:
            err_msg = res.stderr.strip() or f"Operation denied by {gate}"
            sys.stdout.write(json.dumps({"decision": "deny", "reason": err_msg}))
            return 0

    sys.stdout.write(json.dumps({"decision": "allow"}))
    return 0


def handle_post_tool(payload: dict) -> int:
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}
    session_id = str(payload.get("conversationId", "unknown"))

    if tool_name in ("write_to_file", "replace_file_content", "multi_replace_file_content", "write_file", "edit_file"):
        claude_payload = {
            "session_id": session_id,
            "tool_name": CANONICAL_TOOL.get(tool_name, tool_name),
            "tool_input": {"file_path": str(args.get("TargetFile", "") or args.get("Path", ""))},
        }
        run_canonical_hook("frontmatter-reminder.py", claude_payload)
        preview_res = run_canonical_hook("artifact-preview-gate.py", claude_payload)
        if preview_res and preview_res.stderr:
            sys.stderr.write(preview_res.stderr)

    sys.stdout.write(json.dumps({}))
    return 0


def handle_stop(payload: dict) -> int:
    session_id = str(payload.get("conversationId", "unknown"))
    message = str(payload.get("lastAssistantMessage", ""))

    claude_payload = {
        "session_id": session_id,
        "last_assistant_message": message,
    }

    res = run_canonical_hook("incident-gate.py", claude_payload)
    if res and res.stdout:
        try:
            out = json.loads(res.stdout)
            if out.get("decision") == "block":
                reason = out.get("hookSpecificOutput", {}).get("additionalContext") or out.get("reason", "Hook requested continuation.")
                sys.stdout.write(json.dumps({"decision": "continue", "reason": reason}))
                return 0
        except (json.JSONDecodeError, ValueError):
            pass

    interview_res = run_canonical_hook(
        "interview_session_hook.py",
        {"runtime": "antigravity", "session_id": session_id},
        args=["verify", "antigravity"],
    )
    if interview_res and interview_res.stdout:
        try:
            interview = json.loads(interview_res.stdout)
            if interview.get("decision") == "block":
                sys.stdout.write(
                    json.dumps({"decision": "continue", "reason": interview.get("reason", "")})
                )
                return 0
        except (json.JSONDecodeError, ValueError):
            pass
    sys.stdout.write(json.dumps({}))
    return 0


def main() -> int:
    payload = load_payload()
    if len(sys.argv) < 2:
        sys.stdout.write(json.dumps({}))
        return 0

    mode = sys.argv[1].lower()
    if mode == "pre-invocation":
        return handle_pre_invocation(payload)
    elif mode == "pre-tool":
        return handle_pre_tool(payload)
    elif mode == "post-tool":
        return handle_post_tool(payload)
    elif mode == "stop":
        return handle_stop(payload)

    sys.stdout.write(json.dumps({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
