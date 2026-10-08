import typer
from pathlib import Path
import json

from pod_opencode.reader import read_project
from pod_opencode.commands.tasks import _task_to_info
from pod_opencode.commands.resources import _resource_to_info
from pod_opencode.utils import jstr

app = typer.Typer()

TASK_FIELDS = (
    "name",
    "start",
    "finish",
    "duration",
    "percent_complete",
    "outline_level",
    "parent_id",
    "milestone",
    "resource_names",
)

RESOURCE_FIELDS = ("name", "email", "max_units", "notes")


def _changes(old, new, fields):
    """Return {field: {from, to}} for differing fields."""
    diff = {}
    for field in fields:
        old_value = getattr(old, field)
        new_value = getattr(new, field)
        if old_value != new_value:
            diff[field] = {"from": old_value, "to": new_value}
    return diff


@app.callback(invoke_without_command=True)
def diff(
    old_file: str = typer.Argument(..., help="Original .pod or .xml file"),
    new_file: str = typer.Argument(..., help="Revised .pod or .xml file"),
):
    """Compare two project files and report added, removed, and changed items."""
    for label, path in (("old", old_file), ("new", new_file)):
        if not Path(path).exists():
            error = {"error": f"File not found: {path}", "code": "FILE_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

    try:
        old_project = read_project(old_file)
        new_project = read_project(new_file)

        old_name = jstr(old_project.getProjectProperties().getProjectTitle())
        new_name = jstr(new_project.getProjectProperties().getProjectTitle())

        old_tasks = {t.unique_id: t for t in _read_tasks(old_project)}
        new_tasks = {t.unique_id: t for t in _read_tasks(new_project)}
        old_resources = {r.unique_id: r for r in _read_resources(old_project)}
        new_resources = {r.unique_id: r for r in _read_resources(new_project)}

        tasks_changed = []
        for uid in sorted(set(old_tasks) & set(new_tasks)):
            changed = _changes(old_tasks[uid], new_tasks[uid], TASK_FIELDS)
            if changed:
                tasks_changed.append({"unique_id": uid, "changes": changed})

        resources_changed = []
        for uid in sorted(set(old_resources) & set(new_resources)):
            changed = _changes(old_resources[uid], new_resources[uid], RESOURCE_FIELDS)
            if changed:
                resources_changed.append({"unique_id": uid, "changes": changed})

        added_tasks = [
            t for uid, t in sorted(new_tasks.items()) if uid not in old_tasks
        ]
        removed_tasks = [
            t for uid, t in sorted(old_tasks.items()) if uid not in new_tasks
        ]
        added_resources = [
            r for uid, r in sorted(new_resources.items()) if uid not in old_resources
        ]
        removed_resources = [
            r for uid, r in sorted(old_resources.items()) if uid not in new_resources
        ]

        result = {
            "project_name": {"from": old_name, "to": new_name}
            if old_name != new_name
            else None,
            "tasks_added": [t.model_dump() for t in added_tasks],
            "tasks_removed": [t.model_dump() for t in removed_tasks],
            "tasks_changed": tasks_changed,
            "resources_added": [r.model_dump() for r in added_resources],
            "resources_removed": [r.model_dump() for r in removed_resources],
            "resources_changed": resources_changed,
            "summary": {
                "tasks_added": len(added_tasks),
                "tasks_removed": len(removed_tasks),
                "tasks_changed": len(tasks_changed),
                "resources_added": len(added_resources),
                "resources_removed": len(removed_resources),
                "resources_changed": len(resources_changed),
            },
        }
        typer.echo(json.dumps(result, indent=2))
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        error = {"error": str(e), "code": "READ_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)


def _read_tasks(project):
    tasks = project.getTasks()
    return [_task_to_info(t, project) for t in tasks] if tasks else []


def _read_resources(project):
    resources = project.getResources()
    return [_resource_to_info(r) for r in resources] if resources else []
