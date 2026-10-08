import typer
from pathlib import Path
import json
from typing import Optional

from pod_opencode.reader import read_project
from pod_opencode.writer import apply_project_name, write_output, resolve_output_path
from pod_opencode.models import RunSuccess
from pod_opencode.utils import (
    jint,
    jstr,
    next_ids,
    parse_duration,
    to_java_datetime,
    validate_task_inputs,
    check_effective_order,
    suggest_name,
    find_cycle_uids,
    set_resource_max_units,
    ValidationError,
)
from pod_opencode.commands.tasks import (
    RELATION_TYPES,
    _insert_task,
    _create_assignment,
    _matching_assignments,
    _resolve_parent,
    _resolve_resource,
    _sweep_deleted_links,
)

app = typer.Typer()


class OpError(Exception):
    """A failed run operation carrying a stable error code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _need_task(project, value, refs, role="task"):
    """Resolve a UID, ref label, or name to a Java Task or raise OpError."""
    if isinstance(value, int):
        task = project.getTaskByUniqueID(jint(value))
        if task is None:
            raise OpError("TASK_NOT_FOUND", f"Task not found: {value}")
        return task
    if isinstance(value, str) and value in refs:
        return refs[value]
    matches = [t for t in project.getTasks() if jstr(t.getName()) == value]
    if len(matches) == 1:
        return matches[0]
    hint = suggest_name(value, refs, project, kind="task")
    if not matches:
        raise OpError("TASK_NOT_FOUND", f"Task not found: {value!r}{hint}")
    raise OpError("INVALID_VALUE", f"Ambiguous task name: {value!r}{hint}")


def _need_resource(project, value, refs):
    """Resolve a UID, ref label, or name to a Java Resource or raise OpError."""
    if isinstance(value, int):
        resource = project.getResourceByUniqueID(jint(value))
        if resource is None:
            raise OpError("RESOURCE_NOT_FOUND", f"Resource not found: {value}")
        return resource
    if isinstance(value, str) and value in refs:
        return refs[value]
    matches = [r for r in project.getResources() if jstr(r.getName()) == value]
    if len(matches) == 1:
        return matches[0]
    hint = suggest_name(value, refs, project, kind="resource")
    if not matches:
        raise OpError("RESOURCE_NOT_FOUND", f"Resource not found: {value!r}{hint}")
    raise OpError("INVALID_VALUE", f"Ambiguous resource name: {value!r}{hint}")


def _apply_op(project, index, item, task_refs, res_refs):
    """Apply one operation in memory. Returns a receipt dict."""
    if not isinstance(item, dict) or "op" not in item:
        raise OpError("INVALID_VALUE", f"operations[{index}] needs an 'op'")
    op = item["op"]

    if op == "add":
        if not item.get("name"):
            raise OpError("INVALID_VALUE", f"operations[{index}]: add needs a name")
        start_dt, finish_dt, dur = validate_task_inputs(
            item.get("start"), item.get("finish"), item.get("duration")
        )
        parent = None
        if item.get("parent") is not None:
            parent = _resolve_parent(project, task_refs, item["parent"])
        task = _insert_task(
            project,
            item["name"],
            notes=item.get("notes"),
            start_dt=start_dt,
            finish_dt=finish_dt,
            duration=dur,
            milestone=bool(item.get("milestone", False)),
            parent_task=parent,
        )
        task_refs[item["name"]] = task
        if item.get("ref"):
            task_refs[item["ref"]] = task
        for res in item.get("resources") or []:
            if isinstance(res, dict):
                res_name, units = res.get("name"), res.get("units", 1.0)
            else:
                res_name, units = res, 1.0
            if not res_name or units <= 0:
                raise OpError(
                    "INVALID_VALUE",
                    f"operations[{index}]: invalid resource entry {res!r}",
                )
            _create_assignment(
                project, task, _need_resource(project, res_name, res_refs), float(units)
            )
        return {"op": "add", "unique_id": int(task.getUniqueID())}

    if op == "update":
        task = _need_task(project, item.get("unique_id", item.get("ref")), task_refs)
        if item.get("name"):
            task.setName(item["name"])
        if item.get("notes") is not None:
            task.setNotes(item["notes"])
        if (
            item.get("start") is not None
            or item.get("finish") is not None
            or item.get("duration") is not None
            or item.get("percent_complete") is not None
        ):
            start_dt, finish_dt, dur = validate_task_inputs(
                item.get("start"),
                item.get("finish"),
                item.get("duration"),
                item.get("percent_complete"),
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
            if item.get("percent_complete") is not None:
                task.setPercentageComplete(item["percent_complete"])
        if item.get("milestone") is not None:
            task.setMilestone(bool(item["milestone"]))
        return {"op": "update", "unique_id": int(task.getUniqueID())}

    if op == "delete":
        task = _need_task(project, item.get("unique_id", item.get("ref")), task_refs)
        uid = int(task.getUniqueID())
        before = {
            int(t.getUniqueID())
            for t in project.getTasks()
            if t.getUniqueID() is not None
        }
        project.removeTask(task)
        _sweep_deleted_links(project, before)
        return {"op": "delete", "unique_id": uid}

    if op == "assign":
        task = _need_task(project, item.get("task", item.get("unique_id")), task_refs)
        resource = _need_resource(project, item.get("resource"), res_refs)
        units = item.get("units", 1.0)
        if units <= 0:
            raise OpError("INVALID_VALUE", f"operations[{index}]: units must be > 0")
        if _matching_assignments(
            project, int(task.getUniqueID()), int(resource.getUniqueID())
        ):
            raise OpError(
                "INVALID_VALUE",
                f"operations[{index}]: already assigned",
            )
        new_uid = _create_assignment(project, task, resource, float(units))
        return {"op": "assign", "unique_id": new_uid}

    if op == "unassign":
        task = _need_task(project, item.get("task", item.get("unique_id")), task_refs)
        resource = _need_resource(project, item.get("resource"), res_refs)
        matched = _matching_assignments(
            project, int(task.getUniqueID()), int(resource.getUniqueID())
        )
        if not matched:
            raise OpError(
                "ASSIGNMENT_NOT_FOUND", f"operations[{index}]: no such assignment"
            )
        for assignment in matched:
            assignment.remove()
        return {"op": "unassign", "unique_id": int(task.getUniqueID())}

    if op == "link":
        from org.mpxj import Relation, RelationType

        task = _need_task(project, item.get("task", item.get("unique_id")), task_refs)
        pred = _need_task(project, item.get("pred"), task_refs)
        if int(task.getUniqueID()) == int(pred.getUniqueID()):
            raise OpError(
                "INVALID_VALUE", f"operations[{index}]: cannot link to itself"
            )
        link_type = str(item.get("type", "FS")).upper()
        if link_type not in RELATION_TYPES:
            raise OpError(
                "INVALID_VALUE", f"operations[{index}]: bad type {item.get('type')!r}"
            )
        lag = parse_duration(item["lag"]) if item.get("lag") else None
        if item.get("lag") and lag is None:
            raise OpError("INVALID_VALUE", f"operations[{index}]: bad lag")
        for existing in task.getPredecessors():
            if (
                int(existing.getPredecessorTask().getUniqueID())
                == int(pred.getUniqueID())
                and str(existing.getType()) == link_type
            ):
                raise OpError("INVALID_VALUE", f"operations[{index}]: link exists")
        builder = (
            Relation.Builder()
            .predecessorTask(pred)
            .successorTask(task)
            .type(getattr(RelationType, RELATION_TYPES[link_type]))
        )
        if lag is not None:
            builder.lag(lag)
        task.addPredecessor(builder)
        if int(task.getUniqueID()) in find_cycle_uids(project):
            raise OpError(
                "INVALID_VALUE", f"operations[{index}]: link would create a cycle"
            )
        return {"op": "link", "unique_id": int(task.getUniqueID())}

    if op == "unlink":
        task = _need_task(project, item.get("task", item.get("unique_id")), task_refs)
        pred = _need_task(project, item.get("pred"), task_refs)
        link_type = str(item["type"]).upper() if item.get("type") else None
        if link_type is not None and link_type not in RELATION_TYPES:
            raise OpError("INVALID_VALUE", f"operations[{index}]: bad type")
        matched = [
            rel
            for rel in task.getPredecessors()
            if int(rel.getPredecessorTask().getUniqueID()) == int(pred.getUniqueID())
            and (link_type is None or str(rel.getType()) == link_type)
        ]
        if not matched:
            raise OpError("LINK_NOT_FOUND", f"operations[{index}]: no such link")
        for rel in matched:
            task.removePredecessor(
                rel.getPredecessorTask(), rel.getType(), rel.getLag()
            )
        return {"op": "unlink", "unique_id": int(task.getUniqueID())}

    if op == "rename":
        if not item.get("project_name"):
            raise OpError(
                "INVALID_VALUE", f"operations[{index}]: rename needs project_name"
            )
        apply_project_name(project, item["project_name"])
        return {"op": "rename"}

    if op == "resource_add":
        if not item.get("name"):
            raise OpError(
                "INVALID_VALUE", f"operations[{index}]: resource_add needs a name"
            )
        ids = [int(r.getID()) for r in project.getResources() if r.getID() is not None]
        uids = [
            int(r.getUniqueID())
            for r in project.getResources()
            if r.getUniqueID() is not None
        ]
        resource = project.addResource()
        resource.setID(jint(max(ids or [0]) + 1))
        resource.setUniqueID(jint(max(uids or [0]) + 1))
        resource.setName(item["name"])
        if item.get("email"):
            resource.setEmailAddress(item["email"])
        if item.get("max_units") is not None:
            if float(item["max_units"]) <= 0:
                raise OpError(
                    "INVALID_VALUE", f"operations[{index}]: max-units must be > 0"
                )
            set_resource_max_units(resource, float(item["max_units"]))
        res_refs[item["name"]] = resource
        if item.get("ref"):
            res_refs[item["ref"]] = resource
        return {"op": "resource_add", "unique_id": int(resource.getUniqueID())}

    raise OpError("INVALID_VALUE", f"operations[{index}]: unknown op {op!r}")


@app.callback(invoke_without_command=True)
def run(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    script: str = typer.Argument(..., help="Path to run JSON script"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Run many operations from a JSON script in one JVM session.

    The whole script validates in memory first: any failure aborts the run
    and nothing is written. See references/batch.md for item shapes.
    """
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    script_path = Path(script)
    if not script_path.exists():
        error = {"error": f"File not found: {script}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        try:
            spec = json.loads(script_path.read_text())
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid run JSON: {e}")
        items = spec.get("operations")
        if isinstance(items, (str, bytes, dict)):
            items = []
        else:
            try:
                items = [x for x in items]
            except TypeError:
                items = []
        if not items:
            raise ValidationError("Run script needs a non-empty 'operations' list")

        project = read_project(str(file_path))
        task_refs = {}
        res_refs = {}
        receipts = []
        apply_project_name(project, spec.get("project_name"))
        try:
            for index, item in enumerate(items):
                receipts.append(_apply_op(project, index, item, task_refs, res_refs))
        except OpError as e:
            error = {
                "error": str(e),
                "code": e.code,
                "failed_operation": index,
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = RunSuccess(output=output_path, results=receipts)
        typer.echo(response.model_dump_json(indent=2))
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
