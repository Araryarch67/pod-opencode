import typer
import atexit
from pod_opencode import __version__
from pod_opencode.jvm import start_jvm, shutdown_jvm
from pod_opencode.commands import (
    info,
    convert,
    tasks,
    resources,
    assignments,
    diff,
    check,
)

app = typer.Typer(help="CLI for reading and modifying ProjectLibre POD files via MPXJ")


@app.callback(invoke_without_command=False)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        is_flag=True,
        is_eager=True,
        callback=lambda ctx, param, value: (
            (typer.echo(f"pod-opencode {__version__}"), typer.Exit(0))
            if value
            else None
        ),
    ),
):
    """Initialize JVM and register atexit cleanup."""
    start_jvm()
    atexit.register(shutdown_jvm)


app.add_typer(info.app, name="info", help="Display project metadata")
app.add_typer(convert.app, name="convert", help="Convert POD/XML to MSPDI XML")
app.add_typer(tasks.app, name="tasks", help="Manage tasks")
app.add_typer(resources.app, name="resources", help="Manage resources")
app.add_typer(assignments.app, name="assignments", help="View resource assignments")
app.add_typer(diff.app, name="diff", help="Compare two project files")
app.add_typer(check.app, name="check", help="Lint a project file")


if __name__ == "__main__":
    app()
