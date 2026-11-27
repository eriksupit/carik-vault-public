---
name: id-prose
description: >-
  Reconstruct AI-generated Indonesian prose contaminated by English calques, floating deictics, or inanimate subjects into natural Indonesian using writing-style/prose-writing-style.md and optional lint/fact_diff checks. Use when the owner says "rombak bahasa Indonesia", "bersihkan kalke", "tulis ulang lebih alami", or "konversi bahasa logis".
---

# id-prose

## Purpose

Merekonstruksi teks prosa Bahasa Indonesia hasil AI yang tercemar kalke Inggris, deiksis spasial melayang, subjek tak bernyawa, atau gaya bertele-tele menjadi prosa Indonesia yang alami, logis, dan berpijak pada fakta konkret. Skill ini merujuk pada pedoman tunggal `writing-style/prose-writing-style.md` dan berjalan penuh secara tekstual dengan linter opsional fail-open serta satu-satunya gerbang bahasa `fact_diff.py`.

## Procedure

1. **Baca jangkar gaya proyek.** Buka `writing-style/prose-writing-style.md` terlebih dahulu bila tersedia agar seluruh rekonstruksi mengikuti register formal-sederhana, S-P-O-K, dan larangan metafora fisik pada hal bukan benda.
2. **Zonasi dan lindungi bagian baku.** Pisahkan frontmatter/tabel (biarkan utuh), kutipan verbatim (bekukan total), istilah kerja asing baku (`commit`, `output`, `download`, `branch`), serta nama/ejaan arsip sebelum menyunting tubuh prosa.
3. **Identifikasi enam kategori kalke utama:**
   - Kalke spasial & deiksis semu (jangkarkan ke lokasi fisik nyata).
   - Pergeseran subjek inanimat (dahulukan aktor atau wadah, kecuali fenomena alam/gravitasi).
   - Asumsi batin narator (ganti dengan pengamatan kasatmata).
   - Eksplanasi negatif & redundansi (ubah menjadi aksi fisik positif tunggal).
   - Verba hampa & nominalisasi beruntun (`melakukan pengangkutan` → `mengangkut`).
   - Klausa relatif & rujukan `-nya` yang terdislokasi (rapikan urutan sebab-akibat dan anteseden).
4. **Uji kolokasi yang meragukan pada bukti eksternal.** Bila ada pasangan kata yang terasa seperti terjemahan Inggris dan diragukan kewajarannya, periksa di sumber redaksional tepercaya (media nasional bereputasi, KBBI, Badan Bahasa) bila pencarian web tersedia; jika tidak teruji atau tetap cacat struktur, turunkan ke verba dasar yang lugas.
5. **Rekonstruksi utuh dalam satu lintasan.** Tulis ulang paragraf secara menyatu (bukan tambal-sulam kata per kata) dengan pasif Tipe 2 yang benar untuk Persona 1/2 (`Surat itu saya tulis`, bukan `Surat itu ditulis oleh saya`), tanpa mengarang pelaku manusia fiktif, dan tetap menjaga seluruh entitas, angka, tanggal, serta polaritas negasi.
6. **Tinjauan dingin & pemeriksaan opsional (fail-open).** Baca ulang hasil secara terpisah untuk mendeteksi sisa kalke atau erosi fakta. Jika `python3` tersedia, jalankan:
   ```bash
   python3 .agents/skills/id-prose/scripts/prose_language_lint.py <berkas-hasil>
   python3 .agents/skills/anti-translationese/scripts/fact_diff.py <berkas-asli> <berkas-hasil>
   ```
   `prose_language_lint.py` bersifat penasihat (selalu exit 0), sedangkan `fact_diff.py` adalah satu-satunya gerbang deterministik pada lapisan bahasa untuk menjamin paritas entitas, angka, tanggal, dan negasi.

## Rules & Boundaries

- Gunakan `id-prose` untuk rekonstruksi menyeluruh; untuk audit dan perbaikan kalimat terbatas tanpa perombakan total, gunakan `anti-translationese`.
- Dilarang mengarang aktor manusia baru atau mengubah fakta, angka, tanggal, maupun tingkat kepastian klaim asli.
- Pertahankan istilah kerja asing yang baku di bidang pembaca; dilarang melakukan indonesianisasi paksa.
- Hanya `fact_diff.py` yang bertindak sebagai gerbang pemblokir; linter frasa hanya memberi sinyal untuk dinilai ulang oleh penalaran agen.

## Output & Verification

1. Teks hasil bersih dari kalke Inggris, subjek inanimat artifisial, verba hampa, dan metafora fisik pada konsep abstrak sesuai `writing-style/prose-writing-style.md`.
2. Bila Python tersedia, `fact_diff.py` keluar dengan kode 0 (paritas fakta dan negasi terjaga) dan temuan `prose_language_lint.py` sudah ditinjau.
3. Sajikan teks hasil (atau jalur berkas yang disunting) bersama ringkasan perubahan pokok dan status pemeriksaan fakta.
