#!/usr/bin/env python3
"""debate_forum_runner.py — Hermetic panel runner for the debate skill.

OMP kernel fast path (debate skill, Procedure step 2.A): compose a
multi-seat adversarial panel from `PanelSeat` + `DebateConfig`, format
hermetic zero-tool prompts, dispatch them in parallel through the eval
kernel's `completion()` API, parse each panelist's structured verdict, and
aggregate the positions into a moderator digest.

The module is stdlib-only and kernel-agnostic: the caller supplies the
`completion` callable (the kernel global) at dispatch time, so this file
stays importable and unit-testable outside the eval kernel.

Moderator duty is intentionally NOT automated: `synthesize_panel_positions`
only organizes panel output (severity buckets, theme frequency, consensus
signals). Weighing arguments and emitting the ONE final recommendation
remains the moderator's reasoned act per the debate skill.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = "1.0.0"

HERMETIC_RULE = (
    "PURE COGNITIVE EVALUATOR. DILARANG memanggil tool apa pun "
    "(read/grep/bash/edit/write/hub/task). Anda tidak punya akses filesystem: "
    "seluruh bahan audit (teks yang diaudit, batasan keras) sudah disertakan "
    "lengkap di bawah. Tidak ada riset tambahan yang diperlukan; nilai murni "
    "dari teks yang diberikan."
)

VERDICT_SCHEMA_HINT = """\
{
  "seat": "<nama seat persis seperti diberikan>",
  "verdict": "CONFORM | AMEND | REJECT",
  "summary": "1-2 kalimat ringkasan penilaian keseluruhan",
  "strengths": ["keunggulan yang benar-benar terbukti dalam teks"],
  "defects": [
    {
      "severity": "blocking | major | minor",
      "dimension": "aspek yang dilanggar / berisiko",
      "evidence": "kutipan spesifik dari teks audited atau rujukan aturan",
      "recommendation": "perbaikan konkret, bukan opini umum"
    }
  ],
  "conflicts": ["poin di mana perspektif seat lain kemungkinan berbeda pendapat"],
  "overall_recommendation": "satu rekomendasi utuh untuk moderator"
}
"""


@dataclass
class PanelSeat:
    """One discipline/expertise seat on the panel."""

    name: str
    discipline: str
    focus: str
    is_adversary: bool = False


@dataclass
class DebateConfig:
    """Framing shared by every seat of one debate."""

    problem: str
    audited_text: str
    hard_constraints: Sequence[str] = ()
    extra_context: Sequence[str] = field(default_factory=list)


def format_hermetic_prompt(seat: PanelSeat, config: DebateConfig) -> str:
    """Compose the self-contained zero-tool prompt for one panel seat."""
    role_tag = "DEVIL'S ADVOCATE / RED TEAM" if seat.is_adversary else "PANELIS DISIPLIN"
    lines: List[str] = [
        f"# {role_tag} — {seat.discipline}",
        "",
        f"**Seat name:** {seat.name}",
        "",
        HERMETIC_RULE,
        "",
        "## Masalah yang didebatkan",
        "",
        config.problem,
        "",
        "## Fokus seat Anda",
        "",
        seat.focus,
        "",
        "## Teks yang diaudit (lengkap, verbatim)",
        "",
        "```text",
        config.audited_text,
        "```",
        "",
        "## Batasan keras yang mengikat",
        "",
    ]
    for constraint in config.hard_constraints:
        lines.append(f"- {constraint}")
    if config.extra_context:
        lines.append("")
        lines.append("## Konteks tambahan")
        lines.append("")
        for item in config.extra_context:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Tugas",
            "",
            "Audit teks di atas dari perspektif disiplin Anda terhadap batasan keras dan ",
            "kualitas keunggulan mutlak. Cari setiap cara teks bisa salah, berlebihan, ",
            "bertentangan, atau tidak layak ditulis ke disk. Beri peringkat keparahan "
            "(blocking = harus diperbaiki sebelum penulisan; major = perlu amendemen; "
            "minor = saran penyempurnaan).",
            "",
            "## Format jawaban",
            "",
            "Kembalikan HANYA SATU objek JSON valid tanpa teks lain (tanpa markdown fence):",
            "",
            "```json",
            VERDICT_SCHEMA_HINT,
            "```",
            "",
            "Peringkat severity: `blocking` hanya untuk cacat yang membuat penulisan ke disk "
            "tidak layak sebelum diperbaiki. `evidence` wajib merujuk kutipan teks atau aturan "
            "konkret — opini tanpa bukti tidak dihitung.",
        ]
    )
    return "\n".join(lines)


def parse_panelist_response(raw: str, expected_seat: str) -> Dict[str, Any]:
    """Parse a panelist's raw output into a verdict dict.

    Accepts (1) a bare JSON object, (2) a fenced ```json block, or (3) the
    first balanced {...} region in the text. A seat-name mismatch is recorded
    in `_parse_warnings`, never silently corrected.
    """
    text = raw.strip()
    payload: Optional[str] = None
    candidates: List[str] = []

    if text.startswith("{"):
        candidates.append(text)
    for block in re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL):
        candidates.append(block)
    if not candidates:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        parsed.setdefault("_parse_warnings", [])
        seat_value = str(parsed.get("seat", "")).strip()
        if seat_value != expected_seat:
            parsed["_parse_warnings"].append(
                f"seat name mismatch: expected '{expected_seat}', got '{seat_value or '<empty>'}'"
            )
        parsed.setdefault("verdict", "UNPARSEABLE")
        return parsed

    raise ValueError(
        f"no JSON verdict object found in panelist response for seat '{expected_seat}'; "
        f"raw preview: {text[:300]!r}"
    )


def _severity_bucket(severity: str) -> str:
    key = severity.strip().lower()
    if key in {"blocking", "major", "minor"}:
        return key
    return "minor"  # unknown severity degrades to minor for counting


def synthesize_panel_positions(responses: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate parsed panelist verdicts into a moderator digest.

    Output is organizational only: per-seat verdicts, severity buckets,
    defect-dimension frequency, and consensus signals (same dimension flagged
    by >= 2 seats). The moderator weighs and decides; nothing here concludes.
    """
    verdicts: Dict[str, str] = {}
    buckets: Dict[str, List[Dict[str, Any]]] = {"blocking": [], "major": [], "minor": []}
    dimensions: List[str] = []
    warnings: List[str] = []
    summaries: Dict[str, str] = {}
    strengths: Dict[str, List[str]] = {}

    for response in responses:
        seat = str(response.get("seat") or response.get("_expected_seat") or "?")
        verdicts[seat] = str(response.get("verdict", "UNPARSEABLE"))
        summaries[seat] = str(response.get("summary", ""))
        strengths[seat] = [
            str(item) for item in response.get("strengths", []) if isinstance(item, str)
        ]
        for warning in response.get("_parse_warnings", []):
            warnings.append(f"{seat}: {warning}")
        for defect in response.get("defects", []):
            if not isinstance(defect, dict):
                continue
            severity = _severity_bucket(str(defect.get("severity", "minor")))
            entry = {
                "seat": seat,
                "severity": severity,
                "dimension": str(defect.get("dimension", "")).strip(),
                "evidence": str(defect.get("evidence", "")).strip(),
                "recommendation": str(defect.get("recommendation", "")).strip(),
            }
            buckets[severity].append(entry)
            if entry["dimension"]:
                dimensions.append(entry["dimension"].lower())

    theme_frequency: Dict[str, int] = {}
    for dimension in dimensions:
        theme_frequency[dimension] = theme_frequency.get(dimension, 0) + 1
    top_themes = sorted(theme_frequency.items(), key=lambda pair: (-pair[1], pair[0]))

    # Consensus signal: the same normalized dimension flagged (blocking or major)
    # by two or more distinct seats.
    cross_seat: Dict[str, set] = {}
    for entry in buckets["blocking"] + buckets["major"]:
        if entry["dimension"]:
            cross_seat.setdefault(entry["dimension"].lower(), set()).add(entry["seat"])
    consensus = [
        {"dimension": dimension, "seats": sorted(seat_set)}
        for dimension, seat_set in sorted(cross_seat.items())
        if len(seat_set) >= 2
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "seat_count": len(verdicts),
        "verdicts": verdicts,
        "summaries": summaries,
        "strengths": strengths,
        "buckets": buckets,
        "theme_frequency_top": top_themes,
        "consensus_signals": consensus,
        "parse_warnings": warnings,
    }


def dispatch_panel(
    seats: Sequence[PanelSeat],
    config: DebateConfig,
    completion: Callable[..., Any],
    model: str = "default",
    timeout: float = 120.0,
) -> List[Dict[str, Any]]:
    """Dispatch all seats in parallel via the kernel completion API and parse.

    `completion` is the eval-kernel global `completion(prompt, model=...)`
    returning a handle with `.wait(timeout=...)`. Unparseable responses are
    preserved with a `parse_error` marker instead of dropping the seat.
    """
    handles: Dict[str, Any] = {}
    for seat in seats:
        prompt = format_hermetic_prompt(seat, config)
        handles[seat.name] = completion(prompt, model=model)

    responses: List[Dict[str, Any]] = []
    for seat in seats:
        try:
            raw = str(handles[seat.name].wait(timeout=timeout))
        except Exception as exc:  # pragma: no cover - kernel handle failure
            responses.append(
                {
                    "seat": seat.name,
                    "verdict": "UNPARSEABLE",
                    "parse_error": f"wait failed: {exc}",
                    "_parse_warnings": [],
                }
            )
            continue
        try:
            parsed = parse_panelist_response(raw, expected_seat=seat.name)
        except ValueError as exc:
            parsed = {
                "seat": seat.name,
                "verdict": "UNPARSEABLE",
                "parse_error": str(exc),
                "_parse_warnings": [],
            }
        responses.append(parsed)
    return responses


def _cli_main(argv: List[str]) -> int:
    """CLI interface for debate_forum_runner in bash/eval environments."""
    import sys

    if len(argv) == 1:
        print(f"debate_forum_runner schema_version={SCHEMA_VERSION}")
        print("exports:", ", ".join(
            n for n in (
                "PanelSeat", "DebateConfig", "format_hermetic_prompt",
                "parse_panelist_response", "synthesize_panel_positions",
                "dispatch_panel",
            )
            if n in globals()
        ))
        return 0

    cmd = argv[1]
    if cmd == "synthesize":
        source = sys.stdin.read() if len(argv) <= 2 else open(argv[2], "r", encoding="utf-8").read()
        raw_list = json.loads(source)
        if not isinstance(raw_list, list):
            raise ValueError("Input for 'synthesize' must be a JSON array of parsed responses.")
        digest = synthesize_panel_positions(raw_list)
        print(json.dumps(digest, indent=2, ensure_ascii=False))
        return 0

    if cmd == "parse":
        if len(argv) < 3:
            print("Usage: debate_forum_runner.py parse <seat_name> [response_file]", file=sys.stderr)
            return 1
        seat_name = argv[2]
        raw_text = sys.stdin.read() if len(argv) <= 3 else open(argv[3], "r", encoding="utf-8").read()
        parsed = parse_panelist_response(raw_text, expected_seat=seat_name)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
        return 0

    print(f"Unknown subcommand: {cmd}. Available: synthesize, parse", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    import sys

    sys.exit(_cli_main(sys.argv))
