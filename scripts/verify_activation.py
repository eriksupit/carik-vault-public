#!/usr/bin/env python3
"""Verify hook activation integrity for this vault.

Checks three silent failure modes:

1. Project implementations and continuity remain exclusively under `.agents/`;
   obsolete `.claude` adapter paths are absent.
2. Every hook command string in `.claude/settings.json`, `.codex/hooks.json`,
   and `.agents/hooks.json` names a script file that exists, in both the
   `.../hooks/<name>.py` form and the Codex `direct <name>.py` form; so does every
   hook `lib/registry.py` reports as dispatched, adapter-hardcoded names included.
3. Four-runtime parity per `lib/parity.py`, including the mandatory Class C guards.

Exit 0 when intact; exit 1 with named findings otherwise. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_TOKEN = re.compile(r"""(?:hooks/|\bdirect\s+)([\w-]+\.py)""")

def _load_hook_lib(root: Path, name: str):
    """Load a hooks/lib module by path; hooks are not an importable package."""
    import importlib.util

    path = root / ".agents" / "hooks" / "lib" / f"{name}.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"hook_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parity_findings(root: Path) -> list[str]:
    """Report missing dispatched scripts and four-runtime parity breaks."""
    registry = _load_hook_lib(root, "registry")
    parity = _load_hook_lib(root, "parity")
    if registry is None or parity is None:
        return [".agents/hooks/lib/registry.py and parity.py must exist; parity is unverifiable without them"]
    exemptions_path = root / ".agents" / "hooks" / "parity-exemptions.json"
    try:
        exemptions = json.loads(exemptions_path.read_text(encoding="utf-8")).get("hooks", {})
    except (OSError, ValueError):
        exemptions = {}
    snapshot = registry.runtime_hooks(root)
    hooks_dir = root / ".agents" / "hooks"
    findings = [
        f"{runtime} dispatches missing hook {name}"
        for runtime in sorted(snapshot)
        for name in sorted(snapshot[runtime])
        if not (hooks_dir / name).is_file()
    ]
    return findings + parity.findings(snapshot, exemptions)



def find_commands(node) -> list[str]:
    """Collect every 'command' string from a nested hooks-config structure."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "command" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(find_commands(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(find_commands(item))
    return found


def check(root: Path) -> list[str]:
    findings: list[str] = []
    agents_hooks = root / ".agents" / "hooks"

    for relative in (
        ".claude/hooks",
        ".claude/skills",
        ".claude/commands",
        ".claude/CONTEXT.md",
        ".claude/LESSONS.md",
        ".claude/MEMORY.md",
    ):
        adapter = root / relative
        if adapter.exists() or adapter.is_symlink():
            findings.append(f"{relative} must be absent; canonical project state lives under .agents")

    for config in (".claude/settings.json", ".codex/hooks.json", ".agents/hooks.json"):
        path = root / config
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            findings.append(f"{config}: unparsable JSON ({exc})")
            continue
        for command in find_commands(data):
            for script_name in SCRIPT_TOKEN.findall(command):
                if not (agents_hooks / script_name).is_file():
                    findings.append(f"{config}: command references missing hook {script_name}")
    findings.extend(parity_findings(root))
    return findings


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    findings = check(root)
    if findings:
        for f in findings:
            print(f"FAIL {f}")
        return 1
    print(f"OK hook activation intact at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
