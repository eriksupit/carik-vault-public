---
name: scratchpad
description: >-
  Maintain a live discussion scratchpad in .agents/sessions/YYYY-MM-DD--<topic>-scratchpad.md triggered semantically or on owner request, without context-window scripts or Python. Use when the owner says "catat di scratchpad", "buat scratchpad", "simpan obrolan ini", or "perbarui scratchpad".
---

# scratchpad

## Purpose

Menyediakan ruang catat hidup berbasis berkas teks terbuka selama diskusi panjang, curah gagasan, atau perumusan konsep berlangsung agar butir keputusan dan perubahan arah tidak hilang saat obrolan memanjang. Skill ini berjalan penuh secara bebas-Python tanpa skrip pemantau *context window* di seluruh aplikasi GUI maupun CLI.

## Procedure

1. **Kenali waktu yang tepat untuk membuka atau memperbarui *scratchpad*:**
   - **Proaktif (semantik):** begitu obrolan penjajakan mencapai minimal 3 putaran substantif, memunculkan minimal 2 keputusan atau revisi yang saling berkaitan, atau mulai membahas beberapa berkas sekaligus, beri tahu pemilik secara singkat dan sarankan pencatatan ke `.agents/sessions/`.
   - **Permintaan langsung:** jalankan segera setiap kali pemilik meminta obrolan dicatat ke *scratchpad*.
2. **Tetapkan nama berkas tanpa menimpa catatan lama.** Gunakan pola `.agents/sessions/YYYY-MM-DD--<slug-topik>-scratchpad.md` (buat folder `.agents/sessions/` bila belum ada). Jika *scratchpad* untuk topik dan tanggal yang sama sudah ada, perbarui isinya secara rapi; jangan menimpa *scratchpad* dari tanggal atau topik lain.
3. **Susun isi dalam tiga bagian tetap.** Awali dengan YAML *frontmatter* (`title`, `date`, `updated`, `type: session-scratchpad`, `status: draft`, `tags`) yang diisi otomatis oleh agen, diikuti tiga bagian:
   - `## 1. Rumusan Terpadu` berisi rangkuman paling mutakhir atas konsep, rencana, atau kesepakatan sementara saat ini.
   - `## 2. Catatan Putaran Diskusi` berisi ringkasan kronologis per putaran (usulan, koreksi, alasan, dan keputusan pemilik).
   - `## 3. Poin Terbuka dan Tindak Lanjut` berisi pertanyaan yang belum diputuskan serta daftar langkah kerja berikutnya (misalnya draf yang siap dipindahkan ke `work/concept/`, `work/drafts/`, `work/canon/`, atau `notes/`).
4. **Jaga pemisahan peran antar-ruang ingatan Carik Vault.** Gunakan *scratchpad* khusus sebagai papan coretan selama diskusi masih bergerak, dan jangan mencampurkannya dengan `notes/meeting-minutes/` (notulen rapat resmi lewat `notulen`), `.agents/Memory.md` (fakta jangka panjang lewat `remember`), `.agents/Context.md` (log kejadian sesi lewat `session-log`), atau `handoff/` (paket serah-terima tutup sesi).
5. **Baca ulang berkas sebelum melapor.** Periksa kembali berkas `.agents/sessions/YYYY-MM-DD--<slug-topik>-scratchpad.md` yang baru ditulis, lalu laporkan lokasinya secara deklaratif kepada pemilik.

## Rules & Boundaries

- Dilarang bergantung pada skrip pendeteksi *context window*, Python, direktori global di luar vault, atau aplikasi Obsidian sebagai syarat jalan.
- Dilarang mencatat kata sandi, kunci API, token rahasia, atau kredensial pribadi ke dalam `.agents/sessions/`.
- Dilarang menghapus atau menimpa berkas *scratchpad* dari hari atau topik sebelumnya agar riwayat pemikiran tetap terjaga.
- Sebelum memindahkan hasil rumusan dari *scratchpad* menjadi dokumen tetap di `work/concept/`, `work/drafts/`, `work/canon/`, `notes/`, `AGENTS.md`, `CREATIVE-LAW.md`, atau `.agents/Memory.md`, sampaikan ringkasan tujuan dan pokok isinya terlebih dahulu untuk disetujui pemilik.

## Output & Verification

1. Berkas `.agents/sessions/YYYY-MM-DD--<slug-topik>-scratchpad.md` tersimpan lengkap dengan YAML *frontmatter* dan tiga bagian baku (`Rumusan Terpadu`, `Catatan Putaran Diskusi`, `Poin Terbuka dan Tindak Lanjut`).
2. Hasil baca ulang membuktikan tidak ada bagian yang terpotong dan tidak ada data kredensial rahasia yang ikut tertulis.
3. Laporkan jalur berkas dan intisari pembaruan yang baru dicatat dalam Bahasa Indonesia lugas dengan penutup deklaratif.
