#!/usr/bin/env python3
"""Judge a four-runtime hook snapshot against declared exemptions.

A hook dispatched by one runtime and missing from another is a finding, because
a gate that denies under one agent and is silently absent under another produces
a false sense of enforcement. An asymmetry may be declared in
`parity-exemptions.json`, but only with a non-empty reason.

The Class C physical guards in `REQUIRED_GUARDS` are the exception: each must be
dispatched by every runtime, and no exemption waives that. Without this rule,
removing a guard from all four runtimes at once leaves no asymmetry to report.
Stdlib only.
"""
from __future__ import annotations

REQUIRED_GUARDS = ("vault-boundary-guard.py", "git-scope-guard.py")


def findings(snapshot: dict[str, set[str]], exemptions: dict) -> list[str]:
    """Return one finding per missing Class C guard or undeclared/mis-declared asymmetry."""
    results: list[str] = []
    runtimes = sorted(snapshot)
    for guard in REQUIRED_GUARDS:
        missing = [r for r in runtimes if guard not in snapshot[r]]
        if missing:
            results.append(f"Class C guard {guard} is not dispatched by {missing}; it is mandatory in every runtime")
    every_hook = sorted(set().union(*snapshot.values()) - set(REQUIRED_GUARDS)) if snapshot else []

    for hook in every_hook:
        present = {r for r in runtimes if hook in snapshot[r]}
        absent = [r for r in runtimes if r not in present]
        if not absent:
            continue

        if not isinstance(exemptions, dict) or hook not in exemptions:
            results.append(
                f"{hook} is dispatched by {sorted(present)} but missing from {absent} "
                f"with no entry in parity-exemptions.json"
            )
            continue

        rule = exemptions[hook]
        if not isinstance(rule, dict):
            results.append(f"{hook} has a malformed parity exemption entry; expected a dict")
            continue

        if not str(rule.get("reason") or "").strip():
            results.append(f"{hook} has a parity exemption with no reason")
            continue

        raw_runtimes = rule.get("runtimes")
        if not (isinstance(raw_runtimes, (list, tuple)) and all(isinstance(r, str) for r in raw_runtimes)):
            results.append(
                f"{hook} has a malformed parity exemption entry; 'runtimes' must be a list or tuple of strings"
            )
            continue

        declared = set(raw_runtimes)
        unexpected = sorted(present - declared)
        if unexpected:
            results.append(
                f"{hook} is exempted for {sorted(declared)} but is also dispatched by "
                f"{unexpected}; widen or remove the exemption"
            )

        missing = sorted(declared - present)
        if missing:
            results.append(
                f"{hook} is exempted for {sorted(declared)} but {missing} does not dispatch it; "
                f"narrow the exemption or restore the wiring"
            )
    return results
