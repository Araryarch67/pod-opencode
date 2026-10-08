import typer
from pathlib import Path
import json
from typing import Optional

from pod_opencode.reader import read_project
from pod_opencode.writer import apply_project_name, write_output, resolve_output_path
from pod_opencode.models import (
    TaskInfo,
    TaskListResponse,
    Predecessor,
    WriteSuccess,
    ImportSuccess,
)
from pod_opencode.utils import (
    java_date_to_iso,
    duration_to_str,
    parse_duration,
    to_java_datetime,
    validate_task_inputs,
    check_effective_order,
    units_to_java,
    ValidationError,
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


@app.command("list")
def list_tasks(
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


def _insert_task(
    project,
    name,
    notes=None,
    start_dt=None,
    finish_dt=None,
    duration=None,
    milestone=False,
    percent_complete=None,
    parent_task=None,
):
    """Create a task with valid IDs, outline level, and WBS.

    When parent_task is given, the task is inserted right after the
    parent's subtree so the ID-sorted writer keeps outline order.
    Returns the new Java Task object.
    """
    # NOTE: builtin list() is shadowed by the list command in this
    # module, so materialise the Java list with a comprehension.
    ordered = sorted([t for t in project.getTasks()], key=lambda t: int(t.getID() or 0))
    _, new_uid = next_ids(project.getTasks())

    new_task = project.addTask()
    new_task.setUniqueID(jint(new_uid))
    new_task.setName(name)
    if notes:
        new_task.setNotes(notes)
    if milestone:
        new_task.setMilestone(True)

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
                if t.getParentTask() is not None and t.getParentTask() == parent_task
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

    if start_dt:
        new_task.setStart(to_java_datetime(start_dt))
    if finish_dt:
        new_task.setFinish(to_java_datetime(finish_dt))
    if duration is not None:
        new_task.setDuration(duration)
    if percent_complete is not None:
        new_task.setPercentageComplete(percent_complete)
    return new_task


@app.command()
def add(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    name: str = typer.Option(..., help="Task name"),
    start: Optional[str] = typer.Option(None, help="Start date (ISO 8601)"),
    finish: Optional[str] = typer.Option(None, help="Finish date (ISO 8601)"),
    duration: Optional[str] = typer.Option(None, help="Duration (e.g., '5d', '40h')"),
    notes: Optional[str] = typer.Option(None, help="Task notes"),
    parent_id: Optional[int] = typer.Option(None, help="Parent task UniqueID"),
    milestone: bool = typer.Option(False, help="Mark task as milestone"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Add a new task to the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))

        parent_task = project.getTaskByUniqueID(jint(parent_id)) if parent_id else None
        if parent_id and parent_task is None:
            error = {
                "error": f"Parent task not found: {parent_id}",
                "code": "TASK_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        start_dt, finish_dt, dur = validate_task_inputs(start, finish, duration)
        new_task = _insert_task(
            project,
            name,
            notes=notes,
            start_dt=start_dt,
            finish_dt=finish_dt,
            duration=dur,
            milestone=milestone,
            parent_task=parent_task,
        )

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(
            output=output_path, affected_unique_id=new_task.getUniqueID()
        )
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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
    milestone: Optional[bool] = typer.Option(
        None, help="Mark/unmark task as milestone"
    ),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
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
        if start or finish or duration or percent_complete is not None:
            start_dt, finish_dt, dur = validate_task_inputs(
                start, finish, duration, percent_complete
            )
            check_effective_order(
                task.getStart(), task.getFinish(), start_dt, finish_dt
            )
            if start_dt:
                task.setStart(to_java_datetime(start_dt))
            if finish_dt:
                task.setFinish(to_java_datetime(finish_dt))
            if dur is not None:
                task.setDuration(dur)
            if percent_complete is not None:
                task.setPercentageComplete(percent_complete)
        if milestone is not None:
            task.setMilestone(milestone)

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path, affected_unique_id=unique_id)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
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

        before = {
            int(t.getUniqueID())
            for t in project.getTasks()
            if t.getUniqueID() is not None
        }
        project.removeTask(task)
        _sweep_deleted_links(project, before)
        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path, affected_unique_id=unique_id)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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


RELATION_TYPES = {
    "FS": "FINISH_START",
    "SS": "START_START",
    "FF": "FINISH_FINISH",
    "SF": "START_FINISH",
}


def _create_assignment(project, task, resource, units):
    """Assign resource to task (units as fraction, 1.0 = full). Returns new UID."""
    assignment = task.addResourceAssignment(resource)
    assignment.setUnits(units_to_java(units))
    uids = [
        int(a.getUniqueID())
        for a in project.getResourceAssignments()
        if a.getUniqueID() is not None
    ]
    new_uid = max(uids or [0]) + 1
    assignment.setUniqueID(jint(new_uid))
    return new_uid


def _sweep_deleted_links(project, before_uids):
    """Remove predecessor links pointing at tasks that no longer exist.

    removeTask does not clean links from surviving tasks, which would
    linger as dangling PredecessorLinks in the file.
    """
    gone = before_uids - {
        int(t.getUniqueID()) for t in project.getTasks() if t.getUniqueID() is not None
    }
    for other in project.getTasks():
        for rel in [r for r in other.getPredecessors()]:
            pred = rel.getPredecessorTask()
            if (
                pred is not None
                and pred.getUniqueID() is not None
                and int(pred.getUniqueID()) in gone
            ):
                other.removePredecessor(pred, rel.getType(), rel.getLag())


def _matching_assignments(project, task_uid, resource_uid):
    """Return assignments linking the given task and resource UniqueIDs."""
    found = []
    for assignment in project.getResourceAssignments():
        task = assignment.getTask()
        resource = assignment.getResource()
        if (
            task is not None
            and resource is not None
            and int(task.getUniqueID()) == task_uid
            and int(resource.getUniqueID()) == resource_uid
        ):
            found.append(assignment)
    return found


@app.command()
def assign(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    task_uid: int = typer.Argument(..., help="Task UniqueID"),
    resource_uid: int = typer.Argument(..., help="Resource UniqueID"),
    units: float = typer.Option(1.0, help="Units (1.0 = 100%)"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Assign a resource to a task."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        if units <= 0:
            raise ValidationError("units must be greater than 0")

        project = read_project(str(file_path))
        task = project.getTaskByUniqueID(jint(task_uid))
        if not task:
            error = {"error": f"Task not found: {task_uid}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)
        resource = project.getResourceByUniqueID(jint(resource_uid))
        if not resource:
            error = {
                "error": f"Resource not found: {resource_uid}",
                "code": "RESOURCE_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        if _matching_assignments(project, task_uid, resource_uid):
            raise ValidationError(
                f"Resource {resource_uid} is already assigned to task {task_uid}"
            )

        new_uid = _create_assignment(project, task, resource, units)

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path, affected_unique_id=new_uid)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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
def unassign(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    task_uid: int = typer.Argument(..., help="Task UniqueID"),
    resource_uid: int = typer.Argument(..., help="Resource UniqueID"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Remove a resource assignment from a task."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        matched = _matching_assignments(project, task_uid, resource_uid)
        if not matched:
            error = {
                "error": f"No assignment of resource {resource_uid} on task {task_uid}",
                "code": "ASSIGNMENT_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        for assignment in matched:
            assignment.remove()

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path, affected_unique_id=task_uid)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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
def link(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    task_uid: int = typer.Argument(..., help="Successor task UniqueID"),
    pred_uid: int = typer.Argument(..., help="Predecessor task UniqueID"),
    type: str = typer.Option("FS", help="Relation type: FS, SS, FF, SF"),
    lag: Optional[str] = typer.Option(None, help="Lag (e.g., '2d')"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Link a predecessor task to a task."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        from org.mpxj import Relation, RelationType

        link_type = type.upper()
        if link_type not in RELATION_TYPES:
            raise ValidationError(
                f"Invalid relation type: {type!r} (use FS, SS, FF, SF)"
            )

        lag_duration = parse_duration(lag) if lag else None
        if lag and lag_duration is None:
            raise ValidationError(f"Invalid lag: {lag!r} (use e.g. '2d', '8h')")

        project = read_project(str(file_path))
        task = project.getTaskByUniqueID(jint(task_uid))
        if not task:
            error = {"error": f"Task not found: {task_uid}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)
        pred = project.getTaskByUniqueID(jint(pred_uid))
        if not pred:
            error = {"error": f"Task not found: {pred_uid}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        if task_uid == pred_uid:
            raise ValidationError("A task cannot link to itself")

        for existing in task.getPredecessors():
            if (
                int(existing.getPredecessorTask().getUniqueID()) == pred_uid
                and str(existing.getType()) == link_type
            ):
                raise ValidationError(
                    f"Task {task_uid} is already linked to {pred_uid} ({link_type})"
                )

        builder = (
            Relation.Builder()
            .predecessorTask(pred)
            .successorTask(task)
            .type(getattr(RelationType, RELATION_TYPES[link_type]))
        )
        if lag_duration is not None:
            builder.lag(lag_duration)
        task.addPredecessor(builder)

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path, affected_unique_id=task_uid)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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
def unlink(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    task_uid: int = typer.Argument(..., help="Successor task UniqueID"),
    pred_uid: int = typer.Argument(..., help="Predecessor task UniqueID"),
    type: Optional[str] = typer.Option(
        None, help="Relation type to remove: FS, SS, FF, SF (default: all)"
    ),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Remove a predecessor link from a task."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        link_type = type.upper() if type else None
        if link_type is not None and link_type not in RELATION_TYPES:
            raise ValidationError(
                f"Invalid relation type: {type!r} (use FS, SS, FF, SF)"
            )

        project = read_project(str(file_path))
        task = project.getTaskByUniqueID(jint(task_uid))
        if not task:
            error = {"error": f"Task not found: {task_uid}", "code": "TASK_NOT_FOUND"}
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        matched = [
            rel
            for rel in task.getPredecessors()
            if int(rel.getPredecessorTask().getUniqueID()) == pred_uid
            and (link_type is None or str(rel.getType()) == link_type)
        ]
        if not matched:
            error = {
                "error": f"No link from task {pred_uid} to task {task_uid}",
                "code": "LINK_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        for rel in matched:
            task.removePredecessor(
                rel.getPredecessorTask(), rel.getType(), rel.getLag()
            )

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path, affected_unique_id=task_uid)
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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


def _resolve_parent(project, created_by_name, ref):
    """Resolve a batch parent ref (UniqueID or task name) to a Java Task."""
    if isinstance(ref, int):
        task = project.getTaskByUniqueID(jint(ref))
        if task is None:
            raise ValidationError(f"Parent task not found: {ref}")
        return task
    if ref in created_by_name:
        return created_by_name[ref]
    matches = [t for t in project.getTasks() if jstr(t.getName()) == ref]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValidationError(f"Parent task not found: {ref!r}")
    raise ValidationError(f"Ambiguous parent task name: {ref!r}")


def _resolve_resource(project, name):
    """Resolve a resource name to exactly one Java Resource."""
    matches = [r for r in project.getResources() if jstr(r.getName()) == name]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValidationError(f"Resource not found: {name!r}")
    raise ValidationError(f"Ambiguous resource name: {name!r}")


@app.command("import")
def import_tasks(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    batch: str = typer.Argument(..., help="Path to batch JSON file"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Create many tasks at once from a batch JSON file.

    Batch format: {"project_name": "...", "tasks": [{"name": "...",
    "start": "YYYY-MM-DD", "finish": "...", "duration": "5d",
    "notes": "...", "milestone": false, "percent_complete": 0,
    "parent": "<task name or UniqueID>",
    "resources": ["Alice", {"name": "Bob", "units": 0.5}]}]}
    Parents may reference tasks created earlier in the same batch.
    """
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    batch_path = Path(batch)
    if not batch_path.exists():
        error = {"error": f"File not found: {batch}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        try:
            spec = json.loads(batch_path.read_text())
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid batch JSON: {e}")
        items = spec.get("tasks")
        # NOTE: builtin list is shadowed by the list command in this
        # module, so never reference it, not even in `is` comparisons.
        if isinstance(items, (str, bytes, dict)):
            items = []
        else:
            try:
                items = [x for x in items]
            except TypeError:
                items = []
        if not items:
            raise ValidationError('Batch JSON needs a non-empty "tasks" list')

        project = read_project(str(file_path))
        created_by_name = {}
        created_uids = []

        for index, item in enumerate(items):
            label = f"tasks[{index}]"
            if not isinstance(item, dict) or not item.get("name"):
                raise ValidationError(f"{label} needs a name")
            start_dt, finish_dt, dur = validate_task_inputs(
                item.get("start"),
                item.get("finish"),
                item.get("duration"),
                item.get("percent_complete"),
            )
            parent_task = None
            if item.get("parent") is not None:
                parent_task = _resolve_parent(project, created_by_name, item["parent"])
            new_task = _insert_task(
                project,
                item["name"],
                notes=item.get("notes"),
                start_dt=start_dt,
                finish_dt=finish_dt,
                duration=dur,
                milestone=bool(item.get("milestone", False)),
                percent_complete=item.get("percent_complete"),
                parent_task=parent_task,
            )
            created_by_name[item["name"]] = new_task
            created_uids.append(int(new_task.getUniqueID()))
            for res in item.get("resources") or []:
                if isinstance(res, dict):
                    res_name, units = res.get("name"), res.get("units", 1.0)
                else:
                    res_name, units = res, 1.0
                if not res_name or units <= 0:
                    raise ValidationError(
                        f"{label} has an invalid resource entry: {res!r}"
                    )
                resource = _resolve_resource(project, res_name)
                _create_assignment(project, new_task, resource, float(units))

        batch_name = project_name or spec.get("project_name")
        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, batch_name)
        write_output(project, output_path)

        response = ImportSuccess(
            output=output_path, created_unique_ids=created_uids, count=len(created_uids)
        )
        result = response.model_dump_json(indent=2)
        typer.echo(result)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValidationError as e:
        error = {"error": str(e), "code": "INVALID_VALUE"}
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
