#!/usr/bin/env python3
"""Tests for vault-boundary-guard.py."""
from __future__ import annotations

import json
import os as _os
import shutil as _shutil
import subprocess
import sys
import tempfile as _tempfile
from pathlib import Path as _P

HOOK = _P(__file__).resolve().parent / "vault-boundary-guard.py"
VAULT = _P(__file__).resolve().parent.parent.parent
_HOME = str(_P.home())


def run(payload: dict, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(_os.environ)
    env.pop("VAULT_ALLOW_EXTERNAL", None)
    mock_file_content = None
    if env_extra:
        env_copy = dict(env_extra)
        mock_file_content = env_copy.pop("_MOCK_ALLOW_EXTERNAL_FILE", None)
        env.update(env_copy)
    
    allow_file = VAULT / ".agents" / "allow-external"
    existed = allow_file.exists()
    old_content = allow_file.read_text(encoding="utf-8") if existed else None
    
    if mock_file_content is not None:
        allow_file.write_text(mock_file_content + "\n", encoding="utf-8")

    try:
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )
    finally:
        if mock_file_content is not None:
            if existed and old_content is not None:
                allow_file.write_text(old_content, encoding="utf-8")
            else:
                allow_file.unlink(missing_ok=True)


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


CASES: list[tuple[str, dict, int, dict | None]] = [
    # --- writes outside the vault: the prohibition the guard exists for ----------
    (
        "blocks a copy into the user-global skill store (SCOPE.md names user-global stores)",
        bash(f"cp -R .agents/skills/goal {_HOME}/.agents/skills/goal"),
        2,
        None,
    ),
    (
        "blocks a destructive shell verb aimed outside the vault",
        bash(f"rm -rf {_HOME}/Documents/other-vault/work"),
        2,
        None,
    ),
    (
        "blocks a redirect that writes outside the vault even from a reading verb",
        bash(f"cat raw-kb/SOURCES.md > {_HOME}/Documents/other-vault/SOURCES.md"),
        2,
        None,
    ),
    (
        "blocks an external file write",
        {"tool_name": "Write", "tool_input": {"file_path": f"{_HOME}/Documents/other-vault/AGENTS.md"}},
        2,
        None,
    ),
    (
        "blocks an external edit",
        {"tool_name": "Edit", "tool_input": {"file_path": f"{_HOME}/.codex/config.toml"}},
        2,
        None,
    ),
    (
        "blocks a copy whose destination leaves the vault",
        bash(f"cp work/WORKFLOW.md {_HOME}/Documents/elsewhere/WORKFLOW.md"),
        2,
        None,
    ),
    (
        "blocks an unrecognised tool name touching an external path",
        {"tool_name": "some_new_writer", "tool_input": {"file_path": f"{_HOME}/Documents/elsewhere/x.md"}},
        2,
        None,
    ),
    (
        "blocks a payload carrying no tool name at all",
        {"tool_input": {"file_path": f"{_HOME}/Documents/elsewhere/x.md"}},
        2,
        None,
    ),
    (
        "blocks an interpreter reaching a foreign vault — a script is not provably a read",
        bash(f'python3 -c \'import pathlib; pathlib.Path("{_HOME}/Documents/another-vault/.agents/skills").glob("*/SKILL.md")\''),
        2,
        None,
    ),
    (
        "fails closed when the command cannot be parsed",
        bash(f'cat "{_HOME}/Documents/elsewhere/unclosed.md'),
        2,
        None,
    ),
    (
        "blocks a tilde-path write via shell redirect",
        bash('echo "bad" > ~/.bashrc'),
        2,
        None,
    ),
    (
        "blocks a relative path write exiting vault via Write tool",
        {"tool_name": "Write", "tool_input": {"file_path": "../sibling-vault/AGENTS.md", "content": "bad"}},
        2,
        None,
    ),
    (
        "blocks a tilde-path edit via Edit tool",
        {"tool_name": "Edit", "tool_input": {"file_path": "~/.codex/config.toml"}},
        2,
        None,
    ),
    # --- reads outside the vault: repealed 2026-08-18, must NOT be blocked -------
    (
        "allows a plain read of a foreign vault file",
        {"tool_name": "Read", "tool_input": {"file_path": f"{_HOME}/Documents/other-vault/AGENTS.md"}},
        0,
        None,
    ),
    (
        "allows a grep whose path argument leaves the vault",
        {"tool_name": "Grep", "tool_input": {"pattern": "brave", "path": f"{_HOME}/Documents/elsewhere"}},
        0,
        None,
    ),
    (
        "allows a glob outside the vault",
        {"tool_name": "Glob", "tool_input": {"path": f"{_HOME}/Downloads", "pattern": "*.pdf"}},
        0,
        None,
    ),
    (
        "allows a shell read of a global config",
        bash(f"grep -n harness {_HOME}/.codex/config.toml"),
        0,
        None,
    ),
    (
        "allows reading an owner-supplied source in Downloads",
        bash(f"cat {_HOME}/Downloads/reference.md"),
        0,
        None,
    ),
    (
        "allows a piped chain where every segment only reads",
        bash(f"cat {_HOME}/Downloads/reference.md | head -40 | wc -l"),
        0,
        None,
    ),
    (
        "allows pulling an owner-supplied source INTO the vault",
        bash(f"cp {_HOME}/Downloads/source.pdf raw-kb/user-provided/source.pdf"),
        0,
        None,
    ),
    (
        "allows a read-only git subcommand",
        bash("git log --oneline -5"),
        0,
        None,
    ),
    (
        "allows a reading command that silences stderr to /dev/null",
        bash(f"grep -n harness {_HOME}/.codex/config.toml 2>/dev/null"),
        0,
        None,
    ),
    (
        "allows a file-descriptor dupe, which names no path",
        bash(f"ls {_HOME}/Downloads 1>&2"),
        0,
        None,
    ),
    (
        "allows an in-vault redirect while the command reads outside",
        bash(f"cat {_HOME}/Downloads/reference.md 1>work/scratch.txt"),
        0,
        None,
    ),
    (
        "allows git with flags before a read subcommand",
        bash(f"git -C {_HOME}/Documents/another-vault log --oneline -3"),
        0,
        None,
    ),
    (
        "blocks git with flags before a write subcommand",
        bash(f"git -C {_HOME}/Documents/another-vault commit -m probe"),
        2,
        None,
    ),
    (
        "allows a loop whose body only reads",
        bash(f"for f in {_HOME}/Downloads/a.md {_HOME}/Downloads/b.md; do cat $f; done"),
        0,
        None,
    ),
    (
        "blocks a loop whose body writes outside the vault",
        bash(f"for f in {_HOME}/Downloads/a.md; do rm -f $f; done"),
        2,
        None,
    ),
    (
        "allows a conditional whose branches only read",
        bash(f"if grep -q x {_HOME}/Downloads/a.md; then cat {_HOME}/Downloads/b.md; fi"),
        0,
        None,
    ),
    (
        "blocks a conditional that guards an external write",
        bash(f"if true; then rm -rf {_HOME}/Documents/another-vault; fi"),
        2,
        None,
    ),
    # --- everything legitimate inside the vault must still pass ------------------
    ("allows a relative in-vault command", bash("python3 scripts/sync-skills.py --check"), 0, None),
    ("allows an absolute in-vault path", bash(f"ls {VAULT}/.agents/skills"), 0, None),
    (
        "allows an in-vault file write",
        {"tool_name": "Write", "tool_input": {"file_path": f"{VAULT}/work/test.md"}},
        0,
        None,
    ),
    ("allows system paths", bash("/usr/bin/env python3 --version && ls /etc/hosts"), 0, None),
    ("allows the session scratchpad", bash("cat /private/tmp/claude-501/scratch/notes.txt"), 0, None),
    ("allows a tool call with no path at all", bash("git status --short"), 0, None),
    (
        "allows an external WRITE target the owner named via VAULT_ALLOW_EXTERNAL",
        bash(f"cp -R .agents/skills/goal {_HOME}/Documents/another-vault/goal"),
        0,
        {"VAULT_ALLOW_EXTERNAL": f"{_HOME}/Documents/another-vault"},
    ),
    (
        "still blocks a DIFFERENT write target when one target is authorized",
        bash(f"cp -R .agents/skills/goal {_HOME}/Documents/some-third-vault/goal"),
        2,
        {"VAULT_ALLOW_EXTERNAL": f"{_HOME}/Documents/another-vault"},
    ),
    (
        "splits VAULT_ALLOW_EXTERNAL on os.pathsep and honours every absolute entry",
        bash(f"cp -R .agents/skills/goal {_HOME}/Documents/another-vault/goal"),
        0,
        {"VAULT_ALLOW_EXTERNAL": f"{_HOME}/Documents/first-vault{_os.pathsep}{_HOME}/Documents/another-vault"},
    ),
    (
        "ignores a relative VAULT_ALLOW_EXTERNAL entry instead of widening the boundary",
        bash(f"cp -R .agents/skills/goal {_HOME}/Documents/another-vault/goal"),
        2,
        {"VAULT_ALLOW_EXTERNAL": "Documents/another-vault"},
    ),
    # --- anti-privilege escalation: .agents/allow-external mutations strictly blocked ---
    (
        "blocks tool write to .agents/allow-external",
        {"tool_name": "Write", "tool_input": {"file_path": ".agents/allow-external", "content": "/tmp/evil"}},
        2,
        None,
    ),
    (
        "blocks tool edit to absolute path of .agents/allow-external",
        {"tool_name": "Edit", "tool_input": {"file_path": f"{VAULT}/.agents/allow-external", "content": "/tmp/evil"}},
        2,
        None,
    ),
    (
        "blocks shell redirect writing to .agents/allow-external",
        bash("echo '/tmp/evil' > .agents/allow-external"),
        2,
        None,
    ),
    (
        "blocks shell redirect append to .agents/allow-external",
        bash(f"echo '/tmp/evil' >> {VAULT}/.agents/allow-external"),
        2,
        None,
    ),
    (
        "blocks cp targeting .agents/allow-external",
        bash("cp /tmp/evil .agents/allow-external"),
        2,
        None,
    ),
    (
        "blocks tee targeting .agents/allow-external",
        bash("echo '/tmp/evil' | tee .agents/allow-external"),
        2,
        None,
    ),
    (
        "blocks touch targeting .agents/allow-external",
        bash("touch .agents/allow-external"),
        2,
        None,
    ),
    (
        "allows read of .agents/allow-external",
        bash("cat .agents/allow-external"),
        0,
        None,
    ),
    (
        "allows test -f on .agents/allow-external",
        bash("test -f .agents/allow-external"),
        0,
        None,
    ),
    (
        "blocks write to foreign .agents/sessions/",
        {"tool_name": "Write", "tool_input": {"file_path": f"{_HOME}/Documents/another-vault/.agents/sessions/sess.md"}},
        2,
        None,
    ),
    (
        "allows external write authorized via .agents/allow-external file",
        {"tool_name": "Write", "tool_input": {"file_path": f"{_HOME}/Downloads/allow-test/file.txt"}},
        0,
        {"_MOCK_ALLOW_EXTERNAL_FILE": f"{_HOME}/Downloads/allow-test"},
    ),
    ("never blocks on malformed input", {"tool_input": None}, 0, None),
]

