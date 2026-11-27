# Handoff document skeleton (11 sections)

This is the full template for the handoff `.md` file. Reproduce these sections in order. Do not add a Table of Contents, a "Conclusion", or decorative sections. A section may be empty-with-reason ("None this session.") but must not be silently dropped.

Output language: **English** (the reader is a Claude model; project Model Instruction Language Policy applies).

```markdown
---
title: Handoff — <short title>
date: YYYY-MM-DD
updated: YYYY-MM-DD
type: handoff
status: active
tags:
  - handoff
  - continuity
---

# HANDOFF — <short title: the work in progress + the object it acts on>

**Date:** YYYY-MM-DD | **Worktree:** <path or "n/a"> | **Branch:** <branch> | **HEAD:** <short SHA + subject at write time; instruct re-discovery via `git log -1 --oneline` at session start>

<Orientation paragraph, un-headed. One paragraph: session type (AUDIT-ONLY / EXEC / DESIGN / TEST), the task, why now, and explicitly what this session does NOT do. This fences scope before any detail.>

## Goal

- **Session Goal:** <a `/goal`-ready completion condition: one measurable end state + a stated check proving it (e.g. "`npm test` exits 0", "`git status` clean") + any constraint that must not change. Phrase it so the next session's own output can demonstrate it. Max 4000 chars. The user pastes this verbatim into the `/goal` UI command.>
- **Ultimate Goal:** <the larger objective this session is one step toward — narrative context for the reader; not fed to `/goal`>
- **Linkage:** <one sentence: how Session Goal advances Ultimate Goal — narrative context; not fed to `/goal`>

## TL;DR

<Substantive summary of where work stands plus the working hypothesis / main state claim. Not a rigid 3-liner — dense but factual.>

## Context & Decisions

<Bold lead-in sub-blocks: "<X> recap.", "What changed.", a `commit | subject` table when relevant, "Decision this session.", "Mandatory references:" as a bulleted path list. Point to SCOPE.md / source docs / memory entries by path; do not duplicate their content.>

## Current State

<Bulleted facts with evidence only:
- Commits since divergence from <main>: `<short-SHA> <subject>` each
- File facts where relevant: mtime / byte / line counts
- Folder / artifact inventory if relevant
- Test/build status: pass / fail / not run this session
- Uncommitted work: brief, or "none"
Do not list files touched — `git diff <main>...HEAD` is the source of truth.>

## <Task-Specific Dimensions>

<Slot section. Name and content depend on the task type. Examples:
- Audit session → `### D1 — <dimension>` … `### Dn`, each with: what to check, exact ref line/path, expected verdict, an "Output:" directive.
- Execution session → `### Mandate A.1` … with scope + DoD + dispatch target.
If the task has no distinct dimensions, write "Not applicable — single linear task." and keep the header.>

## Next Steps

<Numbered, ordered by priority, phased. Each step names a concrete action and the file/path/command target. Include a `### (NO Phase X)` negative-scope phase when something must explicitly NOT be done in the next session.>

## Branch-Specific Anti-Pitfalls

<ONLY pitfalls discovered or re-confirmed this session in this branch. Each: "Do NOT <X> because <Y, with evidence: commit SHA, file:line, or test failure>." Do NOT re-list global MEMORY.md rules — those auto-load. If nothing branch-specific was learned: "None this session.">

## Acceptance Criteria for This Session

<Numbered. Each criterion independently verifiable. The next session uses this to know when its own work is done.>
```

## Per-section writing rules

- **YAML frontmatter, Title + Metadata + Orientation** are mandatory and always first, in that order. The handoff `.md` follows the active vault's agent-created Markdown frontmatter contract; never add YAML to the initial-prompt `.txt`.
- **Goal** is mandatory. Construct the complete three-line payload once and insert it verbatim into both package artifacts. The user may paste the Session Goal value into `/goal`; `/goal` does not parse files. Separately, `bootstrap` parses the complete literal `## Goal` block in both artifacts and requires normalized equality. Keep all three sub-labels, and keep routing metadata outside this block. If Ultimate Goal is unknown, write `Ultimate Goal: <unknown — not yet defined by user>` rather than omitting the line.
- **Task-Specific Dimensions** is the only renamable section. Everything else keeps its exact header text.
- Cite evidence for every state claim (SHA, `file:line`, test name+status). No filler, no narrative voice, no "great progress".
- If a section would exceed ~8 lines, push detail into a referenced doc and point to it.
