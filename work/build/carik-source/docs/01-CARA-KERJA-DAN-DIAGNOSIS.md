---
title: Cara Kerja Carik Vault dan Diagnosis Kendala
date: 2026-11-26
updated: 2026-11-26
type: guide
status: active
tags:
  - panduan-user
  - arsitektur
  - diagnosis
  - carik-vault
---

# Cara Kerja Carik Vault dan Diagnosis Kendala

Carik Vault bekerja lewat empat elemen yang saling menopang: Model, Harness, Vault beserta 30 skill di dalamnya, dan peran Anda sebagai pengarah. Memahami batas peran keempatnya membantu Anda mendiagnosis delapan kendala lapangan tanpa menebak-nebak.

## 1. Empat Elemen Sistem Carik Vault

Carik Vault bekerja karena empat elemen yang saling menopang. Memahami batas peran masing-masing elemen membantu Anda menemukan penyebab masalah dalam hitungan detik, bukan menebak-nebak saat hasil kerja agen meleset.

### 1.1 Model (Mesin Nalar)

Model adalah kecerdasan buatan yang menganalisis masalah, menyusun argumen, merancang dokumen, dan meninjau bukti. Model sangat kuat dalam penalaran, tetapi memiliki empat batas fisik bawaan:

- **Tidak punya ingatan lintas obrolan (*stateless*).** Begitu Anda membuka jendela chat baru, Model mulai dari nol kecuali ada berkas yang dibacakan kepadanya.
- **Kapasitas baca terbatas (*context window*).** Semakin panjang satu obrolan, semakin mudah detail lama tergeser atau terlupakan oleh Model.
- **Rawan mengarang tanpa bahan rujukan.** Jika Anda bertanya tanpa menyertakan dokumen sumber, Model cenderung mengisi kekosongan dengan jawaban yang terdengar meyakinkan tetapi belum tentu benar.
- **Tidak bisa menyentuh berkas komputer sendirian.** Model hanya memproses teks. Tanpa perantara aplikasi, Model tidak bisa membaca folder, menyimpan catatan, atau menjalankan perintah di komputer Anda.

### 1.2 Harness (Infrastruktur dan Ruang Kerja)

Harness adalah aplikasi yang menghubungkan Model ke folder Carik Vault di komputer Anda, misalnya ChatGPT Desktop, Claude Cowork, Antigravity Desktop App, Claude Code, atau Codex.

Carik Vault menerapkan prinsip **Progressive Enhancement** pada lapisan Harness:

- **Lapisan teks berjalan mandiri untuk 28 skill.** Seluruh aturan kerja di `AGENTS.md`, alur 5 folder di `WORKFLOW.md`, dan 28 skill teks serta ingatan di `.agents/skills/` berbentuk teks Markdown biasa yang berjalan penuh di aplikasi GUI tanpa Python maupun terminal. Dua skill olah PDF lokal (`pdf-read` dan `pdf-ocr`) membutuhkan `python3` dan alat lokal, sehingga tidak memiliki jalur bebas-Python.
- **Pengaman fisik aktif saat Python tersedia.** Pada lingkungan yang mendukung hook dan memiliki `python3`, Harness menjalankan pagar pengaman otomatis di `.agents/hooks/public-pretool.py`. Pagar ini memblokir penulisan liar ke luar batas folder vault dan menyaring kebocoran kredensial sensitif. Jika Python tidak terpasang di komputer Anda, peluncur pengaman berhenti secara aman tanpa mengganggu pekerjaan. Dukungan hook dan akses folder ditentukan oleh masing-masing aplikasi vendor, bukan oleh Carik Vault.
- **Pagar anti sisipan perintah (*anti-prompt-injection*).** Setiap berkas rujukan di `raw-kb/` dan halaman web hasil *browsing* diperlakukan murni sebagai data pasif, bukan perintah sistem. Teks di dalam dokumen pihak ketiga atau situs web tidak pernah berwenang menimpa `AGENTS.md`, membatalkan aturan Anda, atau mengakses berkas rahasia di komputer Anda.

### 1.3 Vault dan 30 Skill di Dalamnya

Vault adalah folder teks terbuka di komputer Anda. Semua catatan, konsep, draf, hasil final, dan 30 skill di `.agents/skills/` hidup di dalam folder ini, bukan disimpan di server tertutup milik vendor aplikasi AI.

