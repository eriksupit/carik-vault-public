---
title: Shared Agent Hooks
date: 2026-08-16
updated: 2026-11-22
type: documentation
status: active
tags:
  - file-over-app-harness
  - governance
  - hooks
---

# Shared Agent Hooks

This directory is the canonical implementation tree for the harness's deterministic
governance backstops. Claude Code activation in `.claude/settings.json` invokes
these scripts directly. Codex (`.codex/hooks.json` → `codex-adapter.py`),
Antigravity (`.agents/hooks.json` → `antigravity-adapter.py`), and DeepSeek
(`deepseek-runner` skill → `deepseek-adapter.py`) reach the same tree
through adapters.

Policy lives in the named hook scripts and nowhere else. A runtime adapter
translates lifecycle envelopes and tool vocabulary only; it must never restate a
policy expression, a message, or a decision. `wire-skills.py` stays Claude-specific
because Codex skill registration is owned by `scripts/sync-skills.py`.

## The gating principle

A rule that exists only as prose is a cognitive rule, and a cognitive rule cannot be
gated — the agent either follows it or does not, and nothing on disk records which.
Every blocking hook here is possible only because its rule has a **mandatory trace
that is a filesystem fact**:

- `skill-usage-recorder.py` appends each `Skill` invocation to
  `.agents/telemetry/skill-usage.jsonl`. Because the harness — not the agent — decides
  when it fires, an agent that skipped a skill cannot fabricate the record.
  `prose-language-gate.py` reads that log as an advisory signal.
- `artifact-research-gate.py` checks the text against the `source_id` values registered
  in `raw-kb/SOURCES.md`. The checkable fact is not "did the agent browse" but "does
  this artifact name a source that is actually registered".
- `vault-boundary-guard.py` turns the SCOPE.md boundary into a path predicate, and reads
  its downward reach from `.agents/derived-vaults.json` — refusing any row whose target
  carries the root harness's own initializer skill.

Where no such trace exists, the hook is a reminder and is named one. Hooks that judged
natural-language replies by regex (Class A) are amputated, not kept as advisories.

## The hooks

| Hook | Class | Event | Behavior |
|---|---|---|---|
| `vault-boundary-guard.py` | C, required in every runtime | PreToolUse | deny a tool call that writes to a user path outside the vault |
| `git-scope-guard.py` | C, required in every runtime | PreToolUse (Bash) | deny broad staging (`-A`, `-u`, `.`, `:/`, wildcards), forced push, and session/task mixed staging |
| `goal-contract-gate.py` | C, factory only | PreToolUse (Write/Edit) | deny a substantive write until `## Goal Contract` is in the transcript |
| `incident-gate.py` | C on PreToolUse, B on Stop; factory only | PreToolUse, Stop | deny a tool call matching an active incident in `.agents/incidents/`; at turn end a matched `stop_token` only warns on stderr and exits 0 |
| `discussion-intake-gate.py` | C | PreToolUse (Write/Edit) | deny downstream drafting before the stage's entry artifacts are active |
| `artifact-research-gate.py` | C | PreToolUse (Write/Edit) | deny a `work/` artifact that names no registered source |
| `prose-language-gate.py` | B, advisory | PreToolUse (Write/Edit) | warn on stderr when a prose write lands before `anti-translationese` ran this session; always exits 0 |
| `skill-usage-recorder.py` | B | PreToolUse (Skill) | record every skill invocation; never blocks |
| `frontmatter-reminder.py` | B | PostToolUse (Write/Edit) | nudge the frontmatter contract |
| `artifact-preview-gate.py` | B | PostToolUse (Write/Edit) | compile a local HTML preview of the written Markdown or Canvas |
| `governance-reminder.py` | B | UserPromptSubmit | inject the static standing governance rules each turn; never parses the prompt |
| `interview_session_hook.py` | B | SessionStart, UserPromptSubmit, Stop | interview scratch-pad continuity (not DeepSeek) |
| `wire-skills.py` | installer | SessionStart | remove obsolete `.claude/skills` and `.claude/commands` adapters |

Amputated as Class A: `menu-guard.py`, `skill-gate.py`, `single-preview-guard.py`, and
`summary-first-gate.py` (with `lib/approval_state.py` and `lib/plan_evidence.py`).
Summary-First approval stays a procedure in `WORKFLOW.md`; no hook enforces it.

