---
name: browsing
description: >-
  Research web pages using the user's real browser through progressive enhancement (built-in harness browser tools, optional fail-open local browser helper, or user-guided flow), saving summaries to notes/ and sources to raw-kb/SOURCES.md. Use when the owner says "browsing", "buka browser", "riset di browser", or "cari di web pakai browser".
---

# browsing

## Purpose

Membantu pemilik menelusuri halaman web dan melakukan riset menggunakan browser nyata di komputer pemilik (bukan hanya mode headless), lalu menyimpan hasil risetnya secara rapi sebagai berkas teks terbuka di dalam vault. Skill ini menjaga riset tetap aman lintas 12 harness (4 aplikasi GUI awam dan 8 lingkungan CLI/ADE) melalui prinsip *Progressive Enhancement* tanpa memasang perangkat lunak atau ekstensi tambahan.

## Procedure

1. **Tetapkan pertanyaan riset dan sumber awal.** Rumuskan pokok yang dicari, daftar URL atau kata kunci awal, serta jenis informasi yang perlu diambil dalam satu sampai dua kalimat singkat sebelum membuka halaman apa pun.
2. **Pilih jalur akses browser sesuai kemampuan harness saat ini (berurutan, *fail-open*):**
   - **Jalur 1 — Tool browser atau *computer-use* bawaan harness (utama jika tersedia dan aktif).** Gunakan jembatan browser bawaan aplikasi AI yang sedang dipakai pemilik untuk membuka URL, membaca isi halaman, dan menelusuri tautan relevan secara langsung.
   - **Jalur 2 — Jalur kolaboratif bersama pemilik (utama lintas seluruh 12 harness, bebas-Python).** Jika harness tidak menyediakan tool browser aktif, atau halaman berada di balik login, *paywall*, maupun CAPTCHA, pandu pemilik dalam dua langkah konkret:
     1. Tampilkan URL atau kata kunci pencarian agar pemilik membukanya langsung di browser komputernya sendiri.
     2. Minta pemilik menyalin bagian teks yang relevan ke percakapan, atau menyimpan halaman sebagai PDF/berkas ke `raw-kb/user-provided/` untuk dibaca agen.
   - **Jalur 3 — Skrip bantu lokal opsional *fail-open* (khusus lingkungan dengan terminal dan `python3`).** Bila `python3` tersedia dan Jalur 1 tidak aktif, agen boleh memakai `.agents/skills/browsing/scripts/browser_helper.py` (100% pustaka standar Python, tanpa instalasi paket):
     - Membuka URL langsung di browser default komputer pemilik (meminta izin pemilik sebelum membuka):
       ```bash
       python3 .agents/skills/browsing/scripts/browser_helper.py open "https://contoh.tld"
       ```
     - Memeriksa tab aktif browser nyata yang sedang membuka port *remote debugging* Chrome DevTools Protocol (`127.0.0.1:9222`) jika pemilik sengaja menyalakannya sendiri:
       ```bash
       python3 .agents/skills/browsing/scripts/browser_helper.py cdp-tabs --port 9222
       ```
     - Mengambil teks bersih halaman publik tanpa login bila server mengizinkan akses langsung:
       ```bash
       python3 .agents/skills/browsing/scripts/browser_helper.py fetch-text "https://contoh.tld"
       ```
     Jika `python3` tidak tersedia, port CDP tidak aktif, atau akses diblokir, lewati bersih tanpa gagal keras dan langsung gunakan Jalur 2.
3. **Saring temuan dan pisahkan fakta dari tafsir.** Ringkas fakta kunci yang langsung menjawab pertanyaan riset, catat kutipan atau angka penting apa adanya, dan tandai bagian yang belum terverifikasi.
4. **Tulis dua keluaran wajib di dalam vault:**
   - **Catatan ringkasan riset** di `notes/riset-YYYY-MM-DD--<topik>.md` memakai frontmatter YAML standar (`title`, `date`, `type: research-note`, `status: active`), berisi pertanyaan riset, temuan utama, poin penting, dan daftar tautan sumber beserta tanggal akses.
   - **Entri sumber ringkas** di `raw-kb/SOURCES.md` memuat judul halaman, URL, tanggal akses, dan jalur akses yang dipakai (`harness-browser`, `user-assisted`, `cdp-user-browser`, atau `public-fetch`).
5. **Verifikasi berkas hasil** sebelum melapor kepada pemilik.

## Rules & Boundaries

- Dilarang memasang perangkat lunak, ekstensi browser, atau paket eksternal (`pip`, `npm`, `brew`) secara otomatis.
- Dilarang membangun atau menjalankan kendali layar/mouse OS (*computer-use*) secara paksa di luar tool bawaan harness yang memang sudah diaktifkan pemilik.
- Dilarang melakukan aksi sensitif di browser pemilik tanpa persetujuan eksplisit pada langkah tersebut: mengisi kata sandi atau login otomatis, mengirim form transaksi atau pembayaran, menghapus data akun, maupun memposting konten atas nama pemilik.
- Dilarang melewati CAPTCHA, pemeriksaan anti-bot, atau gerbang login secara paksa; saat bertemu hambatan tersebut, hentikan akses otomatis dan serahkan interaksi ke pemilik di browsernya sendiri.
- Dilarang menyalin atau menyimpan cookie sesi, token otentikasi, maupun kredensial ke dalam berkas vault.
- Seluruh penulisan berkas wajib berada di dalam vault (`notes/` dan `raw-kb/SOURCES.md`), tunduk pada `.agents/hooks/vault-boundary-guard.py`, tanpa ketergantungan pada direktori global maupun aplikasi desktop Obsidian sebagai runtime.
- Ikuti disiplin `anti-sycophancy` dan `confidence`: jangan mengarang isi halaman yang tidak berhasil dibaca; nyatakan jujur halaman mana yang gagal diakses dan alasannya.

## Output & Verification

1. Satu berkas catatan ringkasan riset tersimpan rapi di `notes/riset-YYYY-MM-DD--<topik>.md` dan seluruh URL sumber tercatat pada `raw-kb/SOURCES.md`.
2. Baca balik kedua berkas untuk memastikan judul, URL, tanggal akses, dan temuan utama sesuai fakta dari halaman yang benar-benar diakses (tanpa kredensial atau cookie yang ikut tersimpan).
3. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana: lokasi berkas catatan di `notes/`, jumlah sumber yang dicatat di `raw-kb/SOURCES.md`, jalur browser yang dipakai, serta hambatan halaman (bila ada) secara deklaratif.
