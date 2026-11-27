#!/usr/bin/env python3
"""Executable contract for the governance continuity store."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


SCRIPT = Path(__file__).with_name("governance_store.py")
HANDOFF_PROMPT_RE = re.compile(r"^INITIAL-PROMPT-([A-Za-z0-9][A-Za-z0-9._-]*)\.txt$")
HANDOFF_FILE_RE = re.compile(r"^HANDOFF-([A-Za-z0-9][A-Za-z0-9._-]*)\.md$")
ROOT = SCRIPT.parents[1]
INITIALIZER = ROOT / ".agents/skills/file-over-app-init/scripts/init_vault.py"
# A Carik vault bundles no `bootstrap` skill; it runs the user-global copy, which is the
# resolver closure-procedure and handoff invoke. Prefer a vault-local copy when present.
RESOLVER = next(
    (p for p in (ROOT / ".agents/skills/bootstrap/scripts/resolve_handoff.py",
                 Path.home() / ".agents/skills/bootstrap/scripts/resolve_handoff.py") if p.is_file()),
    ROOT / ".agents/skills/bootstrap/scripts/resolve_handoff.py",
)
HANDOFF_GOAL = """## Goal

- **Session Goal:** Repair the package contract.
- **Ultimate Goal:** Preserve reliable continuity.
- **Linkage:** The session goal advances the ultimate goal.
"""
HANDOFF_FRONTMATTER = """---
title: Test Handoff
date: 2026-08-10
updated: 2026-08-10
type: handoff
status: active
tags:
  - handoff
  - test
---
"""
ARCHIVE_INDEX = """---
title: Archived Handoff Pairs
date: 2026-08-11
updated: 2026-08-11
type: documentation
status: active
tags:
  - test
---

# Archived Handoff Pairs

## Arsip

"""
BASE = """---
title: {title}
date: 2026-08-11
updated: 2026-08-11
type: {kind}
status: active
tags:
  - test
---

