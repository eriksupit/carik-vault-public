#!/usr/bin/env python3
"""UserPromptSubmit hook: self-carried governance reminder for every vault.

Injects a short standing-governance reminder each turn so the harness's mandatory
skills stay near-automatic even on a machine without the user's global gate hooks
(the vault carries the skills; this carries the trigger). Emits the Claude Code
UserPromptSubmit contract: stdout JSON with hookSpecificOutput.additionalContext.

The reminder is static: it never classifies the prompt's natural language. Judging
whether the user is complaining, or whether a mistake repeated, is model-side work
encoded in AGENTS.md, so the debate trigger is restated here, not detected.
"""
from __future__ import annotations

import json
import sys

BASE = (
    "Governance active (AGENTS.md, Mandatory governance skills): keep anti-sycophancy, "
    "confidence, brave applied; ground every work/ artifact in sources registered in "
    "raw-kb/SOURCES.md before writing it. Standing rules: "
    "(1) a recommendation, next step, or debate panel verdict is composed via "
    "the recommend skill; (2) every response to the user is delivered via brave "
    "at the confidence skill's >95% gate; (3) menus on options are forbidden (anti-sycophancy "
    "Prohibition 3) — correct any that slip through by re-invoking recommend at >95%; "
    "(4) research/evidence-gathering checks primary evidence and iterates toward a "
    ">95%-confidence answer; "
    "(5) at the START of any non-trivial task, post the '## Goal Contract' block (Objective, "
    "Completion condition, Evaluator, Out of scope, Ultimate goal) visibly in chat before the "
    "first working action — `.agents/hooks/goal-contract-gate.py` blocks substantive writes until it exists; "
    "(6) closers must be declarative statements; option menus and interrogative validation questions are strictly prohibited; "
    "(7) when the turn writes or revises Indonesian prose, open "
    "writing-style/prose-writing-style.md first — it is the single canonical home for every "
    "language rule; anti-translationese audits an existing sentence, id-prose "
    "rebuilds a text with web-attested evidence, and the layer's only gate is fact_diff.py; "
    "(8) after two consecutive mistakes on the same issue, or as soon as the user complains "
    "about the current approach, convene debate and stop iterating solo."
)


def main() -> int:
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    json.dump(
        {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": BASE}},
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
