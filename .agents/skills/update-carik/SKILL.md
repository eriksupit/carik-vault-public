---
name: update-carik
description: >-
  Safely update a child Carik vault from the official public carik-vault-public release (GitHub or local ZIP in work/inbox/), updating only upstream-owned files with preview and backup while preserving all user data and custom skills. Use when the owner says "update carik", "perbarui carik", "cek update carik", or "ambil pembaruan carik".
---

# update-carik

## Purpose

Memperbarui *child vault* Carik dari paket rilis publik resmi `eriksupit/carik-vault-public` (`work/build/carik-vault-release.zip` atau folder paket rilis) secara aman. Skill ini hanya memperbarui berkas milik induk (*upstream-owned* seperti skill publik resmi, panduan publik di `docs/`, aturan kanonis, command, hook, dan skrip) melalui tahap pratinjau dan cadangan otomatis, sambil melindungi penuh seluruh data kerja, ingatan, `SCOPE.md`, `ATURAN-LOKAL.md`, dan skill kustom milik pemilik vault.

## Procedure

1. **Tetapkan salah satu dari dua jalur sumber rilis resmi** (repositori `https://github.com/eriksupit/carik-vault-public` berstatus **PUBLIC** sehingga tidak membutuhkan akun atau login GitHub):
   - **Jalur A (CLI Online via `--from-github` tanpa login):** pada lingkungan CLI yang memiliki `python3` dan akses internet, ambil langsung paket rilis terbaru dari repositori publik resmi lewat flag `--from-github`.
   - **Jalur B (GUI Awam atau Offline via paket lokal di `work/inbox/`):** arahkan pemilik mengunduh `carik-vault-release.zip` dari `https://github.com/eriksupit/carik-vault-public/raw/main/work/build/carik-vault-release.zip`, menaruhnya di `work/inbox/`, lalu langsung mengekstraknya ke dalam subfolder di `work/inbox/` (misalnya `work/inbox/carik-vault/`) untuk jalur bebas-Python, atau biarkan sebagai `work/inbox/carik-vault-release.zip` untuk jalur `--source`.
2. **Periksa batas kepemilikan dan buat pratinjau perubahan (*dry-run* wajib sebelum menulis):**
   - **Jalur utama (bebas-Python, lintas 12 harness termasuk 4 GUI awam):** baca `.agents/carik-release.json` dari paket rilis sumber di `work/inbox/`. Bandingkan berkas yang masuk daftar `upstream_owned_paths` dan `upstream_skills` terhadap isi vault saat ini. Pastikan seluruh jalur pada `protected_user_paths` (`SCOPE.md`, `ATURAN-LOKAL.md`, `work/`, `notes/`, `raw-kb/`, `handoff/`, `.agents/Memory.md`, `.agents/memory/`, `.agents/Context.md`, `.agents/Lessons.md`, `.agents/archive/`, `.obsidian/`) serta skill kustom buatan pemilik di `.agents/skills/` tidak masuk daftar ubah. Pengecualian *seed*: `SCOPE.md`, `.agents/Memory.md`, `.agents/Context.md`, dan `.agents/Lessons.md` disalin dari paket rilis **hanya jika belum ada** di vault (dicatat sebagai berkas ditambah) dan tidak pernah ditimpa; `raw-kb/SOURCES.md`, `handoff/`, `notes/`, dan `work/` tidak pernah di-*seed*. Tampilkan daftar berkas yang akan ditambah dan diperbarui kepada pemilik.
   - **Penolakan otomatis (pratinjau maupun `--apply`):** skrip menolak seluruh pembaruan tanpa menulis apa pun (status `rejected`, `reason` memuat daftar jalur) bila (a) jalur tulis atau jalur cadangan melewati *symlink* di vault, atau (b) paket mengklaim berkas yang sudah ada di vault padahal `.agents/carik-release.json` milik vault tidak mencatatnya sebagai *upstream-owned* (misalnya `SOURCES.md` atau skill lokal). Pemeriksaan (b) berlaku bila vault sudah memiliki metadata rilis. Jangan memaksa pembaruan yang ditolak; laporkan jalurnya kepada pemilik.
   - **Jalur opsional *fail-open* (lingkungan dengan terminal dan `python3`):** jalankan pratinjau tanpa menulis apa pun:
     ```bash
     # Jalur CLI online (langsung dari GitHub publik tanpa login)
     python3 .agents/skills/update-carik/scripts/update_carik.py --target "$PWD" --from-github

     # Jalur ZIP lokal di work/inbox/ (offline atau unduhan manual)
     python3 .agents/skills/update-carik/scripts/update_carik.py --target "$PWD" --source "work/inbox/carik-vault-release.zip"
     ```
     Jika `python3` tidak tersedia atau unduhan gagal, lewati bersih tanpa gagal keras dan lanjutkan dengan jalur utama bebas-Python.
