import typer
import atexit
from typing import Optional
from pod_opencode import __version__
from pod_opencode.jvm import start_jvm, shutdown_jvm
from pod_opencode.commands import tasks, resources, assignments
from pod_opencode.commands.info import info as info_fn
from pod_opencode.commands.convert import convert as convert_fn
from pod_opencode.commands.diff import diff as diff_fn
from pod_opencode.commands.check import check as check_fn
from pod_opencode.commands.run import run as run_fn

app = typer.Typer(help="CLI for reading and modifying ProjectLibre POD files via MPXJ")


def _show_version():
    typer.echo(f"pod-opencode {__version__}")
    raise typer.Exit()


@app.callback(invoke_without_command=False)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        is_eager=True,
        callback=lambda ctx, param, value: _show_version() if value else None,
    ),
):
    """Initialize JVM and register atexit cleanup."""
    start_jvm()
    atexit.register(shutdown_jvm)


app.add_typer(tasks.app, name="tasks", help="Manage tasks")
app.add_typer(resources.app, name="resources", help="Manage resources")
app.add_typer(assignments.app, name="assignments", help="View resource assignments")

# Single-action groups are registered as real commands so options parse
# in any position (group callbacks only accept options before arguments).
app.command("info", help="Display project metadata")(info_fn)
app.command("convert", help="Convert POD/XML to MSPDI XML or native POD")(convert_fn)
app.command("diff", help="Compare two project files")(diff_fn)
app.command("check", help="Lint a project file")(check_fn)
app.command("run", help="Run many operations from a JSON script")(run_fn)


if __name__ == "__main__":
    app()
