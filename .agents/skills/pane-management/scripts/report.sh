#!/usr/bin/env bash
# Deliver one report-back message from a sub-agent to the supervisor.
# Usage: report.sh <supervisor-pane-id> <sender-name> "<message>"
#
# 1. Appends the report to a durable inbox outside the project (survives a
#    message that gets merged into text the human is typing in the supervisor):
#    ${PANE_MANAGEMENT_STATE:-~/.local/state/pane-management}/inbox-<pane>.log
# 2. Notifies the supervisor agent with `herdr agent prompt`, retrying while the
#    supervisor shows an approval/question dialog (agent_blocked).
# Exit 0 = recorded and notified; 1 = notify failed; 2 = supervisor stayed
# blocked; 3 = inbox write failed. On non-zero, say so in your own pane.
set -o pipefail

[ $# -eq 3 ] || { echo "usage: report.sh <supervisor-pane-id> <sender-name> <message>" >&2; exit 64; }
sup=$1 sender=$2 msg=$3
attempts=${REPORT_ATTEMPTS:-12}
delay=${REPORT_DELAY_SECONDS:-10}
line="[$sender] $msg"

state=${PANE_MANAGEMENT_STATE:-$HOME/.local/state/pane-management}
inbox="$state/inbox-${sup//:/-}.log"
mkdir -p "$state" && printf '%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "${line//$'\n'/ }" >>"$inbox" ||
  { echo "report NOT recorded: cannot append to $inbox" >&2; exit 3; }

for ((i = 1; i <= attempts; i++)); do
  if out=$(herdr agent prompt "$sup" "$line" 2>&1); then
    echo "report recorded in $inbox and delivered to $sup (attempt $i)"
    exit 0
  fi
  code=$(jq -r '.error.code // empty' <<<"$out" 2>/dev/null)
  if [ "$code" != "agent_blocked" ]; then
    echo "report recorded in $inbox but NOT delivered to $sup: $out" >&2
    exit 1
  fi
  echo "supervisor $sup is blocked on a dialog; retry $i/$attempts in ${delay}s" >&2
  sleep "$delay"
done
echo "report recorded in $inbox but NOT delivered: supervisor $sup stayed blocked for $((attempts * delay))s" >&2
exit 2
