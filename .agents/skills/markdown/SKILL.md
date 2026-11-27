---
name: markdown
description: >-
  Create and edit Obsidian Flavored Markdown notes with YAML frontmatter, wikilinks, embeds, callouts, and tags using pure Python-free text editing. Use when the owner says "buat catatan markdown", "rapikan format obsidian", "tambah wikilink", or "pasang callout".
---

# markdown

## Purpose

Membuat dan merapikan berkas Markdown berformat Obsidian Flavored Markdown (OFM) — meliputi frontmatter YAML, tautan internal `[[wikilink]]`, sematan `![[embed]]`, kotak `callout`, dan tag — secara langsung sebagai berkas teks terbuka 100% bebas-Python agar terbaca rapi di Obsidian maupun editor teks biasa.

## Procedure

1. **Pasang frontmatter YAML di baris paling atas** (sesuai kontrak vault bila membuat catatan proyek: `title`, `date`, `updated`, `type`, `status`, `tags`, serta `aliases` bila perlu):
   ```yaml
   ---
   title: Judul Catatan
   date: YYYY-MM-DD
   updated: YYYY-MM-DD
   type: note
   status: active
   tags:
     - topik
   ---
   ```
   Detail tipe properti tersedia di `references/PROPERTIES.md`.
2. **Tulis struktur isi dengan Markdown standar dan sintaks khusus Obsidian:**
   - **Tautan internal (wikilink):** `[[Nama Catatan]]`, `[[Nama Catatan|Teks Tampil]]`, `[[Nama Catatan#Heading]]`, atau `[[Nama Catatan#^id-blok]]`. Gunakan tautan Markdown standar `[teks](https://...)` khusus untuk URL eksternal.
   - **Sematan (embed):** awali wikilink dengan tanda seru, seperti `![[Nama Catatan#Bagian]]`, `![[gambar.png|500]]`, atau `![[dokumen.pdf#page=2]]` (lihat `references/EMBEDS.md`).
   - **Callout:** gunakan blok kutipan bertipe `> [!note]`, `> [!warning] Judul`, atau `> [!info]-` (tertutup bawaan); daftar tipe lengkap ada di `references/CALLOUTS.md`.
   - **Tag, sorotan, dan komentar tersembunyi:** `#tag`, `#induk/anak`, `==teks disorot==`, `%%komentar tersembunyi%%`, serta blok `mermaid` atau matematika LaTeX (`$...$`, `$$...$$`) bila diperlukan.
3. **Periksa keterbacaan berkas mentah.** Pastikan seluruh tautan internal merujuk nama catatan yang benar dan struktur heading berjenjang rapi (`#`, `##`, `###`).

## Rules & Boundaries

- Seluruh pekerjaan dilakukan dengan penyuntingan teks murni 100% bebas-Python dan tanpa mengandalkan aplikasi Obsidian sebagai runtime.
- Gunakan `[[wikilink]]` untuk rujukan di dalam vault dan `[label](url)` hanya untuk tautan eksternal.
- Jangan menumpuk sintaks khusus Obsidian bila Markdown standar sudah lebih jelas dibaca di editor teks biasa.
- Untuk berkas di bawah aturan tata kelola vault, wajib memenuhi kontrak frontmatter 6 properti dasar.

## Output & Verification

1. Baca ulang berkas `.md` yang dibuat atau disunting: pastikan pembuka dan penutup `---` frontmatter YAML valid, format tanggal `YYYY-MM-DD`, serta tidak ada blok kode, callout, atau wikilink yang tidak tertutup.
2. Pastikan setiap tautan `[[...]]` dan sematan `![[...]]` mengarah ke berkas atau heading yang benar-benar ada (atau disebut jelas bila berupa tautan rencana).
3. Laporkan jalur berkas dan ringkasan struktur catatan kepada pemilik dalam Bahasa Indonesia sederhana.
