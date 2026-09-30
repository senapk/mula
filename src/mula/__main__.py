from __future__ import annotations

from types import SimpleNamespace

import typer

from .cli_add import AddCommand, add
from .actions import Actions
from .credentials import Credentials
from .moodle_api import MoodleAPI
from .cli_selection import normalize_selection as _selection
from .cli_update import UpdateCommand, resume, update
from .course_sections import CourseSections
from .__init__ import __version__


app = typer.Typer(
    help="Gerenciar VPLs do Moodle de forma automatizada.",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=False,
    invoke_without_command=True,
)
section_app = typer.Typer(help="Add, rename or remove course sections.")
app.add_typer(section_app, name="section")


@app.callback()
def main_callback(
    ctx: typer.Context,
    config: str | None = typer.Option(None, "--config", help="config file path"),
    timeout: int | None = typer.Option(
        None, "--timeout", "-t", min=1,
        help="Maximum wait for a Moodle response, in seconds",
    ),
    version: bool = typer.Option(False, "--version", "-v", is_eager=True, help="show version"),
) -> None:
    """Gerenciar VPLs do Moodle de forma automatizada."""
    del config  # Kept for CLI compatibility; configuration files are not implemented yet.
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if timeout is not None:
        if ctx.invoked_subcommand == "resume":
            raise typer.BadParameter("resume uses the saved timeout; --timeout cannot override it")
        MoodleAPI.default_timeout = timeout

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    credentials = Credentials.load_credentials().load_file()
    if ctx.invoked_subcommand not in ("auth", "alias", "add", "update", "resume"):
        credentials.fill_empty()


@app.command(help="Show user courses")
def courses() -> None:
    Actions.courses(SimpleNamespace())


@app.command(help="Authenticate user")
def auth() -> None:
    Actions.auth(SimpleNamespace())


@app.command(help="Set alias for a course ID")
def alias(
    alias: str = typer.Argument(..., help="Alias for the course"),
    course: int = typer.Argument(..., help="Moodle course ID"),
) -> None:
    Actions.alias(SimpleNamespace(alias=alias, course=course))


@app.command("list", help="List course sections and VPL activities")
def list_course(
    course: str = typer.Option(..., "--course", "-c", help="Moodle course ID or alias"),
    section: int | None = typer.Option(None, "--section", "-S", min=0, help="Course section index"),
    url: bool = typer.Option(False, "--url", "-u", help="Show VPL URLs"),
    topic: bool = typer.Option(False, "--topic", "-t", help="Show only section topics"),
) -> None:
    Actions.list(SimpleNamespace(course=course, section=section, url=url, topic=topic))


app.command("add", cls=AddCommand)(add)


@app.command(
    help="Remove selected problems from Moodle",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def rm(
    ctx: typer.Context,
    course: str = typer.Option(..., "--course", "-c", help="Moodle course ID or alias"),
    all_: bool = typer.Option(False, "--all", "-A", help="Select all VPL activities"),
    ids: list[int] | None = typer.Option(None, "--id", "-I", help="Activity ID (repeat for multiple IDs)"),
    labels: list[str] | None = typer.Option(None, "--label", "-L", help="Activity label (repeat for multiple labels)"),
    sections: list[int] | None = typer.Option(None, "--section", "-S", help="Section index (repeat for multiple sections)"),
) -> None:
    selection = _selection(all_, ids, labels, sections, ctx.args)
    Actions.rm(SimpleNamespace(course=course, **vars(selection)))


@app.command(
    help="Download selected problems to local files",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def down(
    ctx: typer.Context,
    course: str = typer.Option(..., "--course", "-c", help="Moodle course ID or alias"),
    all_: bool = typer.Option(False, "--all", "-A", help="Select all VPL activities"),
    ids: list[int] | None = typer.Option(None, "--id", "-I", help="Activity ID (repeat for multiple IDs)"),
    labels: list[str] | None = typer.Option(None, "--label", "-L", help="Activity label (repeat for multiple labels)"),
    sections: list[int] | None = typer.Option(None, "--section", "-S", help="Section index (repeat for multiple sections)"),
    output: str = typer.Option(".", "--output", "-o", help="Output directory"),
) -> None:
    selection = _selection(all_, ids, labels, sections, ctx.args)
    Actions.down(SimpleNamespace(course=course, output=output, **vars(selection)))


app.command("update", cls=UpdateCommand, context_settings={"allow_extra_args": True})(update)
app.command("resume")(resume)


@section_app.command("add", help="Add a section at the end of the course")
def section_add(
    course: str = typer.Option(..., "--course", "-c", help="Moodle course ID or alias"),
    name: str | None = typer.Option(None, "--name", "-n", help="Optional section name"),
) -> None:
    manager = CourseSections(course)
    try:
        index, section_name = manager.add(name)
        typer.echo(f"Added section {index}: {section_name}")
    finally:
        manager.close()


@section_app.command("rename", help="Rename a course section")
def section_rename(
    course: str = typer.Option(..., "--course", "-c", help="Moodle course ID or alias"),
    index: int = typer.Option(..., "--index", "-s", min=0, help="Zero-based section index"),
    name: str = typer.Option(..., "--name", "-n", help="New section name"),
) -> None:
    manager = CourseSections(course)
    try:
        manager.rename(index, name)
        typer.echo(f"Renamed section {index} to: {name.strip()}")
    finally:
        manager.close()


@section_app.command("remove", help="Remove a section and its activities")
def section_remove(
    course: str = typer.Option(..., "--course", "-c", help="Moodle course ID or alias"),
    index: int = typer.Option(..., "--index", "-s", min=0, help="Zero-based section index"),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt"),
) -> None:
    manager = CourseSections(course)
    try:
        _, section_name = manager.section_info(index)
        if not yes:
            typer.confirm(
                f'Remove section {index} "{section_name}" and permanently delete all activities inside it?',
                abort=True,
            )
        manager.remove(index)
        typer.echo(f"Removed section {index}: {section_name}")
    finally:
        manager.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
