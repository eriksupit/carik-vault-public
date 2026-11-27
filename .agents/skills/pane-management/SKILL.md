---
name: pane-management
description: >-
  Coordinate multi-pane sandboxed Herdr teams (omp, pi, agy) via spawn-team.sh, report.sh, record-report.sh, audit-writes.sh, and teardown-team.sh with disjoint write boundaries. Use when the owner says "siapkan pane", "atur pane", "buat tim pane", or "teardown pane".
---

# pane-management

## Purpose

Mengatur pembentukan, koordinasi, verifikasi laporan, audit batas tulis, dan pembubaran tim multi-agen di dalam Herdr (`HERDR_ENV=1`) pada macOS menggunakan sandbox OS (`sandbox-exec`). Seluruh mekanisme operasional dijalankan melalui skrip di `.agents/skills/pane-management/scripts/` sehingga supervisor murni berkoordinasi dan setiap sub-agen bekerja di batas tulis yang saling lepas.

## Procedure

1. **Tetapkan lokasi skrip lokal dan cek platform.** Gunakan direktori `.agents/skills/pane-management` di akar proyek sebagai sumber utama (`PM=".agents/skills/pane-management"`). Pastikan berjalan di dalam Herdr (`HERDR_ENV=1`) dan `sandbox-exec` tersedia di macOS; jika bukan, hentikan dan laporkan.
2. **Baca pasangan handoff terbaru dan tentukan prefix.** Ambil `handoff/INITIAL-PROMPT-*.txt` terbaru beserta pasangan `handoff/HANDOFF-<suffix>.md`, lalu turunkan `<prefix>` singkat agar `<prefix>-<role>` tidak melebihi 32 karakter (`^[a-z][a-z0-9_-]{0,31}$`).
3. **Rancang dan uji roster dengan `--dry-run`.** Pilih peran dari `references/roster-archetypes.md` (maksimal 8 sub-agen, 4 per tab; hanya peran `integrator` yang boleh dan wajib menulis `.git/`; semua model Gemini `gemini-*` wajib memakai engine `agy`, bukan `omp`/`pi`). Validasi tanpa menulis berkas lewat:
   ```bash
   jq -n '<roster JSON>' | bash "$PM/scripts/spawn-team.sh" --dry-run -
   ```
   Perbaiki semua penolakan hingga keluar `ROSTER OK`, sajikan tabel roster kepada pemilik, dan tunggu persetujuan eksplisit sebelum spawn.
4. **Spawn tim dan verifikasi handshake.** Setelah pemilik menyetujui, jalankan:
   ```bash
   jq -n '<approved roster JSON>' | bash "$PM/scripts/spawn-team.sh" -
   ```
   Skrip menulis `roster.json`, `run.env`, `baseline.tsv`, kartu peran (`roles/<name>.md`), profil sandbox (`sandbox/<name>.sb`), `pane-map.md`, meluncurkan tiap agen di bawah `sandbox-exec`, dan mengirim handshake (`references/handshake-templates.md`).
5. **Catat laporan dan verifikasi kesiapan (`READY n/n`).** Setiap sub-agen melapor lewat `bash "$PM/scripts/report.sh" <supervisor-pane> <name> "STATUS: <DONE|BLOCKED|NEEDS_CONTEXT> — <ringkasan>"`. Supervisor memverifikasi kotak masuk dengan:
   ```bash
   bash "$PM/scripts/record-report.sh" --inbox <state_dir>/roster.json
   ```
   Tangani pane bermasalah (baca pane, perbaiki, atau `teardown-team.sh` + respawn) hingga `READY n/n`, lalu masuk mode siaga sampai pemilik memberi perintah kerja.
6. **Delegasi, audit batas tulis, dan teardown.** Kirim tugas lewat `herdr agent prompt` ke pane pemiliknya. Sebelum menyatakan satu unit kerja solid, wajib jalankan:
   ```bash
   bash "$PM/scripts/audit-writes.sh" <state_dir>/roster.json
   ```
   (harus exit 0, plus laporan `STATUS: DONE` dari reviewer/auditor). Setelah seluruh pekerjaan selesai, tutup tim dengan `bash "$PM/scripts/teardown-team.sh" <state_dir>/roster.json`.

## Rules & Boundaries

- **Kontrak Supervisor:** supervisor **hanya berkoordinasi** dan dilarang menyunting/membuat/menghapus berkas secara manual, menulis handoff/log, atau menjalankan perintah Git/GH bermutasi (`add`, `commit`, `push`, `merge`, `gh pr create/merge`). Semua perubahan dilakukan pane pekerja atau skrip skill ini.
- **Batas tulis saling lepas:** tidak boleh ada dua agen dengan jalur tulis sama atau saling menaungi; `.git/` khusus `integrator`; agen read-only memakai `write: []`.
- **Periksa jalur *Worker Checkpoint* dalam brief delegasi:** saat brief tugas multi-langkah menetapkan `.agents/sessions/workers/<nama-worker>-<slug-tugas>.md`, pastikan jalur itu masuk `write` worker penerima di `roster.json`; bila tidak, perluas batas tulisnya lewat respawn yang disetujui pemilik atau tetapkan jalur *checkpoint* di dalam batas tulis yang sudah ada, sebelum tugas dikirim. Agen read-only (`write: []`) dikecualikan dari *Worker Checkpoint* dan cukup melapor lewat `report.sh`.
- **Jangan menghapus skrip fungsional** (`spawn-team.sh`, `report.sh`, `record-report.sh`, `audit-writes.sh`, `teardown-team.sh`) dan berkas referensi di folder skill ini.
- **Gerbang persetujuan:** dilarang melakukan spawn pane sebelum pemilik menyetujui roster, dan dilarang mengirim `/bootstrap` atau tugas sebelum pemilik memerintahkannya.

## Output & Verification

1. Tahap persiapan: `spawn-team.sh --dry-run -` mencetak `ROSTER OK`, `spawn-team.sh -` keluar dengan kode 0, dan `record-report.sh --inbox` mencapai `READY n/n`.
2. Tahap penutupan unit kerja: `audit-writes.sh <state_dir>/roster.json` keluar dengan kode 0 tanpa pelanggaran batas tulis.
3. Laporkan status kesiapan atau hasil audit secara ringkas (maksimal 6 baris pada kesiapan awal) dalam Bahasa Indonesia kepada pemilik.
