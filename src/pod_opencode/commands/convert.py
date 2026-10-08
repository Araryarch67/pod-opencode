import typer
from pathlib import Path
import json

from pod_opencode.reader import read_project
from pod_opencode.writer import write_project
from pod_opencode.models import WriteSuccess

app = typer.Typer()


@app.callback(invoke_without_command=True)
def convert(
    input_file: str = typer.Argument(..., help="Input .pod or .xml file"),
    output_file: str = typer.Argument(..., help="Output .xml file"),
):
    """Convert a POD/XML file to MSPDI XML format."""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        error = {"error": f"File not found: {input_file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    if output_path.suffix.lower() == ".pod":
        error = {
            "error": "Output must be .xml (MPXJ cannot write POD format)",
            "code": "INVALID_OUTPUT_FORMAT",
        }
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(input_path))
        write_project(project, str(output_path))

        response = WriteSuccess(output=str(output_path))
        output = response.model_dump_json(indent=2)
        typer.echo(output)
    except FileNotFoundError as e:
        error = {"error": str(e), "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except ValueError as e:
        error = {"error": str(e), "code": "INVALID_OUTPUT_FORMAT"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
    except Exception as e:
        error = {"error": str(e), "code": "WRITE_ERROR"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)
