---
name: update-carik
description: >-
  Safely update a Carik vault from the official public release (GitHub or local ZIP in work/inbox/), updating only upstream-owned files with preview and backup while keeping all user notes, memory, and custom skills intact. Use when the owner says "update carik", "perbarui carik", "cek update carik", or "ambil pembaruan carik".
---

# update-carik

## Purpose

Memperbarui Carik Vault Anda dari paket rilis publik resmi `eriksupit/carik-vault-public` dengan aman. Skill ini hanya memperbarui berkas sistem bawaan Carik (*upstream-owned* seperti skill resmi, panduan di `docs/`, aturan dasar, dan pengaman *hook*) lewat tahap pratinjau dan cadangan otomatis, sehingga seluruh catatan kerja, bahan riset, `SCOPE.md`, `ATURAN-LOKAL.md`, ingatan kerja, serta skill buatan Anda sendiri tetap 100% aman dan tidak tertimpa.

## Procedure

1. **Pilih salah satu dari dua jalur sumber rilis resmi** (repositori `https://github.com/eriksupit/carik-vault-public` terbuka untuk umum tanpa perlu akun atau login):
   - **Jalur A (Aplikasi GUI Awam atau Offline via paket lokal di `work/inbox/`):** arahkan pemilik mengunduh berkas `carik-vault-release.zip` dari halaman publik `https://github.com/eriksupit/carik-vault-public/raw/main/work/build/carik-vault-release.zip`, menaruhnya di `work/inbox/`, lalu langsung mengekstrak ZIP tersebut ke dalam subfolder di `work/inbox/` (misalnya `work/inbox/carik-vault/`) agar agen dapat langsung membaca `.agents/carik-release.json` tanpa Python maupun terminal. (Pada lingkungan CLI yang memiliki `python3`, berkas `work/inbox/carik-vault-release.zip` juga dapat langsung dipakai lewat `--source`).
   - **Jalur B (Lingkungan CLI Online via `--from-github` tanpa login):** jika aplikasi AI memiliki terminal, `python3`, dan koneksi internet, gunakan langsung opsi `--from-github` untuk mengambil rilis terbaru dari repositori publik tanpa login.
2. **Periksa batas kepemilikan dan susun pratinjau perubahan (*dry-run* wajib sebelum menulis):**
   - **Jalur utama (bebas-Python, berjalan di semua aplikasi GUI maupun CLI):** baca `.agents/carik-release.json` dari paket rilis yang telah diekstrak di `work/inbox/`. Bandingkan daftar `upstream_owned_paths` dan `upstream_skills` terhadap isi vault saat ini. Pastikan seluruh jalur milik pengguna pada `protected_user_paths` (`SCOPE.md`, `ATURAN-LOKAL.md`, `work/`, `notes/`, `raw-kb/`, `handoff/`, `.agents/Memory.md`, `.agents/memory/`, `.agents/Context.md`, `.agents/Lessons.md`, `.agents/archive/`, `.obsidian/`) serta folder skill buatan pemilik sendiri di `.agents/skills/` tidak masuk daftar ubah. Pengecualian berkas awal (*seed*): `SCOPE.md`, `.agents/Memory.md`, `.agents/Context.md`, dan `.agents/Lessons.md` hanya disalin bila berkas tersebut belum ada sama sekali di vault, dan tidak pernah ditimpa bila sudah ada; `raw-kb/SOURCES.md`, `handoff/`, `notes/`, dan `work/` tidak pernah disentuh.
   - **Jalur opsional *fail-open* (`python3` di CLI):** jalankan pratinjau tanpa mengubah berkas apa pun:
     ```bash
     # Opsi 1: Langsung dari GitHub publik (tanpa login)
     python3 .agents/skills/update-carik/scripts/update_carik.py --target "$PWD" --from-github

     # Opsi 2: Dari berkas ZIP lokal di work/inbox/
     python3 .agents/skills/update-carik/scripts/update_carik.py --target "$PWD" --source "work/inbox/carik-vault-release.zip"
     ```
     Skrip otomatis menolak pembaruan (`status: "rejected"`) tanpa menulis apa pun bila menemukan *symlink* pada jalur sasaran atau bila paket mencoba mengklaim berkas lokal milik pengguna yang belum terdaftar sebagai *upstream-owned*. Jika `python3` tidak tersedia atau unduhan internet gagal, beralih bersih ke Jalur A bebas-Python.
