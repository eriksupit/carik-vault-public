---
title: Panduan Memakai Carik Vault di Harness Populer
date: 2026-11-26
updated: 2026-11-26
type: guide
status: active
tags:
  - panduan-user
  - harness
  - chatgpt-desktop
  - claude-cowork
  - antigravity
  - carik-vault
---

# Panduan Memakai Carik Vault di Harness Populer

Carik Vault dirancang agar satu folder yang sama bisa dibuka di berbagai aplikasi AI tanpa mengubah format catatan Anda. Aturan kerja (`AGENTS.md`), alur 5 folder, dan 30 skill adalah perilaku Carik Vault, sedangkan cara menghubungkan folder lokal, tampilan antarmuka, dan dukungan hook adalah perilaku aplikasi vendor yang dapat berubah sewaktu-waktu (informasi vendor di bawah mengacu pada keadaan per 2026-11-26).

Ikuti panduan berbasis kapabilitas di bawah untuk tiga aplikasi GUI populer, lalu pastikan koneksi selalu lewat Tes Koneksi 10 Detik.

## 1. Panduan 3 Harness GUI Populer

### 1.1 ChatGPT Desktop (macOS dan Windows)

ChatGPT versi web di browser tidak dapat membuka folder lokal di komputer Anda (per 2026-11-26). Untuk bekerja langsung dengan folder Carik Vault, Anda harus memakai aplikasi **ChatGPT Desktop** yang tersedia di macOS dan Windows.

1. Buka aplikasi **ChatGPT Desktop** di komputer Anda.
2. Hubungkan seluruh folder lokal Carik Vault sebagai ruang kerja atau folder proyek. Jangan sekadar mengunggah satu berkas ke chat biasa.
3. Kirim kalimat pembuka `"Baca AGENTS.md lalu bantu saya memulai pekerjaan hari ini."`
4. Jalankan **Tes Koneksi 10 Detik** dengan mengirim `"Sebutkan daftar folder yang ada di dalam work/ sekarang."` dan pastikan agen menjawab tepat lima folder (`inbox`, `concept`, `drafts`, `canon`, `archive`).

**Status dan catatan jujur:** Pengujian langsung pada aplikasi ChatGPT Desktop belum dilakukan terpisah. Karena menu antarmuka aplikasi vendor dapat berubah, selalu jadikan keberhasilan Tes Koneksi 10 Detik sebagai bukti bahwa folder vault benar-benar terhubung.

### 1.2 Claude Cowork (Desktop)

1. Buka aplikasi **Claude Desktop** di komputer Anda.
2. Hubungkan seluruh folder lokal Carik Vault sebagai ruang kerja Cowork (bukan mengunggah satu berkas ke chat biasa).
3. Kirim kalimat pembuka `"Baca AGENTS.md lalu bantu saya memulai pekerjaan hari ini."`
4. Jalankan **Tes Koneksi 10 Detik** untuk memastikan agen dapat melihat isi folder `work/` dan membaca aturan di `.agents/skills/`.

**Status dan catatan jujur:** Claude Cowork versi Desktop telah teruji di macOS untuk membaca `AGENTS.md`, mengenali struktur 2 zona dan 5 laci `work/`, membaca prosedur skill di `.agents/skills/`, serta membaca fakta memori lintas harness (`.agents/Memory.md` dan `.agents/memory/`) tanpa duplikasi. Uji tulis berkas baru belum dilakukan terpisah. Selain itu, pengaman hook `.claude/settings.json` tidak terbukti aktif di Cowork (berbeda dari Claude Code CLI), sehingga disiplin kerja di Cowork bertumpu pada lapisan teks `AGENTS.md`.

### 1.3 Antigravity Desktop App

1. Buka aplikasi **Antigravity Desktop App** di komputer Anda.
2. Hubungkan seluruh folder lokal Carik Vault sebagai workspace.
3. Kirim kalimat pembuka `"Baca AGENTS.md lalu bantu saya memulai pekerjaan hari ini."`
4. Jalankan **Tes Koneksi 10 Detik**. Untuk menguji penyimpanan fakta, kirim `"Tolong catat bahwa rapat mingguan jatuh setiap Senin pukul 09.00, simpan sebagai fakta."` lalu pastikan berkas fakta baru muncul di `.agents/memory/` dan tercatat di `.agents/Memory.md`.

**Status dan catatan jujur:** Antigravity Desktop App telah teruji penuh di macOS untuk membaca `AGENTS.md`, menulis catatan serta ingatan kerja ke disk lokal, dan menjalankan pengaman otomatis `.agents/hooks.json`. Pengaman otomatis tersebut aktif saat `python3` tersedia. Linux dan WSL belum diuji perangkat penuh, sedangkan pada Windows native tanpa Python atau WSL, Antigravity App berjalan lewat lapisan teks Markdown.

