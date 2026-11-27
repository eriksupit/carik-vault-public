# Initial-prompt skeleton (12 sections — merge of supervisor + agent variants)

This is the full template for the paste-able initial-prompt `.txt` file. It is derived by merging two real-world variants: a supervisor/author variant (richer: working rules, closure deliverables) and an executor/agent variant (leaner: standby directive). The merged skeleton below is the universal superset.

Output language: **English**. Format: plain text, paste-able verbatim into a fresh session — no dependency on markdown rendering. Section headers use `##` so they are readable both as text and as markdown.

```
<0. Optional: bare skill-invocation lead-in lines, one per line, e.g.>
/using-superpowers
/<domain-skill>

Paired handoff: handoff/HANDOFF-<same-suffix>.md

## Mandatory Skill Invocation — Read FIRST

<List the skills the next session MUST invoke before any substantive response, each with a one-clause "when". Cite the governing rule/section if one exists.>

## Working Rules / Truth Source (Rank 1-3)

<Core operational rules. Define the truth hierarchy explicitly: Rank 1 = runtime code paths, Rank 2 = blueprint/spec, Rank 3 = design docs. State explicitly what is NOT a truth source. (Promoted to universal: the agent variant omitted this; the omission is a gap, not a deliberate exclusion.)>

## You Are in Session <session-name>

<Successor lineage: which session this succeeds and that session's closure state. Then the Mandate: single-line if simple, or `### Mandate A.1` / `### Mandate A.2` sub-sections if the scope is multi-part. Mandate = the concrete task. It is NOT the Goal.>

## Goal

- **Session Goal:** <a `/goal`-ready completion condition: one measurable end state + a stated check proving it + any constraint that must not change. Phrase it so this session's own output can demonstrate it. Max 4000 chars. The user pastes this verbatim into the `/goal` UI command at session start.>
- **Ultimate Goal:** <the larger objective this session is one step toward — narrative context; not fed to `/goal`>
- **Linkage:** <one sentence: how Session Goal advances Ultimate Goal — narrative context; not fed to `/goal`>

## Bootstrap Reading (mandatory order)

<Numbered list. Item 0 is always "Read this prompt in full (anticipate truncation)". Bold the critical docs. Include `.agents/Context.md` and `.agents/Lessons.md` directly after item 0, plus `SCOPE.md` (repo root or `docs/<branch-name>/`) when it exists. End with an optional "Lazy-on-demand:" tail listing docs to read only when needed.>

## Verify State via Grep

<A fenced command block of git/grep commands, each followed by a `# expect ...` annotation stating the expected output. Include a `cd <worktree>` preamble if the code lives in a different worktree.>

## After Bootstrap — <DIRECTIVE>

<Pick one directive variant and state it explicitly:
- "START IMMEDIATELY" — autonomous start, no "present understanding" turn, no "ask to begin".
- "STANDBY" — await dispatch before acting.
Cite the question-discipline rule that governs when the session may ask the user vs. decide autonomously.>

## Special Concerns / Pre-Execute

<Numbered concerns + anti-pattern reminders that must be internalized before the first action. Merge of the supervisor "Special Concerns" section and the agent "anti-pattern reminder" bullets.>

## Communication Rules

<Role separation (who is supervisor / agent / user), message-prefix protocol, line-width and word-budget limits.>

### Output Format for <role>

<The exact wrapper the session must use when reporting, e.g. a fenced block prefixed `SUPERVISOR:` or `AGENT:`.>

## End-of-Session Closure Deliverables

<KEYSTONE — mandatory, never optional. State that before the session may close it MUST produce:
1. The next handoff `.md` (per the handoff skeleton, including a `## Goal` section).
2. The next initial-prompt `.txt` (per this skeleton, including a `## Goal` section).
3. Any tasklist / decision-log annotation the workflow requires.
State explicitly: "Without these artifacts landed, the session is NOT closed." This section is what keeps the handoff→initial-prompt→goal chain unbroken across sessions.>

## Anti-Flailing Reminder

<Bulleted "If tempted to <X> outside scope → STOP + escalate per <rule>." List the concrete temptations specific to this work.>

<Terminator line, matching the directive in "After Bootstrap":>
Go.
   — or —
Standby.
```

## Per-section rules

- Sections 1, 3, 4, 5, 6, 7, 9, 10, 11 and the terminator are **universal — always present**.
- Section 0 (bare `/skill` lines) and the `cd` preamble in section 6 are **optional slots**.
- Section 2 (Working Rules / Truth Source) and Section 10 (Closure Deliverables) are **promoted to universal** even though the leaner agent variant omitted them — both are too load-bearing to drop.
- Section 10 is the keystone for this skill's dual-deliverable mandate: it is the mechanism that forces the *next* session to itself produce a handoff + initial-prompt, so the chain never breaks.
- New output contains exactly one anchored `Paired handoff: handoff/HANDOFF-<same-suffix>.md` field before the first instructional section. Prior or superseded handoff references may appear as historical prose, but never with the `Paired handoff:` label.
- Construct the complete three-line Goal payload once and insert it verbatim into both package artifacts. The user may paste the Session Goal value into `/goal`; `/goal` does not parse files. Separately, `bootstrap` parses the complete literal `## Goal` block from both files and requires normalized equality.
