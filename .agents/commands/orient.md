---
description: Build a full, detailed mental model of this vault. Invokes the orient skill — guided reading of the canonical files in order, then a comprehension gate the agent must pass with file:line citations. Works in the harness and in any generated project vault.
---

# /orient

Invoke the **`orient`** skill via the Skill tool, then follow it exactly.

The skill:

1. Detects the environment (harness vs generated project vault).
2. Guides reading the canonical governance, continuity, and domain files in order.
3. Gates on a comprehension quiz that MUST be answered with valid `file:line`
   citations from the live vault files — not from memory, not from the skill.
4. Records an `Orientation completed` marker in `.agents/Context.md`.

Use on first contact with a vault, or any time you need to re-orient after a major
governance change or when the vault model feels stale.

$ARGUMENTS
