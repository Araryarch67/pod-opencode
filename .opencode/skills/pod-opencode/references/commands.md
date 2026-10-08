# Commands reference

All commands emit one JSON object on stdout. Errors emit `{"error": "...", "code": "..."}` on stderr with non-zero exit.

## info

```bash
pod-opencode info <file>
```

`file`: `.pod` or `.xml`. Returns `{name, project_id, start_date, finish_date, author, company, task_count, resource_count}`.

## convert

```bash
pod-opencode convert <input_file> <output.xml>
```

Converts POD/XML to MSPDI XML. `output` must end in `.xml`.

## tasks

```bash
pod-opencode tasks list <file> [--filter-name TEXT]
pod-opencode tasks get <file> <unique_id>
pod-opencode tasks add <file> --name TEXT [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] --output <file.xml>
pod-opencode tasks update <file> <unique_id> [--name TEXT] [--start DATE] [--finish DATE] [--duration TEXT] [--notes TEXT] [--percent-complete FLOAT] --output <file.xml>
pod-opencode tasks delete <file> <unique_id> --output <file.xml>
```

- `DATE`: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`.
- `DURATION`: `5d`, `40h`, `2w` (MPXJ human format).
- `update --percent-complete`: 0–100 float.
- `add` / `update` / `delete` return `{"status": "ok", "output": "<path>", "affected_unique_id": N}`.

## resources

```bash
pod-opencode resources list <file>
pod-opencode resources get <file> <unique_id>
pod-opencode resources add <file> --name TEXT [--email TEXT] [--max-units FLOAT] --output <file.xml>
pod-opencode resources update <file> <unique_id> [--name TEXT] [--email TEXT] [--max-units FLOAT] --output <file.xml>
pod-opencode resources delete <file> <unique_id> --output <file.xml>
```

- `--max-units`: `1.0` = full time.

## assignments (read-only)

```bash
pod-opencode assignments list <file> [--task-id INT] [--resource-id INT]
```

Filter by task `unique_id` and/or resource `unique_id`. There is no add/update/delete for assignments in v0.1.0.
