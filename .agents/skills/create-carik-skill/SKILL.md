---
name: create-carik-skill
description: >-
  Guide non-technical owners through a one-question-per-turn interview to design, write, verify, and user-test a new local skill conforming to .agents/skills/CARIK-SKILLS-FORMAT.md. Use when the owner says "buat skill baru", "bikin skill carik", "tambah keahlian baru", or "rancang skill".
---

# create-carik-skill

## Purpose

Membantu pemilik atau pengguna awam merancang, menulis, memverifikasi, dan menguji skill lokal baru di `.agents/skills/<nama-skill>/SKILL.md` melalui percakapan bertahap tanpa formulir kaku dan tanpa beban istilah teknis. Seluruh aturan format, template, dan daftar cek merujuk langsung ke `.agents/skills/CARIK-SKILLS-FORMAT.md` sebagai satu-satunya sumber kebenaran format.

## Procedure

1. **Pindai awal secara diam-diam.** Periksa isi direktori `.agents/skills/` terlebih dahulu untuk mencegah duplikasi. Jika kebutuhan pemilik sudah tercakup oleh skill aktif yang ada, rekomendasikan memakai atau memperluas skill tersebut daripada membuat skill baru.
2. **Jalankan wawancara bertahap — tepat satu pertanyaan per giliran pesan.** Lewati pertanyaan yang sudah terjawab eksplisit pada giliran sebelumnya, dan jangan pernah menyodorkan daftar banyak pertanyaan sekaligus:
   - **Giliran 1 (Tujuan & konteks):** tanyakan skill baru ini untuk apa dan dalam situasi apa pemilik akan memakainya.
   - **Giliran 2 (Masalah inti, nama, & pemicu):** tanyakan masalah utama yang paling sering mengganggu saat ini, lalu ajukan **satu rekomendasi** rumusan masalah, calon nama `kebab-case`, dan minimal 3 frasa pemicu Bahasa Indonesia yang natural (ikuti `anti-sycophancy` dan `recommend`; dilarang menu opsi).
   - **Giliran 3 (Alur kerja masukan ke keluaran):** tanyakan apa yang biasanya diberikan pemilik dan hasil apa yang diharapkan, lalu ajukan **satu rekomendasi** alur kerja *file-first* bebas-Python beserta batasan utamanya.
3. **Tetapkan keputusan teknis secara mandiri.** Jangan membebani pengguna awam dengan keputusan teknis. Agen memutuskan dan menjelaskan alasannya dalam Bahasa Indonesia sederhana apakah cukup satu berkas `SKILL.md` murni (bawaan `.agents/skills/CARIK-SKILLS-FORMAT.md`) atau membutuhkan skrip opsional *fail-open* / berkas `references/`, dengan tetap menjaga `0` ketergantungan global, `0` instalasi perangkat lunak otomatis, dan kepatuhan pada `.agents/hooks/vault-boundary-guard.py`.
4. **Sajikan rekap wawancara dan tahan eksekusi.** Tampilkan satu blok rekap ringkas sebelum menulis berkas apa pun:
   - **Nama skill:** `<nama-kebab-case>`
   - **Tujuan & konteks:** `<ringkasan 1–2 kalimat>`
   - **Masalah inti:** `<masalah yang diselesaikan>`
   - **Frasa pemicu (ID):** `<minimal 3 frasa natural>`
   - **Ringkasan alur kerja:** `<masukan → langkah utama → keluaran>`
   - **Keputusan struktur & perkakas (oleh agen):** `<1 berkas SKILL.md murni / + skrip fail-open atau references/ beserta alasannya>`
   - **Jalur target:** `.agents/skills/<nama-kebab-case>/SKILL.md`
   Nyatakan secara deklaratif bahwa penulisan berkas ditahan sampai pemilik menyatakan setuju.
5. **Tulis berkas dan verifikasi.** Setelah pemilik menyetujui eksekusi:
   - Baca `.agents/skills/CARIK-SKILLS-FORMAT.md` dan tulis `.agents/skills/<nama-kebab-case>/SKILL.md` mengikuti seluruh 6 aturan bakunya secara ketat.
   - Jika `.agents/skills/manifest.json` ada di vault, daftarkan entri skill baru pada `harness_owned` dengan `"publish_user": false`.
   - Periksa seluruh butir pada Daftar Cek Verifikasi di `.agents/skills/CARIK-SKILLS-FORMAT.md` secara manual (jalur utama bebas-Python). Jika `python3` dan `scripts/sync-skills.py` tersedia, jalankan pemeriksaan opsional *fail-open* `python3 scripts/sync-skills.py --check` (`errors=0`).
6. **Gerbang uji coba oleh pengguna.** Setelah berkas jadi dan lolos verifikasi, laporkan lokasi berkasnya lalu **minta pemilik langsung mencobanya** dengan menyertakan **satu contoh kalimat pemicu siap pakai**. Jika hasil uji coba belum sesuai harapan pemilik, revisi berkas `SKILL.md` yang sama, ulangi verifikasi, dan minta uji ulang hingga tuntas.

## Rules & Boundaries

- Merujuk langsung ke `.agents/skills/CARIK-SKILLS-FORMAT.md`; dilarang menyalin ulang seluruh aturan atau template panjangnya ke dalam percakapan maupun skill baru.
- Dilarang mengajukan lebih dari satu pertanyaan per giliran wawancara, dan dilarang melempar menu opsi tanpa pilihan.
- Dilarang menulis `.agents/skills/<nama>/SKILL.md` sebelum rekap wawancara disetujui secara eksplisit oleh pemilik.
- Dilarang membuat berkas `agents/openai.yaml`, memasang perangkat lunak otomatis, bergantung pada direktori global, atau menuntut aplikasi desktop Obsidian sebagai runtime.

## Output & Verification

1. Berkas `.agents/skills/<nama-kebab-case>/SKILL.md` terbit rapi dan memenuhi seluruh butir Daftar Cek Verifikasi pada `.agents/skills/CARIK-SKILLS-FORMAT.md` (serta terdaftar `publish_user: false` di `.agents/skills/manifest.json` bila manifest ada).
2. Jika Python tersedia, `python3 scripts/sync-skills.py --check` selesai dengan `errors=0`.
3. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana lokasi berkas skill baru, ringkasan cara kerjanya, dan satu contoh kalimat pemicu siap pakai untuk uji coba langsung.
