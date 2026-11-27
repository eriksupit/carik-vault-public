#!/usr/bin/env python3
"""Regression tests for the bootstrap handoff resolver contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("resolve_handoff.py")
GOAL = """## Goal

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


def run_resolver(root: Path, initial: str | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT), "--root", str(root)]
    if initial is not None:
        command.extend(["--initial-prompt", initial])
    return subprocess.run(command, text=True, capture_output=True, check=False)


class ResolveHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        (self.root / "handoff").mkdir()

    def write_pair(
        self,
        suffix: str = "project-2026-08-10-120000",
        *,
        initial_goal: str | None = GOAL,
        handoff_goal: str | None = GOAL,
        pairing_lines: list[str] | None = None,
        prose: str = "",
        bootstrap_lines: list[str] | None = None,
    ) -> tuple[Path, Path]:
        initial = self.root / "handoff" / f"INITIAL-PROMPT-{suffix}.txt"
        handoff = self.root / "handoff" / f"HANDOFF-{suffix}.md"
        if pairing_lines is None:
            pairing_lines = [f"Paired handoff: handoff/HANDOFF-{suffix}.md"]
        initial_parts = [*(pairing_lines or []), prose]
        if initial_goal is not None:
            initial_parts.append(initial_goal)
        if bootstrap_lines is not None:
            initial_parts.extend(["## Bootstrap Reading", *bootstrap_lines])
        initial.write_text("\n\n".join(part for part in initial_parts if part), encoding="utf-8")
        handoff_body = handoff_goal or "# Handoff without a goal\n"
        handoff.write_text(HANDOFF_FRONTMATTER + "\n" + handoff_body, encoding="utf-8")
        return initial, handoff

    def assert_passes(self, result: subprocess.CompletedProcess[str], initial: Path, handoff: Path) -> dict[str, object]:
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIs(payload["goal_match"], True)
        self.assertEqual(payload["initial_prompt"], str(initial.resolve()))
        self.assertEqual(payload["handoff"], str(handoff.resolve()))
        return payload

    def assert_fails(self, result: subprocess.CompletedProcess[str], error_fragment: str) -> None:
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(json.dumps({"error": error_fragment})[1:-1], result.stderr)

    def test_canonical_pair_passes(self) -> None:
        (self.root / "SCOPE.md").write_text("scope\n", encoding="utf-8")
        initial, handoff = self.write_pair(bootstrap_lines=["- Read `SCOPE.md`."])
        payload = self.assert_passes(run_resolver(self.root), initial, handoff)
        self.assertEqual(payload["bootstrap_files"], ["SCOPE.md"])

    def test_missing_initial_goal_fails(self) -> None:
        initial, _ = self.write_pair(initial_goal=None)
        result = run_resolver(self.root)
        self.assert_fails(result, f"missing ## Goal block in {initial.relative_to(self.root)}")

    def test_missing_handoff_goal_fails(self) -> None:
        _, handoff = self.write_pair(handoff_goal=None)
        result = run_resolver(self.root)
        self.assert_fails(result, f"missing ## Goal block in {handoff.relative_to(self.root)}")

    def test_session_goal_mismatch_fails(self) -> None:
        changed = GOAL.replace("Repair the package contract.", "Repair a different contract.")
        self.write_pair(handoff_goal=changed)
        self.assert_fails(run_resolver(self.root), "paired ## Goal blocks do not match exactly")

    def test_ultimate_goal_mismatch_fails(self) -> None:
        changed = GOAL.replace("Preserve reliable continuity.", "Preserve partial continuity.")
        self.write_pair(handoff_goal=changed)
        self.assert_fails(run_resolver(self.root), "paired ## Goal blocks do not match exactly")

    def test_linkage_mismatch_fails(self) -> None:
        changed = GOAL.replace("advances", "does not advance")
        self.write_pair(handoff_goal=changed)
        self.assert_fails(run_resolver(self.root), "paired ## Goal blocks do not match exactly")

    def test_matching_designated_pair_passes(self) -> None:
        initial, handoff = self.write_pair()
        self.assert_passes(run_resolver(self.root), initial, handoff)

    def test_duplicate_designated_pair_fields_fail(self) -> None:
        suffix = "duplicate-2026-08-10-120000"
        line = f"Paired handoff: handoff/HANDOFF-{suffix}.md"
        self.write_pair(suffix, pairing_lines=[line, line])
        self.assert_fails(run_resolver(self.root), "initial prompt declares more than one paired handoff")

    def test_designated_pair_suffix_mismatch_fails(self) -> None:
        suffix = "selected-2026-08-10-120000"
        other = "other-2026-08-10-120000"
        self.write_pair(suffix, pairing_lines=[f"Paired handoff: handoff/HANDOFF-{other}.md"])
        (self.root / "handoff" / f"HANDOFF-{other}.md").write_text(GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), "paired handoff suffix does not match initial prompt")

    def test_zero_pair_field_derives_legacy_suffix(self) -> None:
        initial, handoff = self.write_pair(pairing_lines=[])
        self.assert_passes(run_resolver(self.root), initial, handoff)

    def test_superseded_handoff_in_prose_is_ignored(self) -> None:
        prose = (
            "Warning: handoff/HANDOFF-old-2026-08-09-090000.md is superseded.\n"
            "History also mentions handoff/HANDOFF-older-2026-08-08-080000.md."
        )
        initial, handoff = self.write_pair(prose=prose)
        self.assert_passes(run_resolver(self.root), initial, handoff)

    def test_explicit_initial_prompt_selects_exact_pair(self) -> None:
        selected_initial, selected_handoff = self.write_pair("a-2026-08-10-120000")
        self.write_pair("z-2026-08-10-130000")
        relative = str(selected_initial.relative_to(self.root))
        self.assert_passes(run_resolver(self.root, relative), selected_initial, selected_handoff)

    def test_unsuffixed_initial_prompt_fails(self) -> None:
        initial = self.root / "handoff" / "INITIAL-PROMPT.txt"
        initial.write_text(GOAL, encoding="utf-8")
        result = run_resolver(self.root, "handoff/INITIAL-PROMPT.txt")
        self.assert_fails(result, f"missing or malformed initial prompt: {initial.resolve()}")

    def test_root_escape_fails(self) -> None:
        result = run_resolver(self.root, "../INITIAL-PROMPT-escape.txt")
        self.assert_fails(result, "unsafe initial prompt path: ../INITIAL-PROMPT-escape.txt")

    def test_missing_bootstrap_path_fails(self) -> None:
        self.write_pair(bootstrap_lines=["- Read `missing.md`."])
        self.assert_fails(run_resolver(self.root), "missing mandatory bootstrap file: missing.md")

    def test_duplicate_initial_goal_fails(self) -> None:
        conflicting = GOAL.replace("Repair the package contract.", "Conflicting session goal.")
        self.write_pair(initial_goal=GOAL + "\n" + conflicting)
        self.assert_fails(run_resolver(self.root), "expected exactly one ## Goal block in handoff/INITIAL-PROMPT-project-2026-08-10-120000.txt")

    def test_duplicate_handoff_goal_fails(self) -> None:
        conflicting = GOAL.replace("Repair the package contract.", "Conflicting session goal.")
        self.write_pair(handoff_goal=GOAL + "\n" + conflicting)
        self.assert_fails(run_resolver(self.root), "expected exactly one ## Goal block in handoff/HANDOFF-project-2026-08-10-120000.md")

    def test_goal_requires_all_three_labels(self) -> None:
        cases = {
            "Session Goal": GOAL.replace("- **Session Goal:** Repair the package contract.\n", ""),
            "Ultimate Goal": GOAL.replace("- **Ultimate Goal:** Preserve reliable continuity.\n", ""),
            "Linkage": GOAL.replace("- **Linkage:** The session goal advances the ultimate goal.\n", ""),
        }
        for label, invalid_goal in cases.items():
            with self.subTest(label=label):
                self.write_pair(initial_goal=invalid_goal, handoff_goal=invalid_goal)
                self.assert_fails(run_resolver(self.root), f"missing or duplicate {label} in handoff/INITIAL-PROMPT-project-2026-08-10-120000.txt")

    def test_duplicate_goal_label_fails(self) -> None:
        duplicate = GOAL.replace(
            "- **Ultimate Goal:** Preserve reliable continuity.",
            "- **Session Goal:** Duplicate.\n- **Ultimate Goal:** Preserve reliable continuity.",
        )
        self.write_pair(initial_goal=duplicate, handoff_goal=duplicate)
        self.assert_fails(run_resolver(self.root), "missing or duplicate Session Goal in handoff/INITIAL-PROMPT-project-2026-08-10-120000.txt")

    def test_multiline_pairing_field_fails(self) -> None:
        suffix = "multiline-2026-08-10-120000"
        self.write_pair(suffix, pairing_lines=[f"Paired handoff:\n\nhandoff/HANDOFF-{suffix}.md"])
        self.assert_fails(run_resolver(self.root), "malformed paired handoff field")

    def test_latest_symlinked_initial_prompt_escape_fails(self) -> None:
        suffix = "symlink-2026-08-10-120000"
        initial, _ = self.write_pair(suffix)
        external = Path(tempfile.mkstemp(prefix="external-initial-", suffix=".txt")[1])
        self.addCleanup(external.unlink, missing_ok=True)
        external.write_text(initial.read_text(encoding="utf-8"), encoding="utf-8")
        initial.unlink()
        initial.symlink_to(external)
        candidate = self.root.resolve() / "handoff" / initial.name
        self.assert_fails(run_resolver(self.root), f"path escapes project root: {candidate}")

    def test_in_root_symlinked_handoff_fails_cleanly(self) -> None:
        suffix = "handoff-alias-2026-08-10-120000"
        _, handoff = self.write_pair(suffix)
        target = self.root / handoff.name
        handoff.rename(target)
        handoff.symlink_to(target)
        alias = self.root.resolve() / handoff.relative_to(self.root)
        self.assert_fails(run_resolver(self.root), f"paired handoff must not be a symlink: {alias}")

    def test_missing_handoff_frontmatter_fails(self) -> None:
        _, handoff = self.write_pair()
        handoff.write_text(GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"missing YAML frontmatter in {handoff.relative_to(self.root)}")

    def test_invalid_handoff_frontmatter_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("date: 2026-08-10", "date: 10-08-2026", 1)
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"invalid date in {handoff.relative_to(self.root)}: 10-08-2026")

    def test_missing_handoff_frontmatter_property_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("status: active\n", "")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"missing frontmatter properties in {handoff.relative_to(self.root)}: status")

    def test_empty_handoff_tags_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("  - handoff\n  - test\n", "")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"tags must be a non-empty YAML list in {handoff.relative_to(self.root)}")

    def test_empty_quoted_frontmatter_scalar_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", 'title: ""')
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_comment_only_frontmatter_scalar_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", "title: # comment")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_basic_iso_date_without_hyphens_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("date: 2026-08-10", "date: 20260810", 1)
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"invalid date in {handoff.relative_to(self.root)}: 20260810")

    def test_malformed_inline_tags_fail(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("tags:\n  - handoff\n  - test", "tags: [,]")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"tags must be a non-empty YAML list in {handoff.relative_to(self.root)}")

    def test_null_inline_tags_fail(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("tags:\n  - handoff\n  - test", "tags: [null]")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"tags must be a non-empty YAML list in {handoff.relative_to(self.root)}")

    def test_iso_week_date_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("date: 2026-08-10", "date: 2026-W33-1", 1)
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"invalid date in {handoff.relative_to(self.root)}: 2026-W33-1")

    def test_in_root_symlinked_latest_prompt_fails_cleanly(self) -> None:
        suffix = "alias-2026-08-10-120000"
        initial, _ = self.write_pair(suffix)
        target = self.root / "handoff" / "target.txt"
        initial.rename(target)
        initial.symlink_to(target.name)
        candidate = self.root.resolve() / "handoff" / initial.name
        self.assert_fails(run_resolver(self.root), f"initial prompt must not be a symlink: {candidate}")

    def test_invalid_unknown_frontmatter_value_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("status: active", "status: active\nrogue: [unterminated")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"invalid YAML frontmatter in {handoff.relative_to(self.root)}")

    def test_invalid_frontmatter_keys_fail(self) -> None:
        for rogue in (": rogue", "- rogue: x", "bad\tkey: x"):
            with self.subTest(rogue=rogue):
                _, handoff = self.write_pair()
                invalid = HANDOFF_FRONTMATTER.replace("status: active", f"status: active\n{rogue}")
                handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
                self.assert_fails(run_resolver(self.root), f"invalid YAML frontmatter in {handoff.relative_to(self.root)}")

    def test_non_yaml_top_level_line_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("status: active", "status: active\nthis is not YAML")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"invalid YAML frontmatter in {handoff.relative_to(self.root)}")

    def test_plain_scalar_with_sequence_indicator_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", "title: - not-text")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_unsupported_indented_frontmatter_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", "title: Test Handoff\n  nested: invalid")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"invalid YAML frontmatter in {handoff.relative_to(self.root)}")

    def test_plain_scalar_with_colon_space_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", "title: Test: Handoff")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_invalid_double_quoted_escape_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", 'title: "bad\\q"')
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_unescaped_single_quote_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", "title: 'can't'")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_collection_frontmatter_text_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("title: Test Handoff", "title: [not, text]")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property title in {handoff.relative_to(self.root)}")

    def test_numeric_frontmatter_text_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("type: handoff", "type: 123")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"empty frontmatter property type in {handoff.relative_to(self.root)}")

    def test_inline_tags_followed_by_block_item_fail(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("tags:\n  - handoff\n  - test", "tags: [handoff]\n  - extra")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"tags must be a non-empty YAML list in {handoff.relative_to(self.root)}")

    def test_mapping_inline_tag_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("tags:\n  - handoff\n  - test", "tags: [key: value]")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"tags must be a non-empty YAML list in {handoff.relative_to(self.root)}")

    def test_malformed_block_tag_structure_fails(self) -> None:
        _, handoff = self.write_pair()
        invalid = HANDOFF_FRONTMATTER.replace("  - test", "  broken: value")
        handoff.write_text(invalid + "\n" + GOAL, encoding="utf-8")
        self.assert_fails(run_resolver(self.root), f"tags must be a non-empty YAML list in {handoff.relative_to(self.root)}")

    def test_parent_directory_shorthand_fails(self) -> None:
        self.write_pair(bootstrap_lines=["- Read `../../`."])
        self.assert_fails(run_resolver(self.root), "unsafe bootstrap path: ../../")

    def test_absolute_directory_shorthand_fails(self) -> None:
        self.write_pair(bootstrap_lines=["- Read `/tmp/`."])
        self.assert_fails(run_resolver(self.root), "unsafe bootstrap path: /tmp/")

    def test_missing_directory_shorthand_fails(self) -> None:
        self.write_pair(bootstrap_lines=["- Read `does-not-exist/`."])
        self.assert_fails(run_resolver(self.root), "missing mandatory bootstrap directory: does-not-exist/")

if __name__ == "__main__":
    unittest.main()
