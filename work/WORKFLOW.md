---
title: Alur Kerja Rekayasa Perangkat Lunak — Carik Vault Public
date: 2026-11-17
updated: 2026-11-24
type: workflow
status: active
tags:
  - workflow
  - app-build
  - software-engineering
  - tata-kelola
---

# Alur Kerja Rekayasa Perangkat Lunak — Carik Vault Public

Ini adalah prosedur kanonis untuk profil `app-build` pada proyek **Carik Vault Public**, beroperasi di bawah filosofi **Human-Sovereign, File-First, Intelligence-First Agentic Harness Architecture** pada [CREATIVE-LAW.md](../CREATIVE-LAW.md) (Bagian 2): kecerdasan *agent* memimpin substansi rekayasa (didahului wawancara `grill-with-docs`, PRD `to-prd`, riset preseden arsitektur nyata, dan sketsa kontrak `architect`), sedangkan fakta eksekusi perangkat lunak dinilai secara deterministik oleh *compiler*, *typecheck*, tes otomatis, *build*, dan pagar Class C. Blok `CORE_GOVERNANCE` di bawah mengatur kontrak *frontmatter*, provenans `raw-kb/`, otoritas keputusan, dan isolasi Git; bagian ini mengatur alur kerja deterministik pengembangan perangkat lunak.

## Urutan Kerja Wajib (8 Tahap)

Setiap pembangunan fitur atau aplikasi wajib menempuh urutan berikut. Melompati tahap adalah pelanggaran proses. Alur ini berbentuk *loop*: kegagalan pada verifikasi atau ulasan mengembalikan kerja ke tahap paling awal yang artefaknya harus diperbaiki.

```text
1. research / brainstorming       -> work/research/
2. design doc                     -> docs/design/              (gerbang persetujuan pemilik)
3. implementation plan            -> work/implementation-plan/ & docs/plans/ (goal per tugas + 1 ultimate goal)
4. execution                      -> work/build/
5. verification / audit / resolve -> work/verification/
6. self / agent review            -> work/review/
7. report to user                 -> work/review/              (gerbang persetujuan pemilik)
8. test / review by a reviewer    -> work/review/
```

### 1. Research / Brainstorming (`work/research/`)
- Rumuskan masalah, target pengguna, kriteria sukses, batasan teknis, dan *non-goals*.
- Mulai dari `work/research/intake.md` (`status: research-pending`). Daftarkan seluruh bahan acuan ke `raw-kb/SOURCES.md` sebelum dipakai sebagai bukti.

### 2. Design Doc (`docs/design/`) — Gerbang Pemilik
- Susun dokumen desain sesuai `docs/design/README.md`: konteks, *goals & non-goals*, desain yang diusulkan, alternatif yang dipertimbangkan (dengan tepat satu rekomendasi), *trade-offs & risks*, dampak, dan pertanyaan terbuka.
- Dokumen ini berstatus draf kerja hingga disetujui eksplisit oleh pemilik. Tidak ada rencana implementasi yang boleh ditulis sebelum dokumen desain disetujui.

### 3. Implementation Plan (`work/implementation-plan/` & `docs/plans/`)
- Pecah desain yang disetujui menjadi tugas-tugas terisolasi yang dapat di-*revert* mandiri.
- Setiap tugas wajib menyatakan satu *goal* dan satu metode verifikasi deterministik; seluruh rencana wajib menyatakan satu *ultimate goal*.
- Terapkan prinsip *deep modules*, *seams*, dan *locality*.

