# pod-opencode

A Python CLI tool for reading and modifying ProjectLibre `.pod` files via MPXJ. Designed to enable AI assistants (like Claude) to interact with project schedule data programmatically.

## Overview

`pod-opencode` bridges ProjectLibre and AI tools by providing structured JSON access to project data (tasks, resources, assignments) and the ability to add, edit, or remove items. All output is valid JSON, making it ideal for AI consumption.

**Key Technical Facts:**
- Uses [MPXJ](https://mpxj.org/) (Java library) with Python bindings
- Reads ProjectLibre `.pod` files and MSPDI XML files
- **Cannot write POD format directly** — output is MSPDI XML (which ProjectLibre opens natively)
- Requires a Java JRE on your system
- Cross-platform (macOS, Linux, Windows)
- Ships as an **AI agent skill** (`pod-opencode`) for OpenCode, Claude Code, Codex, Cursor, and other agents

## AI Agent Skill

No extra setup when you open this repo in a supported agent — the skill is pre-installed project-locally:

| Agent | Discovery path in this repo |
|---|---|
| OpenCode | `.opencode/skills/pod-opencode/SKILL.md` |
| Claude Code | `.claude/skills/pod-opencode/SKILL.md` |
| Codex / Cursor / generic | `.agents/skills/pod-opencode/SKILL.md`, `.codex/skills/pod-opencode/SKILL.md` |
| Skill-registry tools (`npx skills add`) | `skills/pod-opencode/SKILL.md` (canonical source) |

Use it in another project (global install):

```bash
./scripts/install-skill.sh
```

This copies the canonical skill to `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/`, and `~/.codex/skills/`. Restart the agent and verify `pod-opencode` appears in `/skills` (or invoke explicitly: `@pod-opencode`).

Check prerequisites from the skill:

```bash
python skills/pod-opencode/scripts/check-env.py
```

> Contributors: edit only `skills/pod-opencode/*`, then run `./scripts/sync-skills.sh` to refresh the project-local copies.

## Installation

### Prerequisites
- Python 3.10+
- Java JRE (any version 8 or later)

### Setup
```bash
git clone <repo-url>
cd pod-opencode-cli

pip install -e ".[dev]"  # includes dev dependencies for testing
```

Or minimal install:
```bash
pip install -e .
```

## Quick Start

### Read Project Metadata
```bash
pod-opencode info project.pod
```
Output (JSON):
```json
{
  "name": "My Project",
  "project_id": "P001",
  "start_date": "2025-01-01",
  "finish_date": "2025-12-31",
  "author": "Alice",
  "company": "Acme Corp",
  "task_count": 42,
  "resource_count": 7
}
```

### List All Tasks
```bash
pod-opencode tasks list project.pod
```
Output (JSON array of tasks with UniqueID, name, dates, duration, resource assignments, etc.)

### Get a Specific Task
```bash
pod-opencode tasks get project.pod 1
```

### Add a Task
```bash
pod-opencode tasks add project.pod \
  --name "New Task" \
  --start 2025-07-01 \
  --duration "5d" \
  --output output.xml
```

### Update a Task
```bash
pod-opencode tasks update project.pod 1 \
  --name "Renamed Task" \
  --percent-complete 50 \
  --output output.xml
```

### Delete a Task
```bash
pod-opencode tasks delete project.pod 1 --output output.xml
```

### Manage Resources
```bash
pod-opencode resources list project.pod
pod-opencode resources get project.pod 1
pod-opencode resources add project.pod --name "Charlie" --max-units 1.0 --output output.xml
pod-opencode resources update project.pod 1 --email "charlie@example.com" --output output.xml
pod-opencode resources delete project.pod 1 --output output.xml
```

### View Resource Assignments
```bash
pod-opencode assignments list project.pod
pod-opencode assignments list project.pod --task-id 1        # Filter by task
pod-opencode assignments list project.pod --resource-id 2    # Filter by resource
```

### Convert Between Formats
```bash
pod-opencode convert project.pod project.xml
```

## Commands Reference

### `info`
Display project-level metadata (title, author, dates, counts).
```bash
pod-opencode info <file>
```

### `convert`
Convert a POD/XML file to MSPDI XML format.
```bash
pod-opencode convert <input_file> <output.xml>
```

### `tasks`
Manage project tasks.
```bash
pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] --output <file.xml>
pod-opencode tasks update <file> <unique_id> [--name] [--start] [--finish] [--duration] [--notes] [--percent-complete FLOAT] --output <file.xml>
pod-opencode tasks delete <file> <unique_id> --output <file.xml>
```

### `resources`
Manage project resources.
```bash
pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] --output <file.xml>
pod-opencode resources update <file> <unique_id> [--name] [--email] [--max-units] --output <file.xml>
pod-opencode resources delete <file> <unique_id> --output <file.xml>
```

### `assignments`
View resource-to-task assignments (read-only).
```bash
pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

## JSON Output Format

All read commands output a single JSON object to stdout. Errors go to stderr.

### Tasks List
```json
{
  "tasks": [
    {
      "unique_id": 1,
      "id": 1,
      "name": "Planning",
      "wbs": "1",
      "outline_level": 1,
      "parent_id": null,
      "is_summary": false,
      "milestone": false,
      "start": "2025-01-01",
      "finish": "2025-01-06",
      "duration": "5d",
      "percent_complete": 0.0,
      "actual_start": "2025-01-01",
      "actual_finish": "2025-01-06",
      "notes": null,
      "predecessors": [],
      "resource_names": ["Alice"]
    }
  ],
  "count": 1
}
```

### Resources List
```json
{
  "resources": [
    {
      "unique_id": 1,
      "id": 1,
      "name": "Alice",
      "resource_type": "Work",
      "email": "alice@acme.com",
      "max_units": 1.0,
      "notes": null
    }
  ],
  "count": 1
}
```

### Assignments List
```json
{
  "assignments": [
    {
      "unique_id": 1,
      "task_unique_id": 1,
      "task_name": "Planning",
      "resource_unique_id": 1,
      "resource_name": "Alice",
      "units": 1.0,
      "work": "40h",
      "actual_work": "40h",
      "start": "2025-01-01",
      "finish": "2025-01-06"
    }
  ],
  "count": 1
}
```

### Write Success
```json
{
  "status": "ok",
  "output": "/path/to/output.xml",
  "affected_unique_id": 1
}
```

### Error Response (stderr)
```json
{
  "error": "File not found: missing.pod",
  "code": "FILE_NOT_FOUND"
}
```

## Important Notes

### POD to XML Round-Trip

MPXJ **cannot write POD format directly**. When you modify a project, the output is always **MSPDI XML** (`.xml`). This is not a limitation:

1. **ProjectLibre opens MSPDI XML natively** — File > Open works with `.xml` files
2. **Full data preservation** — MSPDI is a complete format that preserves all task, resource, and assignment data
3. **Workflow**: Read `.pod` → Modify → Write `.xml` → Open in ProjectLibre → (optional) Save as `.pod` if needed

All write commands require `--output <file.xml>` and will reject `.pod` extensions with a clear error message.

### Entity IDs

MPXJ uses two ID systems:
- **UniqueID** — Stable, never changes even after edits. Used for `get`, `update`, `delete` operations.
- **ID** — Sequential, can change after insert/delete. Included in output for reference only.

Always use **UniqueID** when referencing tasks or resources in commands.

### Date Format

- **Input**: ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`)
- **Output**: ISO 8601 date format (`YYYY-MM-DD`)
- **Examples**: `--start 2025-07-01`, `--finish 2025-12-31`

