#!/usr/bin/env bash
# Close every pane (and the second tab) of a team spawned by spawn-team.sh and
# clear the supervisor's pane/agent name. Role cards, profiles, and the pane map stay.
# Usage: teardown-team.sh <roster.json>      (run from the project root)
set -o pipefail

die() { echo "teardown-team: $*" >&2; exit 1; }
[ $# -eq 1 ] || die "usage: teardown-team.sh <roster.json>"
roster=$1
state_dir=$(jq -r '.state_dir' "$roster" | sed 's:/*$::') || die "cannot read $roster"
map="$state_dir/pane-map.md" run="$state_dir/run.env"
[ -f "$map" ] && [ -f "$run" ] || die "missing $map or $run"

for p in $(awk -F'|' 'NR > 6 && $3 != "" { gsub(/ /, "", $3); print $3 }' "$map"); do
  herdr pane close "$p" >/dev/null 2>&1 && echo "closed pane $p" || echo "pane $p already gone"
done
tab2=$(sed -n 's/^TAB2=//p' "$run")
[ -n "$tab2" ] && { herdr tab close "$tab2" >/dev/null 2>&1 && echo "closed tab $tab2" || echo "tab $tab2 already gone"; }
sup=$(sed -n 's/^SUP=//p' "$run")
herdr pane rename "$sup" --clear >/dev/null 2>&1
herdr agent rename "$sup" --clear >/dev/null 2>&1
echo "team torn down; supervisor $sup names cleared"
