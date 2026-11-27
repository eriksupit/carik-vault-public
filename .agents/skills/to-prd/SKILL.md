---
name: to-prd
description: >-
  Synthesize the current conversation context and codebase understanding into a durable Markdown PRD saved to work/research/ following File-Over-App. Use when the owner says "buat PRD", "jadikan PRD", "susun PRD", or "tulis dokumen PRD".
---

# to-prd

## Purpose

Menyintesis konteks percakapan, hasil wawancara desain, dan pemahaman basis kode saat ini menjadi satu dokumen *Product Requirements Document* (PRD) berbasis Markdown terbuka di `work/research/YYYY-MM-DD--<topik>-prd.md`. Skill ini mematuhi *File-Over-App* tanpa bergantung pada *issue tracker* eksternal maupun skrip instalasi pihak ketiga.

## Procedure

1. **Verifikasi kondisi proyek tanpa mewawancarai ulang.** Baca berkas relevan di repositori, glosarium domain, catatan *scratchpad*, dan ADR terkait agar PRD memakai istilah kanonis yang akurat. Jika konteks masih penuh ambiguitas kritis, arahkan ke `grill-with-docs` lebih dulu.
2. **Tentukan *seam* pengujian perilaku.** Identifikasi batas antarmuka (*seam*) tertinggi tempat perilaku fitur akan diuji (utamakan *seam* yang sudah ada). Sampaikan usulan *seam* tersebut bersama ringkasan *Summary-First* kepada pemilik sebelum menulis berkas PRD.
3. **Susun berkas PRD di `work/research/YYYY-MM-DD--<slug-topik>-prd.md`** setelah persetujuan *Summary-First*, memakai frontmatter YAML standar (`title`, `date`, `updated`, `type: prd`, `status: draft`, `tags`) dan struktur tujuh bagian:
   - `## Problem Statement` — masalah nyata dari sudut pandang pengguna.
   - `## Solution` — solusi yang ditawarkan dari sudut pandang pengguna.
   - `## User Stories` — daftar bernomor menyeluruh dengan pola `Sebagai <aktor>, saya ingin <fitur>, agar <manfaat>`.
   - `## Implementation Decisions` — modul yang dibuat/diubah, kontrak antarmuka, keputusan arsitektur, skema, dan interaksi penting tanpa menempel jalur berkas rapuh atau potongan kode panjang yang cepat usang (kecuali skema/tipe ringkas hasil verifikasi).
   - `## Testing Decisions` — perilaku eksternal yang diuji, modul target, dan pola uji rujukan.
   - `## Out of Scope` — batas tegas yang tidak dikerjakan.
   - `## Further Notes` — catatan tambahan beserta tautan sumber preseden arsitektur dari `raw-kb/SOURCES.md`.
4. **Baca ulang berkas PRD** untuk memastikan tidak ada fakta yang dikarang dan seluruh tujuh bagian lengkap.

## Rules & Boundaries

- Dilarang memublikasikan PRD ke *issue tracker* eksternal atau mewajibkan perintah instalasi pihak ketiga; keluaran primer selalu berkas teks terbuka di `work/research/`.
- Dilarang menimpa berkas PRD lama untuk topik yang berbeda; tambahkan akhiran angka bila nama berkas sudah terpakai.
- Penulisan berkas wajib didahului persetujuan *Summary-First* dan bebas dari kredensial atau rahasia.
- Berjalan 100% bebas-Python tanpa ketergantungan pada direktori global maupun aplikasi Obsidian sebagai *runtime*.

## Output & Verification

1. Berkas `work/research/YYYY-MM-DD--<slug-topik>-prd.md` ada, ber-frontmatter YAML valid, dan memuat ketujuh bagian wajib secara lengkap.
2. Baca ulang berkas untuk memastikan istilah sesuai glosarium proyek, seluruh keputusan berasal dari konteks terverifikasi, dan tidak ada rujukan *issue tracker* eksternal.
3. Laporkan lokasi berkas PRD dan ringkasan cakupannya dalam Bahasa Indonesia lugas dengan penutup deklaratif.