Perbedaan ini berdampak langsung pada cara ingatan kerja bertahan:

- **Memori akun vendor** terikat pada satu aplikasi dan satu akun. Jika Anda pindah dari ChatGPT ke Claude atau Antigravity, ingatan bawaan aplikasi lama tidak ikut berpindah.
- **Memori berkas terbuka di Vault** tersimpan sebagai berkas Markdown di disk Anda dan langsung terbaca oleh aplikasi AI mana pun yang membuka folder yang sama. Carik Vault menatanya ke dalam **5 lapisan kontinuitas**:
  1. **Scratchpad obrolan** (`.agents/sessions/YYYY-MM-DD--<topik>-scratchpad.md`, lewat skill `scratchpad`) untuk mencatat jalannya diskusi panjang yang berkembang.
  2. **Memori jangka panjang** (`.agents/memory/<fakta>.md` dan indeks `.agents/Memory.md`, lewat skill `remember`) untuk fakta dan preferensi tetap yang bersumber.
  3. **Log sesi** (`.agents/Context.md` dan `.agents/Lessons.md`, lewat skill `session-log`) untuk kronologi posisi kerja serta catatan koreksi dan pelajaran.
  4. **Notulen rapat** (`notes/meeting-minutes/`, lewat skill `notulen`) untuk memisahkan keputusan final dari usulan tertunda.
  5. **Serah-terima sesi** (`handoff/`, lewat skill `handoff` dan `bootstrap`) untuk menyambung pekerjaan ke obrolan berikutnya tanpa mengulang penjelasan dari awal.

Untuk menjaga ruang baca Model tetap ringan, Carik Vault memakai mekanisme **progressive disclosure**. Model tidak memuat isi seluruh 30 skill sekaligus pada awal obrolan. Model cukup membaca daftar ringkas skill, lalu membuka berkas `.agents/skills/<nama-skill>/SKILL.md` hanya ketika tugas Anda membutuhkan skill tersebut.

### 1.4 Peran User (Anda Pawang, AI Tukang)

Anda memegang kedaulatan penuh atas tujuan, keputusan penting, dan penilaian hasil akhir. Sistem tidak berjalan optimal tanpa empat disiplin dasar dari Anda:

1. **Tetapkan tujuan dan batas yang jelas.** Sampaikan sasaran, hasil akhir yang diharapkan, dan hal yang belum perlu dikerjakan. Biarkan agen membantu merumuskannya ke `SCOPE.md` atau lewat `carik-guided-goal`.
2. **Taruh bahan sumber asli di `raw-kb/`.** Simpan PDF, transkrip, atau dokumen rujukan di `raw-kb/user-provided/` agar agen bekerja berdasarkan bukti primer, bukan ingatan umum.
3. **Uji klaim AI dan jangan langsung percaya.** Minta bukti sumber atau baris berkas untuk angka, kutipan, dan kesimpulan penting. Gunakan kalimat pemicu seperti `"cek dulu buktinya"` atau `"kamu yakin?"` bila jawaban terasa meragukan.
4. **Jaga kontinuitas sesi dan aturan pribadi.** Biasakan menutup sesi panjang dengan `closing`, memulai sesi baru dengan `bootstrap`, dan mencatat aturan kerja pribadi Anda di `ATURAN-LOKAL.md`.

## 2. Diagnosis dan Solusi 8 Gejala Nyata

Tabel berikut memetakan delapan kendala lapangan ke lapisan penyebabnya agar Anda langsung tahu bagian mana yang harus diperbaiki.