### Duration Format

- **Input/Output**: Human-readable format used by MPXJ
- **Examples**: `5d`, `40h`, `2w`

## Testing

Run the test suite:
```bash
pytest -v
```

This will:
- Validate JSON output schemas
- Test all CLI commands with a sample project
- Verify error handling (file not found, invalid IDs, etc.)

## Architecture

```
src/pod_opencode/
├── jvm.py              # JPype JVM lifecycle management
├── reader.py           # MPXJ project reading
├── writer.py           # MSPDI XML writing
├── models.py           # Pydantic JSON schemas
├── utils.py            # Date/duration conversion utilities
├── cli.py              # Root Typer app
└── commands/
    ├── info.py         # Project metadata
    ├── convert.py      # Format conversion
    ├── tasks.py        # Task CRUD
    ├── resources.py    # Resource CRUD
    └── assignments.py  # Assignment viewing
```

## Development

Install dev dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest -v
```

Run the CLI in development:
```bash
python -m pod_opencode --help
```

## Limitations

- **Java Dependency**: Requires a JRE on the system (no bundled Java)
- **POD Write**: MPXJ does not support writing POD format. Output is always MSPDI XML, which ProjectLibre opens natively
- **First Build Slow**: The first build of the MPXJ package translates Java to .NET via IKVM and may take extra time
- **JVM Lifecycle**: The JVM starts once per CLI invocation and cannot be restarted (JPype constraint)

## References

- [MPXJ Documentation](https://mpxj.org/)
- [MPXJ Python Bindings](https://mpxj.org/python/)
- [ProjectLibre](https://www.projectlibre.com/)
- [MSPDI Format](https://en.wikipedia.org/wiki/Microsoft_Project#XML_format)
