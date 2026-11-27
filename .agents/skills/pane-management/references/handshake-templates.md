# Handshake, Report & Readiness Templates (Herdr, omp, pi, agy)

`scripts/spawn-team.sh` generates the role card and the handshake from `roster.json`; nothing here needs hand-filling for the initial setup. This file documents what is sent, so the supervisor can check reports and re-send by hand when self-healing.

## 1. Role card (`<state_dir>/roles/<name>.md`)

Contains: name, project, supervisor name and pane ID; responsibility; working directory; write boundary (explicit paths or `STRICTLY READ-ONLY`, stated as OS-enforced); forbidden paths; what an `Operation not permitted` write means; two-tier language policy; and the report-back mandate with the exact command:

```bash
bash <skill-dir>/scripts/report.sh <SUPERVISOR_PANE_ID> <name> "STATUS: <DONE|BLOCKED|NEEDS_CONTEXT> — <ringkasan>"
```

omp and pi load it with `--append-system-prompt`, so it survives compaction. agy has no such flag: `spawn-team.sh` sends the card text as the first turn (`-i`) and waits for that turn to settle; every card ends with an instruction to re-read the card file after compaction. The matching `<state_dir>/sandbox/<name>.sb` profile is what actually enforces the boundary.

## 2. Initial handshake (sent with `herdr agent prompt <name> "<text>"`, no `--wait`)

```text
[INITIAL HANDSHAKE] Tim "<prefix>": kamu <name>. Role card-mu sudah dimuat (sumber: <cwd>/<state_dir>/roles/<name>.md). Jangan mengedit file apa pun untuk handshake ini. Jalankan perintah ini; ganti HANYA <ringkas>, salin bagian lain persis tanpa tambahan apa pun:
bash <skill>/scripts/report.sh <SUPERVISOR_PANE_ID> <name> "STATUS: DONE — peran: <ringkas>; write boundary: <paths|READ-ONLY>; mandat lapor-balik diterima"
lalu akhiri giliranmu.
```

Manual re-send (self-heal): copy the text from the template above with the values from `pane-map.md`. Run `herdr agent read <name>` first: a timeout does not prove the first handshake was lost.

## 3. Valid inbound report

Arrives in the supervisor as a new user message:

```text
[<name>] STATUS: DONE — peran: <ringkas>; write boundary: <paths|READ-ONLY>; mandat lapor-balik diterima
```

### Verification (`record-report.sh`)

```bash
bash <skill-dir>/scripts/record-report.sh --inbox <state_dir>/roster.json        # all reports since spawn (normal use)
bash <skill-dir>/scripts/record-report.sh <state_dir>/roster.json '<full report line>'   # one line by hand
```

Accepts the report only when the sender is a roster agent, the status is `DONE`, the text contains `write boundary: <exact roster entry>;` (`READ-ONLY` for `[]`), and it contains `mandat lapor-balik diterima`. It writes `DONE` or `REJECTED: <reason>` into the pane map and prints `READY k/n` (ready = `launch=verified` + `DONE`). Exit 0 accepted, 4 rejected.

The agent is not asked for its pane ID or cwd: the supervisor already holds both from `spawn-team.sh`, and self-reported values prove nothing.

## 4. Delivery behaviour (`report.sh`)

- First appends `<timestamp><TAB>[<name>] <message>` to the durable inbox `${PANE_MANAGEMENT_STATE:-~/.local/state/pane-management}/inbox-<supervisor-pane>.log` (outside the project, so the sandbox allows it). This inbox is the record of truth.
- Then notifies through `herdr agent prompt <supervisor-pane> "[<name>] <message>"`. It works while the supervisor is busy, but the text can merge into a draft a human is typing in the supervisor input; that is why `record-report.sh --inbox` reads the inbox, not the chat.
- On `agent_blocked` (supervisor shows an approval/question dialog) it retries every 10 s, 12 times (`REPORT_ATTEMPTS`, `REPORT_DELAY_SECONDS`).
- Exit 0 recorded and notified; 1 notify failed (other Herdr error); 2 still blocked after retries; 3 inbox write failed. On non-zero the agent must say so in its own pane.

## 5. Task dispatch after bootstrap

```bash
herdr agent prompt <name> "<tugas>. Batas tulis tetap sesuai role card. Lapor dengan report.sh saat selesai/gagal/terblokir."
```

## 6. Readiness report to the user (≤6 lines, Indonesian, aku–kamu)

```text
Semua <N> pane di workspace `<WS_ID>` sudah dibuat dan agen omp/pi/agy-nya berjalan sesuai roster yang kamu setujui.
Cek Herdr lolos untuk semua agen: jenis agen, cwd `<cwd>`, status siap (<daftar name@pane>).
Round-trip 100%: semua agen mengirim STATUS: DONE dengan write boundary yang cocok dan menerima mandat lapor-balik ke `<SUPERVISOR_PANE_ID>`.
Tidak ada pane yang gagal, ghost, atau terblokir.
Peta pane: `<state_dir>/pane-map.md`; role card: `<state_dir>/roles/`.
Tim siap; aku standby menunggu arahanmu sebelum menjalankan `/bootstrap`.
```
