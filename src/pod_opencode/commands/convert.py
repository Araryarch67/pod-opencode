import typer
from pathlib import Path
import json
from typing import Optional

from pod_opencode.reader import read_project
from pod_opencode.writer import apply_project_name, write_output, resolve_output_path
from pod_opencode.models import WriteSuccess
from pod_opencode.utils import ValidationError

app = typer.Typer()


@app.callback(invoke_without_command=True)
def convert(
    input_file: str = typer.Argument(..., help="Input .pod or .xml file"),
    output_file: Optional[str] = typer.Argument(
        None, help="Output file (.xml or .pod)"
    ),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Convert a POD/XML file to MSPDI XML or native POD format."""
    input_path = Path(input_file)

    if not input_path.exists():
        error = {"error": f"File not found: {input_file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        output_path = resolve_output_path(str(input_path), output_file, in_place)
        project = read_project(str(input_path))
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(output=output_path)
        output = response.model_dump_json(indent=2)
        typer.echo(output)
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
