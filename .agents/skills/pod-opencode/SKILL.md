---
name: pod-opencode
description: Read and modify ProjectLibre .pod / MSPDI XML schedules via the pod-opencode CLI (tasks, resources, assignments, dependencies, batch import, scripted runs, diff, lint). Use for any .pod or MSPDI .xml work. All output is JSON.
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

If `pod-opencode` is not found, install it first, then continue:

```bash
pip install pod-opencode
pod-opencode --help      # verify install
```

No PyPI access, or want the skill installed everywhere too? Run the
bootstrap from a checkout (or via curl, see README):

```bash
./scripts/bootstrap.sh
```

If already inside this repo, just `pip install -e .`. Requires Java JRE on PATH. First run may be slow (MPXJ init).

## Core rules

1. **Read `.pod` or `.xml`, write `.xml` or `.pod`.** Both outputs open in ProjectLibre. Prefer `.pod` when the user will open the file directly.
2. **Use UniqueID, not ID.** Every `get` / `update` / `delete` / `assign` / `link` command takes UniqueIDs. Never guess one: run `tasks list` (or `resources list`) first, then use the exact `unique_id` values returned.
3. **Dates are ISO 8601** (`--start 2025-07-01`). **Durations** look like `5d`, `40h`, `2w`. **Units are fractions** (`1.0` is full time). **`--percent-complete`** takes 0-100.
4. **Parse stdout as JSON.** Never scrape human text; there is none.
5. **One change: single command. Several changes: ONE `run` call.** Chained commands each pay a JVM startup and can leave half-applied work; `run` validates everything upfront and writes once. Format: `references/run.md`.

## Commands

```bash
pod-opencode info <file>
pod-opencode convert [--project-name TEXT] <input.pod|xml> <output.xml|output.pod>

pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--parent-id UID] [--milestone] [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode tasks update <file> <unique_id> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete FLOAT] [--milestone|--no-milestone] [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode tasks delete <file> <unique_id> [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode tasks assign <file> <task_uid> <resource_uid> [--units FLOAT] [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode tasks unassign <file> <task_uid> <resource_uid> [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode tasks link <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--lag TEXT] [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode tasks unlink <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--project-name TEXT] --output <out.xml|out.pod>

pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode resources update <file> <unique_id> [--name TEXT] [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode resources delete <file> <unique_id> [--project-name TEXT] --output <out.xml|out.pod>

pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]

pod-opencode tasks import <file> <batch.json> [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode run <file> <script.json> [--project-name TEXT] --output <out.xml|out.pod>
pod-opencode diff <old> <new>
pod-opencode check <file>
```

Every write command also accepts `--in-place` instead of `--output`: the input is copied to `<input>.bak`, then overwritten. `--output` and `--in-place` cannot be combined.

`--project-name` sets the project name shown as the window title in ProjectLibre. Set it once on `convert` (or any write); it persists in the file for chained edits.

Full flags and JSON schemas: see `references/commands.md` and `references/json-schemas.md`.
Batch file format: `references/batch.md`. Run script format: `references/run.md`.
Chaining rules: `references/roundtrip.md`.

## Typical workflow

1. `pod-opencode info project.pod` (confirm the file loads, note task/resource counts).
2. `pod-opencode tasks list project.pod` (collect the exact `unique_id` values you will reference).
3. Do the work:
   - one change: a single command with `--output /tmp/out.pod`, e.g.:
     ```bash
     pod-opencode tasks add project.pod --name "New Task" --start 2025-07-01 --duration "5d" --output /tmp/out.pod
     ```
   - several changes: ONE `run` call (see rule 5 and `references/run.md`).
   - many new tasks at once: `tasks import` (see `references/batch.md`).
4. Keep editing the **latest** output (each write is a complete new snapshot, never a delta).
5. Run `pod-opencode check` on the result. Fix reported errors, then hand over the output path.

## Error handling

- Any failure prints exactly one `{"error": ..., "code": ...}` object on stderr with a non-zero exit. Fix the arguments and retry; do not hand-edit XML or `.pod` bytes.
- `INVALID_VALUE` means a bad flag value (dates, durations, percents, unknown type). Nothing was written.
- `TASK_NOT_FOUND`, `RESOURCE_NOT_FOUND`, `ASSIGNMENT_NOT_FOUND`, `LINK_NOT_FOUND` name the missing item. In `run` scripts, unknown names add a "did you mean?" hint.
- `run` failures add `failed_operation` (the index that failed); nothing was written.
- JVM errors (`JPype`, `Java`) mean Java is missing or MPXJ init failed; run `scripts/check-env.py` and report.
