---
name: orient
description: >-
  Run first-contact vault orientation when no Orientation completed marker exists in .agents/Context.md, or on /orient, verifying core governance files internally, logging the marker, and greeting the owner briefly (100% Python-free). Use when the owner says "orient", "pahami vault ini", "onboard", or "kenali vault ini".
---

# orient

## Purpose

Membangun pemahaman utuh atas struktur dan aturan kerja Carik Vault pada **kontak pertama** (ketika belum ada penanda `Orientation completed` di `.agents/Context.md`) atau saat pemilik memanggil `/orient`. Skill ini berjalan 100% bebas-Python: agen memeriksa berkas inti secara menyeluruh di belakang layar, mencatat penanda selesai di `.agents/Context.md`, lalu menyapa pemilik dengan singkat dan ramah tanpa membanjiri layar dengan laporan teknis.

## Procedure

1. **Baca 9 berkas inti secara berurutan di belakang layar.** Jangan melompati urutan dan jangan menebak dari ingatan model:
   - Inti aturan kerja: `SCOPE.md`, `README.md`, `WORKFLOW.md`, dan `AGENTS.md` (ditambah `ATURAN-LOKAL.md` jika tersedia di akar vault).
   - Ingatan dan log sesi: `.agents/Memory.md`, `.agents/Context.md`, serta `.agents/Lessons.md` (buka berkas di `.agents/memory/` hanya bila relevan dengan tugas aktif).
   - Panduan gaya dan daftar sumber: `writing-style/prose-writing-style.md` dan `raw-kb/SOURCES.md`.
   - Bila melanjutkan pekerjaan lama, baca juga pasangan terbaru di `handoff/`.
2. **Pastikan 9 pokok tata kelola secara internal (tanpa menumpahkannya ke chat):** pastikan agen telah memverifikasi langsung dari berkas aktual tentang (1) peran `AGENTS.md` sebagai satu sumber aturan lintas aplikasi, (2) urutan baca sebelum kerja, (3) pembagian **Zona Kerja Harian** dan **Zona Pendukung**, (4) alur 5 folder di `work/` (`inbox`, `concept`, `drafts`, `canon`, `archive`), (5) prinsip *File-Over-App* dan *Progressive Enhancement*, (6) aturan `raw-kb/SOURCES.md` dan konversi PDF, (7) fungsi `.agents/{Context,Lessons,Memory}.md`, (8) aturan bahasa lugas tanpa menu opsi dan tanpa pertanyaan validasi di akhir pesan, serta (9) daftar 30 skill publik berformat `CARIK-SKILLS-FORMAT.md`. Tampilkan rincian kutipan baris (`file:line`) di chat **hanya jika** pemilik secara eksplisit memintanya.
3. **Catat penanda selesai secara ringkas di `.agents/Context.md`.** Tambahkan satu entri di bagian paling bawah `.agents/Context.md`:
   ```markdown
   ## [YYYY-MM-DD] Orientation completed
   - Orientasi kontak pertama selesai (9 berkas inti dan alur kerja 5-folder Carik Vault terverifikasi).
   ```
   Jika `.agents/Context.md` belum ada, sampaikan kepada pemilik sebelum membuat berkas baru.
4. **Sapa pemilik cukup dalam 2 sampai 3 kalimat ramah.** Gunakan Bahasa Indonesia sehari-hari yang sopan dan jelas: kabarkan bahwa Anda sudah membaca aturan dan struktur Carik Vault, sebutkan fokus kerja di `SCOPE.md` saat ini (atau ajak pemilik menyebutkan pekerjaan pertamanya bila `SCOPE.md` masih kosong/awal), lalu tutup dengan pernyataan siap membantu.

## Rules & Boundaries

- Dilarang menampilkan dinding audit teknis 9 poin `file:line` kepada pengguna awam pada sapaan kontak pertama, kecuali diminta secara eksplisit.
- Dilarang melewati pembacaan berkas asli atau mencatat `Orientation completed` sebelum kesembilan berkas inti benar-benar dibaca.
- Dilarang menyalin ulang isi aturan ke catatan baru sebagai sumber kebenaran kedua.
- Lewati orientasi penuh pada sesi berikutnya bila penanda `Orientation completed` sudah tercatat di `.agents/Context.md`; cukup jalankan pembacaan ringan atau `bootstrap`.
- Seluruh prosedur 100% bebas-Python, bebas Git, dan bebas terminal.

## Output & Verification

1. Kesembilan berkas inti telah dibaca langsung dan dipahami secara internal oleh agen.
2. Entri `## [YYYY-MM-DD] Orientation completed` tercatat rapi di bagian paling bawah `.agents/Context.md` (terverifikasi dengan membaca ulang bagian akhir berkas).
3. Balasan chat ke pemilik terdiri atas 2 sampai 3 kalimat ramah berbahasa Indonesia yang menyebut fokus `SCOPE.md` dan ditutup secara deklaratif tanpa daftar audit teknis.
