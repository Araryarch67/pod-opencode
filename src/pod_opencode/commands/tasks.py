import typer
from pathlib import Path
import json
from typing import Optional

from pod_opencode.reader import read_project
from pod_opencode.writer import apply_project_name, write_output
from pod_opencode.models import TaskInfo, TaskListResponse, Predecessor, WriteSuccess
from pod_opencode.utils import (
    java_date_to_iso,
    duration_to_str,
    parse_date,
    parse_duration,
    to_java_datetime,
    jstr,
    jint,
    next_ids,
)

app = typer.Typer()


def _task_to_info(task, project) -> TaskInfo:
    """Convert a Java Task object to TaskInfo."""
    predecessors = []
    if task.getPredecessors():
        for pred in task.getPredecessors():
            predecessors.append(
                Predecessor(
                    task_unique_id=pred.getPredecessorTask().getUniqueID(),
                    relation_type=str(pred.getType()),
                    lag=duration_to_str(pred.getLag()),
                )
            )

    resource_names = []
    if task.getResourceAssignments():
        for assignment in task.getResourceAssignments():
            res = assignment.getResource()
            if res:
                resource_names.append(jstr(res.getName()))

    return TaskInfo(
        unique_id=task.getUniqueID(),
        id=task.getID(),
        name=jstr(task.getName()),
        wbs=jstr(task.getWBS()),
        outline_level=task.getOutlineLevel(),
        parent_id=task.getParentTask().getUniqueID() if task.getParentTask() else None,
        is_summary=task.getSummary(),
        milestone=task.getMilestone(),
        start=java_date_to_iso(task.getStart()),
        finish=java_date_to_iso(task.getFinish()),
        duration=duration_to_str(task.getDuration()),
        percent_complete=task.getPercentageComplete(),
        actual_start=java_date_to_iso(task.getActualStart()),
        actual_finish=java_date_to_iso(task.getActualFinish()),
        notes=jstr(task.getNotes()),
        predecessors=predecessors,
        resource_names=resource_names,
    )


