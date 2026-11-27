---
title: Mulai dari Sini - Panduan Cepat Carik Vault
date: 2026-11-23
updated: 2026-11-26
type: guide
status: active
tags:
  - panduan
  - mulai-dari-sini
  - carik-vault
---

# Mulai dari Sini

Selamat datang di **Carik Vault**. Folder ini menyimpan bahan, catatan, konsep, dan hasil kerja Anda dalam format teks terbuka supaya tetap rapi, tahan lama, dan dapat dibaca oleh berbagai aplikasi AI.

## Langkah 0: Siapkan Folder Vault di Komputer Anda

Tempatkan dulu folder Carik Vault di lokasi yang aman sebelum membuka aplikasi AI.

1. **Ekstrak berkas ZIP yang Anda unduh.** Di Windows, klik kanan berkas `carik-vault-release.zip` lalu pilih **Extract All**. Di macOS, klik ganda berkas ZIP tersebut sampai muncul folder baru.
2. **Pindahkan folder ke lokasi tetap di luar `Downloads`.** Taruh di folder lokal di luar sinkronisasi awan, misalnya folder `carik-vault` langsung di bawah folder akun macOS (`/Users/<nama-anda>/carik-vault`) atau `C:\carik-vault` di Windows. Folder `Downloads` rawan terhapus saat Anda membersihkan komputer.
3. **Hindari folder sinkronisasi awan aktif.** Jangan menaruh vault di dalam iCloud Desktop/Documents, OneDrive, atau Google Drive Sync. Layanan sinkronisasi otomatis sering memicu konflik berkas ketika agen AI sedang membaca dan menulis. Untuk cadangan ke Google Drive, gunakan skill `backup-drive` yang membuat arsip ZIP secara terkendali.
4. **Kenali berkas `.md`.** Semua catatan di vault ini berformat teks biasa berekstensi `.md` (Markdown). Anda bisa membukanya langsung dengan **Notepad** di Windows atau **TextEdit** di macOS, atau cukup meminta agen AI membacakan dan merangkum isinya.

## 1. Mengenal 2 Zona Folder

Seluruh isi vault terbagi ke dalam dua zona supaya Anda tidak bingung saat membuka folder di Finder maupun File Explorer.

- **Zona Kerja Harian (tempat Anda beraktivitas):**
  - `MULAI-DARI-SINI.md` berisi panduan cepat ini.
  - `work/` menampung alur kerja utama dalam 5 laci berurutan: `inbox/` untuk bahan mentah dan masukan awal, `concept/` untuk kerangka dan konsep, `drafts/` untuk draf yang sedang disunting, `canon/` untuk hasil final yang sudah disetujui, serta `archive/` untuk salinan lama dan cadangan ZIP.
  - `notes/` menyimpan catatan lepas dan notulen rapat di `notes/meeting-minutes/` (subfolder ini dibuat otomatis oleh agen saat pertama kali membuat notulen).
  - `raw-kb/` menyimpan bahan referensi asli (seperti PDF, transkrip, atau dokumen sumber di `user-provided/` dan hasil riset agen di `agent-acquired/`) beserta daftarnya di `raw-kb/SOURCES.md`.
  - `handoff/` menyimpan berkas serah-terima untuk menyambung pekerjaan pada sesi berikutnya.
- **Zona Pendukung (referensi dan sistem di belakang layar):**
  - `docs/` berisi pedoman user lengkap: [Cara Kerja dan Diagnosis](docs/01-CARA-KERJA-DAN-DIAGNOSIS.md), [Panduan Harness Populer](docs/02-PANDUAN-HARNESS-POPULER.md), dan [Katalog 30 Skill](docs/03-KATALOG-SKILL-VAULT.md).
  - `writing-style/` berisi pedoman gaya penulisan prosa Bahasa Indonesia.
  - Berkas aturan di akar folder mencakup `AGENTS.md`, `WORKFLOW.md`, `SCOPE.md`, `README.md`, `CARIK-CHARTER.md`, `CREATIVE-LAW.md`, `CLAUDE.md`, serta `ATURAN-LOKAL.md` jika Anda membuat berkas aturan pribadi.
  - Folder teknis mencakup `.agents/`, `.obsidian/`, `.claude/`, `.codex/`, dan `scripts/`. Di macOS Finder, folder berawalan titik seperti `.agents/` dan `.obsidian/` tersembunyi secara bawaan (bila perlu ditampilkan, tekan `Command + Shift + .`). Di Windows File Explorer, folder berawalan titik tampil kasat mata karena Windows memakai atribut Hidden, bukan awalan titik. Anda tidak perlu membuka atau menyunting folder teknis itu secara manual karena agen AI yang membacanya.

## 2. Cara Membuka Vault di Aplikasi AI

Anda tidak perlu memasang Python, terminal, atau aplikasi Obsidian untuk menjalankan 28 skill teks dan ingatan. Python atau alat lokal baru dibutuhkan untuk 2 skill olah PDF lokal (`pdf-read` dan `pdf-ocr`) serta pengaman hook fisik opsional. Pilih aplikasi AI yang mendukung akses folder lokal, hubungkan folder vault ini sebagai ruang kerja, lalu kirim kalimat pembuka berikut:

> "Baca AGENTS.md lalu bantu saya memulai pekerjaan hari ini."

