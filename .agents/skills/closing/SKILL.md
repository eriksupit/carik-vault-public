---
name: closing
description: >-
  Close a working session cleanly without coding workflows: write a mandatory session recap in notes/, update durable memory via remember, log events and lessons via session-log, refresh SCOPE.md if changed, and create a handoff pair when continuing. Use when the owner says "closing", "tutup sesi", "akhiri sesi", or "selesai hari ini".
---

# closing

## Purpose

Menutup sesi kerja secara rapi melalui satu pintu untuk alur non-coding agar seluruh hasil kerja, ingatan permanen, dan tata kelola vault selalu mutakhir lintas sesi. Skill ini mengorkestrasi `remember`, `session-log`, pembaruan `SCOPE.md`, penulisan rekap sesi wajib di `notes/`, serta `handoff` secara bebas-Python dan lintas 12 harness.

## Procedure

1. **Kumpulkan bukti aktual sesi.** Inventarisasi pekerjaan yang selesai, keputusan penting, daftar berkas yang dibuat atau diubah, serta apakah pekerjaan masih akan dilanjutkan pada sesi berikutnya. Periksa langsung berkas yang terkait; jangan mengarang capaian atau isi berkas dari ingatan.
2. **Tulis rekap sesi wajib ke `notes/`.** Buat satu berkas rekap baru di `notes/rekap-sesi-YYYY-MM-DD--<topik>.md` dengan frontmatter YAML standar (`title`, `date`, `updated`, `type: session-recap`, `status: active`, `tags`), berisi ringkasan capaian, keputusan utama, daftar berkas yang berubah, dan tindak lanjut (jika ada). Jika nama berkas sudah terpakai, tambahkan akhiran waktu (`-HHMM`) agar tidak menimpa berkas lama.
3. **Simpan fakta permanen baru lewat `remember`.** Pindahkan keputusan, istilah, atau preferensi jangka panjang yang muncul pada sesi ini ke `.agents/memory/<fakta>.md` dan perbarui indeks `.agents/Memory.md`. Lewati langkah ini jika tidak ada fakta permanen baru.
4. **Catat posisi akhir dan pelajaran lewat `session-log`.** Tambahkan entri posisi akhir sesi ke `.agents/Context.md` dan catat koreksi atau pelajaran penting (jika ada) ke `.agents/Lessons.md`. Jika berkas melewati ambang ukuran atau jumlah entri, jalankan rotasi arsip non-destruktif (`ARCHIVE`) ke `.agents/archive/`.
5. **Perbarui `SCOPE.md` bila fokus berubah.** Jika tujuan aktif, batas cakupan, atau daftar artefak berubah selama sesi, perbarui `SCOPE.md` agar tetap mencerminkan keadaan terbaru. Jika tidak ada perubahan lingkup, biarkan `SCOPE.md` apa adanya.
6. **Buat pasangan serah-terima lewat `handoff` saat sesi berlanjut.** Jika pekerjaan akan dilanjutkan pada sesi berikutnya (atau pemilik meminta prompt pembuka sesi baru), jalankan `handoff` untuk menulis pasangan `handoff/HANDOFF-<suffix>.md` dan `handoff/INITIAL-PROMPT-<suffix>.txt` dengan blok `## Goal` identik. Jika sesi sudah tuntas tanpa kelanjutan, jangan menulis `INITIAL-PROMPT-*.txt` agar `bootstrap` pada sesi baru tidak menarik pekerjaan yang sudah selesai.
7. **Jalankan pemeriksaan opsional (*fail-open*).** Jika `python3` dan `scripts/governance_store.py` tersedia, jalankan `python3 scripts/governance_store.py check`. Jika vault memakai Git dan perintah `git` tersedia, periksa `git status --short` untuk melaporkannya kepada pemilik tanpa menjalankan commit atau push otomatis; jika tidak, laporkan `Git: tidak tersedia di lingkungan ini` tanpa mengarang status Git.

## Rules & Boundaries

- Seluruh langkah non-destruktif (menulis rekap sesi baru ke `notes/`, menambah entri ke `.agents/Context.md` dan `.agents/Lessons.md`, menyimpan fakta baru ke `.agents/Memory.md`, menyelaraskan `SCOPE.md` bila berubah, dan membuat pasangan `handoff` saat sesi berlanjut) wajib dijalankan langsung tanpa menunggu syarat "bila diminta".
- Tindakan berpotensi destruktif atau mengubah keadaan luar — menimpa berkas lama, menghapus atau mengosongkan (`PURGE`) log maupun arsip, serta menjalankan `git commit` atau `git push` — wajib ditahan sampai pemilik memberi persetujuan eksplisit.
- Skill ini khusus penutupan sesi kerja non-coding: tidak menjalankan audit diff kode paksa, rangkaian tes perangkat lunak, maupun pengelolaan cabang Git.
- Seluruh pernyataan capaian, daftar berkas, dan status tindak lanjut wajib berdasar bukti berkas nyata sesuai disiplin `anti-sycophancy` dan `confidence`.
- Nol ketergantungan pada direktori global, nol instalasi perangkat lunak, dan nol ketergantungan pada aplikasi desktop Obsidian sebagai runtime.

## Output & Verification

1. Berkas rekap sesi baru ada dan terbaca di `notes/rekap-sesi-YYYY-MM-DD--<topik>.md` dengan frontmatter YAML valid serta daftar capaian dan berkas yang akurat.
2. `.agents/Context.md` memuat entri penutup terbaru (ditambah `.agents/Lessons.md`, `.agents/Memory.md`, `SCOPE.md`, dan pasangan `handoff/` sesuai kondisi sesi).
3. Bila `python3` dan berkas `scripts/governance_store.py` tersedia, `python3 scripts/governance_store.py check` selesai tanpa galat; bila salah satunya tidak tersedia, laporkan `pemeriksaan skrip: tidak tersedia` tanpa mengarang hasil.
4. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana secara deklaratif: lokasi berkas rekap di `notes/`, berkas tata kelola/memori yang diperbarui, status pasangan `handoff` (dibuat atau tidak karena sesi tuntas), dan status Git (jika ada).
