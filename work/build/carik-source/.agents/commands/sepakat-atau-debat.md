---
description: Critically verify a user claim, proposal, or question via anti-sycophancy, confidence (>95% on primary evidence), and recommend, closing with one declarative recommendation (with direct SKILL.md read fallback).
---

# /sepakat-atau-debat

Jalankan skill **`anti-sycophancy`**, **`confidence`**, dan **`recommend`** melalui Skill tool bila tersedia. Jika aplikasi AI Anda tidak memiliki Skill tool, baca langsung berkas `.agents/skills/anti-sycophancy/SKILL.md`, `.agents/skills/confidence/SKILL.md`, dan `.agents/skills/recommend/SKILL.md`, lalu ikuti prosedurnya secara berurutan.

## Masukan yang Diuji

$ARGUMENTS

## Kontrak Jawaban Wajib

1. **Baris pertama:** buka respons dengan baris persis `Confidence: NN%` (`NN` bilangan bulat 0–100) berdasarkan bukti primer aktual (berkas, dokumen, atau sumber terverifikasi — bukan asumsi).
2. **Verifikasi sebelum setuju:** perlakukan pernyataan atau usulan sebagai klaim yang harus diuji. Dilarang membuka dengan pujian kosong ("Anda benar", "poin bagus", "tentu saja") tanpa bukti primer.
3. **Jika keyakinan ≤95%:** jangan menebak atau menghaluskan kalimat; sebutkan celah bukti spesifik dan langkah verifikasi berikutnya (atau eskalasi transparan bila celah khusus milik pemilik).
4. **Satu rekomendasi & penutup deklaratif:** bila membandingkan alternatif, uraikan kelebihan, risiko, dan kapan masing-masing tepat, lalu tutup dengan **tepat satu rekomendasi terbaik** sebagai kalimat deklaratif (dilarang menu opsi "A atau B?" dan dilarang pertanyaan validasi seperti "Setuju?" atau "Boleh saya lanjut?").
5. **Bahasa:** gunakan Bahasa Indonesia formal-sederhana yang lugas sesuai `writing-style/prose-writing-style.md`.
