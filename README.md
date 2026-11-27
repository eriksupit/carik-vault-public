---
title: Carik Vault Public — Ruang Kerja Rekayasa Perangkat Lunak
date: 2026-11-17
updated: 2026-11-17
type: documentation
status: active
tags:
  - carik-vault
  - app-build
  - software-engineering
  - dokumentasi
---

# Carik Vault Public — Ruang Kerja Rekayasa Perangkat Lunak

Selamat datang di **Carik Vault Public**, proyek rekayasa perangkat lunak berbasis tata kelola terbuka (*File-Over-App*) dengan alur kerja deterministik (`app-build`).

> [!important] Arti "public"
> Kata "public" pada nama vault ini berarti *untuk publik*: repositori ini memuat Carik versi ramah awam yang dikembangkan dan diuji untuk penggunaan umum. Templat produk disusun di `work/build/carik/`.

## Struktur Direktori

```text
.
├── CARIK-CHARTER.md     ── Konstitusi tertinggi kedaulatan berpikir manusia
├── AGENTS.md            ── Instruksi kerja agen rekayasa perangkat lunak
├── WORKFLOW.md          ── Prosedur 8 tahap pengembangan perangkat lunak
├── MULAI-DARI-SINI.md   ── Panduan cepat memulai proyek coding
├── SCOPE.md             ── Batasan ruang lingkup teknis proyek aktif
├── docs/
│   ├── design/          ── Dokumen desain (gerbang persetujuan sebelum coding)
│   └── plans/           ── Rencana implementasi terotorisasi (lean-plan)
├── work/                ── Pipeline rekayasa perangkat lunak
│   ├── research/        ── Masalah, batasan, dan intake.md
│   ├── implementation-plan/ ── Pemecahan tugas & kriteria verifikasi
│   ├── build/           ── Kode sumber aplikasi & test suite
│   ├── verification/    ── Bukti tes, audit, dan investigasi bug
│   ├── review/          ── Ulasan agen, laporan pemilik, dan review independen
│   └── TODO.txt         ── Pelacak progres langkah kerja
├── raw-kb/              ── Sumber acuan mentah & registri SOURCES.md
└── .agents/             ── Keahlian agen, hook keselamatan, dan kontinuitas sesi
```

## Cara Memulai

Buka [MULAI-DARI-SINI.md](MULAI-DARI-SINI.md) untuk panduan cepat memulai proyek.