### 4. Execution (`work/build/`)
- Kode sumber nyata dibangun tugas demi tugas sesuai rencana.
- **Pemisahan Files-over-App:** FOA berlaku penuh untuk tata kelola, desain, rencana, dan kontinuitas (`.agents/`, `docs/`, `work/research/`, `work/verification/`, `work/review/`). Untuk `work/build/`, direktori ini boleh memuat proyek kode penuh beserta *package manager*, *build toolchain*, dan *test runner*.
- **Otorisasi Eksekusi Kode (`lean-plan`):** Sesuai Invarian #4 `CREATIVE-LAW.md`, hook regex `summary-first-gate.py` telah diamputasi. Setelah rencana implementasi disetujui dan tercatat di `docs/plans/`, disiplin *Summary-First* dan alur `lean-plan` untuk penulisan kode di `work/build/` ditegakkan melalui penalaran agen atas kontrak teks tanpa token regex per-berkas.
- Jaga setiap commit terisolasi per tugas sesuai aturan Git di `CORE_GOVERNANCE`.

### 5. Verification / Audit / Resolve (`work/verification/`)
- Jalankan verifikasi deterministik yang ditetapkan pada setiap tugas (unit test, integration test, typecheck, linter, build check).
- Setiap kegagalan adalah celah yang harus dilacak akar penyebabnya, diperbaiki, dan diuji ulang—bukan ditambal gejalanya. Audit kesesuaian hasil terhadap kontrak tugas.

### 6. Self / Agent Review (`work/review/`)
- Agen meninjau ulang hasil kerjanya terhadap dokumen desain, *goal* rencana, kesehatan arsitektur, serta kontrak harness (*frontmatter*, provenans, isolasi Git).

### 7. Report to User (`work/review/`) — Gerbang Pemilik
- Laporkan apa yang dibangun, bukti langsung hasil verifikasi/tes, risiko tersisa, dan satu rekomendasi langkah berikutnya.

### 8. Test / Review by Reviewer (`work/review/`)
- Peninjau independen (manusia atau agen peninjau terpisah) menguji dan meninjau perubahan. Temuan yang belum tuntas mengembalikan alur ke tahap terdampak paling awal.

## Gerbang Bukti (*Evidence Gates*)

Promosi status hanya sah bila seluruh syarat terpenuhi dan disetujui eksplisit oleh pemilik:
- **Gate 1 (Research → Design):** Masalah, pengguna, kriteria sukses, batasan, dan *non-goals* jelas; bahan acuan terdaftar; satu rekomendasi agen; disetujui pemilik.
- **Gate 2 (Design → Implementation Plan):** Dokumen desain ada di `docs/design/` dengan satu desain rekomendasi, alternatif, *trade-offs*, dan tanpa pertanyaan terbuka yang menggantung; **persetujuan eksplisit pemilik**.
- **Gate 3 (Plan → Execution):** Setiap tugas memiliki *goal* dan verifikasi terukur; rencana memiliki *ultimate goal*; disetujui pemilik.
- **Gate 4 (Execution → Report):** Implementasi sesuai desain; seluruh verifikasi lulus dengan bukti nyata; temuan *self-review* tuntas tanpa celah tertunda.
- **Gate 5 (Report → Ship):** Persetujuan pemilik setelah laporan; ulasan peninjau independen lulus.

## Tata Kelola Inti (Dikelola Harness)

Blok di bawah ini disinkronkan dari `carik-vault` / `file-over-app-harness` saat inisialisasi. Jangan sunting isinya secara manual di sini.

<!-- BEGIN HARNESS MANAGED: CORE_GOVERNANCE -->

## Universal Development Discipline

Regardless of project, any product built with an agent in this vault follows one mandatory process discipline. This is about orderly work, not domain: whatever the product, the agent must research before designing, design before planning, plan before executing, and verify and review before reporting. The steps are universal; the domain pipeline under `work/` is the vault's concrete instantiation of them, not a replacement for them.

```text
1. research / brainstorming
2. design doc                 (docs/design/, user-approved gate)
3. implementation plan        (a goal per task + one ultimate goal for the whole plan)
4. execution
5. verification / audit / resolve problem
6. self / agent review
7. report to user             (approval gate)
8. test / review by a reviewer
```

The discipline is a loop: a failure at verification, review, or reviewer test returns to the earliest step whose artifact must change, recording the reason, impact, and affected status.

Three parts of this discipline are binding across every vault:

