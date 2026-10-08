import typer
from pathlib import Path
import json
import re

from pod_opencode.reader import read_project
from pod_opencode.utils import jstr

app = typer.Typer()

POD_SEPARATOR = b"@@@@@@@@@@ProjectLibreSeparator_MSXML@@@@@@@@@@"

_TASK_BLOCK = re.compile(r"<Task>.*?</Task>", re.S)
_TASK_UID = re.compile(r"<UID>(\d+)</UID>")
_PRED_UID = re.compile(r"<PredecessorUID>(\d+)</PredecessorUID>")


def _raw_task_links(path):
    """Map task UID to predecessor UIDs by scanning the raw MSPDI text.

    MPXJ silently drops links that point at unknown tasks, so the object
    model cannot report them. The raw scan catches that silent data loss.
    Returns {} when no MSPDI text is present.
    """
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return {}
    if b"PredecessorUID" not in raw:
        return {}
    sep = raw.find(POD_SEPARATOR)
    text = (
        raw[sep + len(POD_SEPARATOR) :].decode("utf-8", "replace")
        if sep >= 0
        else raw.decode("utf-8", "replace")
    )
    links = {}
    for block in _TASK_BLOCK.findall(text):
        uid_match = _TASK_UID.search(block)
        if not uid_match:
            continue
        links[int(uid_match.group(1))] = [int(m) for m in _PRED_UID.findall(block)]
    return links


def _finding(code, severity, unique_id, detail):
    return {
        "code": code,
        "severity": severity,
        "unique_id": unique_id,
        "detail": detail,
    }


@app.callback(invoke_without_command=True)
def check(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
):
    """Lint a project file and report logical problems.

    Prints {"errors": [...], "warnings": [...], "summary": {...}}.
    Exits 1 when any error is found, 0 otherwise. Read-only.
    """
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        errors = []
        warnings = []

        tasks = [t for t in project.getTasks()] if project.getTasks() else []
        by_uid = {}
        for task in tasks:
            if task.getUniqueID() is not None:
                by_uid[int(task.getUniqueID())] = task

        seen_names = {}
        for task in tasks:
            uid = int(task.getUniqueID()) if task.getUniqueID() is not None else None
            name = jstr(task.getName())

            if not name:
                warnings.append(
                    _finding("EMPTY_TASK_NAME", "warning", uid, "Task has no name")
                )
            else:
                seen_names.setdefault(name, []).append(uid)

            start = task.getStart()
            finish = task.getFinish()
            if start is None or finish is None or task.getDuration() is None:
                warnings.append(
                    _finding(
                        "MISSING_DATES",
                        "warning",
                        uid,
                        f"Task {name!r} is missing start, finish, or duration",
                    )
                )
            elif str(finish) < str(start):
                errors.append(
                    _finding(
                        "FINISH_BEFORE_START",
                        "error",
                        uid,
                        f"Task {name!r} finishes before it starts",
                    )
                )

            percent = task.getPercentageComplete()
            if percent is not None and not 0 <= float(percent) <= 100:
                errors.append(
                    _finding(
                        "PERCENT_OUT_OF_RANGE",
                        "error",
                        uid,
                        f"Task {name!r} percent complete is {percent}",
                    )
                )

            if task.getMilestone():
                duration = task.getDuration()
                if duration is not None and float(duration.getDuration()) != 0:
                    warnings.append(
                        _finding(
                            "MILESTONE_WITH_DURATION",
                            "warning",
                            uid,
                            f"Milestone {name!r} has nonzero duration",
                        )
                    )

            parent = task.getParentTask()
            if parent is not None:
                level = task.getOutlineLevel()
                parent_level = parent.getOutlineLevel()
                if level is None:
                    warnings.append(
                        _finding(
                            "MISSING_OUTLINE_LEVEL",
                            "warning",
                            uid,
                            f"Task {name!r} has a parent but no outline level",
                        )
                    )
                elif parent_level is not None and int(level) != int(parent_level) + 1:
                    errors.append(
                        _finding(
                            "BROKEN_HIERARCHY",
                            "error",
                            uid,
                            f"Task {name!r} outline level {level} does not follow "
                            f"parent level {parent_level}",
                        )
                    )

            assignments = task.getResourceAssignments()
            if not assignments:
                warnings.append(
                    _finding(
                        "UNASSIGNED_TASK",
                        "warning",
                        uid,
                        f"Task {name!r} has no resource assignments",
                    )
                )

            predecessors = task.getPredecessors()
            if predecessors:
                for rel in predecessors:
                    pred = rel.getPredecessorTask()
                    if pred is None or pred.getUniqueID() is None:
                        errors.append(
                            _finding(
                                "DANGLING_LINK",
                                "error",
                                uid,
                                f"Task {name!r} links to a missing predecessor",
                            )
                        )
                    elif int(pred.getUniqueID()) not in by_uid:
                        errors.append(
                            _finding(
                                "DANGLING_LINK",
                                "error",
                                uid,
                                f"Task {name!r} links to unknown task "
                                f"{int(pred.getUniqueID())}",
                            )
                        )
                    elif int(pred.getUniqueID()) == uid:
                        errors.append(
                            _finding(
                                "SELF_LINK",
                                "error",
                                uid,
                                f"Task {name!r} links to itself",
                            )
                        )

        for name, uids in seen_names.items():
            if len(uids) > 1:
                warnings.append(
                    _finding(
                        "DUPLICATE_TASK_NAME",
                        "warning",
                        None,
                        f"Name {name!r} is used by tasks {sorted(u for u in uids if u is not None)}",
                    )
                )

        for uid, pred_uids in _raw_task_links(file).items():
            for pred_uid in pred_uids:
                if pred_uid not in by_uid:
                    errors.append(
                        _finding(
                            "DANGLING_LINK",
                            "error",
                            uid,
                            f"Task {uid} links to unknown task {pred_uid} "
                            "(dropped silently on read)",
                        )
                    )

        assignments = (
            [a for a in project.getResourceAssignments()]
            if project.getResourceAssignments()
            else []
        )
        for assignment in assignments:
            # A null resource with a valid task is normal MSPDI: the writer
            # emits a resourceless assignment to carry a task's actuals
            # (e.g. after setting percent complete). Only a missing task
            # means real corruption.
            if assignment.getTask() is None:
                errors.append(
                    _finding(
                        "ORPHAN_ASSIGNMENT",
                        "error",
                        None,
                        "An assignment references a missing task",
                    )
                )

        result = {
            "errors": errors,
            "warnings": warnings,
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "tasks_checked": len(tasks),
                "assignments_checked": len(assignments),
            },
        }
        typer.echo(json.dumps(result, indent=2))
        if errors:
            raise typer.Exit(1)
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
