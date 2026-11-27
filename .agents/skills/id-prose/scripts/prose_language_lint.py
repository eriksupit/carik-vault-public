#!/usr/bin/env python3
"""Frozen-phrase advisory linter for Indonesian prose.

One tier only: the structural calque phrases in references/universal-calques.txt,
each of which is defective in any Indonesian text regardless of the project's
entities, setting, era, or genre. An optional project overlay may add phrases and
may revoke a core one with `!allow <phrase>`. A per-line `<!-- lint-ok: reason -->`
marker exempts its own line and nothing else.

Adopted upstream from file-over-app-film at commit 28a6f78 on 2026-09-22. The five
built-in regex rules that shipped with it (PROSES, BERDIRI, MEMIKUL, HARGA, and the
scene-unit rule) were NOT adopted: three carried closed noun lists whose own
comments conceded the ceiling, and the defect they targeted is an ontological
category error, which the Carik Charter classifies as Substance. Those rules live
as prose principles in writing-style/prose-writing-style.md instead.

Class B under the Carik Charter: this script ALWAYS exits 0. It reports; it never
blocks. A finding is a question, never a command.
"""

import sys
import re
from pathlib import Path

# Per-line exemption for a line that quotes a banned form on purpose — a rule
# table, a lesson entry citing the rejected wording. The reason after the colon
# is mandatory so the marker cannot be used as a silent mute.
LINT_SKIP = re.compile(r"<!--\s*lint-ok:\s*\S[^>]*-->")


def load_rules(skill_root: Path, custom_rules_path: str = None):
    banned_patterns = []

    # 1. Core: universal structural calques shipped with this skill.
    universal_file = skill_root / 'references' / 'universal-calques.txt'
    if universal_file.exists():
        with open(universal_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    banned_patterns.append(('CORE-SYNTAX', re.compile(rf'\b{re.escape(line)}\b', re.IGNORECASE)))

    # 2. Optional project overlay.
    overlay_file = None
    if custom_rules_path:
        overlay_file = Path(custom_rules_path)
    else:
        # Vault convention: <root>/writing-style/frasa-terlarang.txt
        vault_overlay = skill_root.parent.parent.parent / 'writing-style' / 'frasa-terlarang.txt'
        if vault_overlay.exists():
            overlay_file = vault_overlay

    if overlay_file and overlay_file.exists():
        with open(overlay_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('!allow '):
                        allowed_term = line[7:].strip()
                        banned_patterns = [p for p in banned_patterns if p[1].pattern != rf'\b{re.escape(allowed_term)}\b']
                    else:
                        banned_patterns.append(('PROJECT-DENY', re.compile(rf'\b{re.escape(line)}\b', re.IGNORECASE)))

    return banned_patterns


def lint_file(target_path: Path, patterns):
    if not target_path.exists():
        print(f'ADVISORY: file not found, nothing linted: {target_path}', file=sys.stderr)
        return 0

    violations = []
    in_code_fence = False

    with open(target_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f, start=1):
            stripped = line.strip()
            # Toggle fenced code block
            if stripped.startswith('```'):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence:
                continue

            # A document that teaches these rules has to quote what they forbid,
            # and a table row cannot be wrapped in a code fence without breaking
            # the table. One escape hatch, deliberately narrow: an HTML comment
            # carrying a stated reason exempts its own line and nothing else.
            if LINT_SKIP.search(line):
                continue

            for tier, pattern in patterns:
                match = pattern.search(line)
                if match:
                    violations.append((idx, tier, match.group(0), stripped))

    if violations:
        print(f'ADVISORY: {target_path} has {len(violations)} frozen-phrase finding(s):')
        for line_num, tier, matched, raw_line in violations:
            print(f'  [{tier}] Line {line_num}: "{matched}" in -> {raw_line}')
        print('  Each finding is a question, not a command. Override with '
              '<!-- lint-ok: reason --> on the line, or fix the phrase.')
    else:
        print(f'CLEAN: {target_path} ({len(patterns)} frozen-phrase rules loaded).')
    return 0


def main():
    if len(sys.argv) < 2:
        print('Usage: prose_language_lint.py <file_to_lint> [--rules=<custom_rules_file>]')
        sys.exit(0)

    target_file = Path(sys.argv[1])
    custom_rules = None
    for arg in sys.argv[2:]:
        if arg.startswith('--rules='):
            custom_rules = arg.split('=', 1)[1]

    skill_root = Path(__file__).resolve().parent.parent
    patterns = load_rules(skill_root, custom_rules)
    if not patterns:
        # Reporting boundary: state what was observed, conclude nothing that was
        # not. A Class B advisory that aborts the workflow over its own broken
        # install is still a blocker, and this layer is permitted none.
        print('ADVISORY: zero phrase rules loaded — references/universal-calques.txt is '
              'missing or empty, so this run checked nothing.', file=sys.stderr)
        sys.exit(0)
    lint_file(target_file, patterns)
    sys.exit(0)


if __name__ == '__main__':
    main()
