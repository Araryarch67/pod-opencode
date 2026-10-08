<div align="center">
  <h1>pod-opencode</h1>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+"></a>
  <a href="https://pypi.org/project/pod-opencode/"><img src="https://img.shields.io/pypi/v/pod-opencode.svg" alt="PyPI version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
  <p>A Python CLI for reading and writing ProjectLibre <code>.pod</code> files via MPXJ, built so AI assistants can work with project schedules through shell commands.</p>
</div>

Reads print one JSON object, writes return one JSON receipt.

Based on [pod-ai-cli](https://github.com/distractdiverge/pod-ai-cli) by distractdiverge. See [Credits](#credits).

## Contents

- [Features](#features)
- [AI agent skill](#ai-agent-skill)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Commands](#commands)
- [Batch import](#batch-import)
- [Running scripts](#running-scripts)
- [Comparing and checking](#comparing-and-checking)
- [Project name and window title](#project-name-and-window-title)
- [Formats and conventions](#formats-and-conventions)
- [Testing](#testing)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Credits](#credits)
- [License](#license)

## Features

- Read and write `.pod` and MSPDI `.xml`, or edit in place with `--in-place` (automatic `.bak` backup).
- Full task and resource CRUD by stable UniqueID, plus assignments, predecessor links, milestones, and batch import.
- `diff` revisions, `check` files for logical errors, and `run` multi-step scripts in one JVM session.
- Set the stored project name, so ProjectLibre opens the file with the right title.
- JSON everywhere: reads on stdout, receipts for writes, single error objects on stderr with stable codes.

## AI agent skill

This repo ships a `pod-opencode` skill, pre-installed for project-local discovery:

| Agent | Path in this repo |
|---|---|
| OpenCode | `.opencode/skills/pod-opencode/SKILL.md` |
| Claude Code | `.claude/skills/pod-opencode/SKILL.md` |
| Codex, Cursor, generic agents | `.agents/skills/pod-opencode/SKILL.md`, `.codex/skills/pod-opencode/SKILL.md` |
| Skill registries (`npx skills add`) | `skills/pod-opencode/SKILL.md` (canonical source) |

For other projects, one command installs the CLI and applies the skill to every detected agent:

```bash
curl -sSL https://raw.githubusercontent.com/Araryarch67/pod-opencode/main/scripts/bootstrap.sh | bash -s --
```

From a checkout, `./scripts/bootstrap.sh` does the same (`./scripts/install-skill.sh` installs only the skill). Restart the agent and check that `pod-opencode` shows up, or invoke it explicitly with `@pod-opencode`. If the CLI is missing, the skill tells the agent to `pip install pod-opencode`.

## Installation

```bash
pip install pod-opencode
```

Needs Python 3.10+ and a Java JRE 8+ on `PATH` (first run is slow while MPXJ initializes). From source:

```bash
git clone https://github.com/Araryarch67/pod-opencode.git
cd pod-opencode
pip install -e ".[dev]"
```

## Quickstart

```bash
pod-opencode info project.pod
pod-opencode convert --project-name "Sistem Perpustakaan" project.pod hasil.pod
pod-opencode tasks add hasil.pod --name "Perencanaan" \
  --start 2026-10-12 --duration "5d" --output hasil.pod
```

Each write produces a complete new snapshot, so chain edits off the latest file.

## Commands

Every write command takes `--output <file.xml|file.pod>` or `--in-place` (never both), plus optional `--project-name`:

```bash
pod-opencode info <file>
pod-opencode convert <input> [output]
pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <uid>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--parent-id UID] [--milestone]
pod-opencode tasks update <file> <uid> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete 0-100] [--milestone|--no-milestone]
pod-opencode tasks delete <file> <uid>
pod-opencode tasks assign <file> <task_uid> <resource_uid> [--units 1.0]
pod-opencode tasks unassign <file> <task_uid> <resource_uid>
pod-opencode tasks link <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--lag TEXT]
pod-opencode tasks unlink <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF]
pod-opencode tasks import <file> <batch.json>
pod-opencode run <file> <script.json>
pod-opencode diff <old> <new>
pod-opencode check <file>
pod-opencode resources list|get|add|update|delete <file> [args]
pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

`assignments list` only views; mutations live under `tasks`. A successful write prints `{"status": "ok", ...}`; failures print one `{"error": ..., "code": ...}` object on stderr.

## Batch import

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

Parents take a UniqueID or a name (earlier batch items first, then existing tasks). The first invalid item aborts with nothing written.

## Running scripts

One `run` call beats chained commands: a single JVM startup, everything validated in memory, one write at the end, per-operation receipts:

```bash
pod-opencode run project.pod plan.json --output project.pod
```

```json
{
  "operations": [
    {"op": "add", "name": "Planning", "duration": "5d", "ref": "plan"},
    {"op": "assign", "task": "plan", "resource": "Alice"},
    {"op": "link", "task": 2, "pred": 1, "type": "FS"},
    {"op": "rename", "project_name": "Final Name"}
  ]
}
```

Ops address tasks and resources by UniqueID, `"ref"` label, or unambiguous name (typos get a "did you mean?" hint). Supported ops: `add`, `update`, `delete`, `assign`, `unassign`, `link`, `unlink`, `resource_add`, `rename`. Any failure aborts with `failed_operation` set and nothing written.

## Comparing and checking

```bash
pod-opencode diff old.pod new.pod
pod-opencode check project.pod
```

`diff` reports renames, added/removed items, per-field changes by UniqueID, and summary counts. `check` lints for finish-before-start, dangling/self/circular links, broken hierarchy, out-of-range percents, missing dates, unassigned tasks, and duplicate names. It exits 1 on any error, so run it after agent edits and before opening the file in ProjectLibre.

## Project name and window title

ProjectLibre's title bar shows the stored project name, not the file name, so renaming the file never fixes a wrong title:

```bash
pod-opencode convert --project-name "Sistem Perpustakaan" lama.pod baru.pod
```

The name persists in the output file, so later edits keep it without repeating the flag.

## Formats and conventions

- `.pod` files hold a Java serialization header, a separator, and an embedded MSPDI document. This tool writes that exact layout; both MPXJ and ProjectLibre read it. POD files predating ProjectLibre 1.5.5 have no embedded schedule and are reported as unsupported.
- **UniqueID** is stable, use it for `get`/`update`/`delete`. **ID** is positional and may shift.
- Dates are ISO 8601 (`YYYY-MM-DD`), durations look like `5d`, `40h`, `2w`, units are fractions (`1.0` is full time).
- New child tasks land after the parent's subtree with correct outline level and WBS.

## Testing

```bash
pytest -q
```

92 unit tests plus seeded fuzz across XML and POD, run against an MSPDI fixture and a genuine ProjectLibre-written `.pod`. Needs the dev install above. `scripts/sweep.sh` replays every command end to end for manual verification.

## Contributing

1. Skill changes go in `skills/pod-opencode/*`, then `./scripts/sync-skills.sh`.
2. Keep `*.pod` scratch files (and `.bak`) out of git; only `tests/fixtures/real.pod` is tracked.
3. Add or update tests for behavior changes and run `pytest -q` before pushing.
4. Note user-facing changes in `CHANGELOG.md`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Current version: 0.2.0.

## Credits

- [pod-ai-cli](https://github.com/distractdiverge/pod-ai-cli) by distractdiverge, the project this started from.
- [MPXJ](https://mpxj.org/) by Jon Iles, the Java library behind every format here.
- [ProjectLibre](https://www.projectlibre.com/), whose open `.pod` layout made native output possible.

## License

MIT. See [LICENSE](LICENSE).
