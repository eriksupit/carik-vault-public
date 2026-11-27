# Roster Archetypes & Boundary Rules

One role catalogue for all harnesses. A role says *what* an agent does; `engine` (`omp`, `pi`, or `agy`) says *which harness* runs it. Any role can run on any engine, but every Gemini model runs on `agy` (§2).

## 1. Role catalogue

| Role slug | Responsibility | Write boundary (example) | Notes |
|---|---|---|---|
| `supervisor` | Coordinates, orchestrates, supervises, declares work solid (SKILL.md "Supervisor contract") | parent of `state_dir`, e.g. `vault/.agents/memory/` (script-only) | Reserved; changes no file by hand (the skill scripts write `state_dir`), never does task work, never runs mutating git/gh. Handoffs and decision logs go to `doc-writer`. |
| `worker` | Implements features or fixes in a delegated area | explicit feature paths, e.g. `apps/mobile/src/` | Escalates unapproved decisions instead of guessing. |
| `researcher` | Web/docs research with sources and short briefs | `vault/raw-kb/research/` | No app code, no mockups. |
| `ui-architect` | Interactive mockups, visual and ergonomic design | `vault/raw-kb/user-provided/ui-ux-design-mockup/` | No native client code. |
| `doc-writer` | Formal specs, system documentation, handoffs, decision logs | `vault/docs/`, `handoff/` | No implementation or server config. |
| `oracle` | Second opinion before acting: challenges plans, flags architectural risk | `[]` read-only | Findings go to the supervisor by report. |
| `reviewer` | Adversarial review of diffs, tests, edge cases, rule compliance; PR review with `gh pr review` | `[]` read-only | Never fixes; fixes go back to the owning worker via the supervisor. On a PR authored by the same GitHub account, use `gh pr review --comment` (GitHub forbids self-approval). |
| `integrator` | Branch, stage, commit, push, `gh pr create`, `gh pr merge`, `git fetch`, on supervisor dispatch only | exactly `[".git/"]` | The only role allowed to write `.git/`; cannot touch the working tree, so it never runs a local merge, rebase, pull, or checkout that changes files. Create the feature branch before workers start writing. Merge happens on GitHub (`gh pr merge`). |
| `scout` | Fast codebase recon: files, entry points, data flow, risks | `[]` read-only | |
| `evidence-auditor` | Checks that research claims are supported by their sources | `[]` read-only | |
| `auditor-redteam` | Security, usability, ergonomics attack | `[]` read-only | |

Example paths are placeholders: replace them with the project's real directories. `spawn-team.sh --dry-run` rejects any roster where one owner's path equals or contains another owner's path (the supervisor included).

## 2. Engine choice: omp, pi, agy

| | omp | pi | agy (Antigravity CLI) |
|---|---|---|---|
| Launch (by `spawn-team.sh`) | `sandbox-exec -f <profile> omp …` | `sandbox-exec -f <profile> pi …` | `sandbox-exec -f <profile> agy <AGY_FLAGS> …` |
| Role card | `--append-system-prompt <card>` | `--append-system-prompt <card>` | `-i "<card text>"`: first turn, settled before the handshake; the card says to re-read its file after compaction |
| Model | `--model <pattern>` | `--model <pattern>` | `--model <id>`, exact id from `agy models`; default `gemini-3.8-flash-medium` |
| Herdr integration | `omp` | `pi` | `antigravity-cli` |
| Write boundary | OS sandbox: writes under the project denied except the agent's paths | same | same |
| Internal delegation | omp `task` subagents (run inside the same sandbox) | `pi-subagents` extension (`oracle`, `worker`, `reviewer`, `scout`, `researcher`, `evidence-auditor`, `delegate`), same sandbox | agy subagents, same sandbox |

**Gemini → agy.** Every Gemini model (`gemini-*`: Argon `gemini-4-argon-{low,medium,high}`, `gemini-pro-orchestrator-g1-pro`, Hydrogen, Flash) runs on `agy`, whichever harness the supervisor uses. omp and pi list the same models under their `antigravity` provider; a roster must not use that path, and `spawn-team.sh --dry-run` rejects it. An `agy` agent without `model` runs `gemini-3.8-flash-medium`.