_EXT = f"{_HOME}/Downloads"
_EXT_VAULT = f"{_HOME}/Documents/another-vault"

READ_SHAPES = [
    f"cat {_EXT}/a.md",
    f"ls -la {_EXT}",
    f"grep -rn pattern {_EXT}",
    f"head -20 {_EXT}/a.md",
    f"wc -l {_EXT}/a.md",
    f"find {_EXT} -name '*.pdf'",
    f"diff {_EXT}/a.md {_EXT}/b.md",
    f"cat {_EXT}/a.md | head -5 | wc -l",
    f"ls {_EXT} 2>/dev/null",
    f"ls {_EXT} 1>&2",
    f"git -C {_EXT_VAULT} log --oneline -3",
    f"git -C {_EXT_VAULT} status --short",
    f"for f in {_EXT}/a.md; do cat $f; done",
    f"if grep -q x {_EXT}/a.md; then cat {_EXT}/b.md; fi",
    f"if true; then cat {_EXT}/a.md; fi",
    f"if [ -f {_EXT}/a.md ]; then cat {_EXT}/a.md; fi",
    f"[ -d {_EXT} ] && ls {_EXT}",
    f"cat {_EXT}/a.md && ls {_EXT}",
    f"test -f {_EXT}/a.md && cat {_EXT}/a.md",
    f"cp {_EXT}/a.pdf raw-kb/user-provided/a.pdf",
    f"stat {_EXT}/a.md",
    f"file {_EXT}/a.pdf",
    f"shasum {_EXT}/a.pdf",
    f"rg pattern {_EXT}",
    f"echo {_EXT}/a.md",
    f"ls {_EXT} | grep pdf | head -3",
]

