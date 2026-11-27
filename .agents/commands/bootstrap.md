---
description: Resume work from the newest validated handoff pair in handoff/ using the bootstrap skill (with direct SKILL.md read fallback when no Skill tool exists).
---

# /bootstrap

Jalankan skill **`bootstrap`** melalui Skill tool bila tersedia. Jika aplikasi AI Anda tidak memiliki Skill tool, baca langsung berkas `.agents/skills/bootstrap/SKILL.md` lalu ikuti seluruh langkah pada bagian `## Procedure`.

Ringkasan alur:
1. Temukan pasangan terbaru `handoff/INITIAL-PROMPT-*.txt` dan `handoff/HANDOFF-<suffix-sama>.md` menurut tanggal `YYYY-MM-DD` (plus `HHMMSS` bila ada) di akhiran nama, bukan urutan abjad (jalur utama bebas-Python; `resolve_handoff.py` bersifat opsional *fail-open*).
2. Validasi kesamaan blok `## Goal` pada kedua berkas dan frontmatter `.md`.
3. Baca `SCOPE.md`, `.agents/Memory.md`, serta indeks heading dan entri terbaru `.agents/Context.md` dan `.agents/Lessons.md`.
4. Rekonsiliasi perbedaan keadaan terhadap berkas aktual lalu mulai tugas pertama yang sudah diotorisasi pemilik.

$ARGUMENTS
