---
title: Raw KB Source Registry
date: 2026-07-22
updated: 2026-07-22
type: source-registry-template
status: empty
tags:
  - file-over-app-harness
  - raw-kb
  - provenance
---

# Raw KB Source Registry

This document is the mandatory registry for sources under `raw-kb/user-provided/` and `raw-kb/agent-acquired/`. A file existing inside those folders is not enough to make it a registered source.

## Provenance classes

- `user-provided`: a source or specific link chosen and supplied by the user, including files the agent copied or downloaded on the user's instruction.
- `agent-acquired`: a source the agent found and selected during research the user authorized.

Provenance class describes the ingress path. It does not prove legal ownership or copyright.

## Controlled values

- `ingest_method`: `local-copy`, `attachment`, `user-url`, `direct-drop`, or `agent-research`.
- `rights_status`: `user-declared`, `unknown`, `public`, or `licensed`.
- `registration_status`: `registered` or `unregistered`.

## Entry contract

Each source uses one heading and one metadata block containing all of the following fields:

```yaml
source_id:
local_path:
provenance_class:
provided_or_discovered_by:
ingest_method:
original_creator_or_publisher:
original_url_or_attachment_record:
date_added:
file_format:
rights_status:
rights_or_access_note:
derived_files: []
sha256:
registration_status:
```

Record unknown metadata as `unknown`; never invent it. `user-declared` only records the user's claim and is not independent legal verification.

## Registered sources

No sources registered yet.
