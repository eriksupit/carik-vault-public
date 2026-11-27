---
name: scratchpad
description: >-
  Maintain a live discussion scratchpad in .agents/sessions/YYYY-MM-DD--<topic>-scratchpad.md triggered semantically or on owner request, without context-window scripts. Use when the owner says "catat di scratchpad", "buat scratchpad", "simpan obrolan ini", or "perbarui scratchpad".
---

# scratchpad

## Purpose

Menyediakan ruang catat hidup berbasis berkas teks terbuka selama diskusi, eksplorasi konsep, atau perancangan berlangsung agar keputusan dan revisi tidak hilang oleh batas *context window* maupun kompresi sesi. Skill ini berjalan penuh tanpa Python dan tanpa skrip detektor *context window* lintas 12 *harness*.

## Procedure

1. **Deteksi pemicu semantik atau permintaan langsung pemilik.**
   - **Proaktif (semantik):** begitu diskusi eksploratif menyentuh $\ge 3$ putaran substantif, muncul $\ge 2$ keputusan atau revisi yang saling terkait, atau topik mulai bercabang lintas berkas, beri tahu pemilik secara singkat dan rekomendasikan pembuatan atau pembaruan *scratchpad* di `.agents/sessions/`.
   - **Langsung:** jalankan segera bila pemilik meminta mencatat ke *scratchpad*.
2. **Tentukan nama berkas tanpa menimpa arsip lama.** Gunakan jalur `.agents/sessions/YYYY-MM-DD--<slug-topik>-scratchpad.md`. Jika berkas sesi hari yang sama sudah aktif untuk topik yang sama, perbarui berkas itu secara terstruktur; jangan menimpa *scratchpad* dari tanggal atau topik berbeda.
3. **Tulis atau perbarui dengan tiga bagian baku.** Gunakan frontmatter YAML (`title`, `date`, `updated`, `type: session-scratchpad`, `status: draft`, `tags`) diikuti:
   - `## 1. Rumusan Terpadu` — versi terbaru konsep, keputusan, atau desain yang sudah disepakati sementara.
   - `## 2. Catatan Putaran Diskusi` — ringkasan kronologis per putaran (koreksi, alasan, dan keputusan pemilik).
   - `## 3. Poin Terbuka dan Tindak Lanjut Tertunda` — celah yang belum diputus dan daftar langkah berikutnya.
4. **Mode *Worker Checkpoint* (khusus *worker* tugas multi-langkah):**
   - **Jalur:** `.agents/sessions/workers/<nama-worker>-<slug-tugas>.md` (ditetapkan *supervisor* pada *brief* delegasi, masuk *write boundary* *worker*, dan diabaikan Git secara default). *Worker* sekali tembak (*one-shot*) dikecualikan.
   - **4 Parameter Pemicu Otomatis** (perbarui berkas setiap kali salah satu terpenuhi): (a) selesai 1 *milestone* atau 1 rangkaian tes/build, (b) sudah $\ge 3$ kali suntingan berkas atau $\ge 5$ langkah baca/eksekusi berturut-turut pada tugas yang sama, (c) menemui galat/blokir/jalan buntu (catat apa yang dicoba dan penyebab gagalnya sebelum beralih cara), atau (d) tepat sebelum mengirim status `DONE`, `BLOCKED`, atau `NEEDS_CONTEXT` ke *supervisor*.
   - **Format padat (4 bagian):** *Tujuan & Batas Tulis*, *Progres & Bukti Uji*, *Keputusan & Jalan Buntu*, dan *Langkah Tersisa* (bukan transkrip mentah *context window*).
5. **Pisahkan tegas dari empat lapisan kontinuitas lain.** Jangan mencampurkan isi *scratchpad* (draf kerja hidup atau *checkpoint* *worker*) dengan `notes/meeting-minutes/` (notulen pasca-rapat), `.agents/Memory.md` (fakta permanen bersumber), `.agents/Context.md` (kronologi sesi ringkas), atau `handoff/` (serah-terima tutup sesi).
6. **Baca ulang berkas sebelum melapor.** Verifikasi baris yang baru ditulis dan laporkan lokasi berkas secara deklaratif.

## Rules & Boundaries

- Dilarang bergantung pada skrip detektor *context window*, Python, direktori global, atau aplikasi Obsidian sebagai *runtime*.
- Dilarang menyimpan kredensial, token, kata sandi, atau data rahasia dalam teks terbuka di `.agents/sessions/`.
- Dilarang menimpa atau menghapus *scratchpad* tanggal sebelumnya; berkas lama tetap menjadi jejak keputusan.
- Pengukuhan isi *scratchpad* ke dokumen kanonis (`CREATIVE-LAW.md`, `docs/design/`, `AGENTS.md`, atau `Memory.md`) wajib melewati persetujuan *Summary-First* dari pemilik.

## Output & Verification

1. Berkas `.agents/sessions/YYYY-MM-DD--<slug-topik>-scratchpad.md` tersimpan dengan frontmatter lengkap dan tiga bagian baku (`Rumusan Terpadu`, `Catatan Putaran Diskusi`, `Poin Terbuka dan Tindak Lanjut Tertunda`).
2. Baca ulang bagian yang ditulis untuk memastikan tidak ada fakta yang terpotong dan tidak ada data rahasia yang ikut tertulis.
3. Laporkan jalur berkas dan ringkasan butir yang baru dicatat dalam Bahasa Indonesia lugas dengan penutup deklaratif.
