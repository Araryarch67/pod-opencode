import typer
from pathlib import Path
import json
from typing import Optional

from pod_opencode.reader import read_project
from pod_opencode.models import AssignmentInfo, AssignmentListResponse
from pod_opencode.utils import java_date_to_iso, duration_to_str, jstr

app = typer.Typer()


def _assignment_to_info(assignment) -> AssignmentInfo:
    """Convert a Java ResourceAssignment object to AssignmentInfo."""
    task = assignment.getTask()
    resource = assignment.getResource()

    return AssignmentInfo(
        unique_id=assignment.getUniqueID(),
        task_unique_id=task.getUniqueID() if task else None,
        task_name=jstr(task.getName()) if task else None,
        resource_unique_id=resource.getUniqueID() if resource else None,
        resource_name=jstr(resource.getName()) if resource else None,
        units=assignment.getUnits(),
        work=duration_to_str(assignment.getWork()),
        actual_work=duration_to_str(assignment.getActualWork()),
        start=java_date_to_iso(assignment.getStart()),
        finish=java_date_to_iso(assignment.getFinish()),
    )


@app.command()
def list(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
    task_id: Optional[int] = typer.Option(None, help="Filter by task UniqueID"),
    resource_id: Optional[int] = typer.Option(None, help="Filter by resource UniqueID"),
):
    """List all resource assignments in the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        assignments = project.getResourceAssignments()

        assignment_infos = []
        if assignments:
            for assignment in assignments:
                task = assignment.getTask()
                resource = assignment.getResource()

                if task_id and task and task.getUniqueID() != task_id:
                    continue
                if resource_id and resource and resource.getUniqueID() != resource_id:
                    continue

                assignment_infos.append(_assignment_to_info(assignment))

        response = AssignmentListResponse(
            assignments=assignment_infos, count=len(assignment_infos)
        )
        output = response.model_dump_json(indent=2)
        typer.echo(output)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except Exception as e:
        error = {"error": str(e), "code": "READ_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