WRITE_SHAPES = [
    f"rm -rf {_EXT_VAULT}",
    f"cp raw-kb/SOURCES.md {_EXT}/SOURCES.md",
    f"cat raw-kb/SOURCES.md 1>{_EXT}/out.md",
    f"for f in a b; do rm -f {_EXT}/$f; done",
    f"if true; then rm -rf {_EXT_VAULT}; fi",
    f"git -C {_EXT_VAULT} commit -m x",
    f"mkdir -p {_EXT}/new",
    f"touch {_EXT}/new.txt",
    f"sed -i '' s/a/b/ {_EXT}/a.md",
    f"tee {_EXT}/a.md",
    f"mv {_EXT}/a.md {_EXT}/b.md",
    f"chmod 777 {_EXT_VAULT}",
    f"cat $(rm -rf {_EXT_VAULT})",
    f"cat `rm -rf {_EXT_VAULT}`",
    f"echo $(touch {_EXT_VAULT}/x)",
    f"find {_EXT_VAULT} -delete",
    f"find {_EXT_VAULT} -exec rm {{}} ;",
    f"sh -c 'rm -rf {_EXT_VAULT}'",
    f"bash -c 'rm -rf {_EXT_VAULT}'",
    f"ls {_EXT_VAULT} | xargs rm",
    f"echo x | tee {_EXT}/out.txt",
    f"rsync -a . {_EXT_VAULT}",
]


