---
name: backup-drive
description: >-
  Back up the vault as one clean .zip that excludes .git/, .env*, secrets, credentials, and caches, then put it on Google Drive: copy into the Google Drive Desktop folder only with explicit owner permission, else guide a two-step drag-and-drop to drive.google.com. Use when the owner says "backup vault", "cadangkan vault", "simpan ke Google Drive", or "buat cadangan".
---

# backup-drive

## Purpose

Membuat cadangan vault dalam satu berkas `.zip` yang bersih, lalu menaruhnya di Google Drive pemilik. Cadangan tidak memuat riwayat Git, berkas rahasia, kredensial, atau cache. Skill ini tidak butuh OAuth, `rclone`, atau Python: arsip dibuat dengan perintah bawaan sistem, dan pengunggahan memakai aplikasi Google Drive Desktop atau browser biasa.

## Procedure

1. **Tetapkan nama arsip.** `work/archive/backup-<nama-vault>-YYYY-MM-DD-HHMM.zip`. Buat folder `work/archive/` bila belum ada.
2. **Buat arsip dari akar vault** dengan pola pengecualian berikut.
   - macOS / Linux:
     ```bash
     zip -r -q "work/archive/<arsip>.zip" . \
       -x '.git/*' '*/.git/*' '.env*' '*/.env*' \
          '*.pem' '*.key' '*.p12' '*id_rsa*' '*credential*' '*secret*' '*token*' \
          '.agents/allow-external' \
          '*/__pycache__/*' '__pycache__/*' '*/node_modules/*' 'node_modules/*' \
          '*/.venv/*' '.venv/*' '*.pyc' '*.DS_Store' \
          'work/archive/*'
     ```
   - Windows (PowerShell, `tar.exe` bawaan Windows 10+):
     ```powershell
     tar.exe -a -cf "work/archive/<arsip>.zip" --exclude=.git --exclude=".env*" `
       --exclude="*.pem" --exclude="*.key" --exclude="*.p12" --exclude="*id_rsa*" `
       --exclude="*credential*" --exclude="*secret*" --exclude="*token*" `
       --exclude=".agents/allow-external" --exclude=__pycache__ --exclude=node_modules `
       --exclude=.venv --exclude="*.pyc" --exclude=".DS_Store" --exclude="work/archive" .
     ```
3. **Periksa isi arsip** (lihat bagian terakhir). Bila ada berkas terlarang, hapus arsip itu, perbaiki pola, ulangi langkah 2.
4. **Taruh di Google Drive** (Progressive Enhancement, pilih jalur pertama yang tersedia):
   - **Jalur A — Google Drive Desktop, hanya dengan izin eksplisit.** Cari foldernya: macOS `~/Library/CloudStorage/GoogleDrive-<email>/My Drive` (atau `Drive Saya`), Windows biasanya `G:\My Drive`. Folder ini berada di luar vault, jadi penyalinan diblokir `.agents/hooks/vault-boundary-guard.py` sampai pemilik sendiri menambahkan jalur folder itu ke `.agents/allow-external` atau menyetel `VAULT_ALLOW_EXTERNAL` di lingkungan agen. Agen tidak boleh mengubah `.agents/allow-external`. Setelah izin ada, salin dengan `cp "work/archive/<arsip>.zip" "<folder-drive>/"`.
   - **Jalur B — Google Drive Web, dua langkah.** Bila Drive Desktop tidak ada atau izin tidak diberikan, pandu pemilik: (1) buka `https://drive.google.com` di browser dan masuk ke folder tujuan; (2) seret berkas `work/archive/<arsip>.zip` dari Finder/File Explorer ke jendela Drive, lalu tunggu sampai muncul tanda unggahan selesai.
5. **Catat tanggal cadangan di `.agents/Context.md`** dengan format entri `session-log`: judul `## [YYYY-MM-DD HH:MM] Backup vault ke Google Drive`, lalu butir nama arsip, ukuran, jalur unggah (A atau B), dan status (`tersalin`, `menunggu unggahan manual`, atau `gagal`).

## Rules & Boundaries

- Pagar batas vault berlaku penuh. Menulis ke luar vault hanya lewat izin yang ditetapkan pemilik; jangan memindahkan arsip ke lokasi lain sebagai jalan pintas.
- Rahasia tidak boleh ikut: `.env*`, kunci privat, kredensial, token, dan `.agents/allow-external`. Bila ragu apakah sebuah berkas rahasia, kecualikan dan sebutkan kepada pemilik.
- Riwayat `.git/` tidak dicadangkan; cadangan ini salinan isi vault, bukan pengganti repositori.
- Tidak memakai OAuth, `rclone`, API Google, atau memasang perangkat lunak.
- Jangan menyatakan cadangan sudah ada di Google Drive tanpa bukti: pada Jalur A berkasnya terlihat di folder Drive, pada Jalur B pemilik mengonfirmasi unggahan selesai.

## Output & Verification

1. Arsip sah dan berisi:
   ```bash
   ls -l "work/archive/<arsip>.zip" && unzip -l "work/archive/<arsip>.zip" | tail -1
   ```
2. Tidak ada berkas terlarang di dalam arsip (perintah ini harus tidak mengeluarkan apa pun):
   ```bash
   unzip -Z1 "work/archive/<arsip>.zip" | grep -nE '(^|/)\.git/|(^|/)\.env|\.pem$|\.key$|\.p12$|id_rsa|credential|secret|token|allow-external|__pycache__/|node_modules/|\.venv/'
   ```
   Di Windows, ganti `unzip -Z1` dengan `tar.exe -tf`.
3. Jalur A: `ls -l "<folder-drive>/<arsip>.zip"` menunjukkan ukuran yang sama dengan arsip di vault.
4. Entri baru di `.agents/Context.md` ada (`tail -8 .agents/Context.md`).
5. Laporkan kepada pemilik dalam bahasa Indonesia sederhana: nama dan ukuran arsip, jalur yang dipakai, dan status unggahan.
