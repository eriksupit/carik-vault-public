---
name: backup-drive
description: >-
  Back up the vault as one clean .zip archive excluding .git/, .env*, secrets, credentials, and caches via Finder/Explorer Compress or optional CLI, then upload to Google Drive. Use when the owner says "backup vault", "cadangkan vault", "simpan ke Google Drive", or "buat cadangan".
---

# backup-drive

## Purpose

Membuat cadangan Carik Vault dalam satu berkas `.zip` yang bersih tanpa menyertakan berkas rahasia, kredensial, atau cache, lalu menyimpannya ke Google Drive pemilik. Jalur utamanya bebas terminal dan bebas Python sehingga peserta awam dapat mencadangkan vault cukup lewat klik kanan di Finder atau File Explorer dan mengunggahnya ke Google Drive.

## Procedure

1. **Pastikan kebersihan isi sebelum mencadangkan.** Ingatkan pemilik agar tidak menaruh kata sandi mentah, token API, atau berkas `.env` di dalam folder vault. Bila arsip dibuat untuk disimpan juga di dalam vault, gunakan nama `backup-<nama-vault>-YYYY-MM-DD-HHMM.zip` di folder `work/archive/`.
2. **Jalur Utama (Bebas Terminal, untuk Semua Pengguna Awam):**
   - **Langkah 1 (Kompres menjadi ZIP):**
     - **macOS (Finder):** buka folder induk tempat Carik Vault disimpan, klik kanan pada folder vault Anda, lalu klik **Compress "<nama-folder>"** (Kompres).
     - **Windows (File Explorer):** buka folder induk tempat Carik Vault disimpan, klik kanan pada folder vault Anda, lalu pilih **Compress to -> ZIP file** (atau **Send to -> Compressed (zipped) folder**).
     Ubah nama berkas `.zip` yang terbentuk menjadi `backup-<nama-vault>-YYYY-MM-DD.zip` agar tanggal cadangannya mudah dikenali.
   - **Langkah 2 (Unggah ke Google Drive):** buka `https://drive.google.com` di browser (atau buka folder **Google Drive** di Finder / File Explorer), masuk ke folder penyimpanan cadangan Anda, lalu seret (*drag-and-drop*) berkas `.zip` tadi ke dalamnya hingga muncul tanda unggahan selesai.
3. **Jalur Opsional Otomatis (Lingkungan CLI / Terminal bila tersedia, *fail-open*):**
   - Jika aplikasi AI memiliki akses terminal dan pemilik menginginkan pembuatan arsip otomatis di `work/archive/backup-<nama-vault>-YYYY-MM-DD-HHMM.zip`, jalankan dari akar vault:
     - macOS / Linux:
       ```bash
       zip -r -q "work/archive/<arsip>.zip" . \
         -x '.git/*' '*/.git/*' '.env*' '*/.env*' \
            '*.pem' '*.key' '*.p12' '*id_rsa*' '*credential*' '*secret*' '*token*' \
            '*/__pycache__/*' '__pycache__/*' '*/node_modules/*' 'node_modules/*' \
            '*/.venv/*' '.venv/*' '*.pyc' '*.DS_Store' 'work/archive/*'
       ```
     - Windows (PowerShell, `tar.exe` bawaan Windows 10+):
       ```powershell
       tar.exe -a -cf "work/archive/<arsip>.zip" --exclude=.git --exclude=".env*" `
         --exclude="*.pem" --exclude="*.key" --exclude="*.p12" --exclude="*id_rsa*" `
         --exclude="*credential*" --exclude="*secret*" --exclude="*token*" `
         --exclude=__pycache__ --exclude=node_modules --exclude=.venv `
         --exclude="*.pyc" --exclude=".DS_Store" --exclude="work/archive" .
       ```
   - Jika pemilik memakai aplikasi Google Drive Desktop (`~/Library/CloudStorage/GoogleDrive-<email>/My Drive` di macOS atau `G:\My Drive` di Windows) dan meminta agen menyalin berkas `.zip` langsung ke sana, patuhi model izin 2-lapis pada `AGENTS.md`: **minta izin eksplisit lebih dulu di percakapan dengan menyebut jalur folder Google Drive tujuan secara lengkap**, tunggu persetujuan pemilik (serta klik *Allow* pada dialog izin aplikasi bila muncul), baru salin berkas `.zip` tersebut. Bila tidak tersedia atau izin tidak diberikan, pandu pemilik memakai langkah seret-lepas ke `https://drive.google.com`.
4. **Catat riwayat cadangan di `.agents/Context.md`.** Tambahkan entri `## [YYYY-MM-DD HH:MM] Backup vault ke Google Drive` melalui pola `session-log` yang memuat nama berkas `.zip`, jalur yang dipakai (bebas-terminal atau otomatis), dan statusnya (`terunggah`, `tersalin ke Drive Desktop`, atau `menunggu unggahan pemilik`).

## Rules & Boundaries

- Sesuai model izin 2-lapis, agen dilarang menyalin berkas ke folder luar vault (termasuk folder Google Drive Desktop) tanpa meminta izin eksplisit di percakapan yang menyebut lokasi folder tujuan dan menerima persetujuan pemilik.
- Berkas rahasia dan kredensial (`.env*`, kunci privat `.pem`/`.key`/`id_rsa`, token, maupun cache `__pycache__` dan `node_modules`) dilarang masuk ke arsip otomatis.
- Riwayat `.git/` tidak ikut dicadangkan pada jalur otomatis agar ukuran berkas tetap ringan.
- Dilarang memakai OAuth, `rclone`, API eksternal, atau memasang perangkat lunak tambahan.
- Dilarang mengklaim cadangan sudah tersimpan di Google Drive sebelum berkasnya terbukti tersalin di folder Drive Desktop atau pemilik mengonfirmasi unggahan manual selesai.

## Output & Verification

1. Pada jalur bebas-terminal, sampaikan panduan 2 langkah kompres dan unggah secara ringkas, lalu catat status di `.agents/Context.md`.
2. Pada jalur otomatis CLI, pastikan berkas `work/archive/<arsip>.zip` terbentuk dan perintah pemeriksaan `unzip -Z1 "work/archive/<arsip>.zip"` (atau `tar.exe -tf` di Windows) bersih dari `.git/`, `.env`, kunci privat, token, dan `__pycache__/`.
3. Jika disalin ke Google Drive Desktop atas izin pemilik, periksa ukuran berkas di folder tujuan cocok dengan arsip di `work/archive/`.
4. Baca ulang entri baru di bagian akhir `.agents/Context.md`, lalu laporkan nama berkas cadangan dan status penyimpanannya secara deklaratif.
