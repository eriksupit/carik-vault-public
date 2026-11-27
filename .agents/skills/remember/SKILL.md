---
name: remember
description: >-
  Save one durable sourced fact to .agents/memory/<fact>.md and refresh .agents/Memory.md with native file edits (optional Python check), or look up saved facts honestly. Use when the owner says "ingat ini", "tolong catat bahwa", "simpan sebagai fakta", or "kamu ingat soal X?".
---

# remember

## Purpose

Menyimpan satu fakta permanen, keputusan, istilah, atau preferensi jangka panjang ke berkas sumber di `.agents/memory/<fakta>.md` dan memperbarui indeks `.agents/Memory.md`, serta menjawab pertanyaan ingatan secara jujur dari catatan yang ada. Jalur utamanya adalah penyuntingan berkas Markdown secara langsung tanpa wajib memakai Python.

## Procedure

1. **Tentukan mode: cari fakta atau simpan fakta.**
   - **Mode cari fakta ("kamu ingat soal X?"):** periksa `.agents/Memory.md` dan berkas terkait di `.agents/memory/`. Jawab hanya dari entri berstatus `active` beserta tanggal berlakunya. Jika tidak ditemukan, katakan jujur `Belum ada catatan mengenai X.` dan tawarkan untuk menyimpannya bila pemilik menyebutkannya sekarang.
   - **Mode simpan fakta:** lanjutkan ke langkah 2.
2. **Saring kelayakan dan keamanan.** Terima hanya fakta berjangka panjang yang tidak mudah ditemukan ulang dari berkas kanonis lain (satu fakta per berkas). Tolak informasi rahasia (kata sandi, PIN, nomor kartu, kredensial bank, kunci API, token, kunci privat, kode OTP); tawarkan mencatat penunjuk non-rahasia saja atau tutupi bagian rahasia dengan `****`.
3. **Tetapkan sumber dan slot.** Rumuskan fakta dalam satu kalimat dan cantumkan sumbernya: jalur berkas vault yang ada, URL, `source_id:<id>` dari `raw-kb/SOURCES.md`, atau entri `.agents/Context.md` sesi ini untuk pernyataan lisan pemilik. Tentukan `scope` (misalnya `project`) dan `fact_key` (kebab-case singkat), lalu cek `.agents/Memory.md` apakah sudah ada fakta aktif di slot yang sama.
4. **Tulis berkas fakta `.agents/memory/<fact_key>.md`** (tambahkan akhiran tanggal bila nama berkas sudah terpakai):
   ```markdown
   ---
   title: <judul singkat fakta>
   date: YYYY-MM-DD
   updated: YYYY-MM-DD
   type: memory-fact
   status: active
   tags:
     - memory
   fact_id: <fact_key>-YYYYMMDD
   scope: <scope>
   stage: <tahap atau "general">
   fact_key: <fact_key>
   effective: YYYY-MM-DD
   source:
     - <path | URL | source_id:...>
   supersedes: []
   superseded_by:
   ---

   <Pernyataan fakta dalam satu sampai dua kalimat jelas.>
   ```
5. **Tangani pembaruan fakta lama (bila slot sama sudah aktif).** Ubah berkas lama menjadi `status: superseded` dengan `superseded_by: <fact_id baru>`. Pada berkas baru, isi `supersedes: [<fact_id lama>]` dalam format satu baris inline. Jangan pernah menghapus berkas lama.
6. **Perbarui indeks `.agents/Memory.md` (jalur utama bebas-Python).** Baca `.agents/Memory.md`, lalu tambahkan baris entri aktif baru (dan pindahkan atau tandai entri lama bila digantikan) mengikuti struktur tabel atau daftar yang sudah ada di berkas itu.
7. **Verifikasi opsional (fail-open).** Bila `python3` dan `scripts/governance_store.py` tersedia di lingkungan, jalankan `python3 scripts/governance_store.py refresh-memory && python3 scripts/governance_store.py check`. Jika Python tidak tersedia, cukup validasi isi berkas secara manual.

## Rules & Boundaries

- Tanpa sumber yang sah, fakta tidak boleh ditulis.
- Dilarang menyimpan data rahasia dalam bentuk teks terbuka di `.agents/memory/` atau `.agents/Memory.md`.
- Dilarang mengarang atau menebak fakta saat menjawab pencarian memori.
- Nilai `supersedes` wajib memakai format list inline (`[]` atau `[id-lama]`), bukan block list multi-baris.
- Dilarang menghapus berkas fakta yang digantikan; riwayat perubahan harus tetap utuh.

## Output & Verification

1. Baca ulang `.agents/memory/<fact_key>.md` dan `.agents/Memory.md` untuk memastikan fakta aktif, sumber, status, dan tautan indeks sudah sinkron.
2. Jika skrip opsional tersedia, pastikan `scripts/governance_store.py check` selesai tanpa galat.
3. Laporkan kepada pemilik dalam Bahasa Indonesia sederhana fakta apa yang kini diingat, tanpa memaparkan nama field YAML atau perintah teknis kecuali diminta.
