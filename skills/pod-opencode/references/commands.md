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

Converts POD/XML to MSPDI XML (`.xml`) or native ProjectLibre `.pod`. For `convert`, options must precede the file arguments. `--project-name` sets the project name shown as the window title in ProjectLibre.

## project name

Every write command (`convert`, `tasks add/update/delete`, `resources add/update/delete`) accepts `--project-name TEXT`. It sets the project's Name and Title, which is what ProjectLibre displays in its title bar (the file name alone does not change it). Set once; the name persists in the output file for chained edits.

## pod output

`--output` accepts `.xml` or `.pod`. A `.pod` file is the native ProjectLibre container (header + separator + embedded MSPDI); use it when the result must open as a pod file. Child tasks added with `--parent-id` are inserted after the parent's subtree with correct outline level and WBS.

## tasks

```bash
pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--parent-id UID] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks update <file> <unique_id> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode tasks delete <file> <unique_id> [--project-name TEXT] --output <file.xml|file.pod>
```

- `DATE`: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`.
- `DURATION`: `5d`, `40h`, `2w` (MPXJ human format).
- `update --percent-complete`: 0–100 float.
- `add` / `update` / `delete` return `{"status": "ok", "output": "<path>", "affected_unique_id": N}`.

## resources

```bash
pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode resources update <file> <unique_id> [--name TEXT] [--email TEXT] [--max-units FLOAT] [--project-name TEXT] --output <file.xml|file.pod>
pod-opencode resources delete <file> <unique_id> [--project-name TEXT] --output <file.xml|file.pod>
```

- `--max-units`: `1.0` = full time.

## assignments (read-only)

```bash
pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

Filter by task `unique_id` and/or resource `unique_id`. There is no add/update/delete for assignments in v0.1.0.