Perlu dicatat secara jujur bahwa untuk penulisan ke folder kerja biasa di luar folder vault, Antigravity App tidak memunculkan dialog konfirmasi otomatis dari skrip pengaman. Pagar utamanya adalah aturan percakapan di `AGENTS.md`, yang mewajibkan agen meminta izin eksplisit kepada Anda sebelum menulis ke luar vault.

> **2 Peringatan Keamanan Keras**
> 1. **Jangan menyalakan Auto-Approve tanpa batas untuk penulisan di luar workspace.** Jika aplikasi AI menawarkan mode persetujuan otomatis menyeluruh, batasi hanya untuk pekerjaan aman di dalam folder vault. Selalu tinjau izin sebelum agen menulis, mengubah, atau menghapus berkas di folder lain pada komputer Anda.
> 2. **Jangan membuka satu folder vault di dua harness secara bersamaan.** Membuka folder yang sama di dua aplikasi AI pada waktu bersamaan berisiko menimbulkan tabrakan penulisan pada `.agents/Context.md`, `.agents/Memory.md`, dan berkas draf di `work/`. Selesaikan dan tutup sesi di satu aplikasi terlebih dahulu sebelum membuka folder tersebut di aplikasi lain.

## 2. Tabel Perbandingan Jujur 3 Harness Populer

| Aspek | ChatGPT Desktop (macOS dan Windows) | Claude Cowork (Desktop) | Antigravity Desktop App |
|---|---|---|---|
| **Akses folder vault** | Hanya lewat aplikasi ChatGPT Desktop (bukan versi web, per 2026-11-26) | Langsung ke folder lokal lewat aplikasi Claude Desktop | Langsung sebagai workspace desktop |
| **Pengaman otomatis lokal** | Berjalan lewat lapisan teks `AGENTS.md`; belum diuji perangkat terpisah | Hook `.claude/settings.json` tidak terbukti aktif di Cowork (berbeda dari Claude Code CLI); bertumpu pada `AGENTS.md` | Aktif lewat `.agents/hooks.json` saat `python3` tersedia (teruji di macOS; Linux dan WSL belum diuji penuh; Windows native lewat lapisan teks) |
| **Cara update Carik (`update-carik`)** | Unduh dan ekstrak ZIP rilis baru ke subfolder `work/inbox/`, lalu minta agen memperbarui | Unduh dan ekstrak ZIP rilis baru ke subfolder `work/inbox/`, lalu minta agen memperbarui | Bisa lewat ekstraksi ZIP di subfolder `work/inbox/`, atau langsung dari GitHub publik bila terminal dan `python3` aktif |
| **Kecocokan pemakaian** | User yang sudah rutin memakai ChatGPT Desktop di macOS atau Windows dan siap memverifikasi lewat Tes Koneksi 10 Detik | User desktop yang ingin membaca dan mengolah dokumen lokal lewat antarmuka Claude | User yang menginginkan ruang kerja lokal penuh, penulisan berkas rapi, dan pengaman batas folder otomatis |

## 3. Ringkasan Harness CLI dan Editor Kode

Selain tiga aplikasi GUI di atas, seluruh 9 lingkungan CLI dan editor kode berikut membaca `AGENTS.md` yang sama sebagai sumber aturan kerja bersama:

- **Antigravity CLI (`agy`), Claude Code, dan Codex:** mendukung lapisan teks sekaligus pengaman fisik otomatis saat `python3` tersedia. Ketiganya telah teruji di macOS; Linux dan WSL belum diuji perangkat penuh, sedangkan Windows native berjalan lewat lapisan teks. Pengguna CLI yang terhubung internet dapat menjalankan pembaruan `update-carik` langsung dari repositori GitHub publik tanpa login, serta memeriksa benturan skill global lewat `python3 -B scripts/sync-skills.py --check`.
- **OhMyPi/Pi (`omp`):** berjalan lewat lapisan teks Markdown tanpa adapter hook bawaan.
- **Cursor, Windsurf, Kiro, Zed, dan DeepSeek Harness:** memakai `AGENTS.md` sebagai sumber aturan bersama dan belum diuji perangkat secara penuh. Paket publik tidak menyertakan berkas pointer khusus di luar berkas yang tercatat pada [README.md](../README.md).

## Bacaan Lanjutan

- Untuk memahami cara kerja empat elemen sistem dan solusi delapan kendala harian, baca [01-CARA-KERJA-DAN-DIAGNOSIS.md](01-CARA-KERJA-DAN-DIAGNOSIS.md).
- Untuk melihat daftar lengkap 30 skill dan contoh kalimat pemicunya, buka [03-KATALOG-SKILL-VAULT.md](03-KATALOG-SKILL-VAULT.md).
