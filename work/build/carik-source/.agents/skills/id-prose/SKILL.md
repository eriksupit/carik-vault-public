---
name: id-prose
description: >-
  Audit and reconstruct Indonesian prose contaminated by English calques, awkward syntax, floating deictics, or forced translations using writing-style/prose-writing-style.md and optional fail-open scripts. Use when the owner says "rombak bahasa Indonesia", "cek kalimat kaku", "bersihkan kalke", or "ubah ke S-P-O-K".
---

# id-prose

## Purpose

Mengaudit dan merekonstruksi teks prosa Bahasa Indonesia yang tercemar kalke Inggris, kalimat kaku, deiksis spasial melayang, subjek tak bernyawa, pronomina `dia/ia` untuk benda non-manusia, atau indonesianisasi paksa menjadi prosa Indonesia formal-sederhana yang alami dan lugas. Skill ini menyatukan audit kalimat dan rekonstruksi menyeluruh dengan mengacu pada `writing-style/prose-writing-style.md`, berjalan penuh secara bebas-Python, serta menyediakan skrip bantu opsional *fail-open*.

## Procedure

1. **Baca pedoman gaya dan tetapkan mode.** Buka `writing-style/prose-writing-style.md` lebih dulu bila tersedia. Tentukan mode sesuai permintaan pemilik:
   - **AUDIT (lapor saja):** laporkan temuan kalimat kaku/kalke dan arah perbaikan tanpa menyunting berkas.
   - **EDIT / REKONSTRUKSI:** tulis hasil perbaikan ke berkas sasaran atau `<nama>-edited.md` (jangan menimpa sumber bila diminta aman) sambil mempertahankan frontmatter, heading, tabel, blok kode, `[[wikilink]]`, kutipan verbatim, angka, tanggal, dan nama diri.
2. **Audit tiga lapis kalke dan struktur kalimat:**
   - **Lapis L1 (leksikal & kolokasi):** idiom terjemahan (`pada akhir hari` → `pada akhirnya`, `mengambil tempat` → `berlangsung`), rantai kata fungsi (`dalam rangka untuk` → `untuk`), pleonasme aspek (`sedang dalam proses` → `sedang`), serta indonesianisasi paksa (`keluaran` → `output`, `unduh` → `download`, `galat` → `error`, `peramban` → `browser`, `pranala` → `link`).
   - **Lapis L2 (sintaksis & diatesis):** pasif `di- + oleh + Persona 1/2` → pasif Tipe 2 (`Surat itu saya tulis`), preposisi mubazir pada verba transitif (`membahas tentang` → `membahas`), subjek inanimat artifisial (kecuali fenomena alam/gravitasi), verba hampa/nominalisasi beruntun (`melakukan pembayaran` → `membayar`), dan klausa cleft Inggris (`Apa yang membuat X penting adalah Y` → `X penting karena Y`).
   - **Lapis L3 (wacana, deiksis & animasi):** deiksis spasial melayang (jangkarkan ke lokasi fisik), sambungan mekanis berulang (`Sementara itu`, `Di sisi lain`), penerjemahan mekanis `a/the` (`sebuah`, `tersebut`), serta `dia/ia` untuk sistem/benda non-manusia (ganti dengan pelesapan, pengulangan nomina, atau `-nya` alami).
3. **Perbaiki dalam satu lintasan utuh (mode EDIT).** Susun ulang paragraf secara menyatu ke pola S-P-O-K kanonik, pasif Tipe 2, atau topik-komen yang wajar diucapkan kepada rekan kerja, tanpa mengarang aktor manusia fiktif dan tanpa mengubah fakta maupun tingkat kepastian klaim asli. Bila ada kolokasi meragukan dan pencarian web tersedia, uji pada sumber redaksional tepercaya (KBBI, Badan Bahasa, media nasional bereputasi).
4. **Pemeriksaan opsional *fail-open* (hanya bila `python3` tersedia):**
   ```bash
   python3 .agents/skills/id-prose/scripts/check_sentences.py <berkas-hasil> --genre <narrative|expository>
   python3 .agents/skills/id-prose/scripts/prose_language_lint.py <berkas-hasil>
   python3 .agents/skills/id-prose/scripts/fact_diff.py <berkas-asli> <berkas-hasil>
   ```
   `check_sentences.py` dan `prose_language_lint.py` bersifat penasihat (selalu exit 0), sedangkan `fact_diff.py` adalah satu-satunya gerbang keras untuk memastikan paritas entitas, angka, tanggal, dan polaritas negasi. Bila `python3` tidak tersedia, lewati perintah ini dan verifikasi paritas fakta secara manual.

## Rules & Boundaries

- Makna dan kejelasan sebab-akibat selalu mengungguli metrik panjang kalimat; kalimat panjang yang jernih tidak boleh dipecah paksa menjadi potongan patah.
- Dilarang memakai register sastrawi, bahasa mesin (`telah dilakukan penyesuaian`), atau metafora fisik pada konsep abstrak (aturan Substansi di `writing-style/prose-writing-style.md`).
- Pertahankan istilah kerja asing baku di bidang pembaca; dilarang mengarang fakta, entitas, atau angka baru.
- Seluruh skrip bantu bersifat opsional *fail-open*; skill berjalan penuh tanpa Python.

## Output & Verification

1. Mode AUDIT: daftar temuan per paragraf (L1–L3), vonis (`pass` atau `needs-work`), dan arah perbaikan ringkas tanpa mengubah berkas.
2. Mode EDIT: teks hasil bersih dari kalke dan indonesianisasi paksa, serta seluruh entitas, angka, tanggal, dan negasi cocok dengan teks asli (`fact_diff.py` exit 0 bila Python tersedia).
3. Sampaikan hasil perbaikan beserta ringkasan perubahan pokok kepada pemilik dalam Bahasa Indonesia sederhana.
