---
description: Run first-contact vault orientation via the orient skill (with direct SKILL.md read fallback when no Skill tool exists), reading canonical files in order and logging Orientation completed.
---

# /orient

Jalankan skill **`orient`** melalui Skill tool bila tersedia. Jika aplikasi AI Anda tidak memiliki Skill tool, baca langsung berkas `.agents/skills/orient/SKILL.md` lalu ikuti seluruh langkah pada bagian `## Procedure`.

Ringkasan alur (100% bebas-Python):
1. Baca berkas kanonis berurutan: `SCOPE.md` → `README.md` → `WORKFLOW.md` → `AGENTS.md`, diikuti `.agents/Memory.md`, indeks heading dan entri terbaru `.agents/Context.md` dan `.agents/Lessons.md`, serta `writing-style/prose-writing-style.md` dan `raw-kb/SOURCES.md`.
2. Jawab seluruh 9 butir cek pemahaman dengan sitasi `file:line` langsung dari berkas aktual.
3. Catat penanda `## [YYYY-MM-DD] Orientation completed` di bagian paling bawah `.agents/Context.md`.

$ARGUMENTS