- **Design doc gate.** Before any implementation plan, produce a design document in `docs/design/` per `docs/design/README.md`: one recommended design, alternatives named, trade-offs, and open questions. It is a working draft until the user explicitly approves it. No plan is written before that approval. Stress-test designs and extract ADRs using `grill-with-docs` or `concept-architect`.
- **Goal-anchored plan.** Every implementation plan states one goal per task and one ultimate goal for the whole plan. A task with no stated goal is not ready to execute. Apply `codebase-design` principles (deep modules, seams, locality) when planning architecture.
- **Verify-review-report-review loop.** After execution: verify/audit and resolve every gap (using `diagnosing-bugs` for disciplined, feedback-loop first bug resolution, and `audit-patch-gaps` for contract compliance); the agent reviews its own work (using `improve-codebase-architecture` for structural health); report to the user as an approval gate; then an independent reviewer (human or a separate review agent) tests and reviews.
- **Per-Artifact Research Loop.** Before writing any project artifact, the agent runs, in order: (1) determine the knowledge the artifact needs; (2) **browse the internet — mandatory and automatic, a standing workflow-authorized action needing no per-artifact permission** — in both cases, whether or not the user supplied raw material, with the only brake being dedup against `raw-kb/SOURCES.md` (an identical source is not registered twice); (3) register each `agent-acquired` source in `SOURCES.md` and extract findings into atomic `[[wikilinked]]` notes via the `graphify` skill, keeping raw evidence separate from synthesis; (4) only then write the artifact with correct definition and format, citing the `source_id`s and any user-provided material. A pure-synthesis artifact still runs the browse step; it may return no new source, which is valid and logged. This loop is the finest-grained instantiation of "research before designing"; it never bypasses the design-doc gate, the evidence gates, or the provenance discipline above it. Operationalized by the `artifact-research-loop` skill.

How a vault maps its pipeline stages onto this discipline is stated in its `work/WORKFLOW.md`; the stage names remain the vault's own — the discipline never flattens them.

## Summary-First Approval

Before writing agent-authored semantic content, present one concise summary and obtain explicit user validation. This section is the sole complete authority for the rule. `AGENTS.md`, the vault's `work/WORKFLOW.md`, and the portable `summary-first-approval` skill point here without restating it.

### Approval summary

The summary must let the user judge the proposed direction without reading the finished artifact. State all four fields:

1. **Purpose** — why the write exists and what outcome it serves.
2. **Key decisions** — the material claims, choices, or commitments the artifact will make.
3. **Scope** — what the write covers, including any material exclusion needed to prevent overreach.
4. **Target artifacts** — every file whose agent-authored meaning will be created, edited, appended, replaced, deleted, migrated, or repaired.

A vague request to approve future work, a hidden scope, or an omitted target does not authorize a semantic write. Multiple targets may share one approval when the same displayed summary names every target and binds them to one cohesive change.

### Write, readback, and report

After explicit user validation, write the complete artifact directly without displaying its full text first. Then read back every changed artifact and report concisely what was actually written. Approval binds to the summary's purpose, key decisions, scope, and targets; it does not bind exact wording.

The user may explicitly require a full preview for any named write. That instruction overrides the default for its stated scope only; later work returns to Summary-First Approval.

### Strict 2-Turn Handshake and Zero-Mutation Pre-Approval

Under the **Zero-Mutation Pre-Approval Principle**, no file-mutating tool (`write`, `edit`, `patch`, or shell mutation) may be invoked on declared semantic paths until an explicit approval token has been minted from an owner prompt.

Semantic writes follow the **Strict 2-Turn Handshake**:

1. **Turn 1 (Preview & Alignment)**: The model presents a single preview block naming purpose, key decisions, scope, and target artifact. No mutating tool may be invoked in Turn 1.
2. **Turn 2 (Approved Execution)**: The owner validates the proposal with an affirmative command ("approve", "setuju", "lanjutkan"). The model executes the write, reads it back, and reports the verified digest.

