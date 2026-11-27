---
title: Handoff Contract
date: 2026-07-22
updated: 2026-07-22
type: documentation
status: active
tags:
  - file-over-app-harness
  - handoff
  - continuity
---

# Handoff Contract

`handoff/` stores session transition packages so work can resume without depending on an application's chat history. A handoff is a snapshot of a moment, not canonical truth: current files and direct filesystem evidence always outrank a handoff.

At the end of each substantive session, create one **paired** package. The pair is two files sharing the same timestamp:

```text
handoff/HANDOFF-<project-slug>-<YYYY-MM-DD>-<HHMM>.md
handoff/INITIAL-PROMPT-<project-slug>-<YYYY-MM-DD>-<HHMM>.txt
```

- Use a 24-hour local `HHMM` timestamp so the newest pair sorts last.
- Never overwrite an existing pair; each session writes a new one.
- When resuming, read the newest valid pair, then reconcile it against current files before trusting it.

## `HANDOFF-*.md` — the state snapshot

A Markdown note (with the standard frontmatter) recording:

- **Position** — what was being worked on and the exact stopping point.
- **Done this session** — changed artifacts (paths), decisions made, and evidence read.
- **Verified** — what was checked and how (commands, results); what remains unverified.
- **Open threads** — unfinished work, known gaps, and pending user decisions.
- **Next step** — the single most sensible next action.
- **Do-not-repeat** — traps or dead ends encountered, so the next session avoids them.

## `INITIAL-PROMPT-*.txt` — the resume prompt

A plain-text prompt the user (or the next agent) can paste to restart the session cleanly. It names the vault, the active profile and stage, the immediate objective, and points at the paired `HANDOFF-*.md` for full state. Plain text, no frontmatter — it is a prompt, not a vault note.

## Relationship to continuity

A handoff does not replace `.agents/`. Durable events go to `.agents/Context.md`, lessons to `.agents/Lessons.md`, and curated facts to `.agents/Memory.md`. The handoff is the fast resume surface for one specific session boundary; `.agents/` is the running record across all sessions.

## Archive policy

Exactly one pair stays at the top level of `handoff/` — the newest, which `resolve_handoff.py` resolves at bootstrap. Every superseded pair moves to `handoff/archived/` automatically, preserved byte-for-byte and indexed with a SHA-256 per file in `handoff/archived/README.md`. Nothing is deleted or summarized by archiving. Run `python3 scripts/governance_store.py archive-handoff` to trigger archiving manually; the `handoff` skill also runs it automatically after writing and validating a new pair. Retention-gated compaction and pruning exist as separate, owner-approved commands that are never invoked automatically.
