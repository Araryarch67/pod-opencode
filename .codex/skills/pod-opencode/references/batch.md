# Batch import format (`tasks import`)

```bash
pod-opencode tasks import <file> <batch.json> --output <out.xml|out.pod>
```

`--project-name` (flag) wins over the file's `"project-name"` field.
`--in-place` works like other write commands.

```json
{
  "project_name": "Optional default name",
  "tasks": [
    {
      "name": "Planning",
      "start": "2026-10-12",
      "finish": "2026-10-17",
      "duration": "5d",
      "notes": "Kickoff scope",
      "milestone": false,
      "percent_complete": 0,
      "parent": "Phase 1",
      "resources": ["Alice", {"name": "Bob", "units": 0.5}]
    }
  ]
}
```

Rules:

- Items are created in file order. `parent` accepts a UniqueID (existing
  task) or a name (a task created earlier in the same batch, else an
  existing task; ambiguous names are rejected).
- `resources` entries are names (full units) or `{name, units}` objects.
  Names must match exactly one existing resource.
- Dates, durations, and percent go through the same validation as
  `tasks add`. The first problem aborts the whole import and nothing is
  written.