Operational and continuity paths declared in `.agents/policy.json` under `summary_first_exempt_operational_paths` (such as `.agents/Context.md`, `.agents/Lessons.md`, `.agents/Memory.md`, `.agents/memory/`, `.agents/sessions/`, `.agents/incidents/`, `handoff/`, `VERSION`, `CHANGELOG.md`) are exempt from the token requirement so mechanical governance tasks do not deadlock.

### Material drift

A completed write materially deviates when it changes an approved decision, exceeds the approved scope, writes semantic content to an unnamed target, or introduces a consequential claim or commitment absent from the summary. Report the drift and obtain a new user decision before the affected content is promoted to canon, satisfies a gate, or feeds downstream work. The artifact may remain a clearly noncanonical draft while awaiting that decision.

If readback shows no material drift, no second approval is needed merely because the complete wording was not previewed. Normal evidence, completeness, stage, and promotion gates still apply independently.

### Already-authorized and mechanical writes

No separate summary is required when the user's instruction already states the four fields unambiguously, including an explicit end-to-end goal that names the intended outcome and authorized targets. The same applies to exact user-supplied text with an explicit save instruction, byte-identical raw intake, mechanically forced metadata, deterministic generation from approved inputs, closed-form operational records, meaning-preserving migration, and executable implementation under an approved design and plan. If any such operation introduces a new semantic decision, return to Summary-First Approval.

### Persistence and promotion

Approval to write and approval to promote are separate authorities. A Summary-First validation permits persistence within its scope; only the artifact's evidence or stage gate can promote it to canon. One user instruction may authorize both when it says so explicitly.

### Recovery

When an unapproved or materially drifting semantic write is discovered, stop dependent use and report the affected target and delta. Restore the last verified permitted state when it is known, or retain the result as a noncanonical draft while requesting a new user decision. Never guess a prior state or silently promote the drift.

## Writing Style and Language Governance

Every vault carries a universal prose style guide and checklist at `writing-style/` plus the audit script `scripts/prose_style_audit.py` and the living record `.agents/Indonesian-Logic-Language.md`. They apply to all prose (reports, documentation, essays, narrative, synthesis) except academic papers, whose register differs. Follow the guide, consult the living record before drafting, run the script, and review each finding manually. Append new style preferences to `writing-style/prose-writing-style.md` and append newly discovered Indonesian logic or language findings to `.agents/Indonesian-Logic-Language.md`.

Forbid in-document changelogs or session history sections in core governance documents (`AGENTS.md`, `WORKFLOW.md`, `CLAUDE.md`, `README.md`, `SCOPE.md`). Chronological session events belong in `.agents/Context.md`, Git commit messages, and `handoff/` packages.

The prose guide and checklist are **living documents**: when the user sets or corrects a prose-style preference, append it — dated, never overwriting — to the guide's "Preferensi Gaya (Akumulatif)" section, so preferences accumulate across sessions. Add a checklist item when a preference implies a new mechanical check.

Profiles may ship additional writing resources through `resource_files` in `profile.json` (verbatim copies into the vault).

## Capability Provisioning

During project setup — and whenever a new need appears mid-project — the agent must assess the agent capabilities the project requires and recommend the missing ones. This applies universally. A capability is a hook, a skill, a subagent, or, only when packaging is truly needed, a plugin.

Follow this procedure:

1. **Assess.** From the project's research and design, name the concrete capabilities the work needs (for example: a deterministic guard, a repeatable audit procedure, a delegated review agent).
2. **Check what exists.** Look at what is already available globally and vault-local before proposing anything new. Do not recommend recreating a capability that already exists.
3. **Recommend the lightest artifact that works.** Prefer, in order:
   - a **hook** — policy in `.agents/hooks/`, runtime activation in `.claude/settings.json` — for a deterministic, tool-call-time rule;
   - a **skill** (`.agents/skills/`, with runtime publication or registration handled separately) for a reusable procedure the agent should follow;
   - a **subagent** (`.claude/agents/`) for delegated work needing a separate context;
   - a **plugin** only when the capability must be packaged and shared across vaults. A plugin is the last rung, never the default.

   Before proposing a *blocking* hook, ask what its mandatory trace is. A rule whose only trace is the agent's own report cannot be gated — it can only be reminded, and must then be named a reminder. A rule whose trace is a filesystem fact (a registry row, a log the vault writes, a path predicate) can be gated. `.agents/hooks/README.md` records which of this vault's hooks are which, and why.
