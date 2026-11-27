#!/usr/bin/env python3
"""DeepSeek Harness adapter: agent-invoked governance runner for the canonical vault hooks.

Unlike Claude Code, Codex, and Antigravity — where the runtime itself invokes lifecycle
hooks — the DeepSeek Harness (DSH) has no native hook runner (`hook/invoked` and
`hook/result` are declared session event types with no emitter in the rc.6 tree).
Governance under DSH is therefore agent-invoked: the DeepSeek agent runs THIS adapter
itself at lifecycle boundaries, and a vault skill (`deepseek-runner`) plus
the AGENTS.md paragraph anchor the invocation so the agent always recognizes when and
how to run it.

This adapter translates the DeepSeek agent's own tool vocabulary (read, read_image,
write, edit, glob, grep, bash) into the shared Claude-shaped payload and dispatches the
canonical hooks under `.agents/hooks/`. It is DeepSeek-keyed: it refuses to act unless
a DSH environment marker is present, so it is inert under Claude Code, Codex, and
Antigravity even if invoked there.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("hook_telemetry", Path(__file__).resolve().parent / "lib" / "telemetry.py")
_telemetry = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_telemetry)
record_skill_usage = _telemetry.record_skill_usage

ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS = Path(__file__).resolve().parent
TELEMETRY = ROOT / ".agents" / "telemetry" / "skill-usage.jsonl"

# DeepSeek Harness environment markers. When none is present, the adapter is inert.
DSH_MARKERS = ("DSH_SESSION_ID", "DSH_HOME", "DSH_SESSION_JSONL")

# DeepSeek tool names -> canonical hooks that gate them.
WRITE_TOOLS = ("write", "edit")
PATH_TOOLS = ("read", "read_image", "write", "edit", "glob", "grep", "bash")


def load_payload() -> dict:
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def running_under_dsh() -> bool:
    return any(os.environ.get(marker) for marker in DSH_MARKERS)


def session_id_from(payload: dict) -> str:
    sid = payload.get("session_id")
    if isinstance(sid, str) and sid:
        return sid
    return os.environ.get("DSH_SESSION_ID", "unknown")


def project_env() -> dict[str, str]:
    env = os.environ.copy()
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


def additional_context(res: subprocess.CompletedProcess[str] | None) -> str:
    if res is None or not res.stdout:
        return ""
    try:
        out = json.loads(res.stdout)
        return str(out.get("hookSpecificOutput", {}).get("additionalContext", ""))
    except (json.JSONDecodeError, ValueError):
        return ""


def record_skill_telemetry(session_id: str, skill_name: str) -> None:
    """Delegate to the single schema owner in lib/telemetry.py (never raises)."""
    try:
        record_skill_usage(ROOT, session_id, skill_name)
    except Exception:
        pass


def handle_pre_prompt(payload: dict) -> int:
    session_id = session_id_from(payload)
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        prompt = ""

    gov_res = run_canonical_hook("governance-reminder.py", {"prompt": prompt, "session_id": session_id})
    combined = additional_context(gov_res)
    if combined:
        sys.stdout.write(json.dumps({"injectSteps": [{"ephemeralMessage": combined}]}))
    else:
        sys.stdout.write(json.dumps({}))
    return 0


# DeepSeek's tool vocabulary mapped to the canonical Claude-shaped names.
CANONICAL_TOOL = {
    "bash": "Bash",
    "read": "Read",
    "read_image": "Read",
    "glob": "Glob",
    "grep": "Grep",
    "write": "Write",
    "edit": "Edit",
}


def translate_tool_input(tool_name: str, args: dict) -> dict[str, str]:
    """Map DeepSeek tool arguments to the shared Claude-shaped tool_input."""
    if tool_name == "bash":
        return {"command": str(args.get("command", ""))}
    if tool_name == "edit":
        return {
            "file_path": str(args.get("file_path", "")),
            "content": str(args.get("new_string", "")),
            "new_string": str(args.get("new_string", "")),
            "old_string": str(args.get("old_string", "")),
        }
    if tool_name == "write":
        return {
            "file_path": str(args.get("file_path", "")),
            "content": str(args.get("content", "")),
        }
    if tool_name in ("read", "read_image"):
        return {"file_path": str(args.get("file_path", ""))}
    if tool_name in ("glob", "grep"):
        return {"path": str(args.get("path", ""))}
    return {k: str(v) for k, v in args.items() if isinstance(v, (str, int, float))}


def handle_pre_tool(payload: dict) -> int:
    session_id = session_id_from(payload)
    tool_name = str(payload.get("tool_name", ""))
    args = payload.get("tool_input") or {}
    if not isinstance(args, dict):
        args = {}

    translated = translate_tool_input(tool_name, args)
    claude_payload = {
        "session_id": session_id,
        "tool_name": CANONICAL_TOOL.get(tool_name, tool_name),
        "tool_input": translated,
        "transcript_path": os.environ.get("DSH_SESSION_JSONL", ""),
    }

    gates: list[str] = []
    if tool_name in PATH_TOOLS:
        gates.extend(["vault-boundary-guard.py", "incident-gate.py"])
    if tool_name == "bash":
        gates.append("git-scope-guard.py")
    if tool_name in WRITE_TOOLS:
        gates.extend(["goal-contract-gate.py", "discussion-intake-gate.py", "artifact-research-gate.py", "prose-language-gate.py"])

    for gate in gates:
        gate_args = ["--interactive-approval", "--runtime=deepseek"] if gate == "vault-boundary-guard.py" else None
        res = run_canonical_hook(gate, claude_payload, args=gate_args)
        if res is not None and res.returncode != 0:
            err_msg = res.stderr.strip() or f"Operation denied by {gate}"
            sys.stdout.write(json.dumps({"decision": "deny", "reason": err_msg}))
            return 0

    sys.stdout.write(json.dumps({"decision": "allow"}))
    return 0


def handle_post_tool(payload: dict) -> int:
    session_id = session_id_from(payload)
    tool_name = str(payload.get("tool_name", ""))
    args = payload.get("tool_input") or {}
    if not isinstance(args, dict):
        args = {}

    if tool_name in WRITE_TOOLS:
        translated = translate_tool_input(tool_name, args)
        claude_payload = {
            "session_id": session_id,
            "tool_name": CANONICAL_TOOL.get(tool_name, tool_name),
            "tool_input": {"file_path": translated.get("file_path", "")},
        }
        res = run_canonical_hook("frontmatter-reminder.py", claude_payload)
        prev_res = run_canonical_hook("artifact-preview-gate.py", claude_payload)
        reminder = additional_context(res) or (res.stderr.strip() if res is not None else "")
        if prev_res and prev_res.stderr:
            reminder = f"{reminder}\n{prev_res.stderr}".strip()
        if reminder:
            sys.stdout.write(json.dumps({"reminder": reminder}))
            return 0

    sys.stdout.write(json.dumps({}))
    return 0


def handle_stop(payload: dict) -> int:
    session_id = session_id_from(payload)
    message = str(payload.get("last_assistant_message", ""))

    claude_payload = {
        "session_id": session_id,
        "last_assistant_message": message,
    }

    res = run_canonical_hook("incident-gate.py", claude_payload)
    if res and res.stdout:
        try:
            out = json.loads(res.stdout)
            if out.get("decision") == "block":
                reason = (
                    out.get("hookSpecificOutput", {}).get("additionalContext")
                    or out.get("reason", "Hook requested continuation.")
                )
                sys.stdout.write(json.dumps({"decision": "continue", "reason": reason}))
                return 0
        except (json.JSONDecodeError, ValueError):
            pass

    sys.stdout.write(json.dumps({}))
    return 0


def handle_record_skill(payload: dict) -> int:
    session_id = session_id_from(payload)
    skill_name = str(payload.get("skill", ""))
    if skill_name:
        record_skill_telemetry(session_id, skill_name)
    sys.stdout.write(json.dumps({}))
    return 0


def main() -> int:
    if not running_under_dsh():
        return 0
    payload = load_payload()
    if len(sys.argv) < 2:
        sys.stdout.write(json.dumps({}))
        return 0

    mode = sys.argv[1].lower()
    handlers = {
        "pre-prompt": handle_pre_prompt,
        "pre-tool": handle_pre_tool,
        "post-tool": handle_post_tool,
        "stop": handle_stop,
        "record-skill": handle_record_skill,
    }
    handler = handlers.get(mode)
    if handler is not None:
        return handler(payload)

    sys.stdout.write(json.dumps({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