def shape_sweep_cases() -> list[tuple[str, int, int]]:
    results = []
    for command in READ_SHAPES:
        results.append((f"read shape allowed: {command}", run(bash(command)).returncode, 0))
    for command in WRITE_SHAPES:
        results.append((f"write shape denied: {command}", run(bash(command)).returncode, 2))
    return results


def _stage(root: _P, *, harness: bool) -> _P:
    vault = root / ("harness" if harness else "generated")
    (vault / ".agents" / "hooks").mkdir(parents=True)
    _shutil.copy(HOOK, vault / ".agents" / "hooks" / HOOK.name)
    return vault


def _probe(vault: _P, path: str, tool: str = "Write") -> int:
    env = dict(_os.environ)
    env.pop("VAULT_ALLOW_EXTERNAL", None)
    return subprocess.run(
        [sys.executable, str(vault / ".agents" / "hooks" / HOOK.name)],
        input=json.dumps({"tool_name": tool, "tool_input": {"file_path": path}}),
        capture_output=True, text=True, env=env,
    ).returncode


def directional_cases() -> list[tuple[str, int, int]]:
    results = []
    test_tmp_dir = VAULT / ".test_tmp"
    test_tmp_dir.mkdir(parents=True, exist_ok=True)
    with _tempfile.TemporaryDirectory(dir=str(test_tmp_dir)) as raw:
        root = _P(raw)
        child = root / "child-vault"
        child.mkdir()
        stranger = root / "stranger-vault"
        stranger.mkdir()

        harness = _stage(root, harness=True)
        generated = _stage(root, harness=False)

        results += [
            ("harness cannot write into a vault it generated", _probe(harness, f"{child}/AGENTS.md"), 2),
            ("harness is still blocked from writing to an unregistered vault", _probe(harness, f"{stranger}/AGENTS.md"), 2),
            ("generated vault cannot write into its harness", _probe(generated, f"{harness}/AGENTS.md"), 2),
            ("generated vault cannot write into a sibling vault", _probe(generated, f"{child}/AGENTS.md"), 2),
            ("harness may READ a vault it generated", _probe(harness, f"{child}/work/WORKFLOW.md", "Read"), 0),
        ]
    return results


