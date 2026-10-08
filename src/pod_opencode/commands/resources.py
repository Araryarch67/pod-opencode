import typer
from pathlib import Path
import json
from typing import Optional

from pod_opencode.reader import read_project
from pod_opencode.writer import apply_project_name, write_output, resolve_output_path
from pod_opencode.models import ResourceInfo, ResourceListResponse, WriteSuccess
from pod_opencode.utils import jstr, jint, next_ids, ValidationError


app = typer.Typer()


def _resource_to_info(resource) -> ResourceInfo:
    """Convert a Java Resource object to ResourceInfo."""
    return ResourceInfo(
        unique_id=resource.getUniqueID(),
        id=resource.getID(),
        name=jstr(resource.getName()),
        resource_type=str(resource.getType()),
        email=jstr(resource.getEmailAddress()),
        max_units=resource.getMaxUnits(),
        notes=jstr(resource.getNotes()),
    )


@app.command("list")
def list_resources(
    file: str = typer.Argument(..., help="Path to .pod or .xml file"),
):
    """List all resources in the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        resources = project.getResources()

        resource_infos = []
        if resources:
            for resource in resources:
                resource_infos.append(_resource_to_info(resource))

        response = ResourceListResponse(
            resources=resource_infos, count=len(resource_infos)
        )
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
    unique_id: int = typer.Argument(..., help="Resource UniqueID"),
):
    """Get a specific resource by UniqueID."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        resource = project.getResourceByUniqueID(jint(unique_id))

        if not resource:
            error = {
                "error": f"Resource not found: {unique_id}",
                "code": "RESOURCE_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        resource_info = _resource_to_info(resource)
        output = resource_info.model_dump_json(indent=2)
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
    name: str = typer.Option(..., help="Resource name"),
    email: Optional[str] = typer.Option(None, help="Email address"),
    max_units: Optional[float] = typer.Option(None, help="Max units (e.g., 1.0)"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Add a new resource to the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))

        new_id, new_uid = next_ids(project.getResources())
        new_resource = project.addResource()
        new_resource.setID(jint(new_id))
        new_resource.setUniqueID(jint(new_uid))
        new_resource.setName(name)
        if email:
            new_resource.setEmailAddress(email)
        if max_units is not None:
            new_resource.setMaxUnits(max_units)

        output_path = resolve_output_path(str(file_path), output, in_place)
        apply_project_name(project, project_name)
        write_output(project, output_path)

        response = WriteSuccess(
            output=output_path, affected_unique_id=new_resource.getUniqueID()
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
    unique_id: int = typer.Argument(..., help="Resource UniqueID"),
    name: Optional[str] = typer.Option(None, help="New resource name"),
    email: Optional[str] = typer.Option(None, help="New email address"),
    max_units: Optional[float] = typer.Option(None, help="New max units"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Update an existing resource."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        resource = project.getResourceByUniqueID(jint(unique_id))

        if not resource:
            error = {
                "error": f"Resource not found: {unique_id}",
                "code": "RESOURCE_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        if name:
            resource.setName(name)
        if email:
            resource.setEmailAddress(email)
        if max_units is not None:
            resource.setMaxUnits(max_units)

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
    unique_id: int = typer.Argument(..., help="Resource UniqueID"),
    project_name: Optional[str] = typer.Option(
        None, help="Set project name (window title in ProjectLibre)"
    ),
    output: Optional[str] = typer.Option(None, help="Output file (.xml or .pod)"),
    in_place: bool = typer.Option(
        False, "--in-place", help="Modify input in place (backs up to .bak)"
    ),
):
    """Delete a resource from the project."""
    file_path = Path(file)
    if not file_path.exists():
        error = {"error": f"File not found: {file}", "code": "FILE_NOT_FOUND"}
        typer.echo(json.dumps(error), err=True)
        raise typer.Exit(1)

    try:
        project = read_project(str(file_path))
        resource = project.getResourceByUniqueID(jint(unique_id))

        if not resource:
            error = {
                "error": f"Resource not found: {unique_id}",
                "code": "RESOURCE_NOT_FOUND",
            }
            typer.echo(json.dumps(error), err=True)
            raise typer.Exit(1)

        project.removeResource(resource)
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
