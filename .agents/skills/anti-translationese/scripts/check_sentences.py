#!/usr/bin/env python3
"""Anti-translationese checker v3 — deterministic signals and advisory telemetry.

Genre-aware length + redundancy + pronoun + discourse/syntax diagnostics for the
2-stage rewrite loop. It VERIFIES text; it does not generate. Harness-agnostic
(Claude '/', Codex '$', DeepSeek governance runner, or Antigravity native).

Findings are split into two channels, and NEITHER blocks:
  ADVISORY — clear defects the script can size: over-cap sentence
                   (genre-scaled flag), long-dominance (>half 'panjang'),
                   staircase, repeated opener, forced terms.
  REVIEW — heuristics the agent must judge: weak length-spread (vary across
                   the SECTION, not per paragraph), window word-repetition, flat
                   'X adalah Y' copula, ambiguous 'dia', standalone 'ia',
                   function-word bundles ('dalam rangka untuk'), cleft focus triggers
                   ('apa yang membuat X adalah Y'), reference marker density
                   ('sebuah'/'tersebut'), and nonhuman pronoun hints.

Length cap is GENRE-SCALED: narrative 20, expository 30.
It is a strong DEFAULT flag (split the sentence), NOT an absolute law — length is a
proxy; the real target is English STRUCTURE (calque), which a script cannot see. The
agent MAY keep an over-cap sentence when it is clean native hypotaxis (yang /
apposition / sehingga / sedangkan, zero L2-calque markers) AND splitting would
manufacture a worse artifact. Default remedy stays: split at a relational boundary.

Usage:
  python3 check_sentences.py <file> [--genre narrative|expository]

Class B under the Carik Charter: this script ALWAYS exits 0. Every finding is a
question, never a command. The sentence-length cap, long-sentence dominance,
staircase detection, and the FORCED vocabulary list are proxies, not defects —
meaning outranks metrics, and the agent may override any of them with a stated
reason. Word quotas and vocabulary bans are Class A per CARIK-CHARTER.md:150, so
they may inform and must not block.
"""
import json
import re
import sys
from collections import Counter

# Grouped-digit figures keep their thousand/decimal separators as ONE token
# ("3.500", "1,5") so a figure-dense sentence is not over-counted past the cap.
WORD_RE = re.compile(r"\d+(?:[.,]\d+)+|[0-9A-Za-zÀ-ÿ]+(?:-[0-9A-Za-zÀ-ÿ]+)*")
CAP = {"narrative": 20, "expository": 30}
CAP_DEFAULT = 20
STOP = set(
    "yang dan di ke dari itu ini pada untuk dengan dalam akan atau juga tidak tak "
    "ada adalah telah sudah para oleh sebagai agar karena saat ketika lalu kemudian "
    "mereka dia ia kepada atas bisa dapat masih belum harus hanya pun namun tetapi "
    "tapi serta maupun bahwa satu sang".split()
)

# Sastrawi diction: ceremonial/archaic diction. REVIEW, not HARD.
# Verbs with legitimate literal senses (membelai, merangkak, menyelimuti) are
# deliberately EXCLUDED: they would fire on plain physical description and
# train the operator to ignore the channel.
SASTRAWI = ["nan", "sang", "tatkala", "sejatinya", "bagai", "kian"]

# FORCED: Indonesianizations of standard foreign working terms. HARD — no context
# outside a direct quotation justifies them (Register section 3).
FORCED = {
    "keluaran": "output", "masukan": "input", "unduh": "download", "unggah": "upload",
    "galat": "error", "tetikus": "mouse", "daring": "online", "luring": "offline",
    "peramban": "browser", "pranala": "link", "tegar-tunai": "hardware", "sangkil": "efisien",
}