**Claude → omp.** Every Claude model (`anthropic/claude-*`) must run on the `omp` engine (neither `agy` nor `pi`), per owner ruling; ensure the Herdr `omp` integration is `current` (`herdr integration install omp`).

**ChatGPT / OpenAI providers (`openai-chatgpt` vs `openai-codex`).** For ChatGPT / OpenAI models on `omp` (and `pi`), distinguish two separate providers: `openai-chatgpt` (ChatGPT plan — e.g. `openai-chatgpt/gpt-6.2-sol` on `omp`, 128K context, no image input) and `openai-codex` (Codex OAuth — e.g. `openai-codex/gpt-6.2-sol` on `omp` and `pi`, 500K context, image input supported; distinct from the plain API `openai` provider on `pi`). Always inspect the active catalog with `omp models` or `pi --list-models` before locking a `provider/model` entry in a roster.

**pi-subagents is not a pane identity.** Its roles are subagents a pi session can spawn *inside its own pane*: a pi `worker` pane may call its `scout` subagent, for example. A pane's role always comes from its role card. Choose `pi` when the user asks for "mode pi" / "versi pi" or wants pi-subagents available inside that pane.

## 3. Patterns (disjoint example paths; ≤4 agents per tab, ≤2 tabs)

### A. Review & sanity loop
- `<prefix>-oracle` (read-only), `<prefix>-worker` (`<feature paths>`), `<prefix>-reviewer` (read-only)

### B. Research & implementation
- `<prefix>-researcher` (`vault/raw-kb/research/`), `<prefix>-worker` (`<feature paths>`), `<prefix>-oracle` (read-only), `<prefix>-reviewer` (read-only)

### C. UI/UX redesign
- `<prefix>-researcher` (`vault/raw-kb/research/`), `<prefix>-ui-architect` (`vault/raw-kb/user-provided/ui-ux-design-mockup/`), `<prefix>-mobile-executor` (`apps/mobile/src/`), `<prefix>-auditor-redteam` (read-only)

### D. Fullstack feature
- `<prefix>-backend-executor` (`server/src/api/`, `server/tests/api/`), `<prefix>-gateway-bridge` (`server/src/realtime/`, `server/tests/realtime/`), `<prefix>-frontend-executor` (`apps/web/src/`), `<prefix>-auditor-redteam` (read-only)

### E. Research & proposal
- `<prefix>-internal-researcher` (read-only), `<prefix>-market-researcher` (`vault/raw-kb/research/`), `<prefix>-proposal-redteam` (read-only)

### F. Full lifecycle to merge (2 tabs)
- Tab 1: `<prefix>-researcher` (`vault/raw-kb/research/`), `<prefix>-oracle` (read-only), `<prefix>-worker` (`<feature paths>`), `<prefix>-reviewer` (read-only)
- Tab 2: `<prefix>-auditor-redteam` (read-only), `<prefix>-integrator` (`.git/`)

Any roster whose goal includes commit, push, PR, or merge MUST contain an `integrator`: no other agent can write `.git/`, and the supervisor never runs mutating git/gh commands.

## 4. Boundary rules

1. **One writer per path.** No two owners share or nest paths in one active session; the script enforces this.
2. **Supervisor changes nothing.** It coordinates and declares work solid; the skill scripts it runs write `state_dir`, and every task, from research to handoff to merge, belongs to a pane agent.
3. **Read-only roles never write**, not even minor corrections. They report findings; the owning worker fixes.
4. **Git writes belong to the integrator.** Only the `integrator` sandbox allows `.git/`. It commits only the paths the supervisor names, and merges only after the supervisor's solid gate; merging into `main`/protected branches also needs the owner's explicit approval.
5. **Single pane-map writer.** Only the skill scripts (`spawn-team.sh`, `record-report.sh`) write `<state_dir>/pane-map.md`; sub-agents report through `report.sh`, never by editing registry files.
