import typer
from pathlib import Path
import json

from pod_opencode.reader import read_project
from pod_opencode.models import ProjectInfo
from pod_opencode.utils import java_date_to_iso, jstr

app = typer.Typer()


@app.callback(invoke_without_command=True)
def info(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
):
    """Display project metadata as JSON."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        props = project.getProjectProperties()

        project_info = ProjectInfo(
            name=jstr(props.getProjectTitle()),
            project_id=jstr(props.getProjectID()),
            start_date=java_date_to_iso(props.getStartDate()),
            finish_date=java_date_to_iso(props.getFinishDate()),
            status_date=java_date_to_iso(props.getStatusDate()),
            author=jstr(props.getAuthor()),
            company=jstr(props.getCompany()),
            currency_symbol=jstr(props.getCurrencySymbol()),
            task_count=len(list(project.getTasks())) if project.getTasks() else 0,
            resource_count=len(list(project.getResources()))
            if project.getResources()
            else 0,
        )
        output = project_info.model_dump_json(indent=2, exclude_none=False)
        typer.echo(output)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except Exception as e:
        error = {"error": str(e), "code": "READ_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
