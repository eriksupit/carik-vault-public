#!/usr/bin/env bash
# Attribute every file change made since the team was spawned to a roster owner.
# Usage: audit-writes.sh <roster.json>      (run from the project root = git toplevel)
#
# Sub-agents run in sandboxes that can only write their own paths, so a change
# outside every agent boundary and outside the supervisor's own area can only
# come from the supervisor or a human: that is reported as a VIOLATION.
# Covered: working-tree changes (tracked, untracked, deleted, renamed) and files
# changed by commits since spawn. Pre-existing dirty files are ignored unless
# their content changed after spawn (baseline = state_dir/baseline.tsv).
# Exit 0 = no violation; 5 = violation(s); 1 = usage/IO error.
set -o pipefail

die() { echo "audit-writes: $*" >&2; exit 1; }
[ $# -eq 1 ] || die "usage: audit-writes.sh <roster.json>"
roster=$1
[ -f "$roster" ] || die "roster not found: $roster"
state_dir=$(jq -r '.state_dir' "$roster" | sed 's:/*$::')
run="$state_dir/run.env" baseline="$state_dir/baseline.tsv"
[ -f "$run" ] && [ -f "$baseline" ] || die "missing $run or $baseline (written by spawn-team.sh)"
CWD=$(sed -n 's/^CWD=//p' "$run") BASE_HEAD=$(sed -n 's/^BASE_HEAD=//p' "$run")
[ "$(pwd -P)" = "$CWD" ] || die "run from the project root $CWD"
top=$(git rev-parse --show-toplevel 2>/dev/null) || die "not a git repository: the audit needs git"
[ "$(cd "$top" && pwd -P)" = "$CWD" ] || die "project root must be the git toplevel"

norm() { local p=${1#./}; echo "${p%/}"; }
owners=() areas=()
while IFS=$'\t' read -r o p; do owners+=("$o"); areas+=("$(norm "$p")"); done < <(jq -r '
  (.supervisor.write[] | "supervisor\t\(.)"), ("supervisor\t\(.state_dir)"),
  (.agents[] | .role as $o | .write[] | select(. != ".git/" and . != ".git") | "\($o)\t\(.)")' "$roster")

owner_of() { # owner_of <relative path> -> role, or empty
  local f=$1 i a best="" bestlen=0
  for ((i = 0; i < ${#areas[@]}; i++)); do
    a=${areas[$i]}
    if [ "$f" = "$a" ] || [ "${f#"$a"/}" != "$f" ]; then
      [ ${#a} -gt $bestlen ] && { best=${owners[$i]}; bestlen=${#a}; }
    fi
  done
  echo "$best"
}
content_id() { [ -e "$1" ] && git hash-object -- "$1" 2>/dev/null || echo DELETED; }

changed=$(
  git status --porcelain=v1 -z --untracked-files=all | {
    while IFS= read -r -d '' e; do
      echo "${e:3}"
      if [ "${e:0:1}" = R ] || [ "${e:0:1}" = C ]; then IFS= read -r -d '' old && echo "$old"; fi
    done
  }
  head=$(git rev-parse HEAD 2>/dev/null)
  if [ -n "$BASE_HEAD" ] && [ -n "$head" ] && [ "$head" != "$BASE_HEAD" ]; then
    git diff --name-only "$BASE_HEAD" HEAD
  fi
)

violations=0 checked=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  f=$(norm "$f")
  base=$(awk -F'\t' -v p="$f" '$1 == p { print $2 }' "$baseline")
  if [ -n "$base" ] && [ "$base" = "$(content_id "$f")" ]; then continue; fi
  checked=$((checked + 1))
  o=$(owner_of "$f")
  if [ -z "$o" ]; then
    echo "VIOLATION $f (outside every agent boundary and the supervisor area: written by the supervisor or a human)"
    violations=$((violations + 1))
  else
    echo "OK $f -> $o"
  fi
done < <(sort -u <<<"$changed")

echo "AUDIT checked=$checked violations=$violations"
[ $violations -eq 0 ] || exit 5
exit 0