| No | Gejala yang Muncul | Lapisan Penyebab | Penyebab Utama | Solusi Cepat |
|---|---|---|---|---|
| 1 | AI menjawab dalam Bahasa Inggris atau mengabaikan `AGENTS.md` | **Model / User** | Obrolan baru dimulai tanpa menyuruh agen membaca `AGENTS.md` terlebih dahulu, atau aturan belum terbaca di awal sesi. | Kirim kalimat pembuka `"Baca AGENTS.md lalu ikuti aturan kerja dan Bahasa Indonesia di dalamnya."` Untuk sesi lanjutan, mulai dengan `"Lanjutkan sesi"` (`bootstrap`). |
| 2 | AI gagal melihat folder `work/` atau menebak isinya | **Harness / User** | User mengunggah satu berkas ke chat biasa, bukan menghubungkan seluruh folder vault sebagai workspace. | Tutup chat biasa, lalu hubungkan seluruh folder vault sebagai folder proyek atau workspace di aplikasi AI. Uji ulang dengan meminta agen menyebut 5 folder di dalam `work/`. |
| 3 | Folder `.agents/` atau `.obsidian/` tidak terlihat di macOS Finder | **Harness / Sistem Operasi** | macOS Finder menyembunyikan folder berawalan titik secara bawaan. Di Windows File Explorer, folder berawalan titik justru tampil kasat mata karena Windows memakai atribut Hidden, bukan awalan titik. | Biarkan saja karena agen AI tetap dapat membacanya. Jika suatu saat perlu melihatnya di macOS Finder, tekan `Command + Shift + .`. Di Windows, folder tersebut sudah terlihat langsung tanpa pengaturan tambahan. |
| 4 | Muncul pesan blokir pengaman berawalan `Blocked: ...` (atau kode keluarga kredensial seperti `provider-token-prefix` dan `scanner-failure`) | **Harness (Pengaman Fisik)** | Agen mencoba menulis ke luar folder vault, menyentuh folder kredensial sensitif, atau berkas teks mengandung pola token rahasia (seperti *API key*). Label `vault-boundary-blocked` hanya muncul sebagai fallback bila keluaran galat kosong. | Periksa jalur tujuan penulisan agar tetap berada di dalam folder vault, dan pastikan tidak ada kata sandi, token, atau *API key* di dalam catatan yang sedang diproses. |
| 5 | PDF hasil pindai mengembalikan status `ocr_required` atau `partial_extraction` saat diproses `pdf-read` | **Skill / Dokumen Sumber** | Berkas PDF berisi gambar hasil pindai (scan) atau teks tidak lengkap sehingga `pdf-read` menolaknya dengan status `ocr_required` atau `partial_extraction`. | Pindah ke skill `pdf-ocr` (`"OCR PDF ini"`). Kedua skill PDF ini membutuhkan `python3` dan alat lokal (termasuk Tesseract dan Poppler untuk OCR atas izin eksplisit Anda), atau gunakan salinan PDF berbasis teks. |
| 6 | Muncul berkas duplikat berakhiran *conflicted copy* dari iCloud atau OneDrive | **User / Lingkungan Disk** | Folder vault masih ditaruh di dalam folder sinkronisasi awan aktif sehingga perubahan agen bertabrakan dengan sinkronisasi otomatis. | Pindahkan seluruh folder vault ke jalur lokal di luar iCloud, OneDrive, atau Google Drive Sync. Bandingkan berkas yang bentrok, lalu pulihkan versi bersih dari salinan cadangan di `work/archive/` bila diperlukan. |
| 7 | Pembaruan `update-carik` gagal dengan status `rejected` atau tidak menemukan rilis | **Skill / User** | Pada aplikasi GUI, berkas ZIP rilis baru belum diekstrak ke dalam subfolder di `work/inbox/`. Status `rejected` juga muncul bila ada *symlink* pada jalur sasaran atau paket rilis mencoba menyentuh berkas milik user. | Untuk pengguna GUI, ekstrak `carik-vault-release.zip` ke subfolder seperti `work/inbox/carik-vault/`, lalu ulangi perintah pembaruan. Jika status tetap `rejected`, baca pesan penolakannya dan pastikan tidak ada *symlink* di jalur tujuan sebelum mencoba lagi. |
| 8 | Aturan kerja pribadi hilang setelah memperbarui Carik | **User** | Aturan pribadi ditulis langsung ke `AGENTS.md` atau `WORKFLOW.md` yang termasuk berkas sistem bawaan Carik. | Pindahkan seluruh aturan dan preferensi pribadi Anda ke berkas `ATURAN-LOKAL.md` di akar folder vault. Berkas `ATURAN-LOKAL.md` dilindungi dan tidak pernah ditimpa saat `update-carik` dijalankan. |

## Bacaan Lanjutan

- Untuk langkah operasional di ChatGPT Desktop, Claude Cowork, dan Antigravity Desktop App, baca [02-PANDUAN-HARNESS-POPULER.md](02-PANDUAN-HARNESS-POPULER.md).
- Untuk daftar lengkap 30 skill beserta contoh kalimat pemicunya, buka [03-KATALOG-SKILL-VAULT.md](03-KATALOG-SKILL-VAULT.md).