3. **Tahan penulisan sampai pemilik menyetujui pratinjau.** Karena pembaruan akan menimpa berkas *upstream-owned* lama, nyatakan secara deklaratif daftar berkas yang berubah dan tahan penerapan sampai pemilik menyatakan setuju.
4. **Cadangkan berkas terganti dan terapkan pembaruan (setelah izin pemilik):**
   - **Jalur utama (bebas-Python):** salin setiap berkas *upstream-owned* yang akan ditimpa ke folder cadangan baru `work/archive/update-backup-YYYY-MM-DD-HHMMSS/` (tambahkan sufiks `-2`, `-3` bila nama sudah ada) beserta `added.txt` berisi daftar berkas baru terlebih dahulu, lalu salin versi baru dari paket rilis. Saat memperbarui `.agents/skills/manifest.json`, pertahankan entri skill kustom milik pemilik agar tidak hilang. Salin berkas *seed* hanya bila belum ada di vault.
   - **Jalur opsional *fail-open* (`python3`):** jalankan skrip yang sama dengan flag `--apply`:
     ```bash
     python3 .agents/skills/update-carik/scripts/update_carik.py --target "$PWD" --from-github --apply
     ```
     (atau `--source "work/inbox/carik-vault-release.zip" --apply`). Skrip membuat folder cadangan unik `work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/` beserta `added.txt`. Tepat sebelum menulis tiap berkas, skrip memeriksa ulang *symlink* dan membuka berkas tanpa mengikuti *symlink*. Bila pembuatan cadangan atau penulisan gagal, skrip memulihkan otomatis berkas yang diperbarui, menghapus berkas baru yang sudah tertulis dan folder cadangan parsial, lalu melapor status `rolled_back`. Bila pemulihan otomatis gagal, skrip melapor `rollback_failed` dan mempertahankan folder cadangan untuk pemulihan manual. Kode keluar `0` berarti `dry-run` atau `applied`; kode `1` berarti `rejected`, `rolled_back`, `rollback_failed`, atau `unavailable` dan pembaruan tidak boleh dianggap selesai.
5. **Verifikasi hasil pembaruan** sebelum melapor kepada pemilik.
6. **Bersihkan cadangan pada vault Git.** Jika vault memakai Git, setelah hasil pembaruan terverifikasi dan di-*commit* oleh pemilik, hapus folder `work/archive/update-backup-*` yang dibuat pembaruan itu karena riwayat Git sudah menjadi cadangannya. Pada vault tanpa Git, pertahankan folder cadangan.

## Rules & Boundaries

- Selain *seed* berkas yang belum ada (lihat langkah 2), dilarang menyentuh, menimpa, atau menghapus zona milik pemilik (*user-owned*): `SCOPE.md`, `ATURAN-LOKAL.md`, `work/`, `notes/`, `raw-kb/`, `handoff/`, `.agents/Memory.md`, `.agents/memory/`, `.agents/Context.md`, `.agents/Lessons.md`, `.agents/archive/`, `.obsidian/`, maupun folder skill kustom yang dibuat pemilik sendiri di `.agents/skills/`.
- Dilarang menyinkronkan berkas internal pabrik (`profiles/`, skill pabrik `pane-management`, `deepseek-runner`, `branch-scope`, atau `docs/plans/`). Sumber pembaruan wajib paket rilis publik yang memuat `.agents/carik-release.json`.
- Dilarang menerapkan pembaruan (`--apply` atau penimpaan berkas) sebelum pratinjau perubahan ditampilkan dan disetujui eksplisit oleh pemilik.
- Jalankan `--apply` hanya saat tidak ada agen, pane, atau proses lain yang sedang menulis ke vault; hentikan atau jeda dulu tim pane sandbox sebelum memperbarui vault target.
- Setiap berkas *upstream-owned* yang ditimpa wajib memiliki salinan cadangan di folder unik `work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/` sampai hasilnya terverifikasi dan, pada vault Git, di-*commit*.
- Dilarang memasang perangkat lunak atau paket eksternal, dilarang menjalankan `git commit` atau `git push` otomatis, dan seluruh penulisan wajib berada di dalam batas vault (`.agents/hooks/vault-boundary-guard.py`).

## Output & Verification

1. Seluruh berkas *upstream-owned* yang disetujui telah diperbarui, dan salinan lama berkas yang ditimpa tersimpan rapi di `work/archive/update-backup-YYYY-MM-DD-HHMMSS[-N]/` bersama `added.txt`. Status skrip `applied` dengan kode keluar `0`.
2. Periksa bahwa `SCOPE.md`, `ATURAN-LOKAL.md` (bila ada), `notes/`, `work/`, `raw-kb/`, `.agents/Memory.md`, `.agents/Context.md`, `.agents/Lessons.md`, dan skill kustom pemilik tetap utuh.
3. Jika `python3` dan `scripts/sync-skills.py` tersedia, jalankan `python3 -B scripts/sync-skills.py --check` dan pastikan selesai dengan `errors=0`.
4. Laporkan kepada pemilik secara deklaratif: sumber rilis yang dipakai, jumlah berkas ditambah/diperbarui/tidak berubah, lokasi folder cadangan di `work/archive/`, daftar skill kustom yang tetap dipertahankan, serta hasil pemeriksaan.