# Function-word bundles & calque stock phrases (REVIEW channel)
FUNCTION_BUNDLES = [
    (re.compile(r"\bdalam\s+rangka\s+untuk\b", re.I), "dalam rangka untuk -> untuk / demi"),
    (re.compile(r"\bdalam\s+kaitannya\s+dengan\b", re.I), "dalam kaitannya dengan -> terkait / mengenai"),
    (re.compile(r"\bmerujuk\s+pada\s+fakta\s+bahwa\b", re.I), "merujuk pada fakta bahwa -> karena / mengingat"),
    (re.compile(r"\bberdasarkan\s+pada\b", re.I), "berdasarkan pada -> berdasarkan"),
    (re.compile(r"\bpada\s+akhir\s+hari\b", re.I), "pada akhir hari -> pada akhirnya / intinya"),
    (re.compile(r"\boleh\s+karena\s+itu\s+maka\b", re.I), "oleh karena itu maka -> karena itu"),
    (re.compile(r"\byang\s+mana\b", re.I), "yang mana -> yang / relative pronoun calque"),
    (re.compile(r"\b(?:demi\s+untuk|agar\s+supaya|sejak\s+dari)\b", re.I), "pleonasme preposisi ganda -> sederhanakan"),
    # Hyperformal-baku stratum: grammatical, calque-free, and still unreadable.
    # Not English interference — the model selecting dictionary-formal register
    # because it construes formality as politeness. No other channel sees these.
    (re.compile(r"\bdikarenakan\b", re.I), "dikarenakan -> karena"),
    (re.compile(r"\bpasca[-\s]?\w+", re.I), "pasca- -> setelah"),
    (re.compile(r"\bdi(?:maksud|termaksud)\b|\btermaksud\b", re.I), "dimaksud / termaksud -> itu"),
    (re.compile(r"\bterkait\s+dengan\b", re.I), "terkait dengan -> tentang / soal"),
]

# Morfosintaksis & Valensi Telemetri (REVIEW channel)
TRANSITIVE_VALENCY = [
    (re.compile(r"\b(membahas|menceritakan|mengkaji|meneliti|menyatakan|menjelaskan|mempelajari)\s+tentang\b", re.I),
     "verba transitif + tentang ('membahas tentang') -> hapus 'tentang' atau gunakan verba 'ber-' ('bercerita tentang')"),
]

PASIF_TIPE1_P1P2 = re.compile(
    r"\bdi(\w+)\s+(?:oleh\s+)?(saya|aku|kami|kita|kamu|kau|anda)\b(?!\s+(?:dan|serta|bersama|yang|sendiri))\b",
    re.I
)

ASPECT_PLEONASM = [
    (re.compile(r"\b(?:telah|sudah)\s+(?:selesai|berhasil)\b", re.I),
     "pleonasme aspek ('telah selesai' / 'sudah berhasil') -> sederhanakan"),
    (re.compile(r"\bsedang\s+dalam\s+proses\b", re.I),
     "kalkir proses ('sedang dalam proses') -> gunakan 'sedang' + verba"),
]

DIALOGUE_CALQUE = [
    (re.compile(r"\b(?:dengar,\s+kawan|lihat\s+siapa\s+yang\s+datang|jangan\s+main-main\s+denganku|percayalah\s+padaku|kamu\s+pasti\s+bercanda)\b", re.I),
     "kalk percakapan/sulih suara -> gunakan ungkapan tutur lisan Indonesia alami"),
]

REDUPLIKASI_MURNI = {"mata", "tetangga", "kura", "laba", "kanak", "kupu", "paru"}
PLURAL_PLEONASM = re.compile(r"\b(para|banyak|berbagai|semua)\s+([A-Za-zÀ-ÿ]+)-\2\b", re.I)

# Cleft & scaffold structures (REVIEW channel)
CLEFT_PATTERNS = [
    (re.compile(r"\bapa\s+yang\s+(?:membuat|menjadikan|menyebabkan|menjadi)\s+.*?\s+adalah\b", re.I),
     "cleft focus: 'apa yang membuat ... adalah' -> recast directly 'X ... karena Y'"),
    (re.compile(r"\bhal\s+yang\s+penting\s+untuk\s+dicatat\s+adalah\b", re.I),
     "hedging scaffold: 'hal yang penting untuk dicatat adalah' -> state fact directly"),
    (re.compile(r"\bhal\s+ini\s+(?:menunjukkan|membuktikan)\s+bahwa\b", re.I),
     "dummy subject scaffold: 'hal ini menunjukkan bahwa' -> check certainty & recast"),
]