"""


class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".agents/memory").mkdir(parents=True)
        (self.root / ".agents/Context.md").write_text(BASE.format(title="Context", kind="context") + "# Context\n", encoding="utf-8")
        (self.root / ".agents/Lessons.md").write_text(BASE.format(title="Lessons", kind="lessons") + "# Lessons\n", encoding="utf-8")
        (self.root / ".agents/Memory.md").write_text(BASE.format(title="Memory", kind="memory") + "# Memory\n\n## Active facts\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["python3", str(SCRIPT), *args, "--root", str(self.root)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def fact(self, slug: str, *, fact_id: str | None = None, status: str = "active", key: str = "policy", supersedes: str = "", superseded_by: str = "") -> Path:
        path = self.root / ".agents/memory" / f"{slug}.md"
        extra = f"fact_id: {fact_id or slug}\nscope: core\nstage: all\nfact_key: {key}\neffective: 2026-08-11\nsource:\n  - .agents/Context.md\nsupersedes: [{supersedes}]\nsuperseded_by: {superseded_by}\n"
        text = BASE.format(title=slug, kind="memory-fact").replace("status: active\n", f"status: {status}\n" + extra) + f"# {slug}\n\nDescription for {slug}.\n"
        path.write_text(text, encoding="utf-8")
        return path

    def set_memory_updated(self, value: str) -> str:
        path = self.root / ".agents/Memory.md"
        before = path.read_text(encoding="utf-8")
        after = re.sub(r"^updated: .*$", f"updated: {value}", before, count=1, flags=re.M)
        changed = [pair for pair in zip(before.splitlines(), after.splitlines()) if pair[0] != pair[1]]
        self.assertEqual(len(changed), 1, f"expected exactly one changed line, got {changed}")
        path.write_text(after, encoding="utf-8")
        return after

    def memory_updated(self) -> str:
        match = re.search(r"^updated: (.+)$", (self.root / ".agents/Memory.md").read_text(encoding="utf-8"), re.M)
        assert match is not None
        return match.group(1).strip()

    def test_check_passes_when_only_the_stored_date_is_old(self) -> None:
        self.fact("current")
        self.cli("refresh-memory")
        self.set_memory_updated("2020-01-01")
        self.cli("check")

    def test_refresh_preserves_stored_date_when_facts_unchanged(self) -> None:
        self.fact("current")
        self.cli("refresh-memory")
        before = self.set_memory_updated("2020-01-01").encode("utf-8")
        self.cli("refresh-memory")
        self.assertEqual(before, (self.root / ".agents/Memory.md").read_bytes())
        self.assertEqual("2020-01-01", self.memory_updated())

    def test_refresh_stamps_today_when_the_fact_list_changes(self) -> None:
        self.fact("current")
        self.cli("refresh-memory")
        self.set_memory_updated("2020-01-01")
        self.fact("second", key="other")
        self.cli("refresh-memory")
        today = date.today()
        recent = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
        self.assertIn(self.memory_updated(), recent)
        self.cli("check")

    def test_refresh_is_deterministic_and_check_is_read_only(self) -> None:
        self.fact("current")
        self.cli("refresh-memory")
        first = (self.root / ".agents/Memory.md").read_bytes()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.cli("refresh-memory")
        self.cli("check")
        self.assertEqual(first, (self.root / ".agents/Memory.md").read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_conflict_and_bad_lineage_fail(self) -> None:
        self.fact("one", key="same")
        self.fact("two", key="same")
        self.assertIn("ACTIVE_SLOT_CONFLICT", self.cli("check", ok=False).stdout)
        (self.root / ".agents/memory/two.md").unlink()
        self.fact("old", status="superseded", key="old", superseded_by="missing")
        self.assertIn("DANGLING_SUCCESSOR", self.cli("check", ok=False).stdout)

    def test_duplicate_id_and_cycle_fail(self) -> None:
        self.fact("one", fact_id="duplicate", key="one")
        self.fact("two", fact_id="duplicate", key="two")
        self.assertIn("DUPLICATE_FACT_ID", self.cli("check", ok=False).stdout)
        for path in (self.root / ".agents/memory").glob("*.md"):
            path.unlink()
        self.fact("one", status="superseded", key="one", supersedes="two", superseded_by="two")
        self.fact("two", status="superseded", key="two", supersedes="one", superseded_by="one")
        self.assertIn("SUPERSESSION_CYCLE", self.cli("check", ok=False).stdout)

    def test_valid_supersession_refreshes_only_active_fact(self) -> None:
        self.fact("old", status="superseded", key="policy", superseded_by="new")
        self.fact("new", key="policy", supersedes="old")
        self.cli("refresh-memory")
        memory = (self.root / ".agents/Memory.md").read_text(encoding="utf-8")
        self.assertIn("[[memory/new|new]]", memory)
        self.assertNotIn("memory/old", memory)
        self.cli("check")

    def test_rotation_is_lossless_and_retains_thirty(self) -> None:
        self.cli("refresh-memory")
        context = self.root / ".agents/Context.md"
        entries = "".join(f"\n## 2026-08-11 — Entry {n:03d}\n\nBody {n}.\n" for n in range(105))
        context.write_text(BASE.format(title="Context", kind="context") + "# Context\n" + entries, encoding="utf-8")
        lessons_before = (self.root / ".agents/Lessons.md").read_bytes()
        self.cli("rotate-anchors", "--timestamp", "20260811T120000")
        archive = self.root / ".agents/archive/context/Context.20260811T120000.md"
        self.assertTrue(archive.is_file())
        self.assertEqual(30, (self.root / ".agents/Context.md").read_text().count("\n## 2026-"))
        self.assertEqual(75, archive.read_text().count("\n## 2026-"))
        self.assertEqual(lessons_before, (self.root / ".agents/Lessons.md").read_bytes())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertIn(digest, (self.root / ".agents/Context.md").read_text())
        self.cli("check")
        archive.write_text(archive.read_text() + "tamper", encoding="utf-8")
        self.assertIn("ARCHIVE_CHECKSUM_MISMATCH", self.cli("check", ok=False).stdout)

    def test_oversized_unrotatable_window_fails_without_mutation(self) -> None:
        context = self.root / ".agents/Context.md"
        entries = "".join(f"\n## 2026-08-11 — Huge {n}\n\n" + ("x" * 2300) for n in range(31))
        context.write_text(context.read_text() + entries, encoding="utf-8")
        before = context.read_bytes()
        self.assertIn("OVERSIZED_ACTIVE_WINDOW", self.cli("rotate-anchors", ok=False).stdout)
        self.assertEqual(before, context.read_bytes())
        self.assertFalse((self.root / ".agents/archive/context").exists())

    def test_check_rejects_anchor_without_frontmatter_or_fields(self) -> None:
        self.cli("refresh-memory")
        lessons = self.root / ".agents/Lessons.md"
        lessons.write_text("# Broken anchor\n## [2026-11-18] Test\nMissing frontmatter\n", encoding="utf-8")
        self.assertIn("INVALID_FRONTMATTER", self.cli("check", ok=False).stdout)
        lessons.write_text("---\ntitle: Lessons\n---\n# Lessons\n", encoding="utf-8")
        self.assertIn("MISSING_ANCHOR_FIELD", self.cli("check", ok=False).stdout)

    @unittest.skipUnless(INITIALIZER.is_file(), "harness file-over-app-init initializer not shipped; "
                         "the Carik initializer scripts/spawn_vault.py is gated in test_spawn_vault.py")
    def test_initializer_projects_sterile_store(self) -> None:
        source = self.root / "source"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", ".worktrees"))
        target = self.root / "generated"
        result = subprocess.run(
            [
                "python3", str(source / INITIALIZER.relative_to(ROOT)),
                "--source", str(source), "--target", str(target),
                "--project-name", "Sterile", "--profile", "agentic-product",
            ],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue((target / "scripts/governance_store.py").is_file())
        self.assertTrue((target / "docs/design/README.md").is_file())
        self.assertEqual(["README.md"], [p.name for p in (target / "docs/design").iterdir()])
        self.assertEqual([], list((target / ".agents/memory").glob("*.md")))
        self.assertNotIn("film-only-files-over-app", (target / ".agents/Memory.md").read_text())


DESIGN_BASE = """---
title: {title}
date: 2026-08-11
updated: 2026-08-11
type: design
status: {status}
tags:
  - test
