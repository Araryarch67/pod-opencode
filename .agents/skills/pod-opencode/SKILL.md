---
name: pod-opencode
description: Read and modify ProjectLibre .pod / MSPDI XML project schedules via the pod-opencode CLI. Use when working with .pod or MSPDI .xml files to list, get, add, update, or delete tasks and resources, view assignments, get project info, or convert POD to XML. All read output is JSON.
license: MIT
compatibility: Requires Python 3.10+, Java JRE 8+, and the pod-opencode package installed.
metadata:
  audience: ai-agent
  repo: Araryarch67/pod-opencode
---

# pod-opencode

CLI for ProjectLibre `.pod` files (via MPXJ). All read commands print a single JSON object to stdout; errors go to stderr as `{"error": ..., "code": ...}`.

## When to use

- User mentions `.pod`, ProjectLibre, MSPDI XML, tasks, resources, assignments, or project schedule.
- Prefer this skill over manual XML parsing.

## Prerequisites

Check once per session with `scripts/check-env.py`, or manually:

```bash
java -version            # must exist (JRE 8+)
pod-opencode --help      # must exist
```

If `pod-opencode` is not found, clone and install first, then continue:

```bash
git clone https://github.com/Araryarch67/pod-opencode.git
cd pod-opencode
pip install -e .
pod-opencode --help      # verify install
```

If already inside this repo, just `pip install -e .`. Requires Java JRE on PATH. First run may be slow (MPXJ init).

## Core rules

1. **Read `.pod` or `.xml`, write `.xml` only.** MPXJ cannot write POD. All write commands require `--output <file.xml>` and reject `.pod`. Workflow: read `.pod` → modify → write `.xml` → open in ProjectLibre (File > Open works with `.xml`).
2. **Use UniqueID, not ID.** `get` / `update` / `delete` take `unique_id` (stable). `id` is sequential and may shift.
3. **Dates are ISO 8601**: `--start 2025-07-01`. Durations are MPXJ human format: `5d`, `40h`, `2w`.
4. **Parse stdout as JSON.** Never scrape human text; there is none.

## Commands

```bash
pod-opencode info <file>
pod-opencode convert <input.pod|xml> <output.xml>

pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] --output <out.xml>
pod-opencode tasks update <file> <unique_id> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete FLOAT] --output <out.xml>
pod-opencode tasks delete <file> <unique_id> --output <out.xml>

pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] --output <out.xml>
pod-opencode resources update <file> <unique_id> [--name TEXT] [--email TEXT] [--max-units FLOAT] --output <out.xml>
pod-opencode resources delete <file> <unique_id> --output <out.xml>

pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

Full flags and JSON schemas: see `references/commands.md` and `references/json-schemas.md`.

## Typical workflow

1. `pod-opencode info project.pod` — confirm file loads, note task/resource counts.
2. `pod-opencode tasks list project.pod` — find `unique_id` values.
3. Mutate with `--output /tmp/out.xml`, e.g.:
   ```bash
   pod-opencode tasks add project.pod --name "New Task" --start 2025-07-01 --duration "5d" --output /tmp/out.xml
   ```
4. Chain edits off the **latest** `.xml` (each write produces a new full snapshot).
5. Report the output path and `affected_unique_id` from the `{"status":"ok", ...}` response.

POD→XML round-trip details: `references/roundtrip.md`.

## Error handling

- `FILE_NOT_FOUND`, invalid ID, or `.pod` as `--output` → JSON on stderr, non-zero exit. Fix args and retry; do not hand-edit XML.
- JVM errors (`JPype`, `Java`) → Java missing or MPXJ init failed; run `scripts/check-env.py` and report.
