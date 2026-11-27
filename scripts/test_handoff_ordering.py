#!/usr/bin/env python3
"""Regression: handoff suffixes order by date (+ optional HHMMSS), not by raw ASCII."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolver = load("resolve_handoff", ROOT / ".agents/skills/bootstrap/scripts/resolve_handoff.py")
store = load("governance_store", ROOT / "scripts/governance_store.py")

LEGACY = "carik-vault-public-2026-11-18-113000"
SLUG = "2026-11-24--adversarial-review"


def prompts(*suffixes: str) -> list[Path]:
    return [Path(f"handoff/INITIAL-PROMPT-{suffix}.txt") for suffix in suffixes]


class ResolverOrderingTest(unittest.TestCase):
    def test_slug_dated_newer_than_prefixed_legacy(self) -> None:
        newest = resolver.newest_initial_prompt(prompts(LEGACY, SLUG, "2026-11-23--release"))
        self.assertEqual(f"INITIAL-PROMPT-{SLUG}.txt", newest.name)

    def test_hhmmss_orders_same_day(self) -> None:
        newest = resolver.newest_initial_prompt(prompts("p-2026-11-24-090000", "a-2026-11-24-180000", "z-2026-11-23-235959"))
        self.assertEqual("INITIAL-PROMPT-a-2026-11-24-180000.txt", newest.name)

    def test_older_same_day_ties_do_not_block_newer_date(self) -> None:
        newest = resolver.newest_initial_prompt(prompts("2026-11-23--a", "2026-11-23--b", SLUG))
        self.assertEqual(f"INITIAL-PROMPT-{SLUG}.txt", newest.name)

    def test_same_day_without_time_is_refused(self) -> None:
        for pair in (("2026-11-24--a", "2026-11-24--b"), ("2026-11-24--a", "x-2026-11-24-120000"), ("a-2026-11-24-120000", "b-2026-11-24-120000")):
            with self.subTest(pair=pair), self.assertRaisesRegex(resolver.ResolutionError, "pass --initial-prompt explicitly"):
                resolver.newest_initial_prompt(prompts(*pair))

    def test_undated_suffix_is_refused(self) -> None:
        for bad in ("final", "2026-11-24-slug", "x-2026-11-24-1200", "2026-11-24-120000"):
            with self.subTest(bad=bad), self.assertRaisesRegex(resolver.ResolutionError, "matches neither"):
                resolver.newest_initial_prompt(prompts(bad, SLUG))

    def test_legacy_stamp_is_the_trailing_date_not_one_inside_the_prefix(self) -> None:
        self.assertEqual(("2026-11-24", "123000"), resolver.suffix_stamp("project-2026-10-01-2026-11-24-123000"))
        newest = resolver.newest_initial_prompt(prompts("project-2026-10-01-2026-11-24-123000", "2026-11-23--release"))
        self.assertEqual("INITIAL-PROMPT-project-2026-10-01-2026-11-24-123000.txt", newest.name)

    def test_out_of_range_clock_is_refused(self) -> None:
        for bad in ("p-2026-11-24-240000", "p-2026-11-24-126000", "p-2026-11-24-120060", "p-2026-02-30-120000"):
            with self.subTest(bad=bad), self.assertRaisesRegex(resolver.ResolutionError, "invalid date or time"):
                resolver.suffix_stamp(bad)


class ArchiveOrderingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.archive = self.root / "handoff/archived"
        self.archive.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def archive_pairs(self, *suffixes: str) -> None:
        for suffix in suffixes:
            (self.archive / f"HANDOFF-{suffix}.md").write_text("x", encoding="utf-8")
            (self.archive / f"INITIAL-PROMPT-{suffix}.txt").write_text("x", encoding="utf-8")

    def test_raw_entries_are_chronological_across_formats(self) -> None:
        self.archive_pairs(SLUG, LEGACY, "carik-vault-public-2026-11-17-231239", "2026-11-23--release")
        self.assertEqual(
            ["carik-vault-public-2026-11-17-231239", LEGACY, "2026-11-23--release", SLUG],
            store._raw_entries(self.root, "handoff"),
        )

    def test_compaction_cut_through_undecidable_day_is_refused(self) -> None:
        suffixes = [f"2026-01-{day:02d}--s" for day in range(1, 31)] + [f"2026-02-01--{i:02d}" for i in range(25)]
        self.archive_pairs(*suffixes)
        with self.assertRaises(store.StoreError) as caught:
            store.check_retention(self.root)
        self.assertEqual("AMBIGUOUS_HANDOFF_ORDER", caught.exception.code)

    def test_compaction_refuses_cut_inside_day_with_untimed_package(self) -> None:
        earlier = [f"p-2026-10-{day:02d}-080000" for day in range(1, 32)] + [f"p-2026-11-{day:02d}-080000" for day in range(1, 9)]
        split_day = ["2026-11-24--untimed", "p-2026-11-24-100000", "p-2026-11-24-120000"]
        later = [f"p-2026-12-{day:02d}-080000" for day in range(1, 20)]
        self.archive_pairs(*earlier, *split_day, *later)
        raw = store._raw_entries(self.root, "handoff")
        self.assertEqual(61, len(raw))
        cut = len(raw) - store.COMPACT_KEEP
        self.assertEqual(("p-2026-11-24-100000", "p-2026-11-24-120000"), (raw[cut - 1], raw[cut]))
        with self.assertRaises(store.StoreError) as caught:
            store.command_compact_archive(self.root, "handoff")
        self.assertEqual("AMBIGUOUS_HANDOFF_ORDER", caught.exception.code)
        self.assertEqual(61, len(store._raw_entries(self.root, "handoff")), "nothing may be compacted")

    def test_compaction_keeps_newest_by_date(self) -> None:
        suffixes = [f"p-2026-01-{day:02d}-120000" for day in range(1, 31)] + [f"2026-02-{day:02d}--s" for day in range(1, 26)]
        self.archive_pairs(*suffixes)
        store.command_compact_archive(self.root, "handoff")
        self.assertEqual(suffixes[-20:], store._raw_entries(self.root, "handoff"))


if __name__ == "__main__":
    unittest.main()