---

# {title}
"""
PLAN_BASE = """---
title: {title}
date: 2026-08-11
updated: 2026-08-11
type: implementation-plan
status: {status}
tags:
  - test
---

# {title}

**Approved design:** [{title}](../design/{design_name}.md)
"""


class ArchiveDocsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".agents/memory").mkdir(parents=True)
        (self.root / ".agents/Context.md").write_text(BASE.format(title="Context", kind="context") + "# Context\n", encoding="utf-8")
        (self.root / ".agents/Lessons.md").write_text(BASE.format(title="Lessons", kind="lessons") + "# Lessons\n", encoding="utf-8")
        (self.root / ".agents/Memory.md").write_text(BASE.format(title="Memory", kind="memory") + "# Memory\n\n## Active facts\n", encoding="utf-8")
        (self.root / "docs/design").mkdir(parents=True)
        (self.root / "docs/plans").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["python3", str(SCRIPT), *args, "--root", str(self.root)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def write_pair(self, design_name: str, plan_name: str, *, design_status: str = "approved", plan_status: str = "completed") -> tuple[Path, Path]:
        design = self.root / "docs/design" / f"{design_name}.md"
        plan = self.root / "docs/plans" / f"{plan_name}.md"
        design.write_text(DESIGN_BASE.format(title=design_name, status=design_status), encoding="utf-8")
        plan.write_text(PLAN_BASE.format(title=plan_name, status=plan_status, design_name=design_name), encoding="utf-8")
        return design, plan

    def fact_citing(self, slug: str, design_source: str, plan_source: str) -> Path:
        path = self.root / ".agents/memory" / f"{slug}.md"
        text = f"""---
title: {slug}
date: 2026-08-11
updated: 2026-08-11
type: memory-fact
status: active
tags:
  - test
fact_id: {slug}
scope: core
stage: all
fact_key: {slug}
effective: 2026-08-11
source:
  - {design_source}
  - {plan_source}
supersedes: []
superseded_by:
---

# {slug}

