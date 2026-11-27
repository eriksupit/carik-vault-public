#!/usr/bin/env bash
# Verify handshake reports against the roster and record them in the pane map.
# Usage:
#   record-report.sh <roster.json> '<full report line>'
#   record-report.sh --inbox <roster.json>    # every report this team wrote to its durable inbox
# Report line: [<name>] STATUS: DONE — peran: <...>; write boundary: <...>; mandat lapor-balik diterima
# Exit 0 = every processed report accepted; 4 = at least one rejected (reason recorded);
# 1 = usage/IO error. Prints READY <k>/<n>: k agents have launch=verified AND an accepted report.
set -o pipefail

die() { echo "record-report: $*" >&2; exit 1; }
inbox_mode=0
[ "$1" = "--inbox" ] && { inbox_mode=1; shift; }
if [ $inbox_mode -eq 1 ]; then [ $# -eq 1 ] || die "usage: record-report.sh --inbox <roster.json>"
else [ $# -eq 2 ] || die "usage: record-report.sh <roster.json> '<full report line>'"; fi
roster=$1
[ -f "$roster" ] || die "roster not found: $roster"
state_dir=$(jq -r '.state_dir' "$roster" | sed 's:/*$::')
map="$state_dir/pane-map.md"
[ -f "$map" ] || die "pane map not found: $map (run spawn-team.sh first)"
prefix=$(jq -r '.prefix' "$roster")

rejected=0
record() { # record '<line>'
  local line=$1 re name status body expected reason verdict tmp
  re='^\[([a-z][a-z0-9_-]*)\] STATUS: ([A-Z_]+) (—|-) (.*)$'
  if ! [[ $line =~ $re ]]; then echo "skip (not a report line): $line" >&2; return; fi
  name=${BASH_REMATCH[1]} status=${BASH_REMATCH[2]} body=${BASH_REMATCH[4]}
  expected=$(jq -r --arg n "$name" --arg p "$prefix" \
    '.agents[] | select("\($p)-\(.role)" == $n) | .write | if length == 0 then "READ-ONLY" else join(", ") end' "$roster")
  if [ -z "$expected" ]; then echo "skip ($name is not in $roster)" >&2; return; fi
  reason=""
  [ "$status" = DONE ] || reason="status $status"
  case "$body" in *"write boundary: $expected;"*) ;; *) reason="${reason:+$reason; }boundary mismatch (expected: $expected)" ;; esac
  case "$body" in *"mandat lapor-balik diterima"*) ;; *) reason="${reason:+$reason; }mandate not accepted" ;; esac
  verdict="DONE"
  [ -n "$reason" ] && { verdict="REJECTED: $reason"; rejected=1; }
  tmp=$(mktemp) || die "mktemp failed"
  awk -F'|' -v OFS='|' -v n="$name" -v v=" $verdict " '$2 == " " n " " { $8 = v } { print }' "$map" >"$tmp" &&
    mv "$tmp" "$map" || die "cannot update $map"
  echo "$name: $verdict"
}

if [ $inbox_mode -eq 1 ]; then
  run="$state_dir/run.env"
  [ -f "$run" ] || die "missing $run (written by spawn-team.sh)"
  SUP=$(sed -n 's/^SUP=//p' "$run") STARTED=$(sed -n 's/^STARTED=//p' "$run")
  inbox="${PANE_MANAGEMENT_STATE:-$HOME/.local/state/pane-management}/inbox-${SUP//:/-}.log"
  [ -f "$inbox" ] || die "no inbox yet: $inbox"
  # Latest report per agent written since this team was spawned.
  latest=$(awk -F'\t' -v s="$STARTED" '$1 >= s { if (match($2, /^\[[a-z][a-z0-9_-]*\]/)) last[substr($2, 2, RLENGTH - 2)] = $2 }
    END { for (k in last) print last[k] }' "$inbox")
  [ -n "$latest" ] || echo "no report in $inbox since $STARTED"
  while IFS= read -r l; do [ -n "$l" ] && record "$l"; done <<<"$latest"
else
  record "$2"
fi

total=$(jq '.agents | length' "$roster")
ready=$(awk -F'|' '$7 == " verified " && $8 == " DONE " { c++ } END { print c + 0 }' "$map")
pending=$(awk -F'|' 'NR > 6 && $2 != "" && !($7 == " verified " && $8 == " DONE ") { gsub(/ /, "", $2); printf "%s ", $2 }' "$map")
echo "READY $ready/$total${pending:+ — not ready: $pending}"
[ $rejected -eq 0 ] || exit 4
exit 0
