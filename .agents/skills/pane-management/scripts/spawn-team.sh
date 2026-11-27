#!/usr/bin/env bash
# Spawn an approved multi-pane agent team in Herdr from a roster JSON file.
# Usage: spawn-team.sh [--dry-run] <roster.json>     (run from the project root)
#
# Validates the whole roster before touching the layout, then: renames the
# supervisor pane, splits panes (IDs parsed from JSON), writes one role card and
# one sandbox profile per agent, launches each agent (omp, pi, or agy) under
# sandbox-exec so it can write ONLY inside its boundary, verifies agent kind /
# cwd / status via `herdr pane get`, writes the pane map, sends the handshake,
# and waits for every handshake turn to settle.
# Must run on macOS /bin/bash 3.2: no mapfile, no `set -u` (empty arrays).
set -o pipefail

SKILL_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
REPORT_SH="$SKILL_DIR/scripts/report.sh"
# agy (Antigravity CLI): default model for agy agents without "model", and launch flags.
# AGY_FLAGS comes from a live spike: agy's own terminal sandbox nests sandbox-exec, which
# macOS refuses (`sandbox_apply: Operation not permitted`, every command exits 71), so it is
# disabled for the session; the outer sandbox-exec profile still enforces the write boundary.
AGY_DEFAULT_MODEL=gemini-3.8-flash-medium
AGY_FLAGS=(--mode auto --settings '{"enableTerminalSandbox":false}')

die() { echo "spawn-team: $*" >&2; exit 1; }

