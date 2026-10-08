# pod-opencode

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/pod-opencode.svg)](https://pypi.org/project/pod-opencode/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A Python CLI for reading and writing ProjectLibre `.pod` files via MPXJ, built so AI assistants can work with project schedules through shell commands. Every read prints one JSON object, every write returns one JSON receipt.

Based on [pod-ai-cli](https://github.com/distractdiverge/pod-ai-cli) by distractdiverge, extended with native `.pod` output, project renaming, and an installable agent skill. See [Credits](#credits).

## Contents

- [Features](#features)
- [AI agent skill](#ai-agent-skill)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Commands](#commands)
- [Project name and window title](#project-name-and-window-title)
- [The `.pod` format](#the-pod-format)
- [IDs, dates, durations](#ids-dates-durations)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Credits](#credits)
- [License](#license)

## Features

- Read `.pod` and MSPDI `.xml`: project info, tasks, resources, assignments.
- Write back to `.xml` or native `.pod`, or modify in place with `--in-place` (automatic `.bak` backup).
- Add, update, and delete tasks and resources by stable UniqueID.
- Assign resources to tasks, link predecessors (FS, SS, FF, SF with lag), import whole plans from one JSON file.
- Compare two revisions with `diff`.
- Lint a file with `check` before opening it in ProjectLibre.
- Run whole scripts with `run`: many operations, one JVM session, one write.
- Set the project name from the CLI, so ProjectLibre opens the file with the right title.
- JSON on stdout for reads, JSON receipts for writes, JSON errors on stderr with stable codes.

## AI agent skill

This repo ships a `pod-opencode` skill, pre-installed for project-local discovery. No setup when you open this repo in a supported agent:

| Agent | Path in this repo |
|---|---|
| OpenCode | `.opencode/skills/pod-opencode/SKILL.md` |
| Claude Code | `.claude/skills/pod-opencode/SKILL.md` |
| Codex, Cursor, generic agents | `.agents/skills/pod-opencode/SKILL.md`, `.codex/skills/pod-opencode/SKILL.md` |
| Skill registries (`npx skills add`) | `skills/pod-opencode/SKILL.md` (canonical source) |

Use it from any other project with a global install:

```bash
./scripts/install-skill.sh
```

This copies the skill to `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/`, and `~/.codex/skills/`. Restart the agent and check that `pod-opencode` shows up, or invoke it explicitly with `@pod-opencode`.

Verify prerequisites through the skill:

```bash
python skills/pod-opencode/scripts/check-env.py
```

If `pod-opencode` is missing, the skill tells the agent to clone this repo and install it before continuing.

> Contributors: edit only `skills/pod-opencode/*`, then run `./scripts/sync-skills.sh` to refresh the project-local copies.

## Requirements

- Python 3.10 or later.
- A Java JRE, version 8 or later, on `PATH`. The first run can be slow while MPXJ initializes.

## Installation

```bash
pip install pod-opencode
```

Requires Java JRE 8+ on `PATH`. From source instead:

```bash
git clone https://github.com/Araryarch67/pod-opencode.git
cd pod-opencode
pip install -e ".[dev]"   # dev install, includes pytest
```

Check it works:

```bash
pod-opencode --help
```

## Quickstart

Inspect a project:

```bash
pod-opencode info project.pod
```

Rename it and save as a native `.pod` in one step:

```bash
pod-opencode convert --project-name "Sistem Perpustakaan" project.pod hasil.pod
```

Add a task with a start date and duration:

```bash
pod-opencode tasks add hasil.pod \
  --name "Perencanaan" \
  --start 2026-10-12 \
  --duration "5d" \
  --output hasil.pod
```

Chain further edits off the latest file. Each write produces a complete new snapshot, so overwriting the input is safe once you have a backup.

## Commands

```bash
pod-opencode info <file>
pod-opencode convert [--project-name TEXT] <input.pod|xml> <output.xml|output.pod>

pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--parent-id UID] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks update <file> <unique_id> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks delete <file> <unique_id> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks assign <file> <task_uid> <resource_uid> [--units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks unassign <file> <task_uid> <resource_uid> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks link <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--lag TEXT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks unlink <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks import <file> <batch.json> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode run <file> <script.json> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode diff <old_file> <new_file>
pod-opencode check <file>
pod-opencode tasks assign <file> <task_uid> <resource_uid> [--units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks unassign <file> <task_uid> <resource_uid> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks link <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--lag TEXT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks unlink <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--project-name TEXT] --output <file.xml|file.pod>

pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode resources update <file> <unique_id> [--name TEXT] [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode resources delete <file> <unique_id> [--project-name TEXT] --output <file.xml|file.pod>

pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

Notes:

- Options parse in any position on every command.
- Every write command accepts `--in-place` instead of `--output`: the input is copied to `<input>.bak`, then overwritten. The two flags cannot be combined.
- `assignments list` is read-only for viewing. Mutations live under `tasks`: `assign`, `unassign`, `link`, `unlink`, `import` (batch format below).
- A successful write prints `{"status": "ok", "output": "<path>", "affected_unique_id": N}`. Failures print `{"error": "...", "code": "..."}` on stderr, exactly one object per failure.

### Batch import

Create many tasks in one call. Parents reference existing tasks (UniqueID) or tasks created earlier in the same file (name). Resources reference existing resources by name:

```bash
pod-opencode tasks import project.pod batch.json --output project.pod
```

```json
{
  "project_name": "Optional default name",
  "tasks": [
    {"name": "Planning", "start": "2026-10-12", "duration": "5d"},
    {"name": "Charter", "duration": "2d", "parent": "Planning",
     "resources": ["Alice", {"name": "Bob", "units": 0.5}]},
    {"name": "M1 - Approved", "milestone": true, "parent": "Planning"}
  ]
}
```

The first invalid item aborts the import and nothing is written.

### Running scripts

For multi-step edits, prefer one `run` call over chained commands. Each
chained command pays a full JVM startup; `run` pays it once, validates
everything in memory, and writes a single time:

```bash
pod-opencode run project.pod plan.json --output project.pod
```

```json
{
  "project_name": "Optional default name",
  "operations": [
    {"op": "add", "name": "Planning", "duration": "5d", "ref": "plan"},
    {"op": "assign", "task": "plan", "resource": "Alice"},
    {"op": "link", "task": 2, "pred": 1, "type": "FS"},
    {"op": "rename", "project_name": "Final Name"}
  ]
}
```

Any op can address tasks and resources by UniqueID, `"ref"` label from
an earlier op, or unambiguous name (unknown names get a "did you mean?"
hint). Any failure aborts with `failed_operation` set and nothing is
written. Supported ops: `add`, `update`, `delete`, `assign`,
`unassign`, `link`, `unlink`, `resource_add`, `rename`.

### Comparing revisions

```bash
pod-opencode diff old.pod new.pod
```

Reports renames, added and removed items, per-field changes keyed by UniqueID, and a summary count block.

### Checking a file

```bash
pod-opencode check project.pod
```

Lints the file for logical problems: finish before start, dangling or
self links, broken hierarchy, out-of-range percents, missing dates,
unassigned tasks, duplicate names. Prints errors, warnings, and a summary,
and exits 1 when any error is found. Read-only. Run it after agent edits
and before opening the file in ProjectLibre.

## Project name and window title

ProjectLibre's title bar shows the project's internal name, not the file name. Opening `hasil.pod` shows whatever name is stored inside it, so renaming the file never fixes a wrong title. Set the stored name with `--project-name` on any write command:

```bash
pod-opencode convert --project-name "Sistem Perpustakaan" lama.pod baru.pod
```

The name persists in the output file, so later edits without `--project-name` keep it.

## The `.pod` format

A modern `.pod` file holds a Java serialization header, the separator `@@@@@@@@@@ProjectLibreSeparator_MSXML@@@@@@@@@@`, and an embedded MSPDI document. This tool writes exactly that layout: the schedule data lives in the embedded MSPDI part, which both MPXJ and ProjectLibre read. POD files written before ProjectLibre 1.5.5 contain no embedded schedule and cannot be read; the CLI reports those as unsupported instead of crashing.

## IDs, dates, durations

- **UniqueID** is stable across edits. Use it for `get`, `update`, and `delete`. The sequential **ID** can shift after inserts and deletes and is included for reference only.
- **Dates** use ISO 8601 on input (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`) and `YYYY-MM-DD` on output.
- **Durations** use MPXJ human format: `5d`, `40h`, `2w`.
- New child tasks (`--parent-id`) are inserted after the parent's subtree with the right outline level and WBS, so the hierarchy survives a write and re-read.

## Testing

```bash
pytest -v
```

The suite covers every command against an MSPDI fixture and a genuine ProjectLibre-written `.pod` (`tests/fixtures/real.pod`), including rename round-trips, `.pod` output, outline nesting, and error codes. It needs Python, Java, and the dev install above.

## Project layout

```
src/pod_opencode/
├── cli.py              # Root Typer app
├── jvm.py              # JPype JVM lifecycle management
├── reader.py           # MPXJ project reading
├── writer.py           # MSPDI XML and POD writing
├── models.py           # Pydantic JSON schemas
├── utils.py            # Date, duration, and ID conversion utilities
└── commands/
    ├── info.py         # Project metadata
    ├── convert.py      # Format conversion and renaming
    ├── tasks.py        # Task CRUD
    ├── resources.py    # Resource CRUD
    └── assignments.py  # Assignment viewing
skills/pod-opencode/    # Canonical agent skill source
scripts/
├── install-skill.sh    # Global skill install
└── sync-skills.sh      # Sync canonical skill to project-local copies
```

## Contributing

1. Edit only `skills/pod-opencode/*` for skill changes, then run `./scripts/sync-skills.sh`.
2. Keep `*.pod` scratch files out of git. Only `tests/fixtures/real.pod` is tracked, as a test fixture.
3. Add or update tests for behavior changes and run `pytest -q` before pushing.
4. Note user-facing changes in `CHANGELOG.md`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Current version: 0.2.0.

## Credits

- [pod-ai-cli](https://github.com/distractdiverge/pod-ai-cli) by distractdiverge. This project started from its design and CLI structure, then added native `.pod` output, `--project-name`, outline-aware task inserts, MPXJ 16 compatibility fixes, and the agent skill.
- [MPXJ](https://mpxj.org/) by Jon Iles, the Java library that reads and writes every format here.
- [ProjectLibre](https://www.projectlibre.com/), whose open `.pod` layout and source made native output possible.

## License

MIT. See [LICENSE](LICENSE).
