---
title: Design Documents
date: 2026-07-22
updated: 2026-07-22
type: documentation
status: active
tags:
  - file-over-app-harness
  - design
  - documentation
---

# Design Documents

`docs/design/` is the home for every design document a project needs before building. For every profile, the design doc is a required, user-approved gate between research and the implementation plan — part of the Universal Development Discipline in the harness `WORKFLOW.md`.

A design document is not a plan and not code. It states **what** will be built and **why this shape**, so the implementation plan can sequence **how**. One design document per feature or cohesive change. Name files `YYYY-MM-DD-<slug>.md`.

## Mandatory development workflow

Every project in this vault, regardless of profile, must traverse this sequence. Skipping a step is a process violation; the design document sits at step 2 and lives here.

```text
1. research / brainstorming
2. design doc                (docs/design/, user-approved gate)
3. implementation plan       (goal per task + one ultimate goal for the whole plan)
4. execution
5. verification / audit / resolve problem
6. self / agent review
7. report to user            (approval gate)
8. test / review by a reviewer
```

The full discipline is canonical in the harness `WORKFLOW.md` ("Universal Development Discipline"). Each profile's `work/WORKFLOW.md` maps its domain stages onto it. This file governs only the design-document artifact.

## Design document contract

Each design document should contain:

- **Context and problem** — what is being solved, linked to the research artifact and any registered `raw-kb/` sources.
- **Goals and non-goals** — what this design must achieve; what it deliberately excludes.
- **Proposed design** — the chosen structure: components, boundaries, data flow, interfaces, and dependencies.
- **Alternatives considered** — the rejected options and why the chosen one wins. Exactly one recommended design; never a menu left open.
- **Trade-offs and risks** — costs, blast radius, reversibility, and the failure mode if a key assumption is wrong.
- **Impact** — what downstream work (implementation plan, tests) this design implies.
- **Open questions** — anything unresolved that must close before the implementation plan.

## Approval

A design document is a working draft until the user explicitly approves it. Only then does it become the basis for an implementation plan. Record the approval decision and date in the document's `## Update History`, per the decision-authority rule in the harness `WORKFLOW.md`.
