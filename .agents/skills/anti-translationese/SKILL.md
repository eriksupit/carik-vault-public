---
name: anti-translationese
description: >-
  Audit and repair Indonesian sentences that read like translated English using writing-style/prose-writing-style.md and optional check_sentences.py plus fact_diff.py checks. Use when the owner says "cek translationese", "perbaiki kalimat kaku", "ubah ke S-P-O-K", or "audisi bahasa Indonesia".
---

# anti-translationese

## Purpose

Mengaudit dan memperbaiki kalimat atau paragraf Bahasa Indonesia yang sudah ada agar lepas dari struktur terjemahan Inggris, nominalisasi kaku, gaya sastrawi berlebihan, pronomina `dia/ia` untuk benda tak bernyawa, dan indonesianisasi paksa atas istilah kerja baku. Skill ini menjaga makna, rantai sebab-akibat, serta fakta tetap utuh dengan mengacu pada `writing-style/prose-writing-style.md`.

## Procedure

1. **Baca pedoman gaya dan tentukan mode.** Buka `writing-style/prose-writing-style.md` sebelum memulai. Tentukan mode sesuai permintaan pemilik:
   - **AUDIT (lapor saja):** diagnosis temuan dan arah perbaikan tanpa menyunting berkas.
   - **EDIT (perbaikan aman):** tulis hasil perbaikan ke `<nama>-edited.md` (jangan menimpa berkas asli kecuali diminta eksplisit), sambil mempertahankan frontmatter, heading, blok kode, `[[wikilink]]`, angka, dan nama diri.
2. **Jalankan telemetri permukaan opsional (fail-open).** Bila `python3` tersedia, jalankan pemeriksaan penasihat:
   ```bash
   python3 .agents/skills/anti-translationese/scripts/check_sentences.py <berkas> --genre <narrative|expository>
   ```
   Skrip selalu keluar dengan kode 0; setiap tanda (panjang kalimat, repetisi pembuka, istilah paksa) adalah pertanyaan untuk dinilai oleh agen, bukan perintah buta.
3. **Audit makna dan tiga lapis kalke (agen memimpin):**
   - **Lapis L1 (leksikal & frasa):** idiom terjemahan (`pada akhir hari` → `pada akhirnya`, `mengambil tempat` → `berlangsung`), rantai kata fungsi (`dalam rangka untuk` → `untuk`), pleonasme aspek (`sedang dalam proses` → `sedang`).
   - **Lapis L2 (sintaksis & diatesis):** pasif `di- + oleh + Persona 1/2` → pasif Tipe 2 (`sudah saya susun`), preposisi mubazir pada verba transitif (`membahas tentang` → `membahas`), subjek abstrak berkehendak, nominalisasi beruntun, dan klausa cleft Inggris (`Apa yang membuat X penting adalah Y` → `X penting karena Y`).
   - **Lapis L3 (wacana & animasi):** sambungan mekanis berulang (`Sementara itu`, `Di sisi lain`), penerjemahan mekanis `a/the` (`sebuah`, `tersebut`), serta penggunaan `dia/ia` untuk benda/sistem non-manusia (ganti dengan pelesapan, pengulangan nomina, atau `-nya` yang alami).
4. **Perbaiki dalam satu lintasan utuh (mode EDIT).** Gunakan register formal-sederhana yang wajar diucapkan kepada rekan kerja, susun klausa ke S-P-O-K kanonik, pasif Tipe 2, atau topik-komen yang alami, dan pertahankan istilah kerja asing baku (`output`, `input`, `download`, `upload`, `error`, `browser`, `link`, `commit`, `branch`).
5. **Verifikasi ganda (opsional fail-open).** Jika `python3` tersedia, jalankan ulang `check_sentences.py` dan gerbang paritas fakta:
   ```bash
   python3 .agents/skills/anti-translationese/scripts/fact_diff.py <berkas-asli> <berkas-hasil>
   ```
   Pastikan `fact_diff.py` keluar dengan kode 0 (seluruh entitas, angka, tanggal, dan negasi cocok). Bila ditemukan pelajaran bahasa baru yang layak diingat lintas sesi, catat melalui `session-log`.

## Rules & Boundaries

- Makna dan kejelasan sebab-akibat selalu mengungguli angka metrik panjang kalimat; kalimat panjang yang jernih tidak boleh dipecah paksa menjadi potongan patah.
- Dilarang memakai register sastrawi, bahasa mesin (`telah dilakukan perubahan`), atau indonesianisasi paksa (`keluaran`, `unduh`, `galat`, `peramban`, `pranala`) pada teks kerja.
- Untuk perombakan total teks dengan pembuktian kolokasi web, serahkan ke `id-prose`.
- Dilarang menyunting berkas selain teks sasaran yang diminta; `fact_diff.py` adalah satu-satunya gerbang keras pada lapisan bahasa.

## Output & Verification

1. Mode AUDIT: daftar temuan per paragraf (L1–L3 dan makna), vonis (`pass` atau `needs-work`), serta arah perbaikan ringkas tanpa mengubah berkas.
2. Mode EDIT: berkas hasil tertulis aman, `fact_diff.py` lulus (kode keluar 0 bila Python tersedia), dan daftar perubahan utama (`kutipan asli → masalah → perbaikan`) dilaporkan secara ringkas.
3. Seluruh istilah kerja baku dan fakta asli terverifikasi tidak mengalami pergeseran makna.