# Nonhuman system/document keywords for pronoun animacy screening (REVIEW channel)
NONHUMAN_KEYWORDS = {"sistem", "algoritma", "dokumen", "model", "mesin", "program", "perangkat", "aplikasi", "data", "server", "pipeline"}
SYSTEM_ACRONYMS = {"API", "LLM", "GPU", "CPU", "UI", "RAM", "JSON", "SQL", "REST", "SDK", "RAG", "MOE", "TPU", "NLP", "LORA", "FP8", "DB", "OS"}
REF_MARKERS = {"sebuah", "suatu", "tersebut", "hal ini"}


def wordlist_hits(text, terms, affixed=False):
    """Case-insensitive hits. affixed=True also matches Indonesian derivations
    (mengunduh, diunduh, unduhan) by allowing letters on either side of the stem.
    Returns [(term, count)] in list order."""
    out = []
    for t in terms:
        pat = rf"\b\w*{re.escape(t)}\w*\b" if affixed else rf"\b{re.escape(t)}\b"
        n = len(re.findall(pat, text, re.IGNORECASE))
        if n:
            out.append((t, n))
    return out


def strip_frontmatter(text):
    """Drop a well-formed leading YAML frontmatter block (--- ... ---)."""
    if text.lstrip().startswith("---"):
        return re.sub(r"^\s*---.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    return text


_FENCE_RE = re.compile(r"^\s*```")


def paragraphs(text):
    out = []
    for block in re.split(r"\n\s*\n", strip_frontmatter(text)):
        lines = []
        in_fence = False
        for ln in block.splitlines():
            if _FENCE_RE.match(ln):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            stripped = ln.lstrip()
            if not stripped or stripped.startswith(("#", "---", "|", ">", "- ", "* ")):
                continue
            lines.append(ln)
        joined = " ".join(lines).strip()
        if joined:
            out.append(joined)
    return out


ABBREV = {
    "dr", "drs", "dra", "prof", "ir", "hj", "hlm", "dll", "dsb", "dst",
    "tbk", "jl", "no", "rp", "yth", "dkk", "sdr", "vol", "jan", "alm", "pt", "cv"
}
_ABBR_RE = re.compile(r"\b(" + "|".join(sorted(ABBREV, key=len, reverse=True))
                      + r")\.", re.IGNORECASE)

_DOT = chr(0)  # sentinel standing in for a masked abbreviation period

# Universal Sentence Boundary Splitter (quote-aware, bracket-aware)
_SENTENCE_SPLIT_RE = re.compile(
    r'(?<=[.!?])'                # Punctuation
    r'[\'"”’\)\]]*'              # Optional closing quotes or brackets
    r'\s+'                       # Whitespace
    r'(?=[A-Z0-9\-_“"\'‘\(\[])',  # Lookahead for capital, digit, quote, or bracket
    re.UNICODE
)


def sentences(par):
    masked = _ABBR_RE.sub(lambda m: m.group(1) + _DOT, par.strip())
    parts = _SENTENCE_SPLIT_RE.split(masked)
    return [p.replace(_DOT, ".").strip() for p in parts if p.strip()]


def words(s):
    return WORD_RE.findall(s)


def classify(n, cap):
    if n <= 0:
        return None
    if n <= 2:
        return "ekspresif"
    if n <= 6:
        return "pendek"
    if n <= 11:
        return "menengah"
    if n <= cap:
        return "panjang"
    return "OVER"


def content_tokens(s):
    return [w.lower() for w in words(s) if len(w) >= 4 and w.lower() not in STOP]


def find_ia(text):
    return re.findall(r"\bia\b", text, re.IGNORECASE)


def redundancy(sents):
    hard, review = [], []
    # (a) staircase: last content token of sentence i == first of i+1  [HARD]
    for i in range(len(sents) - 1):
        a, b = content_tokens(sents[i]), content_tokens(sents[i + 1])
        if a and b and a[-1] == b[0]:
            hard.append(("staircase", a[-1]))
    # (c) repeated opener: two consecutive sentences share first word  [HARD]
    openers = [words(s)[0].lower() if words(s) else "" for s in sents]
    for i in range(len(openers) - 1):
        if openers[i] and openers[i] == openers[i + 1]:
            hard.append(("repeat-opener", openers[i]))
    # (b) window repetition: a content word appears >=3x in the paragraph [REVIEW]
    allc = [t for s in sents for t in content_tokens(s)]
    for w, c in Counter(allc).items():
        if c >= 3:
            review.append(("repetition", f"{w} x{c}"))
    # (d) flat copula: 'X adalah ...'  [REVIEW]
    for s in sents:
        if re.search(r"\badalah\b", s):
            review.append(("flat-copula", s[:44]))
    return hard, review


def named_refs(par):
    """Candidate proper nouns: capitalized tokens mid-sentence not in stopwords or system acronyms."""
    starts = {words(s)[0] for s in sentences(par) if words(s)}
    return {
        w for w in words(par)
        if w[0].isupper() and w not in starts and w.lower() not in STOP
        and w.upper() not in SYSTEM_ACRONYMS
        and w.lower() not in NONHUMAN_KEYWORDS
    }


def check_discourse_syntax(par):
    """Advisory telemetry for function words, cleft focus, valency, diathesis, aspect, and animacy."""
    review = []
    # Function-word bundles
    for pat, desc in FUNCTION_BUNDLES:
        m = pat.findall(par)
        if m:
            review.append(("function-word-bundle", f"{desc} (x{len(m)})"))
    # Transitive valency
    for pat, desc in TRANSITIVE_VALENCY:
        m = pat.findall(par)
        if m:
            review.append(("transitive-valency", f"{desc} (x{len(m)})"))
    # Pasif Tipe 1 with P1/P2
    m_pasif = PASIF_TIPE1_P1P2.findall(par)
    if m_pasif:
        review.append(("agentive-passive-calque", f"di-{m_pasif[0][0]} oleh {m_pasif[0][1]} -> gunakan Pasif Tipe 2 ('sudah {m_pasif[0][1]} {m_pasif[0][0]}') (x{len(m_pasif)})"))
    # Aspect pleonasm
    for pat, desc in ASPECT_PLEONASM:
        m = pat.findall(par)
        if m:
            review.append(("aspect-pleonasm", f"{desc} (x{len(m)})"))
    # Dialogue calques
    for pat, desc in DIALOGUE_CALQUE:
        m = pat.findall(par)
        if m:
            review.append(("dialogue-calque", f"{desc} (x{len(m)})"))
    # Plural pleonasm (excluding legitimate pure reduplication)
    m_pl = PLURAL_PLEONASM.findall(par)
    for quant, root in m_pl:
        if root.lower() not in REDUPLIKASI_MURNI:
            review.append(("plural-pleonasm", f"{quant} {root}-{root} -> sederhanakan ('{quant} {root}' atau '{root}-{root}')"))
    # Cleft & scaffolds
    for pat, desc in CLEFT_PATTERNS:
        m = pat.findall(par)
        if m:
            review.append(("cleft-or-scaffold", f"{desc} (x{len(m)})"))
    # Reference marker density
    all_w = words(par)
    if len(all_w) >= 25:
        ref_count = sum(1 for w in all_w if w.lower() in REF_MARKERS)
        ratio = (ref_count / len(all_w)) * 100
        if ratio >= 4.0:
            review.append(("reference-density", f"{ratio:.1f}% ({ref_count}/{len(all_w)} tokens) — check excess sebuah/tersebut"))
    # Pronoun animacy check
    has_dia = bool(re.search(r"\bdia\b", par, re.IGNORECASE))
    has_ia = bool(re.search(r"\bia\b", par, re.IGNORECASE))
    nh_hits = [w.lower() for w in all_w if w.lower() in NONHUMAN_KEYWORDS]
    refs = named_refs(par)
    if (has_dia or has_ia) and nh_hits and not refs:
        p_name = "dia" if has_dia else "ia"
        review.append(("pronoun-animacy-hint", f"'{p_name}' with nonhuman terms ({', '.join(sorted(set(nh_hits))[:3])}) & no human named refs — check if antecedent is nonhuman"))
    return review


def analyze(text, genre):
    cap = CAP.get(genre, CAP_DEFAULT)
    blocks, hard_fail = [], False
    structured_findings = []
    all_sent_lens = []
    
    for pi, par in enumerate(paragraphs(text), 1):
        sents = sentences(par)
        rows = [(len(words(s)), classify(len(words(s)), cap), s) for s in sents]
        for n, _, _ in rows:
            all_sent_lens.append(n)
        over = [(n, s) for n, t, s in rows if t == "OVER"]
        type_list = [t for _, t, _ in rows if t and t != "OVER"]
        type_counts = Counter(type_list)
        n_grade = len(type_list)
        need = min(n_grade, 4)
        red_hard, red_review = redundancy(sents)
        disc_review = check_discourse_syntax(par)
        refs = named_refs(par)
        amb = len(refs) >= 2 and bool(re.search(r"\bdia\b", par, re.IGNORECASE))

        lines = [f"P{pi}: {len(sents)} sents, types={sorted(type_counts)}"]
        if over:
            hard_fail = True
            lines.append(f"  ADVISORY over-{cap} ({len(over)}) — split by default; keep "
                         f"only if clean native hypotaxis & splitting would hurt: "
                         + "; ".join(f"[{n}] {s[:40]}" for n, s in over[:3]))
            for n, s in over:
                structured_findings.append({"channel": "ADVISORY", "category": f"over-cap-{cap}", "paragraph": pi, "span": s[:60], "words": n})
        if n_grade and len(type_counts) < need:
            lines.append(f"  review length-spread: {len(type_counts)} of {need} "
                         f"types here — vary across the SECTION, not per paragraph")
            structured_findings.append({"channel": "REVIEW", "category": "length-spread", "paragraph": pi, "details": f"{len(type_counts)}/{need} types"})
        if n_grade >= 4 and type_counts.get("panjang", 0) * 2 > n_grade:
            hard_fail = True
            lines.append(f"  ADVISORY long-dominance: {type_counts['panjang']}/{n_grade} "
                         f"sentences 'panjang' (>half) — vary down, don't default to the cap")
            structured_findings.append({"channel": "ADVISORY", "category": "long-dominance", "paragraph": pi, "ratio": f"{type_counts['panjang']}/{n_grade}"})
        if red_hard:
            hard_fail = True
            lines.append("  ADVISORY redundancy: "
                         + "; ".join(f"{k}:{d}" for k, d in red_hard[:5]))
            for k, d in red_hard:
                structured_findings.append({"channel": "ADVISORY", "category": k, "paragraph": pi, "span": d})
        if red_review:
            lines.append("  review: "
                         + "; ".join(f"{k}:{d}" for k, d in red_review[:5]))
            for k, d in red_review:
                structured_findings.append({"channel": "REVIEW", "category": k, "paragraph": pi, "span": d})
        if disc_review:
            lines.append("  review telemetry: "
                         + "; ".join(f"{k}:{d}" for k, d in disc_review[:5]))
            for k, d in disc_review:
                structured_findings.append({"channel": "REVIEW", "category": k, "paragraph": pi, "span": d})
        if amb:
            lines.append(f"  review ambiguous 'dia': {len(refs)} named refs "
                         f"in paragraph ({sorted(refs)[:4]}) — name them if unclear")
            structured_findings.append({"channel": "REVIEW", "category": "ambiguous-dia", "paragraph": pi, "refs": sorted(refs)[:4]})
        blocks.append("\n".join(lines))

    # 'ia' is now REVIEW (advisory) for narrative/human contexts, not HARD fail
    ia = find_ia(text)
    tail = []
    if ia and genre == "expository":
        tail.append(f"review 'ia' x{len(ia)} — in expository prose, verify 'dia' is preferred or if antecedent is human")
        structured_findings.append({"channel": "REVIEW", "category": "ia-expository-review", "count": len(ia)})
    
    forced = wordlist_hits(text, FORCED, affixed=True)
    if forced:
        hard_fail = True
        tail.append("ADVISORY forced-Indonesianization — keep the foreign term: "
                    + "; ".join(f"{t}(x{n})->{FORCED[t]}" for t, n in forced))
        for t, n in forced:
            structured_findings.append({"channel": "ADVISORY", "category": "forced-indonesianization", "term": t, "count": n, "replacement": FORCED[t]})
    
    sastra = wordlist_hits(text, SASTRAWI)
    if sastra:
        tail.append("review sastrawi diction: "
                    + "; ".join(f"{t}(x{n})" for t, n in sastra)
                    + " — plain it unless deliberate fiction earns it")
        for t, n in sastra:
            structured_findings.append({"channel": "REVIEW", "category": "sastrawi-diction", "term": t, "count": n})
    
    tail.append(f"STATUS: {'FINDINGS (advisory)' if hard_fail else 'CLEAN'} "
                f"(genre={genre}, cap={cap})")
    
    mean_len = (sum(all_sent_lens) / len(all_sent_lens)) if all_sent_lens else 0
    std_len = (sum((x - mean_len) ** 2 for x in all_sent_lens) / len(all_sent_lens)) ** 0.5 if all_sent_lens else 0
    cv = (std_len / mean_len) if mean_len > 0 else 0
    
    json_payload = {
        "status": "FINDINGS" if hard_fail else "PASS",
        "exit_code": 0,
        "genre": genre,
        "cap": cap,
        "metrics": {
            "total_paragraphs": len(blocks),
            "total_sentences": len(all_sent_lens),
            "mean_sentence_length": round(mean_len, 2),
            "std_sentence_length": round(std_len, 2),
            "coefficient_of_variation": round(cv, 2),
        },
        "findings": structured_findings
    }
    
    return "\n\n".join(blocks + ["\n".join(tail)]), not hard_fail, json_payload


def _selftest():
    bad = ("Dia mengurus kegiatan harian organisasi itu. Organisasi ini berada "
           "di bawah Soekarno. Soekarno adalah tokoh pergerakan nasional.")
    _, ok, _ = analyze(bad, "expository")
    assert not ok, "staircase must HARD-fail"
    # word-lists: forced Indonesianization HARD-fails, incl. affixed forms
    out, ok_f, _ = analyze("Pengguna mengunduh berkas itu.", "expository")
    assert not ok_f and "unduh" in out, "affixed 'mengunduh' must HARD-fail"
    out, _, _ = analyze("Sistem menampilkan keluaran dan galat.", "expository")
    assert "keluaran" in out and "galat" in out, "both forced terms must report"
    # sastrawi is REVIEW only — must be reported without failing the run
    out, ok_s, _ = analyze("Sang waktu nan panjang berlalu.", "narrative")
    assert ok_s and "sastrawi" in out, "sastrawi must REVIEW, not HARD-fail"
    # no false positive on plain prose that merely contains similar strings
    out, ok_p, _ = analyze("Dia berjalan pulang. Kereta itu sudah berangkat.", "narrative")
    assert "sastrawi" not in out and "forced" not in out, "clean prose must stay clean"
    _, ok2, _ = analyze("Dia datang. Dia pergi. Semua diam.", "narrative")
    assert not ok2, "repeated opener must HARD-fail"
    # genre-scaled cap: narrative ~20, expository ~30 (a strong default flag).
    over_n = ("Perempuan tua itu berjalan pelan menyusuri lorong gelap yang panjang dan "
              "sepi menuju sebuah pintu besar tua di ujung bangunan kosong itu.")
    assert len(words(over_n)) > 20, "narrative over-cap fixture must exceed 20 words"
    _, okn, _ = analyze(over_n, "narrative")
    assert not okn, "sentence over the narrative cap (20) must flag"
    _, okn_e, _ = analyze(over_n, "expository")
    assert okn_e, "22 words is within the expository cap (30) — must not flag on length"
    over_e = ("Ketika pemerintah kolonial memberlakukan tanam paksa pada tahun 1830, "
              "beban yang ditanggung oleh para petani di seluruh Jawa meningkat sangat "
              "tajam, sehingga banyak sekali desa mengalami kelaparan hebat yang "
              "menewaskan ribuan orang.")
    assert len(words(over_e)) > 30, "expository over-cap fixture must exceed 30 words"
    _, oke, _ = analyze(over_e, "expository")
    assert not oke, "sentence over the expository cap (30) must flag"
    
    # Universal sentence splitting with quotes and unquoted plain sentences
    quoted_txt = '“Merdeka!” serunya. Pemuda itu berdiri tegak. Dia melangkah maju.'
    s_q = sentences(quoted_txt)
    assert len(s_q) == 3, f"Quoted sentences must split into 3, got {len(s_q)}"
    
    unquoted_txt = "Sistem memproses data. Latensi turun drastis. Pengujian berhasil."
    s_uq = sentences(unquoted_txt)
    assert len(s_uq) == 3, f"Plain unquoted sentences must split into 3, got {len(s_uq)}"

    # 'ia' in narrative must PASS exit 0 (demoted from HARD)
    lit_ia = "Ia menatap cakrawala dengan tenang. Angin berembus sepoi."
    _, ok_ia, _ = analyze(lit_ia, "narrative")
    assert ok_ia, "'ia' in narrative prose must pass exit 0"

    # Pasif Tipe 1 P1/P2 in review telemetry
    pasif_sample = "Laporan ini telah disusun oleh saya kemarin."
    out_pasif, ok_pasif, _ = analyze(pasif_sample, "expository")
    assert ok_pasif, "Pasif Tipe 1 P1/P2 must be REVIEW (pass exit 0)"
    assert "agentive-passive-calque" in out_pasif, "agentive-passive-calque must report"

    # Applicative valency check
    val_sample = "Artikel ini membahas tentang kecerdasan buatan."
    out_val, ok_val, _ = analyze(val_sample, "expository")
    assert ok_val, "Transitive valency 'membahas tentang' must be REVIEW"
    assert "transitive-valency" in out_val, "transitive-valency must report"

    # Reduplication exception (pure reduplication 'para mata-mata' must NOT flag plural-pleonasm)
    mata_sample = "Para mata-mata mengawasi pergerakan musuh."
    out_mata, _, _ = analyze(mata_sample, "narrative")
    assert "plural-pleonasm" not in out_mata, "'para mata-mata' is legitimate and must not flag pleonasm"

    # True plural pleonasm ('para faktor-faktor') must flag
    faktor_sample = "Para faktor-faktor penentu sudah diidentifikasi."
    out_faktor, _, _ = analyze(faktor_sample, "expository")
    assert "plural-pleonasm" in out_faktor, "'para faktor-faktor' must flag plural-pleonasm"

    # JSON payload structure check
    _, _, j_payload = analyze(faktor_sample, "expository")
    assert "metrics" in j_payload and "findings" in j_payload, "JSON payload must contain metrics & findings"

    print("selftest OK (check_sentences v4 with hardened morfosintaksis & universal boundary)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    genre = "narrative"
    json_mode = "--json" in args
    if json_mode:
        args.remove("--json")
    if "--genre" in args:
        i = args.index("--genre")
        genre = args[i + 1]
        del args[i:i + 2]
    if not args:
        _selftest()
        sys.exit(0)
    src = args[0]
    text = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    rep, ok, payload = analyze(text, genre)
    if json_mode:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(rep)
    sys.exit(0)
