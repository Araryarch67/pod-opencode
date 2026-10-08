# Commands reference

All commands emit one JSON object on stdout. Errors emit `{"error": "...", "code": "..."}` on stderr with non-zero exit.

## info

```bash
pod-opencode info <file>
```

`file`: `.pod` or `.xml`. Returns `{name, project_id, start_date, finish_date, author, company, task_count, resource_count}`.

## convert

```bash
pod-opencode convert [--project-name TEXT] <input_file> <output.xml|output.pod>
```

Converts POD/XML to MSPDI XML (`.xml`) or native ProjectLibre `.pod`. `--project-name` sets the project name shown as the window title in ProjectLibre.

## project name

Every write command (`convert`, `tasks add/update/delete/import/assign/unassign/link/unlink`, `resources add/update/delete`) accepts `--project-name TEXT` and `--in-place`. The name sets the project's Name and Title, which is what ProjectLibre displays in its title bar (the file name alone does not change it). Set once; the name persists in the output file for chained edits.

## pod output

`--output` accepts `.xml` or `.pod`. Pass `--in-place` instead of `--output` to overwrite the input (a `.bak` backup is written first); the two flags cannot be combined. A `.pod` file is the native ProjectLibre container (header + separator + embedded MSPDI); use it when the result must open as a pod file. Child tasks added with `--parent-id` are inserted after the parent's subtree with correct outline level and WBS.

## tasks

```bash
pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--parent-id UID] [--milestone] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks update <file> <unique_id> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete FLOAT] [--milestone|--no-milestone] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks import <file> <batch.json> [--project-name TEXT] --output <file.xml|file.pod> (batch format: batch.md)
pod-opencode tasks delete <file> <unique_id> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks assign <file> <task_uid> <resource_uid> [--units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks unassign <file> <task_uid> <resource_uid> [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks link <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--lag TEXT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks unlink <file> <task_uid> <pred_uid> [--type FS|SS|FF|SF] [--project-name TEXT] --output <file.xml|file.pod>
```

- `DATE`: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`.
- `DURATION`: `5d`, `40h`, `2w` (MPXJ human format).
- `update --percent-complete`: 0-100 float, rejected otherwise.
- Dates are cross-checked: the effective finish (new or stored) must not
  precede the effective start. Move both together or the update is
  rejected; nothing is written.
- `link` rejects self-links and duplicates. Deleting a task also removes
  predecessor links pointing at it and its subtree.
- `add` / `update` / `delete` return `{"status": "ok", "output": "<path>", "affected_unique_id": N}`.

## resources

```bash
pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode resources update <file> <unique_id> [--name TEXT] [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode resources delete <file> <unique_id> [--project-name TEXT] --output <file.xml|file.pod>
```

- `--max-units`: `1.0` = full time. Units are fractions everywhere
  (`1.0` means 100%), matching what MSPDI stores.

## assignments (list is read-only)

```bash
pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

Mutations live under `tasks`: `assign`, `unassign`, `link`, `unlink`.

## run

```bash
pod-opencode run <file> <script.json> [--project-name TEXT] --output <file.xml|file.pod>
```

Many operations in one JVM session with per-op receipts, validated
upfront and written once at the end. Script format: run.md. Name
precedence: file default, then `rename` ops, then the flag.

## diff

```bash
pod-opencode diff <old_file> <new_file>
```

Reports project rename, added/removed tasks and resources, and per-item
field changes, plus a summary count block.

## check

```bash
pod-opencode check <file>
```

Lints the file and prints `{"errors": [...], "warnings": [...], "summary": {...}}`.
Exits 1 when any error is found, 0 otherwise. Read-only. Run it after a
batch of edits and before opening the file in ProjectLibre.
