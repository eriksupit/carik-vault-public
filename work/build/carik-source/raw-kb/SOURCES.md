---
title: Registri Sumber Raw KB
date: 2026-11-23
updated: 2026-11-23
type: source-registry
status: active
tags:
  - raw-kb
  - provenance
  - sources
---

# Registri Sumber Raw KB

Berkas ini mencatat setiap dokumen sumber mentah yang disimpan di `raw-kb/user-provided/` (diberikan pemilik) dan `raw-kb/agent-acquired/` (ditemukan agen saat riset).

## Format Entri Sumber

```yaml
source_id: <id-unik>
local_path: raw-kb/<user-provided|agent-acquired>/<nama-berkas>
provenance_class: <user-provided | agent-acquired>
ingest_method: <local-copy | attachment | user-url | direct-drop | agent-research>
original_creator_or_publisher: <penulis/penerbit atau unknown>
original_url_or_attachment_record: <URL atau catatan lampiran>
date_added: YYYY-MM-DD
file_format: <pdf | md | txt | html | ...>
rights_status: <user-declared | unknown | public | licensed>
derived_files: []
registration_status: registered
```

## Sumber Terdaftar

Belum ada sumber yang terdaftar.