def interactive_approval_cases() -> list[tuple[str, int, int]]:
    results: list[tuple[str, int, int]] = []
    env = dict(_os.environ)
    env.pop("VAULT_ALLOW_EXTERNAL", None)

    def _run_interactive(payload: dict, runtime: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HOOK), "--interactive-approval", f"--runtime={runtime}"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )

    # 1. Sensitive external paths remain hard-denied across runtimes
    for sensitive in (
        f"{_HOME}/.ssh/id_rsa",
        f"{_HOME}/.aws/credentials",
        f"{_HOME}/.config/gh/hosts.yml",
        f"{_HOME}/.gemini/settings.json",
        f"{_HOME}/.gemini/config/plugins/cfg.json",
        f"{_HOME}/.gemini/oauth_creds.json",
        f"{_HOME}/.codex/config.toml",
        f"{_HOME}/.claude/settings.json",
        f"{_HOME}/Library/LaunchAgents/com.carik.test.plist",
        f"{_HOME}/.zshrc",
        f"{_HOME}/Documents/.env",
    ):
        for rt in ("claude-code", "antigravity", "codex"):
            r = _run_interactive({"tool_name": "Write", "tool_input": {"file_path": sensitive}}, rt)
            results.append((f"interactive ({rt}) hard-denies sensitive {sensitive}", r.returncode, 2))

    # 1a. Official Antigravity brain artifact dirs delegate under interactive mode (not hard-denied)
    for brain_file in (
        f"{_HOME}/.gemini/antigravity-cli/brain/conv-1/plan.md",
        f"{_HOME}/.gemini/antigravity/brain/conv-1/walkthrough.md",
    ):
        r_brain = _run_interactive({"tool_name": "Write", "tool_input": {"file_path": brain_file}}, "antigravity")
        results.append((f"interactive (antigravity) allows brain artifact {brain_file}", r_brain.returncode, 0))

    # 1b. Non-mutating tools and in-vault apply_patch pass; external sensitive & quoted unified-diff blocked
    for ro_tool in ("search_web", "web_search", "update_steps", "read_url_content", "list_resources", "read_resource"):
        r_ro = run({"tool_name": ro_tool, "tool_input": {"query": f"{_HOME}/.ssh"}})
        results.append((f"non-mutating tool allowed: {ro_tool}", r_ro.returncode, 0))
    r_patch_ok = run({"tool_name": "apply_patch", "tool_input": {"patch": "*** Begin Patch\n*** Add File: notes/ok.md\n+hi\n*** End Patch\n"}})
    results.append(("in-vault apply_patch allowed", r_patch_ok.returncode, 0))
    r_patch_sens = _run_interactive(
        {"tool_name": "apply_patch", "tool_input": {"command": f"*** Begin Patch\n*** Add File: {_HOME}/.config/secret\n+bad\n*** End Patch\n"}},
        "codex",
    )
    results.append(("external sensitive apply_patch hard-denied", r_patch_sens.returncode, 2))
    for q_diff in (
        '--- /dev/null\n+++ "b/.agents/allow-external"\n@@ -0,0 +1 @@\n+/tmp/evil\n',
        "--- /dev/null\n+++ 'b/.agents/allow-external'\n@@ -0,0 +1 @@\n+/tmp/evil\n",
        '--- /dev/null\n+++ "b/\\056agents/allow-external"\n@@ -0,0 +1 @@\n+/tmp/evil\n',
    ):
        r_q = run({"tool_name": "apply_patch", "tool_input": {"patch": q_diff}})
        results.append((f"quoted unified diff targeting allow-external blocked ({q_diff.splitlines()[1]})", r_q.returncode, 2))

    # 2. Multi-segment command: ordinary external followed by sensitive external must still hard-deny
    r_multi = _run_interactive(
        bash(f"touch {_HOME}/Documents/ordinary.txt && echo bad > ~/.zshrc"),
        "antigravity",
    )
    results.append(("interactive multi-segment still hard-denies sensitive second segment", r_multi.returncode, 2))

    # 3. Ordinary external path under claude-code returns exit 0 + permissionDecision=ask
    ordinary = f"{_HOME}/Documents/external-factory-test/SCOPE.md"
    r_claude = _run_interactive({"tool_name": "Write", "tool_input": {"file_path": ordinary}}, "claude-code")
    ask_ok = 0
    if r_claude.returncode == 0 and r_claude.stdout.strip():
        try:
            parsed = json.loads(r_claude.stdout)
            spec = parsed.get("hookSpecificOutput", {})
            if spec.get("permissionDecision") == "ask" and ordinary in spec.get("permissionDecisionReason", ""):
                ask_ok = 0
            else:
                ask_ok = 1
        except ValueError:
            ask_ok = 1
    else:
        ask_ok = 1
    results.append(("interactive (claude-code) emits permissionDecision=ask for ordinary external write", ask_ok, 0))

    # 4. Ordinary external path under antigravity & codex delegates to native sandbox approval (exit 0)
    for rt in ("antigravity", "codex"):
        r_nat = _run_interactive({"tool_name": "Write", "tool_input": {"file_path": ordinary}}, rt)
        results.append((f"interactive ({rt}) delegates ordinary external write to native approval", r_nat.returncode, 0))

    return results


def main() -> int:
    failures = 0
    for label, payload, expected, env_extra in CASES:
        result = run(payload, env_extra)
        status = "ok" if result.returncode == expected else "FAIL"
        if status == "FAIL":
            failures += 1
            print(f"{status}: {label}\n   expected exit {expected}, got {result.returncode}\n"
                  f"   stderr: {result.stderr.strip()[:200]}")
        else:
            print(f"{status}: {label}")

    extra = directional_cases() + shape_sweep_cases() + interactive_approval_cases()
    for label, got, expected in extra:
        status = "ok" if got == expected else "FAIL"
        if status == "FAIL":
            failures += 1
            print(f"{status}: {label}\n   expected exit {expected}, got {got}")
        else:
            print(f"{status}: {label}")

    print(f"\n{len(CASES) + len(extra)} cases, {failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