Description.
"""
        path.write_text(text, encoding="utf-8")
        return path

    def test_eligible_pair_is_archived_with_rewritten_links(self) -> None:
        self.write_pair("2026-08-11-alpha", "2026-08-11-alpha-implementation")
        self.cli("archive-docs")
        self.assertFalse((self.root / "docs/design/2026-08-11-alpha.md").exists())
        self.assertFalse((self.root / "docs/plans/2026-08-11-alpha-implementation.md").exists())
        design_archived = self.root / "docs/design/archived/2026-08-11-alpha.md"
        plan_archived = self.root / "docs/plans/archived/2026-08-11-alpha-implementation.md"
        self.assertTrue(design_archived.is_file())
        self.assertTrue(plan_archived.is_file())
        self.assertIn("](../../design/archived/2026-08-11-alpha.md)", plan_archived.read_text(encoding="utf-8"))
        design_index = (self.root / "docs/design/archived/README.md").read_text(encoding="utf-8")
        plan_index = (self.root / "docs/plans/archived/README.md").read_text(encoding="utf-8")
        self.assertIn("2026-08-11-alpha-implementation", design_index)
        self.assertIn(hashlib.sha256(design_archived.read_bytes()).hexdigest(), design_index)
        self.assertIn(hashlib.sha256(plan_archived.read_bytes()).hexdigest(), plan_index)

    def test_ineligible_pairs_left_untouched(self) -> None:
        self.write_pair("2026-08-11-beta", "2026-08-11-beta-implementation", plan_status="review")
        self.write_pair("2026-08-11-gamma", "2026-08-11-gamma-implementation", design_status="review")
        self.cli("archive-docs")
        self.assertTrue((self.root / "docs/design/2026-08-11-beta.md").exists())
        self.assertTrue((self.root / "docs/plans/2026-08-11-beta-implementation.md").exists())
        self.assertTrue((self.root / "docs/design/2026-08-11-gamma.md").exists())
        self.assertTrue((self.root / "docs/plans/2026-08-11-gamma-implementation.md").exists())

    def test_idempotent_second_run(self) -> None:
        self.write_pair("2026-08-11-delta", "2026-08-11-delta-implementation")
        self.cli("archive-docs")
        index_after_first = (self.root / "docs/design/archived/README.md").read_bytes()
        self.cli("archive-docs")
        self.assertEqual(index_after_first, (self.root / "docs/design/archived/README.md").read_bytes())

    def test_exclusion_set_ships_empty(self) -> None:
        # The harness is domain-neutral: the escape hatch exists for consumers, but this
        # repository must never carry a consumer's document stem. Guards against a future
        # re-sync from a derived harness silently reintroducing one.
        namespace: dict = {}
        exec(  # noqa: S102 - reading a constant without importing the module's __main__ path
            next(
                line for line in SCRIPT.read_text(encoding="utf-8").splitlines()
                if line.startswith("DOC_ARCHIVE_EXCLUDED_STEMS")
            ),
            namespace,
        )
        self.assertEqual(set(), namespace["DOC_ARCHIVE_EXCLUDED_STEMS"])

    def test_pointer_resolves_design_with_unrelated_slug(self) -> None:
        # This harness pairs plans and designs whose slugs differ entirely, so the
        # explicit pointer — not stem derivation — must drive resolution.
        design = self.root / "docs/design/2026-08-11-canonical-sync-and-validation.md"
        plan = self.root / "docs/plans/2026-08-11-store-remediation-implementation-plan.md"
        design.write_text(DESIGN_BASE.format(title="canonical-sync", status="approved"), encoding="utf-8")
        plan.write_text(
            PLAN_BASE.format(title="store-remediation", status="completed", design_name="ignored")
            .replace(
                "**Approved design:** [store-remediation](../design/ignored.md)",
                "**Approved Design:** `docs/design/2026-08-11-canonical-sync-and-validation.md`",
            ),
            encoding="utf-8",
        )
        self.cli("archive-docs")
        self.assertFalse(plan.exists())
        self.assertFalse(design.exists())
        self.assertTrue((self.root / "docs/plans/archived" / plan.name).is_file())
        self.assertTrue((self.root / "docs/design/archived" / design.name).is_file())

    def test_unresolved_design_raises(self) -> None:
        plan = self.root / "docs/plans/2026-08-11-orphan-implementation.md"
        plan.write_text(PLAN_BASE.format(title="orphan", status="completed", design_name="does-not-exist"), encoding="utf-8")
        result = self.cli("archive-docs", ok=False)
        self.assertIn("UNRESOLVED_DESIGN_PAIR", result.stdout)

    def test_fact_citing_archived_pair_still_validates(self) -> None:
        self.write_pair("2026-08-11-epsilon", "2026-08-11-epsilon-implementation")
        self.fact_citing("epsilon-fact", "docs/design/2026-08-11-epsilon.md", "docs/plans/2026-08-11-epsilon-implementation.md")
        self.cli("archive-docs")
        self.cli("refresh-memory")
        self.cli("check")

    def test_fact_citing_missing_source_still_fails(self) -> None:
        self.fact_citing("zeta-fact", "docs/design/2026-08-11-does-not-exist.md", "docs/plans/2026-08-11-also-missing-implementation.md")
        result = self.cli("check", ok=False)
        self.assertIn("MISSING_SOURCE", result.stdout)

    def test_archive_index_rotates_past_threshold(self) -> None:
        design_rows = "\n".join(f"- `old-plan-{n:03d}` — archived 2026-08-11 — DESIGN SHA-256 `{'0' * 64}`" for n in range(101))
        (self.root / "docs/design/archived").mkdir(parents=True)
        (self.root / "docs/design/archived/README.md").write_text(ARCHIVE_INDEX + design_rows + "\n", encoding="utf-8")
        self.write_pair("2026-08-11-theta", "2026-08-11-theta-implementation")
        self.cli("archive-docs", "--timestamp", "20260811T200000")
        sub_index = self.root / "docs/design/archived/index-20260811T200000.md"
        self.assertTrue(sub_index.is_file())
        index = (self.root / "docs/design/archived/README.md").read_text(encoding="utf-8")
        self.assertEqual(29, index.count("- `old-plan-"))
        self.assertIn("2026-08-11-theta-implementation", index)


class RetentionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".agents/memory").mkdir(parents=True)
        (self.root / ".agents/Context.md").write_text(BASE.format(title="Context", kind="context") + "# Context\n", encoding="utf-8")
        (self.root / ".agents/Lessons.md").write_text(BASE.format(title="Lessons", kind="lessons") + "# Lessons\n", encoding="utf-8")
        (self.root / ".agents/Memory.md").write_text(BASE.format(title="Memory", kind="memory") + "# Memory\n\n## Active facts\n", encoding="utf-8")
        (self.root / "handoff/archived").mkdir(parents=True)
        (self.root / "docs/design/archived").mkdir(parents=True)
        (self.root / "docs/plans/archived").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["python3", str(SCRIPT), *args, "--root", str(self.root)], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def make_handoff_pairs(self, n: int, prefix: str = "2026-01-01") -> None:
        for i in range(n):
            suffix = f"project-{prefix}-{i:06d}"
            (self.root / f"handoff/archived/HANDOFF-{suffix}.md").write_text(HANDOFF_FRONTMATTER + "\n" + HANDOFF_GOAL, encoding="utf-8")
            (self.root / f"handoff/archived/INITIAL-PROMPT-{suffix}.txt").write_text(f"Paired handoff: handoff/HANDOFF-{suffix}.md\n\n{HANDOFF_GOAL}", encoding="utf-8")

    def make_design_docs(self, n: int, prefix: str = "2026-01-01") -> None:
        for i in range(n):
            name = f"{prefix}-doc-{i:03d}"
            (self.root / f"docs/design/archived/{name}.md").write_text(DESIGN_BASE.format(title=name, status="approved"), encoding="utf-8")

    def test_dormant_at_real_current_volumes(self) -> None:
        self.make_handoff_pairs(16)
        self.make_design_docs(10)
        result = self.cli("check-retention")
        self.assertEqual("OK check-retention", result.stdout.strip())

    def test_compaction_eligible_above_threshold(self) -> None:
        self.make_handoff_pairs(60)
        result = self.cli("check-retention")
        self.assertIn("RETENTION handoff compact eligible=40", result.stdout)

    def test_compact_archive_writes_log_and_deletes_raw(self) -> None:
        self.make_handoff_pairs(60)
        self.cli("compact-archive", "--location", "handoff")
        remaining = [p for p in (self.root / "handoff/archived").iterdir() if p.is_file() and (HANDOFF_PROMPT_RE.fullmatch(p.name) or HANDOFF_FILE_RE.fullmatch(p.name))]
        self.assertEqual(40, len(remaining))  # 20 pairs = 40 files
        log = (self.root / "handoff/archived/COMPACTION-LOG.md").read_text(encoding="utf-8")
        self.assertEqual(40, log.count("— SHA-256 `"))
        self.assertIn("2026-01-01-000000", log)  # oldest of the 40 compacted (indices 0-39)
        self.assertNotIn("2026-01-01-000059", log)  # newest of the 20 retained raw (indices 40-59), never logged
        self.assertIn("2026-01-01-000059", "".join(p.name for p in (self.root / "handoff/archived").iterdir()))

    def test_compact_archive_idempotent(self) -> None:
        self.make_handoff_pairs(60)
        self.cli("compact-archive", "--location", "handoff")
        log_after_first = (self.root / "handoff/archived/COMPACTION-LOG.md").read_bytes()
        self.cli("compact-archive", "--location", "handoff")
        self.assertEqual(log_after_first, (self.root / "handoff/archived/COMPACTION-LOG.md").read_bytes())

    def test_compact_archive_below_threshold_is_noop(self) -> None:
        self.make_handoff_pairs(16)
        self.cli("compact-archive", "--location", "handoff")
        self.assertFalse((self.root / "handoff/archived/COMPACTION-LOG.md").exists())

    def test_prune_archive_dormant_under_total_threshold(self) -> None:
        self.make_handoff_pairs(60)
        self.cli("compact-archive", "--location", "handoff")
        log_before = (self.root / "handoff/archived/COMPACTION-LOG.md").read_bytes()
        self.cli("prune-archive", "--location", "handoff")
        self.assertEqual(log_before, (self.root / "handoff/archived/COMPACTION-LOG.md").read_bytes())

    def test_invalid_location_rejected_by_cli(self) -> None:
        self.make_handoff_pairs(1)
        result = self.cli("compact-archive", "--location", "bogus", ok=False)
        self.assertNotEqual(0, result.returncode)

    def test_missing_location_flag_rejected(self) -> None:
        self.make_handoff_pairs(1)
        result = self.cli("compact-archive", ok=False)
        self.assertIn("--location is required", result.stdout)


@unittest.skipUnless(RESOLVER.is_file(), "bootstrap resolve_handoff.py not installed")
class ArchiveHandoffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / ".agents/memory").mkdir(parents=True)
        (self.root / ".agents/Context.md").write_text(BASE.format(title="Context", kind="context") + "# Context\n", encoding="utf-8")
        (self.root / ".agents/Lessons.md").write_text(BASE.format(title="Lessons", kind="lessons") + "# Lessons\n", encoding="utf-8")
        (self.root / ".agents/Memory.md").write_text(BASE.format(title="Memory", kind="memory") + "# Memory\n\n## Active facts\n", encoding="utf-8")
        resolver_dir = self.root / ".agents/skills/bootstrap/scripts"
        resolver_dir.mkdir(parents=True)
        shutil.copy(RESOLVER, resolver_dir / "resolve_handoff.py")
        (self.root / "handoff").mkdir()
        (self.root / "handoff/archived").mkdir()
        (self.root / "handoff/archived/README.md").write_text(ARCHIVE_INDEX, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["python3", str(SCRIPT), *args, "--root", str(self.root)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def write_pair(self, suffix: str) -> tuple[Path, Path]:
        initial = self.root / "handoff" / f"INITIAL-PROMPT-{suffix}.txt"
        handoff = self.root / "handoff" / f"HANDOFF-{suffix}.md"
        initial.write_text(f"Paired handoff: handoff/HANDOFF-{suffix}.md\n\n{HANDOFF_GOAL}", encoding="utf-8")
        handoff.write_text(HANDOFF_FRONTMATTER + "\n" + HANDOFF_GOAL, encoding="utf-8")
        return initial, handoff

    def test_noop_with_single_pair(self) -> None:
        self.write_pair("project-2026-08-10-090000")
        self.cli("archive-handoff")
        self.assertEqual(2, len([p for p in (self.root / "handoff").iterdir() if p.is_file()]))
        self.assertEqual([], list((self.root / "handoff/archived").glob("HANDOFF-*.md")))

    def test_archives_all_but_the_newest_pair(self) -> None:
        self.write_pair("project-2026-08-10-090000")
        self.write_pair("project-2026-08-10-100000")
        self.write_pair("project-2026-08-11-184500")
        self.cli("archive-handoff")

        top_level = [p.name for p in (self.root / "handoff").iterdir() if p.is_file()]
        self.assertEqual({"INITIAL-PROMPT-project-2026-08-11-184500.txt", "HANDOFF-project-2026-08-11-184500.md"}, set(top_level))

        archived = [p.name for p in (self.root / "handoff/archived").iterdir() if p.is_file() and p.name != "README.md"]
        self.assertEqual(
            {
                "INITIAL-PROMPT-project-2026-08-10-090000.txt", "HANDOFF-project-2026-08-10-090000.md",
                "INITIAL-PROMPT-project-2026-08-10-100000.txt", "HANDOFF-project-2026-08-10-100000.md",
            },
            set(archived),
        )

        index = (self.root / "handoff/archived/README.md").read_text(encoding="utf-8")
        self.assertIn("project-2026-08-10-090000", index)
        self.assertIn("project-2026-08-10-100000", index)
        for path in (self.root / "handoff/archived").glob("HANDOFF-*.md"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertIn(digest, index)
        for path in (self.root / "handoff/archived").glob("INITIAL-PROMPT-*.txt"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertIn(digest, index)

    def test_idempotent_second_run_is_a_noop(self) -> None:
        self.write_pair("project-2026-08-10-090000")
        self.write_pair("project-2026-08-11-184500")
        self.cli("archive-handoff")
        index_after_first = (self.root / "handoff/archived/README.md").read_bytes()
        self.cli("archive-handoff")
        self.assertEqual(index_after_first, (self.root / "handoff/archived/README.md").read_bytes())

    def test_resolver_still_resolves_after_archiving(self) -> None:
        self.write_pair("project-2026-08-10-090000")
        self.write_pair("project-2026-08-11-184500")
        self.cli("archive-handoff")
        result = subprocess.run(
            ["python3", str(self.root / ".agents/skills/bootstrap/scripts/resolve_handoff.py"), "--root", str(self.root)],
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        import json
        data = json.loads(result.stdout)
        self.assertTrue(data["initial_prompt"].endswith("project-2026-08-11-184500.txt"))
        self.assertTrue(data["goal_match"])

    def test_archive_index_rotates_past_threshold(self) -> None:
        rows = "\n".join(f"- `old-{n:03d}` — archived 2026-08-11 — HANDOFF SHA-256 `{'0' * 64}`; INITIAL-PROMPT SHA-256 `{'0' * 64}`" for n in range(101))
        (self.root / "handoff/archived/README.md").write_text(ARCHIVE_INDEX + rows + "\n", encoding="utf-8")
        self.write_pair("project-2026-08-10-090000")
        self.write_pair("project-2026-08-11-184500")
        self.cli("archive-handoff", "--timestamp", "20260811T190000")
        sub_index = self.root / "handoff/archived/index-20260811T190000.md"
        self.assertTrue(sub_index.is_file())
        index = (self.root / "handoff/archived/README.md").read_text(encoding="utf-8")
        self.assertEqual(29, index.count("- `old-"))
        self.assertIn("project-2026-08-10-090000", index)

    def test_unpaired_handoff_fails_closed(self) -> None:
        initial, handoff = self.write_pair("project-2026-08-10-090000")
        self.write_pair("project-2026-08-11-184500")
        handoff.unlink()
        self.assertIn("UNPAIRED_HANDOFF", self.cli("archive-handoff", ok=False).stdout)


if __name__ == "__main__":
    unittest.main()