@app.command()
def list(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    filter_name: Optional[str] = typer.Option(
        None, help="Filter tasks by name substring"
    ),
):
    """List all tasks in the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        tasks = project.getTasks()

        task_infos = []
        if tasks:
            for task in tasks:
                if (
                    filter_name
                    and filter_name.lower() not in (jstr(task.getName()) or "").lower()
                ):
                    continue
                task_infos.append(_task_to_info(task, project))

        response = TaskListResponse(tasks=task_infos, count=len(task_infos))
        output = response.model_dump_json(indent=2)
        typer.echo(output)
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


@app.command()
def get(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    unique_id: int = typer.Argument(..., help="Task UniqueID"),
):
    """Get a specific task by UniqueID."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        task = project.getTaskByUniqueID(jint(unique_id))

        if not task:
            error = {"error": f"Task not found: {unique_id}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        task_info = _task_to_info(task, project)
        output = task_info.model_dump_json(indent=2)
        typer.echo(output)
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


@app.command()
def add(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    name: str = typer.Option(..., help="Task name"),
    start: Optional[str] = typer.Option(None, help="Start date (ISO 8601)"),
    finish: Optional[str] = typer.Option(None, help="Finish date (ISO 8601)"),
    duration: Optional[str] = typer.Option(None, help="Duration (e.g., '5d', '40h')"),
    notes: Optional[str] = typer.Option(None, help="Task notes"),
    parent_id: Optional[int] = typer.Option(None, help="Parent task UniqueID"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: str = typer.Option(..., help="Output .xml file"),
):
    """Add a new task to the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))

        # NOTE: builtin list() is shadowed by the list command in this
        # module, so materialise the Java list with a comprehension.
        ordered = sorted(
            [t for t in project.getTasks()], key=lambda t: int(t.getID() or 0)
        )
        _, new_uid = next_ids(project.getTasks())
        parent_task = project.getTaskByUniqueID(jint(parent_id)) if parent_id else None

        new_task = project.addTask()
        new_task.setUniqueID(jint(new_uid))
        new_task.setName(name)
        if notes:
            new_task.setNotes(notes)

        if parent_task is not None:
            parent_level = (
                int(parent_task.getOutlineLevel())
                if parent_task.getOutlineLevel() is not None
                else 1
            )
            parent_task.addChildTask(new_task)
            new_task.setOutlineLevel(jint(parent_level + 1))
            # Insert right after the parent's subtree so the writer
            # (which sorts by ID) keeps outline order. Shift later IDs.
            idx = ordered.index(parent_task)
            end = idx + 1
            while (
                end < len(ordered)
                and int(ordered[end].getOutlineLevel() or 1) > parent_level
            ):
                end += 1
            for later in ordered[end:]:
                later.setID(jint(int(later.getID()) + 1))
            new_task.setID(jint(int(ordered[end - 1].getID()) + 1))
            parent_wbs = jstr(parent_task.getWBS()) if parent_task.getWBS() else None
            if parent_wbs:
                siblings = sum(
                    1
                    for t in project.getTasks()
                    if t.getParentTask() is not None
                    and t.getParentTask() == parent_task
                )
                new_task.setWBS(f"{parent_wbs}.{siblings}")
        else:
            new_task.setOutlineLevel(jint(1))
            top_wbs = []
            for t in ordered:
                if int(t.getOutlineLevel() or 1) == 1 and t.getWBS():
                    try:
                        top_wbs.append(int(str(t.getWBS())))
                    except ValueError:
                        pass
            new_task.setWBS(str(max(top_wbs or [0]) + 1))
            new_task.setID(jint(max([int(t.getID()) for t in ordered] or [0]) + 1))

        if start:
            start_dt = parse_date(start)
            if start_dt:
                new_task.setStart(to_java_datetime(start_dt))

        if finish:
            finish_dt = parse_date(finish)
            if finish_dt:
                new_task.setFinish(to_java_datetime(finish_dt))

        if duration:
            dur = parse_duration(duration)
            if dur is not None:
                new_task.setDuration(dur)

        apply_project_name(project, project_name)
        write_output(project, output)

        response = WriteSuccess(
            output=output, affected_unique_id=new_task.getUniqueID()
        )
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValueError as e:
        error = {"error": str(e), "code": "INVALID_OUTPUT_FORMAT"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        error = {"error": str(e), "code": "WRITE_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)


@app.command()
def update(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    unique_id: int = typer.Argument(..., help="Task UniqueID"),
    name: Optional[str] = typer.Option(None, help="New task name"),
    start: Optional[str] = typer.Option(None, help="New start date (ISO 8601)"),
    finish: Optional[str] = typer.Option(None, help="New finish date (ISO 8601)"),
    duration: Optional[str] = typer.Option(
        None, help="New duration (e.g., '5d', '40h')"
    ),
    notes: Optional[str] = typer.Option(None, help="New task notes"),
    percent_complete: Optional[float] = typer.Option(
        None, help="Percent complete (0-100)"
    ),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: str = typer.Option(..., help="Output .xml file"),
):
    """Update an existing task."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        task = project.getTaskByUniqueID(jint(unique_id))

        if not task:
            error = {"error": f"Task not found: {unique_id}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        if name:
            task.setName(name)
        if notes is not None:
            task.setNotes(notes)
        if start:
            start_dt = parse_date(start)
            if start_dt:
                task.setStart(to_java_datetime(start_dt))
        if finish:
            finish_dt = parse_date(finish)
            if finish_dt:
                task.setFinish(to_java_datetime(finish_dt))
        if duration:
            dur = parse_duration(duration)
            if dur is not None:
                task.setDuration(dur)
        if percent_complete is not None:
            task.setPercentageComplete(percent_complete)

        apply_project_name(project, project_name)
        write_output(project, output)

        response = WriteSuccess(output=output, affected_unique_id=unique_id)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValueError as e:
        error = {"error": str(e), "code": "INVALID_OUTPUT_FORMAT"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        error = {"error": str(e), "code": "WRITE_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)


@app.command()
def delete(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    unique_id: int = typer.Argument(..., help="Task UniqueID"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: str = typer.Option(..., help="Output .xml file"),
):
    """Delete a task from the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        task = project.getTaskByUniqueID(jint(unique_id))

        if not task:
            error = {"error": f"Task not found: {unique_id}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        project.removeTask(task)
        apply_project_name(project, project_name)
        write_output(project, output)

        response = WriteSuccess(output=output, affected_unique_id=unique_id)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValueError as e:
        error = {"error": str(e), "code": "INVALID_OUTPUT_FORMAT"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        error = {"error": str(e), "code": "WRITE_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
