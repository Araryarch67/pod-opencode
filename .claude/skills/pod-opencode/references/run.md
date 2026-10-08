# Run script format (`pod-opencode run`)

```bash
pod-opencode run <file> <script.json> --output <out.xml|out.pod>
```

One JVM session, many operations, a single write at the end. Every
operation validates in memory first: any failure aborts the run with
`{"error": ..., "code": ..., "failed_operation": N}` and nothing is
written. Prefer this over chained single commands (each of which pays a
full JVM startup).

```json
{
  "project_name": "Optional default name",
  "operations": [
    {"op": "add", "name": "Planning", "start": "2026-10-12",
     "duration": "5d", "notes": "...", "milestone": false,
     "parent": "Phase 1", "resources": ["Alice"],
     "ref": "plan"},
    {"op": "update", "unique_id": 1, "name": "...",
     "percent_complete": 50},
    {"op": "delete", "unique_id": 3},
    {"op": "assign", "task": 1, "resource": 2, "units": 0.5},
    {"op": "unassign", "task": 1, "resource": 2},
    {"op": "link", "task": 2, "pred": 1, "type": "FS", "lag": "1d"},
    {"op": "unlink", "task": 2, "pred": 1},
    {"op": "resource_add", "name": "Charlie", "email": "...",
     "max_units": 1.0, "ref": "ch"},
    {"op": "rename", "project_name": "Final Name"}
  ]
}
```

Rules:

- `add` accepts the same fields as `tasks add`, plus `parent` (UniqueID
  or name, see `batch.md`) and `resources` (names or `{name, units}`).
- Any op that addresses a task or resource accepts a UniqueID, a
  `"ref"` label defined by an earlier op, or an unambiguous name.
  Unknown names get a "did you mean?" hint in the error.
- Name precedence: the file default applies first, `rename` ops override
  it, and flag-level `--project-name` wins over everything.
- The response lists one receipt per operation:
  `{"status": "ok", "output": "...", "results": [{"op": ..., ...}]}`.
