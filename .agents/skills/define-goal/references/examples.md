# Worked Goal Contracts

Four task shapes, each showing the request as it arrived, the trap in it, and the
sharpened contract. Read the sharpening, not just the result — the transformation is
the skill.

---

## 1. Code fix

**Request:** "Fix the login bug, it's flaky."

**Trap:** "flaky" and "fixed" are both unobservable. A loop scored against this
terminates the moment the symptom stops appearing once — which is exactly how flaky
bugs survive a fix.

```markdown
## Goal Contract

- **Objective:** Make the intermittent login failure stop reproducing under the known trigger.
- **Completion condition:** The documented reproduction (10 consecutive logins with an expired refresh token) produces zero 401s, AND a regression test covering that path passes in CI.
- **Evaluator:** `npm test -- auth/refresh` exits 0; the repro script logs 10/10 successes.
- **Out of scope:** Session-timeout UX, refresh-token rotation policy, other auth endpoints.
- **Ultimate goal:** not yet defined by user
```

**What sharpening did:** turned "flaky" into a count (10 consecutive), and added the
regression test — without it, "stops reproducing" is satisfiable by luck.

---

## 2. Vault artifact (evidence-bearing)

**Request:** "Buat artefak riset untuk stage foundation."

**Trap:** "buat artefak" names a deliverable but no acceptance bar. The work can end
with a file that exists and is worthless.

```markdown
## Goal Contract

- **Objective:** Write the foundation-stage research artifact, at the stage the workflow currently permits.
- **Completion condition:** The artifact exists at its canonical path under `work/`, carries every field the stage schema requires, every factual claim resolves to a registered raw-kb wikilink, and no field is left as a placeholder.
- **Evaluator:** File read against the schema field list; each claim's wikilink resolves to an existing raw-kb note.
- **Out of scope:** Any downstream stage's artifact; amending the upstream artifact this one distills; sibling artifacts in the same stage.
- **Ultimate goal:** Complete the foundation stage's artifact set so the next stage's gate can open.
```

**What sharpening did:** named the schema as the evaluator and banned placeholders — the
two ways a "finished" artifact is usually not finished. `Out of scope` blocks the most
likely creep (starting the downstream stage while you are already in it).

---

## 3. Research question

**Request:** "Cari tahu kenapa build-nya lambat."

**Trap:** research tasks have no natural end. Without a condition, the loop ends when
the agent gets bored, and the finding arrives hedged.

```markdown
## Goal Contract

- **Objective:** Identify what accounts for the build-time regression.
- **Completion condition:** One named cause is identified, supported by a measurement showing its share of total build time, and confirmed by a control run where removing or disabling it moves the number.
- **Evaluator:** Two timed builds — baseline and control — with the delta reported.
- **Out of scope:** Implementing the fix; optimising anything not shown to be the cause.
- **Ultimate goal:** Bring CI build time back under its previous ceiling.
```

**What sharpening did:** required a control run. A cause that is merely plausible is the
default output of an unbounded investigation; a cause that moves a number when removed
is a finding.

---

## 4. Ambiguous request

**Request:** "Rapikan dokumentasinya."

**Trap:** two readings — reformat what exists, or rewrite it for accuracy — produce
completely different work, and both are defensible.

Step 5 applies: this is a user-only gap that changes the work materially, so ask once
before posting. Where a smaller ambiguity would allow it, state the assumption inside
the contract instead of blocking.

Resolved as "reformat only":

```markdown
## Goal Contract

- **Objective:** Bring the existing docs into a consistent format, without changing what they claim.
- **Completion condition:** Every file under `docs/` has valid frontmatter, one H1, and heading levels that descend without skipping. No prose claim is altered.
- **Evaluator:** The docs linter exits 0; `git diff` shows no changes inside prose paragraphs.
- **Out of scope:** Correcting stale or wrong content; adding missing docs; restructuring the navigation.
- **Ultimate goal:** not yet defined by user
```

**What sharpening did:** the `git diff` evaluator makes the boundary between "reformat"
and "rewrite" mechanically checkable, so the agent cannot quietly slide from one into
the other.

---

## Pattern across all four

Each `Completion condition` names something that would be **visibly false** if the work
were incomplete: a count, an exit status, a schema, a resolving link, a moved number, a
clean diff.

That is the whole test. Write a condition whose failure is visible, and the loop knows
when to stop.