4. **Isolate by default; flag the generic.** New capabilities are created vault-local so they travel with the vault. When a capability is clearly generic and would be reused across projects, recommend placing it in the user's global configuration instead of duplicating it per vault, and say so.
5. **Document cross-agent needs.** `.claude/` holds runtime activation, which is native to Claude Code and is not read the same way by Codex. Keep the capability itself in the runtime-neutral tree (`.agents/hooks/`, `.agents/skills/`) so another runtime can be wired to the same policy later without forking it, and write any capability that must apply to both agents as plain instructions in `AGENTS.md` or the vault's `work/WORKFLOW.md` as well — never only as a Claude skill or hook.
6. **Recommend, never auto-create.** Proposing a capability is allowed; creating a hook, skill, subagent, or plugin is an execution action that requires explicit user approval per case. Verify the current scaffolding mechanics against up-to-date documentation at the moment of creation, not at the moment of recommendation.

### Illustrative example — not a task

> The following is a case illustration only. It is not work to be performed and does not describe anything this vault must build. It exists solely to show how the procedure above is applied.

Suppose a project produces a monthly report and the work needs financial analysis over spreadsheet data. Applying the procedure: the need is project-specific, so the right artifact is a **vault-local skill** (rung 2), not a plugin. That single skill bundles two different things that are easy to conflate:

- the **procedure** — how the financial analysis is done for this report: which metrics, which checks, what output format. This is the skill proper.
- the **mechanical ability** to read and write the spreadsheet — handled by a small script bundled inside the skill (a skill may carry a `scripts/` file), not by a separate plugin.

Reaching for a full plugin here would violate the lightest-artifact ladder. And if this analysis is clearly reused across many report projects rather than being one-off, the agent flags it as a candidate for the user's global configuration instead of duplicating it per vault. In all cases the agent recommends; it does not create the skill without the user's explicit approval.


## Skill Store Validation and Publication

The harness owns the canonical implementation of every skill declared under `harness_owned` in `.agents/skills/manifest.json`. The user store at `~/.agents/skills/` owns declared global-only skills. User-global Claude copies are generated from the owning source, and Codex registry entries point to that same source.

Run `python3 scripts/sync-skills.py --check` before publishing or updating a vault. Validation fails on invalid routing metadata, undeclared skills, retired active skills, and different immutable-implementation digests under one name. Exact manifest-declared live-data paths use a separate digest and may differ. A same-name pair may remain visible to a host only when its immutable implementation is identical.

External publication follows a preview-first authority sequence: `--publish-user` or `--update-vault PATH` prints the proposed changes; `--apply` authorizes file mutation; `--apply-codex` separately authorizes the global Codex configuration write. A behavioral variation must use `<vault>-<skill>` or `<project>-<skill>`. Do not approve a divergent same-name override.

Publication never dereferences a symlinked destination: a link resolving to the source is a no-op, a link to another directory is written through so the link itself survives, and a dangling link is replaced by a real directory. `.agents/skills` and `.agents/commands` are the sole project-local trees; `.claude/skills` and `.claude/commands` must not exist. `--wire-project` removes obsolete managed adapters for both.

## Agent-Created Markdown Frontmatter

Every Markdown note created by an agent in this vault must begin with valid Obsidian YAML frontmatter. This applies to governance, workflow, continuity, plan, research, and pipeline notes.

Require these properties:

```yaml
---
title: Document Title
date: YYYY-MM-DD
updated: YYYY-MM-DD
type: document-type
status: document-status
tags:
  - at-least-one-tag
---
```

