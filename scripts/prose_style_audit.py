#!/usr/bin/env python3
"""Flag sentence rhythm and lexical repetition for manual prose review."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path


STOPWORDS = {
    "ada", "agar", "akan", "atau", "bagi", "bahwa", "dalam", "dan", "dari",
    "dengan", "di", "ia", "ini", "itu", "juga", "karena", "ke", "ketika",
    "lalu", "maka", "melalui", "mereka", "namun", "oleh", "pada", "para",
    "pun", "saat", "salah", "satu", "sebagai", "sebelum", "sedangkan",
    "setelah", "serta", "tanpa", "telah", "tetapi", "tidak", "untuk", "yang",
}
WATCHED_NEARBY = {"sebuah", "suatu", "itu", "tersebut"}
ROOT_EXCLUSIONS = {"dapat"}
PREFIXES = ("meng", "peng", "meny", "peny", "mem", "pem", "men", "pen", "per", "ber", "ter", "di", "ke", "se")
SUFFIXES = ("kan", "an", "nya", "i")
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-–][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)*")
SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?](?=\s|$)|$)")
META_REPORT = re.compile(
    r"\b(?:dokumen|teks|tulisan|laporan|artikel|cerita|narasi|pembaca)\b[^.!?]{0,30}"
    r"\b(?:kembali|berakhir|dimulai|membuka|menutup|memperlihatkan|menunjukkan|"
    r"mengikuti|berpindah|melompat|melihat)\b|\bkilas balik\b",
    re.I,
)
NON_INDUCTIVE_OPENING = re.compile(
    r"^(?:pada\s+(?:tahun|tanggal|masa|zaman|\d)|"
    r"(?:setelah|sebelum|sebelumnya|setahun\s+sebelumnya|sementara|ketika)\b|"
    r"di\s+(?:era|masa|zaman)\b|"
    r"dalam\s+(?:era|masa|zaman|keadaan)\b|"
    r"(?:dokumen|teks|tulisan|laporan|artikel|cerita|narasi)\s+ini\s+(?:dimulai|bermula|membuka|mengisahkan))",
    re.I,
)
TRANSITION_OPENING = re.compile(r"^(?:namun|karena itu|akibatnya|sebaliknya|meski demikian)\b", re.I)


def prose_body(text: str) -> str:
    if text.startswith("---\n"):
        _, _, text = text.partition("\n---\n")
    return "\n".join(line for line in text.splitlines() if not line.startswith("#"))


def narrative_body(text: str) -> str:
    if text.startswith("---\n"):
        _, _, text = text.partition("\n---\n")
    functional = ("status", "batas", "validasi")
    include = True
    kept: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().casefold()
            include = not heading.startswith(functional)
            continue
        if include and not line.startswith("#"):
            kept.append(line)
    return "\n".join(kept)


def narrative_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", narrative_body(text)) if paragraph.strip()]


def sentences(text: str) -> list[str]:
    protected = re.sub(r"\bdr\.", "dr<DOT>", prose_body(text), flags=re.I)
    return [part.replace("<DOT>", ".").strip() for part in SENTENCE.findall(protected) if part.strip()]


def words(sentence: str) -> list[str]:
    return [word.casefold() for word in WORD.findall(sentence)]


def content_words(sentence: str) -> list[str]:
    return [word for word in words(sentence) if len(word) > 3 and word not in STOPWORDS and not word.isdigit()]


def rough_stem(word: str) -> str:
    stem = word
    for prefix in PREFIXES:
        if stem.startswith(prefix) and len(stem) - len(prefix) >= 4:
            stem = stem[len(prefix):]
            break
    for suffix in SUFFIXES:
        if stem.endswith(suffix) and len(stem) - len(suffix) >= 4:
            stem = stem[:-len(suffix)]
            break
    return stem


def root_forms(sentence: str) -> dict[str, set[str]]:
    forms: dict[str, set[str]] = {}
    for word in content_words(sentence):
        root = rough_stem(word)
        if root not in ROOT_EXCLUSIONS:
            forms.setdefault(root, set()).add(word)
    return forms


def paragraph_terms(paragraph: str) -> set[str]:
    terms = set(content_words(paragraph))
    terms.update(root_forms(paragraph))
    return terms


def audit(text: str) -> list[tuple[str, int, str]]:
    # One tokenization pass, paragraph-aligned. Sentence numbers are derived from a
    # paragraph's position in that pass, never by searching a re-tokenized string in
    # a separately tokenized list: a paragraph that does not end in sentence-final
    # punctuation (a list introduction, a fence line, a table row) tokenizes
    # differently in isolation than it does inside the whole body, and the lookup
    # that assumed otherwise raised ValueError on any structural document.
    paragraphs = narrative_paragraphs(text)
    paragraph_sentences = [sentences(paragraph) for paragraph in paragraphs]
    paragraph_offsets: list[int] = []
    items: list[str] = []
    for group in paragraph_sentences:
        paragraph_offsets.append(len(items))
        items.extend(group)
    narrative_sequence = items
    narrative_items = set(narrative_sequence)
    findings: list[tuple[str, int, str]] = []
    for paragraph_index, group in enumerate(paragraph_sentences):
        if not group:
            continue
        opening = group[0]
        if NON_INDUCTIVE_OPENING.search(opening):
            number = paragraph_offsets[paragraph_index] + 1
            findings.append(("non-inductive-paragraph-opening", number, opening))

    for paragraph_index in range(1, len(paragraphs)):
        group = paragraph_sentences[paragraph_index]
        if not group:
            continue
        previous_paragraph = paragraphs[paragraph_index - 1]
        current_paragraph = paragraphs[paragraph_index]
        opening = group[0]
        if not paragraph_terms(previous_paragraph) & paragraph_terms(current_paragraph):
            if not TRANSITION_OPENING.search(opening):
                number = paragraph_offsets[paragraph_index] + 1
                findings.append(
                    ("weak-paragraph-bridge", number, f"paragraphs {paragraph_index}-{paragraph_index + 1}: {opening}")
                )
    for index, sentence in enumerate(items):
        number = index + 1
        word_count = len(words(sentence))
        if word_count <= 2:
            findings.append(("micro-sentence-review", number, f"{word_count} words: {sentence}"))
        elif word_count <= 5:
            findings.append(("short-sentence", number, f"{word_count} words: {sentence}"))
        elif word_count >= 26:
            findings.append(("long-sentence", number, f"{word_count} words: {sentence}"))

        if sentence in narrative_items and META_REPORT.search(sentence):
            findings.append(("meta-reporting-language", number, sentence))

        repeated = sorted(word for word, count in Counter(content_words(sentence)).items() if count > 1)
        if repeated:
            findings.append(("within-sentence-repeat", number, f"{', '.join(repeated)}: {sentence}"))

        repeated_roots = sorted(
            root for root, forms in root_forms(sentence).items() if len(forms) > 1
        )
        if repeated_roots:
            findings.append(("within-sentence-root-repeat", number, f"{', '.join(repeated_roots)}: {sentence}"))

        if index == 0:
            continue
        previous = items[index - 1]
        current_opening = content_words(sentence)[:2]
        previous_opening = content_words(previous)[:2]
        if len(current_opening) == 2 and current_opening == previous_opening:
            findings.append(("repeated-opening", number, f"sentences {number - 1}-{number}: {' '.join(current_opening)}"))

        current_words = set(words(sentence))
        current_roots = root_forms(sentence)
        for previous_index in range(max(0, index - 2), index):
            earlier = items[previous_index]
            shared_content = sorted(set(content_words(sentence)) & set(content_words(earlier)))
            if shared_content:
                findings.append(
                    ("nearby-content-repeat", number, f"sentences {previous_index + 1}-{number}: {', '.join(shared_content)}")
                )

            watched = sorted(current_words & set(words(earlier)) & WATCHED_NEARBY)
            if watched:
                findings.append(
                    ("nearby-watchword-repeat", number, f"sentences {previous_index + 1}-{number}: {', '.join(watched)}")
                )

            earlier_roots = root_forms(earlier)
            root_variants = sorted(
                root
                for root in current_roots.keys() & earlier_roots.keys()
                if current_roots[root] != earlier_roots[root]
            )
            if root_variants:
                findings.append(
                    ("nearby-root-repeat", number, f"sentences {previous_index + 1}-{number}: {', '.join(root_variants)}")
                )
    return findings


def self_test() -> int:
    sample = (
        "Cerita kembali ke 1944. Sudiro menggerakkan jaringan, lalu jaringan itu menggerakkan rakyat. "
        "Jaringan Barisan Pelopor menggerakkan rakyat menuju Ikada. "
        "Mendesak."
    )
    labels = {label for label, _, _ in audit(sample)}
    expected = {
        "meta-reporting-language",
        "within-sentence-repeat",
        "nearby-content-repeat",
        "micro-sentence-review",
    }
    if not expected <= labels:
        print(f"SELF-TEST FAILED: missing {sorted(expected - labels)}")
        return 2
    functional = "## Batas Penggunaan\n\nKilas balik hanya menjelaskan fakta organisasi."
    if any(label == "meta-reporting-language" for label, _, _ in audit(functional)):
        print("SELF-TEST FAILED: functional section produced a meta-reporting finding")
        return 2
    weak_openings = (
        "Pada 1944, jaringan itu mulai bekerja.",
        "Di era ini, organisasi menghadapi tekanan.",
        "Cerita ini dimulai ketika Jepang kalah.",
        "Setelah kembali, mereka merumuskan Proklamasi.",
    )
    for opening in weak_openings:
        sample_opening = f"## Sinopsis\n\n{opening}"
        if not any(
            label == "non-inductive-paragraph-opening" for label, _, _ in audit(sample_opening)
        ):
            print(f"SELF-TEST FAILED: non-inductive opening was not detected: {opening}")
            return 2
    strong_opening = "## Sinopsis\n\nSyahrir membawa kabar dari radio luar negeri."
    if any(label == "non-inductive-paragraph-opening" for label, _, _ in audit(strong_opening)):
        print("SELF-TEST FAILED: inductive opening produced a finding")
        return 2
    nearby_repeat = "Sebuah keputusan dibuat. Rakyat menunggu. Sebuah jaringan bergerak."
    if not any(label == "nearby-watchword-repeat" for label, _, _ in audit(nearby_repeat)):
        print("SELF-TEST FAILED: nearby watchword repetition was not detected")
        return 2
    root_repeat = "Pemimpin mengambil keputusan. Rakyat menunggu keputusan itu diputuskan."
    if not any(label.endswith("root-repeat") for label, _, _ in audit(root_repeat)):
        print("SELF-TEST FAILED: inflected root repetition was not detected")
        return 2
    weak_bridge = "## Sinopsis\n\nSyahrir pulang.\n\nBarisan Pelopor dibentuk."
    if not any(label == "weak-paragraph-bridge" for label, _, _ in audit(weak_bridge)):
        print("SELF-TEST FAILED: weak paragraph bridge was not detected")
        return 2
    linked_bridge = "## Sinopsis\n\nSyahrir mendesak kemerdekaan.\n\nNamun, keputusan politik belum cukup."
    if any(label == "weak-paragraph-bridge" for label, _, _ in audit(linked_bridge)):
        print("SELF-TEST FAILED: explicit paragraph bridge produced a finding")
        return 2
    print("SELF-TEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.path is None:
        parser.error("path is required unless --self-test is used")

    if not args.path.is_file():
        print(f"ERROR: file not found: {args.path}", file=sys.stderr)
        return 1

    findings = audit(args.path.read_text(encoding="utf-8"))
    for label, number, detail in findings:
        print(f"{args.path}: sentence {number}: [{label}] {detail}")
    if findings:
        print(f"ADVISORY (Class B): {len(findings)} style observation(s) for human review (non-blocking).")
        print("REPAIR ORDER (Advisory): delete -> restructure -> reference or ellipsis -> precise synonym -> justified canonical repetition")
    else:
        print("Prose style check passed: no repetitive or meta patterns detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
