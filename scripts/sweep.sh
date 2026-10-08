#!/usr/bin/env bash
# Practical end-to-end sweep: every command against a real .pod copy.
# Usage: ./scripts/sweep.sh [workdir]
# Fails (exit 1) on the first unexpected result.
set -euo pipefail
D="${1:-/tmp/opencode/sweep}"
REPO=/home/ararya/Documents/pod-opencode
rm -rf "$D"; mkdir -p "$D"
cp "$REPO/tests/fixtures/real.pod" "$D/w.pod"
cd "$REPO"

pass=0
ok() { pass=$((pass+1)); echo "ok $pass: $1"; }
need_ok() { # need_ok <desc> <expected-exit> -- <cmd...>
  local desc="$1"; local want="$2"; shift 2
  if [ "$1" = "--" ]; then shift; fi
  set +e
  out=$("$@" 2>"$D/stderr.txt")
  code=$?
  set -e
  if [ "$code" != "$want" ]; then
    echo "FAIL: $desc (exit $code, want $want)"; cat "$D/stderr.txt"; exit 1
  fi
  ok "$desc"
}
need_json() { echo "$1" | python3 -c "import json,sys; json.load(sys.stdin)" && ok "$2 valid json"; }

echo "--- run 1: reads ---"
need_ok "info pod" 0 -- python3 -m pod_opencode info "$D/w.pod"
need_json "$(python3 -m pod_opencode info "$D/w.pod")" "info"
need_ok "tasks list" 0 -- python3 -m pod_opencode tasks list "$D/w.pod"
need_ok "resources list" 0 -- python3 -m pod_opencode resources list "$D/w.pod"
need_ok "resources get" 0 -- python3 -m pod_opencode resources get "$D/w.pod" 0
need_ok "assignments list" 0 -- python3 -m pod_opencode assignments list "$D/w.pod"
need_ok "check clean-ish" 0 -- python3 -m pod_opencode check "$D/w.pod"

echo "--- run 2: writes ---"
need_ok "convert rename pod" 0 -- python3 -m pod_opencode convert --project-name "Sweep" "$D/w.pod" "$D/w.pod"
need_ok "convert to xml" 0 -- python3 -m pod_opencode convert "$D/w.pod" "$D/w.xml"
need_ok "tasks add" 0 -- python3 -m pod_opencode tasks add "$D/w.pod" --name "T1" --start 2026-10-12 --duration "5d" --output "$D/w.pod"
need_ok "tasks add child milestone" 0 -- python3 -m pod_opencode tasks add "$D/w.pod" --name "M1" --milestone --parent-id 1 --output "$D/w.pod"
need_ok "tasks update pct" 0 -- python3 -m pod_opencode tasks update "$D/w.pod" 1 --percent-complete 25 --output "$D/w.pod"
need_ok "tasks get updated" 0 -- python3 -m pod_opencode tasks get "$D/w.pod" 1
need_ok "resources add" 0 -- python3 -m pod_opencode resources add "$D/w.pod" --name "Budi" --output "$D/w.pod"
need_ok "tasks assign" 0 -- python3 -m pod_opencode tasks assign "$D/w.pod" 1 1 --units 0.5 --output "$D/w.pod"
need_ok "tasks link" 0 -- python3 -m pod_opencode tasks link "$D/w.pod" 2 1 --output "$D/w.pod"
need_ok "assignments filtered" 0 -- python3 -m pod_opencode assignments list "$D/w.pod" --task-id 1
need_ok "tasks unlink" 0 -- python3 -m pod_opencode tasks unlink "$D/w.pod" 2 1 --output "$D/w.pod"
need_ok "tasks unassign" 0 -- python3 -m pod_opencode tasks unassign "$D/w.pod" 1 1 --output "$D/w.pod"
need_ok "resources update" 0 -- python3 -m pod_opencode resources update "$D/w.pod" 1 --email "budi@x.com" --output "$D/w.pod"
need_ok "resources delete" 0 -- python3 -m pod_opencode resources delete "$D/w.pod" 1 --output "$D/w.pod"
need_ok "tasks delete" 0 -- python3 -m pod_opencode tasks delete "$D/w.pod" 2 --output "$D/w.pod"
need_ok "in-place update" 0 -- python3 -m pod_opencode tasks update "$D/w.pod" 1 --percent-complete 50 --in-place
test -f "$D/w.pod.bak" && ok "backup created"
need_ok "diff self clean" 0 -- python3 -m pod_opencode diff "$D/w.pod" "$D/w.pod"
need_ok "check after edits" 0 -- python3 -m pod_opencode check "$D/w.pod"

echo "--- run 3: expected failures ---"
need_ok "get missing task" 1 -- python3 -m pod_opencode tasks get "$D/w.pod" 999
need_ok "bad percent" 1 -- python3 -m pod_opencode tasks update "$D/w.pod" 1 --percent-complete 500 --output "$D/x.xml"
need_ok "bad duration" 1 -- python3 -m pod_opencode tasks add "$D/w.pod" --name X --duration "sehari" --output "$D/x.xml"
need_ok "self link" 1 -- python3 -m pod_opencode tasks link "$D/w.pod" 1 1 --output "$D/x.xml"
need_ok "missing file" 1 -- python3 -m pod_opencode info "$D/nope.pod"

echo "ALL $pass CHECKS PASSED"