- `title`, `type`, and `status` must be non-empty text values.
- `date` records the document's initial date and must use `YYYY-MM-DD`.
- `updated` records the latest substantive content change and must use `YYYY-MM-DD`.
- `tags` must be a non-empty YAML list.
- Add `revision`, `status-note`, `part-of`, `builds-on`, source links, and other properties only when they carry real document-specific meaning. Never create empty optional properties to imitate another note.

The sole path exception is `raw-kb/user-provided/`. Never modify a user-provided source merely to add frontmatter. Record its identity, provenance, checksum, and rights status in `raw-kb/SOURCES.md`. Route any user-uploaded Markdown source into that directory so the exception remains auditable.

This contract applies only to `.md` notes. Do not prepend YAML frontmatter to PDF, image, JSON, plain-text, source-code, or other non-Markdown formats because it can corrupt the file or its format contract.

### Open Knowledge Format and Anti-Plugin Syntax

Notes in the vault represent the "cognitive brain" topology: nodes are defined by frontmatter metadata, directed relationships are declared via `[[wikilinks]]`, and spatial maps use `.canvas`.

- **Standard open syntax only:** Notes must rely strictly on standard Markdown, YAML frontmatter, wikilinks, and standard Obsidian-compatible callouts (`> [!note]`, `> [!tip]`, `> [!warning]`).
- **Anti-Plugin Syntax prohibition:** Agents must NEVER emit proprietary or plugin-dependent syntax (such as Dataview query blocks ````dataview`, Templater tags `<% ... %>`, or custom plugin metadata). All content must remain fully intelligible and navigable in plain text without requiring third-party plugins or runtime daemons.
- **Strict execution separation:** Obsidian is a cognitive layout standard for human perception, never an execution instrument. All agent actions execute directly on the physical filesystem.
## Governance Continuity Store

The vault-local continuity store is the canonical durable memory surface. `.agents/Memory.md` is a bounded active index; each durable fact lives in `.agents/memory/<stable-slug>.md`. External model memory, when present outside the vault, is a derived mirror rather than a competing authority.

Admit only sourced facts, decisions, terminology, and durable preferences that cannot be recovered cheaply from canonical artifacts. A fact record requires the normal note frontmatter plus `fact_id`, `scope`, `stage`, `fact_key`, `effective`, `source`, `supersedes`, and `superseded_by`. At most one active fact may occupy a `scope + fact_key` slot. Replacing a fact requires reciprocal supersession links; history is retained, never silently deleted.

`Context.md` and `Lessons.md` remain chronological active windows. At closure or handoff, run `python3 scripts/governance_store.py rotate-anchors`, then `refresh-memory`, then `check`. Each anchor rotates independently above 64 KiB or 100 entries and retains the newest 30. Archives live below `.agents/archive/`, remain checksum-linked from their parent, and are never used as default bootstrap input.

At bootstrap and before relying on durable facts, run `python3 scripts/governance_store.py check`. Read the active memory index, the anchor heading indexes and newest complete entries, then only task-relevant fact bodies. A named store failure blocks closure, handoff, promotion, and downstream use of the affected facts until repaired.

## Raw KB Source Provenance

Use directory placement as the primary provenance class for every raw source:

```text
raw-kb/
├── SOURCES.md
├── user-provided/
└── agent-acquired/
```

- `user-provided/` contains a source, attachment, local file, or specific URL selected and supplied by the user. A file copied or downloaded by the agent from that user-specified input remains `user-provided`.
- `agent-acquired/` contains a source independently found and selected by the agent during research whose scope the user has authorized. The **Per-Artifact Research Loop** (see "Universal Development Discipline") is itself that standing authorization: within it the agent browses automatically for the active artifact, so a source acquired through the loop is authorized by the workflow and does not require a separate per-scope prompt. Registration and rights discipline below still apply to every such source.

These classes describe the source's ingress path. They do not establish legal ownership, copyright, license, or permission to reuse the material.

### Mandatory source registry

Treat `raw-kb/SOURCES.md` as the single source inventory. Register a source before using it as evidence in analysis, synthesis, or project development. Each entry must include: `source_id`, `local_path`, `provenance_class`, `provided_or_discovered_by`, `ingest_method`, `original_creator_or_publisher`, `original_url_or_attachment_record`, `date_added`, `file_format`, `rights_status`, `rights_or_access_note`, `derived_files`, `sha256`, and `registration_status`.

Use exactly one `ingest_method` of `local-copy`, `attachment`, `user-url`, `direct-drop`, or `agent-research`. Use exactly one `rights_status` of `user-declared`, `unknown`, `public`, or `licensed`. `user-declared` records the user's statement; it is not independent legal verification. Record unavailable metadata as `unknown`; never invent it.

### Intake behavior

- When the user places a file directly in `user-provided/`, preserve its filename and location, compute its SHA-256 checksum, and register it before evidentiary use.
- When the user supplies a specific local path, attachment, or file reference, copy only that identified file into `user-provided/`. Never move, delete, or alter the source file on the user's computer.
- When the user supplies a specific URL, place the retrieved source in `user-provided/` and retain the original URL in the registry.
- When the agent independently discovers a source during authorized research, place it in `agent-acquired/` and retain the discovery URL or access record.
- At the start of raw KB work, compare source files on the filesystem with `SOURCES.md`. Ignore operating-system metadata and empty placeholders such as `.DS_Store` and `.gitkeep`. Mark an unlisted source file as `unregistered`, record only verifiable facts, and do not use it as evidence until registration is complete.

Before copying, compare the destination name and checksum. If the same name and checksum already exist, keep the existing file and do not create a duplicate. If the same name exists with a different checksum, stop the intake and report the conflict. Do not rename either file without explicit user approval.

### Derived material and synthesis

A faithful format conversion (PDF-to-Markdown, audio-to-transcript) retains the source's provenance class, stays with that source class, and is linked through `derived_files`. Agent summaries, evaluations, interpretations, and syntheses are not raw sources; store them inside the vault's synthesis stage under `work/` with links to the registered source IDs.

### Skeleton sterility

The reusable harness skeleton must remain a sterile source of structure and must never contain active raw source material. Its `raw-kb/SOURCES.md` must be byte-identical to `raw-kb/SOURCES-TEMPLATE.md`, and `raw-kb/user-provided/` plus `raw-kb/agent-acquired/` may contain only their `.gitkeep` placeholders. Active sources belong only in an initialized project after intake and registration.

## Evidence Gates and Decision Authority

Every vault defines evidence gates: named conditions that must all hold before a project artifact is promoted from a working draft to project canon. The universal rule:

- The agent may create candidates, gather evidence, test them, and issue exactly one evidence-backed recommendation.
- Only explicit user approval promotes an artifact to the next status. A completed checklist proves readiness for review; it never promotes anything automatically.
- Do not silently replace, revise, or promote an active decision. Record the evidence, proposed change, expected impact, and user decision in the relevant `work/` artifact.
- Missing minimum evidence stops promotion. Material counter-evidence stops promotion. Record contradictions, affected artifacts, and downstream impact, then recommend one outcome: retain, revise, or reject.
- Preserve superseded artifacts and mark their status; never delete decision history.


## Isolated Git Commit and GitHub Push

> [!NOTE] Applicability: Git-Controlled Repositories vs. Non-Git Vaults
> The procedures in this section apply exclusively when the vault operates under Git version control (an initialized `.git` repository). For users running the vault in a local directory or using cloud synchronization (such as iCloud Drive, Dropbox, or OneDrive without a `.git` directory), **all Git commit, push, and remote gates are automatically passive and dormant**. No Git commands, terminal usage, or version control knowledge are required to read, write, or collaborate in this vault.

Apply this gate whenever the user requests a commit, a push, GitHub publication, or a repository connection in a Git-tracked repository. Do not commit or push merely because a session ends.

### Repository boundary

Treat the current vault root as `project_root`. Resolve the nearest Git root with `git rev-parse --show-toplevel` and treat it as `repo_root`.

- Require `repo_root == project_root` before a project-local commit, remote configuration, or push.
- If no Git repository exists and the user has authorized publication, initialize Git only at `project_root`.
- If `repo_root` is a parent directory, do not commit the project through that parent and do not attach a project-specific remote to the parent.
- Before creating a nested standalone repository, verify the parent repository does not already track the project files. If it does, stop and report that an explicit repository migration is required.
- Never initialize Git, migrate tracked files, alter a parent index, or change an existing remote without the applicable explicit user authorization.

### GitHub repository handoff

Before the first push, ask the user to create an empty private GitHub repository without a README, license, or `.gitignore`. Ask for the repository URL only. Do not ask the user for account credentials.

Verify the supplied remote uses `github.com` and matches the repository the user named. Before staging content for a first publication, query the repository metadata and require `visibility: PRIVATE`. An empty remote or a successful authentication check does not prove privacy. Stop before staging or pushing user-provided sources when visibility is public, internal, unknown, or unverifiable. Add the URL as `origin` only when no conflicting remote exists. If `origin` already exists with a different URL, stop and request explicit authorization before changing it.

### Authentication boundary

Never request, accept, print, persist, or transmit a GitHub password, personal access token, private key, recovery code, or session credential. Never write GitHub authentication material to `.env.local`, `.env`, a Markdown note, a script, a remote URL, Git configuration, or any other project file.

Use a locally secured mechanism: GitHub CLI or Git Credential Manager for HTTPS with interactive browser authentication and OS credential storage; or SSH with the private key kept outside the vault and managed by the user's SSH agent. When GitHub CLI authentication is invalid, ask the user to complete `gh auth login -h github.com --web` on their computer. The user must never paste the resulting credential into the conversation or vault.

### Pre-commit gate

Before staging:

1. Verify `repo_root == project_root`.
2. Read the active scope, current branch, `git status --short`, and the relevant working-tree diff.
3. Build an explicit list of files changed for the authorized task.
4. Exclude unrelated user work, files from another project, credentials, private keys, `.env`, and `.env.*` except a deliberately created `.env.example`.
5. Run the checks required by the changed artifacts.

Stage with explicit paths only, using `git add -- <path>...`. Never use `git add -A`, `git add .`, `git add -u`, a repository-wide wildcard, or an unaudited interactive selection.

Before committing, read `git diff --cached --name-status` and prove every staged path belongs to the active task; run `git diff --cached --check`; read the complete staged diff; re-run the relevant verification; commit only when the staged set is isolated and verified.

### Pre-push and post-push gates

Before the first push: verify local authentication without exposing credentials; verify `origin`, the active branch, the local commit, and the intended GitHub owner and repository; query repository metadata and require private visibility; use `git ls-remote --heads origin` to confirm the user-created repository is empty; never force-push unless the user explicitly authorizes that exact destructive operation after reviewing its impact.

Push the verified branch and set upstream only after all gates pass. After push, read the remote branch commit with `git ls-remote origin refs/heads/<branch>` and require it to equal the local `HEAD`. Report success only after that equality is verified.

## Completion Checks

Before claiming a task complete, verify directly from current files:

- every agent-created Markdown note has the required frontmatter properties, ISO dates, and a non-empty tag list;
- no file under `raw-kb/user-provided/` was altered solely to add frontmatter;
- any commit or push passed the repository-root, staged-path, credential, private-visibility, remote, and remote-commit gates;
- every supplied and acquired source is in the matching provenance directory and registered in `raw-kb/SOURCES.md`, with paths and SHA-256 checksums matching the filesystem;
- no unregistered raw source has been used as evidence;
- the active pipeline's stage statuses match the latest explicit user decisions and their evidence gates;
- contradictions and open questions are visible;
- every changed artifact has been read back.
<!-- END HARNESS MANAGED: CORE_GOVERNANCE -->