3. **Tampilkan pratinjau dan tahan penulisan sampai disetujui pemilik.** Sampaikan daftar berkas yang akan ditambah dan diperbarui, tegaskan bahwa catatan dan ingatan pemilik tidak tersentuh, lalu tahan penerapan secara deklaratif sampai pemilik menyatakan setuju.
4. **Cadangkan berkas lama dan terapkan pembaruan (setelah disetujui pemilik):**
   - **Jalur utama (bebas-Python):** salin lebih dulu semua berkas sistem lama yang akan diperbarui ke folder cadangan baru `work/archive/update-backup-YYYY-MM-DD-HHMMSS/` (tambahkan akhiran `-2`, `-3` bila nama folder sudah terpakai) beserta berkas `added.txt` yang mencatat berkas baru, kemudian salin berkas baru dari paket rilis. Saat memperbarui `.agents/skills/manifest.json`, pertahankan entri skill buatan pemilik agar tetap terdaftar. Setelah selesai, pindahkan berkas `carik-vault-release.zip` dari `work/inbox/` ke `work/archive/` atau hapus sesuai arahan pemilik.
   - **Jalur opsional *fail-open* (`python3`):** jalankan perintah pratinjau yang sama dengan menambahkan `--apply`:
     ```bash
     python3 .agents/skills/update-carik/scripts/update_carik.py --target "$PWD" --from-github --apply
     ```
     (atau ganti `--from-github` dengan `--source "work/inbox/carik-vault-release.zip"`). Skrip otomatis mencadangkan berkas terganti ke `work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/` dan memulihkan keadaan semula (`rolled_back`) bila terjadi kegagalan tulis di tengah jalan. Kode keluar `0` menandakan `dry-run` atau `applied`; kode `1` menandakan pembaruan batal atau gagal dan wajib dilaporkan apa adanya.
5. **Periksa keutuhan vault** setelah pembaruan selesai dan catat ringkasannya kepada pemilik. Pada vault yang dikelola dengan Git, folder `work/archive/update-backup-*` boleh dibersihkan setelah perubahan selesai diperiksa dan di-*commit* oleh pemilik; pada vault biasa tanpa Git, simpan folder cadangan tersebut di `work/archive/`.

## Rules & Boundaries

- Dilarang menimpa atau menghapus seluruh jalur milik pemilik: `SCOPE.md` (kecuali belum ada), `ATURAN-LOKAL.md`, `work/`, `notes/`, `raw-kb/`, `handoff/`, `.agents/Memory.md` (kecuali belum ada), `.agents/memory/`, `.agents/Context.md` (kecuali belum ada), `.agents/Lessons.md` (kecuali belum ada), `.agents/archive/`, `.obsidian/`, serta skill kustom buatan pemilik di `.agents/skills/`.
- Dilarang menerapkan pembaruan sebelum daftar pratinjau perubahan ditampilkan dan disetujui oleh pemilik.
- Pastikan tidak ada sesi atau aplikasi AI lain yang sedang menulis ke vault yang sama saat pembaruan dijalankan agar tidak terjadi tabrakan penulisan berkas.
- Setiap berkas bawaan yang diganti wajib dicadangkan lebih dulu ke `work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/`.
- Dilarang memasang aplikasi tambahan, dilarang menjalankan `git commit` atau `git push` tanpa perintah pemilik, dan seluruh penulisan wajib tetap berada di dalam folder vault.

## Output & Verification

1. Berkas bawaan Carik yang disetujui telah diperbarui, dan salinan lamanya tersimpan utuh di `work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/` bersama `added.txt`.
2. Periksa langsung bahwa `SCOPE.md`, `notes/`, `work/`, `raw-kb/`, `.agents/Memory.md`, `.agents/Context.md`, `.agents/Lessons.md`, `ATURAN-LOKAL.md` (bila ada), serta skill buatan pemilik tetap utuh.
3. Jika `python3` tersedia di lingkungan kerja, jalankan `python3 -B scripts/sync-skills.py --check` dan pastikan keluar dengan `errors=0`.
4. Laporkan secara deklaratif kepada pemilik: sumber pembaruan yang digunakan, tanggal rilis paket (`built_date`), jumlah berkas ditambah dan diperbarui, lokasi folder cadangan di `work/archive/`, serta kepastian bahwa seluruh catatan pemilik tetap aman.
