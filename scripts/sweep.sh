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

echo "--- run 2b: run/import/diff/milestone ---"
cat > "$D/plan.json" <<'EOF'
{"project_name": "SweepPlan", "operations": [
  {"op": "add", "name": "A", "start": "2026-10-12", "duration": "2d", "ref": "a"},
  {"op": "add", "name": "B", "duration": "1d", "parent": "a", "ref": "b"},
  {"op": "resource_add", "name": "Cici", "ref": "c"},
  {"op": "assign", "task": "b", "resource": "c"},
  {"op": "link", "task": "B", "pred": "A", "type": "FF"},
  {"op": "update", "ref": "a", "percent_complete": 20}
]}
EOF
cp "$D/w.pod" "$D/plan.pod"
need_ok "run script" 0 -- python3 -m pod_opencode run "$D/plan.pod" "$D/plan.json" --output "$D/plan.pod"
python3 - <<EOF
import json, subprocess
def cli(*a):
    r = subprocess.run(["python3", "-m", "pod_opencode", *a], capture_output=True, text=True)
    assert r.returncode == 0, (a, r.stderr)
    return json.loads(r.stdout)
tasks = {t["name"]: t for t in cli("tasks", "list", "$D/plan.pod")["tasks"]}
assert tasks["B"]["parent_id"] == tasks["A"]["unique_id"], tasks
assert tasks["B"]["resource_names"] == ["Cici"], tasks["B"]
assert tasks["B"]["predecessors"][0]["relation_type"] == "FF", tasks["B"]
assert tasks["A"]["percent_complete"] == 20.0, tasks["A"]
assert cli("info", "$D/plan.pod")["name"] == "SweepPlan"
d = cli("diff", "$D/w.pod", "$D/plan.pod")
assert d["summary"]["tasks_added"] == 2, d["summary"]
assert d["project_name"] == {"from": "Sweep", "to": "SweepPlan"}, d["project_name"]
c = cli("check", "$D/plan.pod")
assert c["summary"]["errors"] == 0, c["errors"]
EOF
ok "run result verified"
cat > "$D/batch.json" <<'EOF'
{"tasks": [{"name": "Imp", "duration": "2d", "resources": ["Cici"]}]}
EOF
need_ok "tasks import" 0 -- python3 -m pod_opencode tasks import "$D/plan.pod" "$D/batch.json" --output "$D/plan.pod"
python3 - <<EOF
import json, subprocess
def cli(*a):
    r = subprocess.run(["python3", "-m", "pod_opencode", *a], capture_output=True, text=True)
    assert r.returncode == 0, (a, r.stderr)
    return json.loads(r.stdout)
tasks = {t["name"]: t for t in cli("tasks", "list", "$D/plan.pod")["tasks"]}
assert "Imp" in tasks, sorted(tasks)
assert tasks["Imp"]["resource_names"] == ["Cici"], tasks["Imp"]
b = tasks["B"]["unique_id"]
r = subprocess.run(["python3", "-m", "pod_opencode", "tasks", "update", "$D/plan.pod", str(b), "--milestone", "--output", "$D/plan.pod"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
assert [t for t in cli("tasks", "list", "$D/plan.pod")["tasks"] if t["unique_id"] == b][0]["milestone"] is True
r = subprocess.run(["python3", "-m", "pod_opencode", "tasks", "update", "$D/plan.pod", str(b), "--no-milestone", "--output", "$D/plan.pod"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
assert [t for t in cli("tasks", "list", "$D/plan.pod")["tasks"] if t["unique_id"] == b][0]["milestone"] is False
EOF
ok "import + milestone toggle verified"
python3 - <<EOF
import subprocess
r = subprocess.run(["python3", "-m", "pod_opencode", "convert", "$D/plan.pod", "$D/surg.xml"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
xml = open("$D/surg.xml").read()
head, sep, tail = xml.partition("<Tasks>")
assert sep, "no Tasks block"
link = "<PredecessorLink><PredecessorUID>999</PredecessorUID><Type>1</Type><LinkLag>0</LinkLag></PredecessorLink>"
open("$D/surg.xml", "w").write(head + sep + tail.replace("</DurationFormat>", "</DurationFormat>" + link, 1))
EOF
ok "surgery done"

echo "--- run 3: expected failures ---"
need_ok "check catches dangling link" 1 -- python3 -m pod_opencode check "$D/surg.xml"
need_ok "get missing task" 1 -- python3 -m pod_opencode tasks get "$D/w.pod" 999
need_ok "bad percent" 1 -- python3 -m pod_opencode tasks update "$D/w.pod" 1 --percent-complete 500 --output "$D/x.xml"
need_ok "bad duration" 1 -- python3 -m pod_opencode tasks add "$D/w.pod" --name X --duration "sehari" --output "$D/x.xml"
need_ok "self link" 1 -- python3 -m pod_opencode tasks link "$D/w.pod" 1 1 --output "$D/x.xml"
need_ok "missing file" 1 -- python3 -m pod_opencode info "$D/nope.pod"

echo "ALL $pass CHECKS PASSED"
