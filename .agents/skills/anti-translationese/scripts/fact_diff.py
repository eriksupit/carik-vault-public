#!/usr/bin/env python3
"""fact_diff — Fase 3.5 enforcer for anti-translationese EDIT mode.

Compares an ORIGINAL and an EDITED file and reports fact-bearing tokens that
APPEARED or DISAPPEARED, so a style-only edit that silently altered content is
caught. It flags candidates; a human/native confirms.

  Channel A (high signal): proper nouns (capitalized) + numbers / roman numerals.
  Channel B (review): lowercase content words (len>=4, non-stopword).

Tokens present in BOTH files cancel out, so ordinary reworded style produces
little noise; only genuine additions/removals surface. Relational drift (e.g.
asserting "kabar DARI X" — a link the original left implicit) is NOT lexical and
will NOT show here; that still needs a human read.

Usage: python3 fact_diff.py <original> <edited>
Exit: 0 = no Channel-A add/remove, 1 = Channel-A differences present.
"""
import re
import sys

WORD_RE = re.compile(r"\d+(?:[.,]\d+)+|[0-9A-Za-zÀ-ÿ]+(?:-[0-9A-Za-zÀ-ÿ]+)*")
# Polarity tokens must NEVER be ignored as stop words because negation flips alter factual truth
POLARITY_SET = {
    "tidak", "tak", "tiada", "bukan", "belum", "tanpa", "jangan",
    "dilarang", "gagal", "batal"
}

STOP = set(
    "yang dan di ke dari itu ini pada untuk dengan dalam akan atau juga "
    "ada adalah telah sudah para oleh sebagai agar karena saat ketika lalu kemudian "
    "mereka dia ia kepada atas bisa dapat masih harus hanya pun namun tetapi "
    "tapi serta maupun bahwa satu sang".split()
)
# Frequent sentence-openers / generic capitalized words that are NOT proper nouns.
COMMON_START = set(
    "dia mereka namun sesudah setelah kemudian lalu pada dalam keempat keduanya "
    "kedua para sinopsis dokumen validasi tokoh pemerintah tentara kabar sudiro "
    "pernyataan pengawasan risiko tekanan perubahan ketidakpastian ancaman rakyat "
    "persiapan kelompok hubungan sistem karena namun".split()
)


def strip_frontmatter(t):
    if t.lstrip().startswith("---"):
        return re.sub(r"^\s*---.*?\n---\s*\n", "", t, count=1, flags=re.DOTALL)
    return t


def body(t):
    lines = [
        ln for ln in strip_frontmatter(t).splitlines()
        if ln.strip() and not ln.lstrip().startswith(("#", "---", "|", ">"))
    ]
    return " ".join(lines)


def entities(text):
    ent = set()
    for w in WORD_RE.findall(text):
        if re.fullmatch(r"\d+(?:[.,]\d+)+|\d+", w) or re.fullmatch(r"[IVX]{1,4}", w):
            ent.add(w)
        elif w[0].isupper() and w.lower() not in COMMON_START:
            ent.add(w)
    return ent


def polarities(text):
    return {w.lower() for w in WORD_RE.findall(text) if w.lower() in POLARITY_SET}


def content(text):
    return {
        w.lower() for w in WORD_RE.findall(text)
        if len(w) >= 3 and not w[0].isupper() and w.lower() not in STOP and w.lower() not in POLARITY_SET
    }


def diff(orig_text, edit_text):
    o_b, e_b = body(orig_text), body(edit_text)
    o_e, e_e = entities(o_b), entities(e_b)
    o_p, e_p = polarities(o_b), polarities(e_b)
    o_c, e_c = content(o_b), content(e_b)
    return {
        "A_added": sorted(e_e - o_e),
        "A_removed": sorted(o_e - e_e),
        "P_added": sorted(e_p - o_p),
        "P_removed": sorted(o_p - e_p),
        "B_added": sorted(e_c - o_c),
        "B_removed": sorted(o_c - e_c),
    }


def report(orig_text, edit_text):
    d = diff(orig_text, edit_text)
    out = ["FACT DIFF (original -> edited)", ""]
    out.append(f"[A] proper-noun/number ADDED   : {d['A_added'] or '-'}")
    out.append(f"[A] proper-noun/number REMOVED : {d['A_removed'] or '-'}")
    out.append(f"[P] polarity/negation ADDED    : {d['P_added'] or '-'}")
    out.append(f"[P] polarity/negation REMOVED  : {d['P_removed'] or '-'}")
    out.append(f"[B] content-word ADDED (review): {d['B_added'] or '-'}")
    out.append(f"[B] content-word REMOVED (rev.): {d['B_removed'] or '-'}")
    
    hard_a = bool(d["A_added"] or d["A_removed"])
    hard_p = bool(d["P_added"] or d["P_removed"])
    hard = hard_a or hard_p
    
    out.append("")
    if hard_p:
        out.append("STATUS: HARD FAIL — POLARITY/NEGATION INVARIANT VIOLATED (fact-flip detected)")
    elif hard_a:
        out.append("STATUS: CHANNEL-A DIFF — verify facts")
    else:
        out.append("STATUS: A clean")
    return "\n".join(out), not hard


def _selftest():
    orig = "dr. Moewardi memimpin. Jepang belum menyerah pada 1945."
    edit = "Moewardi memimpin. Jepang belum menyerah atas sekutu dalam perang dunia II pada 1945."
    d = diff(orig, edit)
    assert "II" in d["A_added"], "roman 'II' addition must show in Channel A"
    assert "dokter" not in d["B_removed"]  # not present in orig here
    assert "sekutu" in d["B_added"], "added content word must show in Channel B"
    o2 = "dr. Moewardi, dokter yang memimpin."
    e2 = "dr. Moewardi, pemimpin."
    assert "dokter" in diff(o2, e2)["B_removed"], "dropped 'dokter' must show"
    
    # Polarity negation flip test (Channel P)
    o_pol = "Model ini tidak menghasilkan halusinasi."
    e_pol = "Model ini menghasilkan halusinasi."
    rep_pol, ok_pol = report(o_pol, e_pol)
    assert not ok_pol, "Dropping 'tidak' must fail Channel P (HARD FAIL)"
    assert "tidak" in rep_pol, "'tidak' must appear in polarity diff"
    
    # Short polarity token 'tak' (3 letters)
    o_tak = "Sistem tak memiliki bias."
    e_tak = "Sistem memiliki bias."
    _, ok_tak = report(o_tak, e_tak)
    assert not ok_tak, "Dropping 3-letter 'tak' must fail Channel P"
    
    # Grouped digits handling
    o_num = "Biaya sekitar 3.500 rupiah dan 1,5 juta."
    e_num = "Biaya sekitar 3.500 rupiah dan 1,5 juta."
    d_num = diff(o_num, e_num)
    assert not d_num["A_added"] and not d_num["A_removed"], "Grouped digits must match identically"
    
    print("selftest OK (fact_diff with Channel P Polarity Invariant)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        _selftest()
        sys.exit(0)
    orig = open(sys.argv[1], encoding="utf-8").read()
    edit = open(sys.argv[2], encoding="utf-8").read()
    rep, ok = report(orig, edit)
    print(rep)
    sys.exit(0 if ok else 1)
