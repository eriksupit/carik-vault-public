#!/usr/bin/env python3
"""Read which hook scripts each runtime actually dispatches.

Each runtime declares hooks in its own shape:

* Claude  - shell commands in `.claude/settings.json` naming `.../hooks/<name>.py`.
* Codex   - `direct <name>.py` arguments in `.codex/hooks.json`, plus names
            hardcoded in `codex-adapter.py`'s patch dispatch.
* Antigravity / DeepSeek - names hardcoded in their own adapter source.

A reader that understands only one shape under-reports coverage, which is how a
half-wired gate stays invisible. Stdlib only.

Limitation:
Adapter parsing is purely name-based (regex matching quoted `*.py` filenames).
Any hook script merely mentioned in a comment or inactive code inside an adapter
source file would be reported as dispatched (a false positive). `NOT_A_GATE`
serves as the only mitigation against non-gate names (libraries and adapter
scripts themselves). Full dispatch/AST analysis is deliberately omitted as
overbuilding because all current adapter matches represent real dispatches.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RUNTIMES = ("claude", "codex", "antigravity", "deepseek")

# `.../hooks/name.py` inside a shell command string.
PATH_FORM = re.compile(r"hooks/([\w-]+\.py)")
# `direct name.py` - Codex passes the hook as a bare adapter argument.
DIRECT_FORM = re.compile(r"direct\s+([\w-]+\.py)")
# A quoted hook filename inside adapter source.
QUOTED_FORM = re.compile(r"""["']([\w-]+\.py)["']""")

# Names that are never dispatched gates: libraries and the adapters themselves.
NOT_A_GATE = {
    "telemetry.py",
    "registry.py",
    "parity.py",
    "codex-adapter.py",
    "antigravity-adapter.py",
    "deepseek-adapter.py",
}


def _commands(node) -> list[str]:
    """Collect every 'command' string from a nested hooks-config structure."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "command" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_commands(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_commands(item))
    return found


def _read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        # Fail-open behavior per AGENTS.md: hooks fail open on malformed plumbing.
        # Division of labour: `scripts/verify_activation.py` already reports unparsable
        # JSON as its own finding in check() (see `f"{config}: unparsable JSON"` branch),
        # so config corruption is caught and reported there. This reader deliberately
        # stays silent to avoid duplicate reporting.
        return None


def _from_config(path: Path, patterns) -> set[str]:
    data = _read_json(path)
    if data is None:
        return set()
    names: set[str] = set()
    for command in _commands(data):
        for pattern in patterns:
            names.update(pattern.findall(command))
    return names


def _from_adapter(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return set(QUOTED_FORM.findall(path.read_text(encoding="utf-8")))


def runtime_hooks(root: Path) -> dict[str, set[str]]:
    """Map each runtime to the set of hook scripts it dispatches."""
    root = Path(root)
    hooks = root / ".agents" / "hooks"
    found = {
        "claude": _from_config(root / ".claude" / "settings.json", (PATH_FORM,)),
        "codex": (
            _from_config(root / ".codex" / "hooks.json", (PATH_FORM, DIRECT_FORM))
            | _from_adapter(hooks / "codex-adapter.py")
        ),
        "antigravity": (
            _from_config(root / ".agents" / "hooks.json", (PATH_FORM,))
            | _from_adapter(hooks / "antigravity-adapter.py")
        ),
        "deepseek": _from_adapter(hooks / "deepseek-adapter.py"),
    }
    assert set(found.keys()) == set(RUNTIMES), (
        f"runtime_hooks keys {set(found.keys())} do not match RUNTIMES {set(RUNTIMES)}"
    )
    return {name: {h for h in found[name] if h not in NOT_A_GATE} for name in RUNTIMES}
