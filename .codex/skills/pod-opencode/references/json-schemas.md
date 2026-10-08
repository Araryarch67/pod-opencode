# JSON schemas

## info

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

## tasks list

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

`tasks get` returns the single task object (no `count` wrapper).

## resources list

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

`resources get` returns the single resource object.

## assignments list

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

## write success

```json
{ "status": "ok", "output": "/path/to/output.xml", "affected_unique_id": 1 }
```

## error (stderr)

```json
{ "error": "File not found: missing.pod", "code": "FILE_NOT_FOUND" }
```