- **ChatGPT Desktop (macOS dan Windows, per 2026-11-26):** ChatGPT versi web di browser tidak dapat membuka folder lokal. Gunakan aplikasi **ChatGPT Desktop**, hubungkan seluruh folder lokal vault ini sebagai ruang kerja, kirim kalimat pembuka di atas, lalu pastikan koneksi lewat Tes Koneksi 10 Detik di bawah. Pengujian langsung pada aplikasi ChatGPT Desktop belum dilakukan terpisah.
- **Claude Cowork (Desktop):** buka aplikasi Claude Desktop, hubungkan seluruh folder lokal vault ini sebagai ruang kerja Cowork, kirim kalimat pembuka di atas, lalu pastikan koneksi lewat Tes Koneksi 10 Detik.
- **Antigravity App:** buka seluruh folder lokal vault ini sebagai workspace di Antigravity App, lalu kirim kalimat pembuka di atas.
- **Aplikasi CLI dan editor kode:** jika Anda memakai Antigravity CLI (`agy`), Claude Code, Codex, OhMyPi/Pi (`omp`), Cursor, Windsurf, Kiro, Zed, atau DeepSeek Harness, buka folder vault ini sebagai direktori proyek dan gunakan kalimat pembuka yang sama.

## 3. Tes Koneksi 10 Detik

Pastikan aplikasi AI benar-benar terhubung ke seluruh folder vault, bukan sekadar menerima satu berkas tempelan.

- **SALAH:** mengunggah satu berkas (misalnya `AGENTS.md` saja) ke chat biasa. Dengan cara ini, agen tidak bisa membaca folder lain dan tidak bisa menyimpan perubahan ke komputer Anda.
- **BENAR:** menghubungkan seluruh folder vault sebagai workspace atau folder proyek.

Kirim kalimat uji cepat ini begitu folder terhubung:

> "Sebutkan daftar folder yang ada di dalam work/ sekarang."

Koneksi berhasil jika agen langsung menjawab lima nama folder yang tepat: `inbox`, `concept`, `drafts`, `canon`, dan `archive`. Jika agen berkata tidak dapat melihat folder atau justru menebak isinya, periksa kembali apakah folder vault sudah terpilih sebagai workspace.

> **Kebiasaan Wajib Harian**
> - **Tutup sesi dengan `closing`.** Sebelum mengakhiri obrolan panjang, katakan `"tutup sesi"` atau `"closing"` supaya agen merangkum posisi kerja dan menyiapkan berkas serah-terima.
> - **Lanjutkan sesi dengan `bootstrap`.** Saat membuka obrolan baru di hari berikutnya, katakan `"lanjutkan sesi"` atau `"bootstrap"` agar agen langsung menyambung dari posisi terakhir.
> - **Simpan aturan pribadi di `ATURAN-LOKAL.md`.** Jika Anda punya kebiasaan atau aturan kerja khusus, taruh di berkas `ATURAN-LOKAL.md` pada akar vault. Berkas ini tidak akan ditimpa saat Carik diperbarui.
> - **Jangan pernah menyimpan data rahasia di vault.** Dilarang menaruh kata sandi, PIN, nomor KTP, rekening atau kartu bank, serta *API key* di catatan mana pun di dalam folder vault.

## 4. Contoh Kalimat Pemicu Sehari-hari

Cukup ketik perintah dalam Bahasa Indonesia biasa. Agen akan membaca skill yang sesuai di `.agents/skills/` dan menjalankannya untuk Anda.

1. **Mulai kerja dan rumuskan tujuan:** `"Saya belum tahu mulai dari mana, bantu saya merumuskan tugas ini."`
2. **Pecah tugas rumit:** `"Pecah jadi langkah semua pekerjaan ini, lalu urutkan dari yang paling penting."`
3. **Buat notulen rapat:** `"Buat notulen dari catatan diskusi ini, pisahkan tegas keputusan final dan usulan yang masih pending."`
4. **Simpan fakta penting lintas sesi:** `"Tolong catat bahwa tenggat laporan kuartal adalah tanggal 25 setiap bulan, simpan sebagai fakta."`
5. **Baca dokumen PDF (butuh `python3` dan alat lokal):** `"Baca PDF yang baru saya taruh di raw-kb/user-provided/ lalu rangkum poin pentingnya."`
6. **Buat laporan visual atau PDF siap cetak A4:** `"Buat laporan visual dari draf di work/drafts/ lalu jadikan PDF siap cetak A4."`
7. **Tutup sesi dan sambung sesi berikutnya:** `"Tutup sesi hari ini dan buat handoff."` Lalu pada sesi berikutnya: `"Lanjutkan sesi dari handoff terbaru."`
8. **Cadangkan vault ke Drive:** `"Cadangkan vault ini menjadi arsip ZIP supaya siap saya simpan ke Google Drive."`
9. **Perbarui Carik dengan aman:** `"Cek dan perbarui Carik dari repositori GitHub publik."` (Untuk aplikasi GUI tanpa terminal, unduh lalu ekstrak berkas ZIP rilis baru ke dalam subfolder di `work/inbox/`, misalnya `work/inbox/carik-vault/`, lalu katakan `"Perbarui Carik dari subfolder rilis baru di work/inbox/."`)

## 5. Mulai Sekarang

Anda tidak perlu menyunting berkas `SCOPE.md` secara manual. Buka folder vault ini di aplikasi AI pilihan Anda, lalu kirim kalimat berikut:

> "Baca AGENTS.md, wawancarai saya sebentar tentang tujuan proyek ini, lalu bantu isikan SCOPE.md."

Untuk pendalaman lebih lanjut, baca tiga berkas pedoman user di folder `docs/`:

- [Cara Kerja Carik Vault dan Diagnosis Kendala](docs/01-CARA-KERJA-DAN-DIAGNOSIS.md)
- [Panduan Memakai Carik Vault di Harness Populer](docs/02-PANDUAN-HARNESS-POPULER.md)
- [Katalog Lengkap 30 Skill Carik Vault dan Cara Pakainya](docs/03-KATALOG-SKILL-VAULT.md)