Every `Stop` hook blocks at most once per `session_id` and then always yields: the
Claude Code Stop contract carries no `stop_hook_active` field, so a hook that always
blocks can hang a session.

## Launcher guard

Every launcher command starts with `command -v python3 >/dev/null 2>&1 || exit 0`.
A host without `python3` skips governance (exit 0) instead of failing every tool call
with 127; with `python3` present the hook's exit code, including a Class C `exit 2`,
passes through unchanged. Native Windows shells lack `command -v`, and a bare
`python3` there can trigger the Microsoft Store installer; that profile is deferred to
the P10 test matrix.

## The vault boundary is asymmetric

A parent harness declares the vaults it may reach in `.agents/derived-vaults.json`
and can read and write them, because that is a designed workflow — the universal
governance layer is delivered downstream one way through
`scripts/sync-skills.py --update-vault`, and that command's target path appears in the
command string the guard inspects. A derived vault ships no registry, so its list is
empty and it can never reach back up.

The registry alone would not hold the asymmetry, because it lives inside the vault
while the guard only denies paths outside it — a derived vault could grant itself reach
by writing a registry naming its parent. The guard therefore drops any row whose target
carries `.agents/skills/file-over-app-init/SKILL.md`. That is a fact on the target's
filesystem, and the row's author cannot forge it, because writing into that target is
exactly what the guard denies. `test_vault_boundary_guard.py` proves both directions.

For an occasional external target, use `VAULT_ALLOW_EXTERNAL=/absolute/prefix`, which the
owner sets in the environment that launches the agent. Multiple prefixes are joined with
`os.pathsep` (`:` on POSIX, `;` on Windows); relative entries are ignored. The two openings differ in the
lifetime of the authorization, not in strictness: the registry is a permanent,
git-tracked grant for a permanent structural relation; the environment variable is a
session-lived grant for an occasional need.

## Coverage

Coverage is recorded per behavior, and a config entry is never counted as proof. Real
event fixtures and allow/deny checks prove it; the `test_*.py` file beside each hook is
that proof, and every one of them runs with `python3 <file>` and no framework.

| Runtime | Coverage | Basis |
|---|---|---|
| Claude Code | proven for the tools that emit hook events | `.claude/settings.json` plus the tests in this directory |
| Codex | wired; `patch-pre`/`patch-post` gate `apply_patch`, `Write`, and `Edit` (pre: goal-contract, discussion-intake, artifact-research, prose-language, incident; post: frontmatter-reminder, artifact-preview) | `.codex/hooks.json`, `test_codex_adapter.py`; no live Codex session run here |
| Antigravity | wired through `pre-invocation`, `pre-tool`, `post-tool`, `stop` | `.agents/hooks.json`, `test_antigravity_adapter.py`; no live Antigravity session run here |
| DeepSeek | advisory: the agent invokes the adapter at each boundary, so a skipped boundary is not caught | `deepseek-runner` skill, `test_deepseek_adapter.py` |
| OMP and other runtimes | not wired | no adapter; outside `lib/registry.py` `RUNTIMES` |

`scripts/verify_activation.py` checks that every script a launcher or adapter names
exists (`hooks/<name>.py` and Codex `direct <name>.py` forms), that hook names have
parity across the four registered runtimes, and that the Class C guards in
`lib/parity.py` `REQUIRED_GUARDS` are dispatched by all four; no exemption waives them.
It does not check that each name runs at the same lifecycle phase; per-phase dispatch
is proven only by the adapter tests.

Known limits, stated rather than hidden. The Class C guards are POSIX-first: the
boundary predicate is proven for absolute macOS user paths, and native Windows
(path separators, temp directory under the user root, `shlex` quoting) is unverified
until P10. Shell expansions and relative traversal remain advisory. Write-side
checks see native file-modification tools, not Markdown generated by a shell command.
The prose advisory clears per session, not per document, because the telemetry records
which skill ran and when — not which file it was applied to. The goal-contract gate needs
a readable transcript and fails open without one.

Every hook fails open on malformed plumbing, so a broken extension cannot wedge a
session; a detected policy violation still denies. Missing wiring is reported by
verification and is never described as enforcement.