dry_run=0
[ "$1" = "--dry-run" ] && { dry_run=1; shift; }
[ $# -eq 1 ] || die "usage: spawn-team.sh [--dry-run] <roster.json | ->"
roster=$1 from_stdin=0
if [ "$roster" = - ]; then # the supervisor never writes the roster file; this script persists it
  stdin_roster=$(mktemp "${TMPDIR:-/tmp}/pm-roster.XXXXXX") || die "cannot create a temp roster"
  trap 'rm -f "$stdin_roster"' EXIT
  cat >"$stdin_roster"; roster=$stdin_roster from_stdin=1
fi
[ -f "$roster" ] || die "roster not found: $roster"
jq -e . "$roster" >/dev/null 2>&1 || die "roster is not valid JSON: $roster"
cwd=$(pwd -P)

# ---------- 1a. Schema validation (jq, no side effects) ----------
errors=$(jq -r '
  def pathok: type == "string" and test("^[A-Za-z0-9._@+-][A-Za-z0-9._@+/-]*$")
              and (sub("/+$"; "") | . != "" and . != ".")
              and (split("/") | index("..") == null);
  def strlist: type == "array" and all(.[]; type == "string");
  . as $r
  | [
      (if ($r.prefix | type) != "string" or ($r.prefix | test("^[a-z][a-z0-9]*(-[a-z0-9]+)*$") | not)
        then "prefix must be lowercase kebab-case" else empty end),
      (if ($r.state_dir | pathok) | not then "state_dir must be a relative path inside the project" else empty end),
      (if ($r.supervisor.write | type) != "array" or ($r.supervisor.write | length) == 0
        then "supervisor.write must be a non-empty array" else empty end),
      (if ($r.agents | type) != "array" or ($r.agents | length) < 1 or ($r.agents | length) > 8
        then "agents must contain 1-8 entries (4 per tab, 2 tabs max)" else empty end),
      ($r.agents[]? | select(.write | type == "array") | . as $a
        | ($a.write | map(sub("^\\./"; "") | sub("/+$"; ""))) as $w
        | if $a.role == "integrator" then
            (if $w != [".git"] then "agent integrator: write must be exactly [\".git/\"]" else empty end)
          elif any($w[]; . == ".git" or startswith(".git/")) then
            "agent \($a.role): only the integrator may write .git/"
          else empty end),
      (if ([$r.supervisor.write[]? | strings | sub("^\\./"; "") | sub("/+$"; "")] | any(. == ".git" or startswith(".git/")))
        then "supervisor.write must not include .git/ (git writes belong to the integrator)" else empty end),
      ($r.agents[]? | . as $a
        | (if ($a.role | type) != "string" or ($a.role | test("^[a-z0-9]+(-[a-z0-9]+)*$") | not)
             then "agent role \($a.role | tojson) must be kebab-case"
           elif $a.role == "supervisor" then "role \"supervisor\" is reserved"
           else empty end),
          (if ($a.engine | IN("omp", "pi", "agy")) | not
             then "agent \($a.role): engine must be omp, pi, or agy (got \($a.engine | tojson))" else empty end),
          (if ($a.description | type) != "string" or $a.description == ""
             then "agent \($a.role): description is required" else empty end),
          (if ($a.write | strlist) | not
             then "agent \($a.role): write must be an array of strings ([] means read-only)" else empty end),
          (if has("forbidden") and (($a.forbidden | strlist) | not)
             then "agent \($a.role): forbidden must be an array of strings" else empty end),
          (if has("model") and (($a.model | type) != "string" or $a.model == "")
             then "agent \($a.role): model must be a non-empty string (omit it for the default)" else empty end),
          (if ($a.model | type) == "string" and ($a.model | test("^(antigravity/)?gemini-")) and $a.engine != "agy"
             then "agent \($a.role): Gemini model \($a.model) must run on engine agy (Antigravity CLI), not \($a.engine | tojson); set \"engine\": \"agy\" and a model id from `agy models`" else empty end)),
      (["supervisor", ($r.agents[]?.role | strings)] | map("\($r.prefix)-\(.)")[]
        | select(test("^[a-z][a-z0-9_-]{0,31}$") | not)
        | "name \(.) violates herdr agent-name rule ^[a-z][a-z0-9_-]{0,31}$"),
      ([$r.agents[]?.role] | group_by(.) | map(select(length > 1)[0])[] | "duplicate role \(.)"),
      (([{o: "supervisor", p: ($r.supervisor.write[]?)}] + [$r.agents[]? as $a | {o: $a.role, p: ($a.write | arrays | .[])}])[]
        | select((.p | pathok) | not)
        | "\(.o): invalid write path \(.p | tojson) (relative, chars A-Za-z0-9._@+-/, no .., not the project root)")
    ]
  | .[]' "$roster")

# ---------- 1b. Path resolution, escape and overlap checks (on real paths) ----------
resolve() { # resolve <relative path> -> absolute physical path (symlinks followed for existing parts)
  local p="$cwd/${1%/}" rest=""
  while [ ! -e "$p" ]; do rest="/$(basename "$p")$rest"; p=$(dirname "$p"); done
  if [ -d "$p" ]; then echo "$(cd "$p" && pwd -P)$rest"
  else echo "$(cd "$(dirname "$p")" && pwd -P)/$(basename "$p")$rest"; fi
}
if [ -z "$errors" ]; then
  owners=() paths=()
  while IFS=$'\t' read -r o p; do
    r=$(resolve "$p")
    case "$r/" in
      "$cwd"/?*) owners+=("$o"); paths+=("$r") ;;
      *) errors+=$'\n'"$o: write path $p resolves to $r, outside the project $cwd" ;;
    esac
  done < <(jq -r '(.supervisor.write[] | "supervisor\t\(.)"), (.agents[] | .role as $o | .write[] | "\($o)\t\(.)")' "$roster")
  for ((i = 0; i < ${#paths[@]}; i++)); do
    for ((j = i + 1; j < ${#paths[@]}; j++)); do
      [ "${owners[$i]}" = "${owners[$j]}" ] && continue
      x=${paths[$i]} y=${paths[$j]}
      if [ "$x" = "$y" ] || [ "${y#"$x"/}" != "$y" ] || [ "${x#"$y"/}" != "$x" ]; then
        errors+=$'\n'"write overlap: ${owners[$i]} owns ${x#"$cwd"/} and ${owners[$j]} owns ${y#"$cwd"/}"
      fi
    done
  done
  sd=$(resolve "$(jq -r '.state_dir' "$roster")") inside=0
  for ((i = 0; i < ${#paths[@]}; i++)); do
    [ "${owners[$i]}" = supervisor ] || continue
    { [ "$sd" = "${paths[$i]}" ] || [ "${sd#"${paths[$i]}"/}" != "$sd" ]; } && inside=1
  done
  [ $inside -eq 1 ] || errors+=$'\n'"state_dir must lie inside supervisor.write (only the skill scripts write state_dir)"
fi
case "$cwd" in *'"'* | *'\'*) errors+=$'\n'"project path $cwd contains a quote or backslash; the sandbox profile cannot encode it" ;; esac
model_catalog() { # model_catalog <engine> -> one model id per line ("provider/model" for omp/pi)
  case $1 in
    omp) omp models 2>/dev/null | awk '/^[a-z0-9-]+ \([0-9]+\)$/ { p = $1 } /^│ / { print p "/" $2 }' ;;
    pi)  pi --list-models 2>/dev/null | awk 'NR > 1 && NF >= 2 { print $1 "/" $2 }' ;;
    agy) agy models 2>/dev/null | awk -F'\t' 'NF >= 2 { print $1 }' ;;
  esac
}
catalog_cmd() { case $1 in omp) echo "omp models" ;; pi) echo "pi --list-models" ;; agy) echo "agy models" ;; esac; }
catalog_engine=""
while IFS=$'\t' read -r e m; do
  command -v "$e" >/dev/null || continue
  [ "$e" = "$catalog_engine" ] || { catalog=$(model_catalog "$e"); catalog_engine=$e; } # input is sorted by engine
  case $e in
    agy) grep -qxF "$m" <<<"$catalog" ;; # agy ids carry the effort (gemini-4-argon-high): exact match only
    *) base=${m%%:*}                     # omp/pi: allow a ":<thinking>" suffix
       case $base in
         */*) grep -qxF "$base" <<<"$catalog" ;;
         *)   grep -q "/$(sed 's/[.[\*^$]/\\&/g' <<<"$base")\$" <<<"$catalog" ;;
       esac ;;
  esac || errors+=$'\n'"model $m is not in the $e model catalog (check: $(catalog_cmd "$e"))"
done < <(jq -r --arg d "$AGY_DEFAULT_MODEL" '[.agents[]? | select(.engine | type == "string")
  | {e: .engine, m: (if .engine == "agy" and ((.model // "") == "") then $d else (.model // "") end)}
  | select(.m | type == "string" and . != "")] | sort_by(.e)[] | "\(.e)\t\(.m)"' "$roster" 2>/dev/null)

# ---------- 1c. Environment checks ----------
command -v sandbox-exec >/dev/null ||
  errors+=$'\n'"sandbox-exec not found: write boundaries are enforced with macOS sandbox-exec; this host is unsupported"
integrations=$(herdr integration status 2>/dev/null)
for e in $(jq -r '[.agents[]?.engine | strings] | unique[]' "$roster"); do
  command -v "$e" >/dev/null || errors+=$'\n'"engine $e is not installed (not on PATH)"
  hi=$e; [ "$e" = agy ] && hi=antigravity-cli # Herdr's integration id for the Antigravity CLI
  # Without Herdr's lifecycle integration the agent always reads as idle, which breaks waits and self-heal.
  grep -q "^$hi: current" <<<"$integrations" ||
    errors+=$'\n'"Herdr integration for $e is not current ($(grep "^$hi:" <<<"$integrations" | cut -d' ' -f2-3)); ask the owner to run: herdr integration install $hi"
done
git_top=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$git_top" ]; then
  [ "$(cd "$git_top" && pwd -P)" = "$cwd" ] ||
    errors+=$'\n'"run from the git toplevel $git_top (audit-writes.sh and the integrator need it)"
  git_dirs=$( { git rev-parse --absolute-git-dir; (cd "$(git rev-parse --git-common-dir)" && pwd -P); } 2>/dev/null | sort -u)
else
  git_dirs=""
  jq -e '[.agents[]?.role] | index("integrator")' "$roster" >/dev/null 2>&1 &&
    errors+=$'\n'"roster has an integrator but $cwd is not a git repository"
fi

prefix=$(jq -r '.prefix' "$roster")
sup_name="$prefix-supervisor"
names=()
while IFS= read -r line; do names+=("$line"); done < <(jq -r --arg p "$prefix" '.agents[]?.role | strings | "\($p)-\(.)"' "$roster")

if [ "$HERDR_ENV" = 1 ]; then
  live=$(herdr agent list 2>/dev/null | jq -r --arg me "$HERDR_PANE_ID" \
    '.result.agents[] | select(.pane_id != $me) | .name // empty')
  for n in "$sup_name" "${names[@]}"; do
    grep -qxF "$n" <<<"$live" && errors+=$'\n'"name $n is already used by another live agent"
  done
elif [ $dry_run -eq 0 ]; then
  errors+=$'\n'"not inside a Herdr pane (HERDR_ENV!=1)"
fi

errors=$(sed '/^$/d' <<<"$errors")
if [ -n "$errors" ]; then
  echo "ROSTER REJECTED — no pane was created:" >&2
  sed 's/^/  - /' <<<"$errors" >&2
  exit 2
fi

n=${#names[@]}
if [ $dry_run -eq 1 ]; then
  echo "ROSTER OK (dry-run): $sup_name + $n agent(s): ${names[*]}"
  exit 0
fi

# ---------- 2. Run record, baseline, layout ----------
SUP=$HERDR_PANE_ID
state_dir=$(jq -r '.state_dir' "$roster" | sed 's:/*$::')
mkdir -p "$state_dir/roles" "$state_dir/sandbox" || die "cannot create $state_dir"
if [ $from_stdin -eq 1 ]; then
  cp "$roster" "$state_dir/roster.json" || die "cannot persist the roster to $state_dir/roster.json"
  roster="$state_dir/roster.json"
fi

# run.env + baseline.tsv feed record-report.sh --inbox and audit-writes.sh.
{
  echo "SUP=$SUP"
  echo "STARTED=$(date '+%Y-%m-%dT%H:%M:%S')"
  echo "CWD=$cwd"
  echo "BASE_HEAD=$( [ -n "$git_top" ] && git rev-parse HEAD 2>/dev/null)"
} >"$state_dir/run.env" || die "cannot write $state_dir/run.env"
: >"$state_dir/baseline.tsv"
if [ -n "$git_top" ]; then
  git status --porcelain=v1 -z --untracked-files=all | while IFS= read -r -d '' e; do
    f=${e:3}
    printf '%s\t%s\n' "$f" "$( [ -e "$f" ] && git hash-object -- "$f" 2>/dev/null || echo DELETED)"
    case ${e:0:1} in R | C) IFS= read -r -d '' old && printf '%s\tDELETED\n' "$old" ;; esac
  done >"$state_dir/baseline.tsv"
fi

created=() created_tabs=()
cleanup_layout() {
  local p t
  for p in "${created[@]}"; do herdr pane close "$p" >/dev/null 2>&1; done
  for t in "${created_tabs[@]}"; do herdr tab close "$t" >/dev/null 2>&1; done
  die "layout failed: $1 (closed the panes and tabs created by this run)"
}
split() { # split <parent> <right|down> <ratio>; sets SPLIT_ID in the caller's shell
  local out
  out=$(herdr pane split --pane "$1" --direction "$2" --ratio "$3" --cwd "$cwd" --no-focus 2>&1) || cleanup_layout "$out"
  SPLIT_ID=$(jq -r '.result.pane.pane_id // empty' <<<"$out")
  [ -n "$SPLIT_ID" ] || cleanup_layout "no pane_id in split response: $out"
  created+=("$SPLIT_ID")
}

herdr pane rename "$SUP" "$sup_name" >/dev/null || die "cannot rename supervisor pane $SUP"
herdr agent rename "$SUP" "$sup_name" >/dev/null 2>&1 ||
  echo "spawn-team: warning: supervisor agent not renamed (agent not detected in $SUP)" >&2

# --ratio is the share kept by the pane being split (measured: 0.333 -> source keeps 1/3).
# Tab 1: supervisor left, agents 1-4 in the right column (1 / 2 stacked / 3 thirds / 2x2).
n1=$n; [ $n1 -gt 4 ] && n1=4
split "$SUP" right 0.5; a=$SPLIT_ID
case $n1 in
  1) panes=("$a") ;;
  2) split "$a" down 0.5; panes=("$a" "$SPLIT_ID") ;;
  3) split "$a" down 0.333; b=$SPLIT_ID; split "$b" down 0.5; panes=("$a" "$b" "$SPLIT_ID") ;;
  4) split "$a" right 0.5; b=$SPLIT_ID; split "$a" down 0.5; c=$SPLIT_ID; split "$b" down 0.5
     panes=("$a" "$b" "$c" "$SPLIT_ID") ;;   # top-left, top-right, bottom-left, bottom-right
esac
# Tab 2: agents 5-8 (1 full / 2 side by side / 3 = left + right stacked / 2x2).
n2=$((n - n1))
if [ $n2 -gt 0 ]; then
  out=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$cwd" --label "$prefix-team-2" --no-focus 2>&1) ||
    cleanup_layout "$out"
  t=$(jq -r '.result.tab.tab_id // empty' <<<"$out") r=$(jq -r '.result.root_pane.pane_id // empty' <<<"$out")
  [ -n "$t" ] && [ -n "$r" ] || cleanup_layout "no tab/root pane id in tab create response: $out"
  created_tabs+=("$t")
  echo "TAB2=$t" >>"$state_dir/run.env"
  case $n2 in
    1) panes+=("$r") ;;
    2) split "$r" right 0.5; panes+=("$r" "$SPLIT_ID") ;;
    3) split "$r" right 0.5; b=$SPLIT_ID; split "$b" down 0.5; panes+=("$r" "$b" "$SPLIT_ID") ;;
    4) split "$r" right 0.5; b=$SPLIT_ID; split "$r" down 0.5; c=$SPLIT_ID; split "$b" down 0.5
       panes+=("$r" "$b" "$c" "$SPLIT_ID") ;;
  esac
fi

# ---------- 3. Role card, sandbox profile, launch, verification ----------
launch() { # launch <pane> <engine> <profile> <shell-tail> <args...>; prints status
  # <shell-tail> is appended verbatim (already shell syntax); <args> are quoted with printf %q,
  # which bash 3.2 cannot apply to non-ASCII text (it emits invalid UTF-8 that herdr rejects).
  local pane=$1 engine=$2 profile=$3 tail=$4 cmd got a_kind a_status i
  shift 4
  cmd="sandbox-exec -f $(printf %q "$profile") $engine"
  for a in "$@"; do cmd+=" $(printf %q "$a")"; done
  [ -n "$tail" ] && cmd+=" $tail"
  herdr pane run "$pane" "$cmd" >/dev/null 2>&1 || { echo "start_failed:pane_run"; return; }
  for ((i = 0; i < 60; i++)); do
    got=$(herdr pane get "$pane" | jq -r '.result.pane | "\(.agent)|\(.agent_status)"')
    a_kind=${got%%|*} a_status=${got#*|}
    if [ "$a_kind" = "$engine" ] && { [ "$a_status" = idle ] || [ "$a_status" = done ]; }; then echo ok; return; fi
    [ "$a_kind" = "$engine" ] && [ "$a_status" = blocked ] && { echo "not_ready:blocked"; return; }
    sleep 1
  done
  echo "start_failed:timeout(agent=$a_kind,status=$a_status)"
}

results=()
for ((i = 0; i < n; i++)); do
  a=$(jq -c ".agents[$i]" "$roster")
  name=${names[$i]} pane=${panes[$i]}
  engine=$(jq -r '.engine' <<<"$a")
  model=$(jq -r --arg d "$AGY_DEFAULT_MODEL" 'if .engine == "agy" and ((.model // "") == "") then $d else (.model // "") end' <<<"$a")
  write_list=$(jq -r '.write | if length == 0 then "READ-ONLY" else join(", ") end' <<<"$a")
  card="$cwd/$state_dir/roles/$name.md"
  profile="$cwd/$state_dir/sandbox/$name.sb"

  jq -r --arg name "$name" --arg prefix "$prefix" --arg sup "$SUP" --arg supname "$sup_name" \
        --arg cwd "$cwd" --arg report "$REPORT_SH" --arg card "$card" '
    "# Role card: \($name)\n",
    "You are `\($name)`, a sub-agent in the multi-pane team of project `\($prefix)`. Your supervisor is `\($supname)` in Herdr pane `\($sup)`.\n",
    "## Responsibility\n\(.description)\n",
    "## Working directory\n`\($cwd)`\n",
    "## Write boundary (OS-enforced)",
    (if .role == "integrator"
      then "You may write ONLY git metadata (the git directory): create branches, stage, commit, push, `gh pr create`, `gh pr merge`, `git fetch`. The working tree under `\($cwd)` is read-only for you (macOS sandbox), so never run a local merge, rebase, pull, stash, or checkout that changes files. Act only on supervisor dispatch and commit only the paths the supervisor names."
    elif (.write | length) == 0
      then "STRICTLY READ-ONLY inside the project. You run in a macOS sandbox that denies every write under `\($cwd)`. Deliver findings only through reports."
      else "You may create or modify files ONLY under: " + (.write | map("`" + . + "`") | join(", ")) + ". You run in a macOS sandbox that denies every other write under `\($cwd)`, including git metadata (only the integrator commits)." end),
    (if (.forbidden // [] | length) > 0 then "Explicitly forbidden: " + (.forbidden | map("`" + . + "`") | join(", ")) + "." else empty end),
    "A write that fails with `Operation not permitted` is the boundary working: do not retry it elsewhere; report BLOCKED instead.\n",
    "## Language",
    "Indonesian when reporting to the supervisor or talking to the owner; English for code, commit messages, and technical docs.\n",
    "## Report-back mandate (mandatory)",
    "When any task finishes, fails, or is blocked, run this BEFORE ending your turn:",
    "```bash",
    "bash \($report) \($sup) \($name) \"STATUS: <DONE|BLOCKED|NEEDS_CONTEXT> — <ringkasan>\"",
    "```",
    "The supervisor does not poll: a task without a delivered report counts as not done. For long tasks, report after each mandate. If the script exits non-zero, say so in your own pane.\n",
    "If your context was compacted or summarized, re-read this card (`\($card)`) before your next action."
  ' <<<"$a" >"$card" || die "cannot write role card $card"

  {
    echo "(version 1)"
    echo "(allow default)"
    echo "(deny file-write* (subpath \"$cwd\"))"
    while IFS= read -r p; do
      [ -n "$p" ] || continue
      case ${p%/} in .git | ./.git) continue ;; esac   # integrator: handled by the git rules below
      r=$(resolve "$p")
      [ -e "$r" ] || mkdir -p "$r"
      echo "(allow file-write* (subpath \"$r\"))"
    done < <(jq -r '.write[]' <<<"$a")
    while IFS= read -r g; do
      [ -n "$g" ] || continue
      if [ "$(jq -r '.role' <<<"$a")" = integrator ]; then echo "(allow file-write* (subpath \"$g\"))"
      else echo "(deny file-write* (subpath \"$g\"))"; fi
    done <<<"$git_dirs"
  } >"$profile" || die "cannot write sandbox profile $profile"

  tail=""
  case $engine in
    # agy has no system-prompt flag: the card becomes the first turn (read by the pane's shell, so
    # its UTF-8 text is never re-quoted here), and the card says to re-read it after compaction.
    agy) args=("${AGY_FLAGS[@]}")
         tail="-i \"\$(printf '%s\\n\\n' 'Role card di bawah ini adalah instruksi sistem untuk seluruh sesi ini. Jangan jalankan tool apa pun sekarang; balas satu kata SIAP lalu tunggu instruksi berikutnya.'; cat $(printf %q "$card"))\"" ;;
    *) args=(--append-system-prompt "$card") ;;
  esac
  [ -n "$model" ] && args+=(--model "$model")

  herdr pane rename "$pane" "$name" >/dev/null
  st=$(launch "$pane" "$engine" "$profile" "$tail" "${args[@]}")
  if [ "$st" = ok ] && [ "$engine" = agy ]; then
    # Let the -i card turn settle so the handshake never lands mid-turn.
    herdr agent wait "$pane" --until working --timeout 15000 >/dev/null 2>&1
    herdr agent wait "$pane" --timeout 120000 >/dev/null 2>&1
    case $(herdr pane get "$pane" | jq -r '.result.pane.agent_status') in
      idle | done) ;;
      blocked) st="not_ready:blocked" ;;
      *) st="not_ready:card_turn" ;;
    esac
  fi
  if [ "$st" = ok ]; then
    herdr agent rename "$pane" "$name" >/dev/null 2>&1 || st="rename_failed"
  fi
  if [ "$st" = ok ]; then
    got=$(herdr pane get "$pane" | jq -r '.result.pane | "\(.agent)|\(.cwd)"')
    g_agent=${got%%|*} g_cwd=${got#*|}
    g_cwd=$(cd "$g_cwd" 2>/dev/null && pwd -P || echo "$g_cwd")
    if [ "$g_agent" != "$engine" ]; then st="wrong_agent:$g_agent"
    elif [ "$g_cwd" != "$cwd" ]; then st="wrong_cwd:$g_cwd"
    else st=verified
    fi
  fi
  results+=("$name|$pane|$engine|${model:-default}|$write_list|$st")
done

# ---------- 4. Pane map (supervisor is the only writer) ----------
map="$state_dir/pane-map.md"
{
  echo "# $prefix pane map"
  echo
  echo "Generated by spawn-team.sh on $(date '+%Y-%m-%d %H:%M:%S'). Supervisor: \`$sup_name\` in \`$SUP\`. cwd: \`$cwd\`. Roster: \`$roster\`."
  echo
  echo "| Agent | Pane | Engine | Model | Write boundary | Launch check | Handshake report |"
  echo "|---|---|---|---|---|---|---|"
  for r in "${results[@]}"; do
    IFS='|' read -r a_name a_pane a_engine a_model a_write a_status <<<"$r"
    echo "| $a_name | $a_pane | $a_engine | $a_model | $a_write | $a_status | pending |"
  done
} >"$map"

# ---------- 5. Handshake + wait for each handshake turn to settle ----------
handshaken=()
for r in "${results[@]}"; do
  IFS='|' read -r a_name a_pane _ _ a_write a_status <<<"$r"
  [ "$a_status" = verified ] || continue
  msg="[INITIAL HANDSHAKE] Tim \"$prefix\": kamu $a_name. Role card-mu sudah dimuat (sumber: $cwd/$state_dir/roles/$a_name.md). Jangan mengedit file apa pun untuk handshake ini. Jalankan perintah ini; ganti HANYA <ringkas>, salin bagian lain persis tanpa tambahan apa pun:
bash $REPORT_SH $SUP $a_name \"STATUS: DONE — peran: <ringkas>; write boundary: $a_write; mandat lapor-balik diterima\"
lalu akhiri giliranmu."
  herdr agent prompt "$a_name" "$msg" >/dev/null 2>&1 && handshaken+=("$a_name")
done
for a_name in "${handshaken[@]}"; do
  herdr agent wait "$a_name" --until working --timeout 15000 >/dev/null 2>&1
  herdr agent wait "$a_name" --timeout 180000 >/dev/null 2>&1
done

# ---------- 6. Summary ----------
echo "SUPERVISOR $sup_name $SUP"
for r in "${results[@]}"; do
  IFS='|' read -r a_name a_pane a_engine _ _ a_status <<<"$r"
  hs=no; printf '%s\n' "${handshaken[@]}" | grep -qxF "$a_name" && hs=sent
  final=$(herdr pane get "$a_pane" 2>/dev/null | jq -r '.result.pane.agent_status // "unknown"')
  echo "AGENT $a_name $a_pane engine=$a_engine launch=$a_status handshake=$hs now=$final"
done
echo "PANE_MAP $map"
echo "NEXT: bash $SKILL_DIR/scripts/record-report.sh --inbox $roster   (repeat when a report notification arrives)"
printf '%s\n' "${results[@]}" | grep -qv '|verified$' && exit 3
exit 0
